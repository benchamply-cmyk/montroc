"""Schéma de la base de données.

Les règles métier qui doivent tenir quoi qu'il arrive sont écrites dans la base
elle-même (clés étrangères, unicité, contraintes CHECK), pas seulement dans le
code Python : une erreur de programmation ne peut pas créer de données incohérentes.
Toute modification de ce fichier s'accompagne d'une migration Alembic
(``alembic revision --autogenerate -m "..."``).
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Noms de contraintes stables : indispensable pour que les migrations Alembic restent lisibles.
CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENTION)


def _enum(cls: type[enum.Enum], nom: str) -> Enum:
    # Stocké en texte + contrainte CHECK : ajouter une valeur ne demande pas d'ALTER TYPE.
    return Enum(
        cls,
        name=nom,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda e: [m.value for m in e],
    )


class StatutObjet(enum.StrEnum):
    disponible = "disponible"  # visible et proposable dans un échange
    reserve = "reserve"  # engagé dans un échange en cours
    echange = "echange"  # parti : l'échange est terminé
    retire = "retire"  # retiré par son propriétaire


class StatutEchange(enum.StrEnum):
    propose = "propose"  # en attente des réponses (48 h)
    accepte = "accepte"  # tout le monde a dit oui : dépôts en cours
    annule = "annule"  # un refus ou un délai dépassé
    termine = "termine"  # objets remis


class Reponse(enum.StrEnum):
    en_attente = "en_attente"
    acceptee = "acceptee"
    refusee = "refusee"


class Horodatage:
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Categorie(Base):
    """Catégories d'objets (poussette, siège auto…). Le slug sert d'identifiant lisible."""

    __tablename__ = "categories"

    slug: Mapped[str] = mapped_column(String(50), primary_key=True)
    libelle: Mapped[str] = mapped_column(String(100))

    __table_args__ = (CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="slug_format"),)


class Utilisateur(Horodatage, Base):
    __tablename__ = "utilisateurs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254))
    pseudo: Mapped[str] = mapped_column(String(40), unique=True)
    zone: Mapped[str | None] = mapped_column(String(80))  # ville au lancement
    fiabilite: Mapped[float] = mapped_column(Float, default=1.0, server_default="1")

    objets: Mapped[list[Objet]] = relationship(back_populates="proprietaire", cascade="all, delete-orphan")
    souhaits: Mapped[list[Souhait]] = relationship(
        back_populates="utilisateur", cascade="all, delete-orphan", order_by="Souhait.rang"
    )

    __table_args__ = (
        CheckConstraint("fiabilite >= 0 AND fiabilite <= 1", name="fiabilite_0_1"),
        # E-mail unique sans tenir compte de la casse.
        Index("uq_utilisateurs_email_lower", func.lower(email), unique=True),
    )


class Objet(Horodatage, Base):
    __tablename__ = "objets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proprietaire_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True)
    categorie_slug: Mapped[str] = mapped_column(ForeignKey("categories.slug"), index=True)
    titre: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    statut: Mapped[StatutObjet] = mapped_column(
        _enum(StatutObjet, "statut_objet"),
        default=StatutObjet.disponible,
        server_default=StatutObjet.disponible.value,
        index=True,
    )

    proprietaire: Mapped[Utilisateur] = relationship(back_populates="objets")

    __table_args__ = (CheckConstraint("length(trim(titre)) > 0", name="titre_non_vide"),)


class Souhait(Horodatage, Base):
    """Ce qui serait utile à un utilisateur : une catégorie entière, ou un objet précis."""

    __tablename__ = "souhaits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True)
    categorie_slug: Mapped[str | None] = mapped_column(ForeignKey("categories.slug"))
    objet_id: Mapped[int | None] = mapped_column(ForeignKey("objets.id", ondelete="CASCADE"))
    rang: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    quantite: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    acceptation_auto: Mapped[bool] = mapped_column(default=False, server_default="false")

    utilisateur: Mapped[Utilisateur] = relationship(back_populates="souhaits")

    __table_args__ = (
        CheckConstraint("(categorie_slug IS NULL) <> (objet_id IS NULL)", name="categorie_ou_objet"),
        CheckConstraint("rang >= 1", name="rang_positif"),
        CheckConstraint("quantite >= 1", name="quantite_positive"),
    )


class Echange(Horodatage, Base):
    """Une boucle proposée : chaque participant donne un objet au suivant."""

    __tablename__ = "echanges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    statut: Mapped[StatutEchange] = mapped_column(
        _enum(StatutEchange, "statut_echange"),
        default=StatutEchange.propose,
        server_default=StatutEchange.propose.value,
        index=True,
    )
    proba_reussite: Mapped[float] = mapped_column(Float)
    expire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    transferts: Mapped[list[Transfert]] = relationship(
        back_populates="echange", cascade="all, delete-orphan", order_by="Transfert.position"
    )

    __table_args__ = (CheckConstraint("proba_reussite >= 0 AND proba_reussite <= 1", name="proba_0_1"),)


class Transfert(Base):
    """Une étape d'une boucle : ``donneur`` remet ``objet`` à ``receveur``, qui accepte ou refuse."""

    __tablename__ = "transferts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    echange_id: Mapped[int] = mapped_column(ForeignKey("echanges.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    donneur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True)
    receveur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True)
    objet_id: Mapped[int] = mapped_column(ForeignKey("objets.id", ondelete="CASCADE"), index=True)
    reponse: Mapped[Reponse] = mapped_column(
        _enum(Reponse, "reponse"), default=Reponse.en_attente, server_default=Reponse.en_attente.value
    )
    repondu_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    echange: Mapped[Echange] = relationship(back_populates="transferts")
    objet: Mapped[Objet] = relationship()

    __table_args__ = (
        UniqueConstraint("echange_id", "position", name="uq_transferts_echange_position"),
        UniqueConstraint("echange_id", "objet_id", name="uq_transferts_echange_objet"),
        CheckConstraint("donneur_id <> receveur_id", name="donneur_different_receveur"),
        CheckConstraint("position >= 0 AND position < 3", name="boucle_max_3"),
    )
