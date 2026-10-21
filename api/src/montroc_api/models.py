"""Schéma de la base de données.

Les règles métier qui doivent tenir quoi qu'il arrive sont écrites dans la base
elle-même (clés étrangères, unicité, contraintes CHECK), pas seulement dans le
code Python : une erreur de programmation ne peut pas créer de données incohérentes.
Toute modification de ce fichier s'accompagne d'une migration Alembic
(``alembic revision --autogenerate -m "..."``).
"""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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
from sqlalchemy.dialects.postgresql import JSONB
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
    modere = "modere"  # retiré par la modération : le propriétaire ne peut pas le remettre en ligne


class EtatObjet(enum.StrEnum):
    """Du meilleur au moins bon : une demande peut fixer un état minimum (même ordre que le moteur)."""

    neuf = "neuf"
    comme_neuf = "comme_neuf"
    tres_bon = "tres_bon"
    bon = "bon"
    correct = "correct"  # anciennement « usagé, fonctionne »


class ModeRecherche(enum.StrEnum):
    precise = "precise"  # l'objet demandé, avec ses critères obligatoires
    flexible = "flexible"  # aussi les alternatives acceptées
    ouverte = "ouverte"  # tout objet des catégories d'intérêt (celle de la demande et celles des alternatives)


class StatutEchange(enum.StrEnum):
    propose = "propose"  # en attente des réponses (48 h)
    accepte = "accepte"  # tout le monde a dit oui : dépôts en cours (7 jours)
    annule = "annule"  # un refus ou un délai dépassé
    termine = "termine"  # tout est déposé : chacun récupère son objet


class Reponse(enum.StrEnum):
    en_attente = "en_attente"
    acceptee = "acceptee"
    refusee = "refusee"


class MotifSignalement(enum.StrEnum):
    illegal = "illegal"  # contenu ou objet illicite
    dangereux = "dangereux"  # produit dangereux ou rappelé
    contrefacon = "contrefacon"
    arnaque = "arnaque"
    inapproprie = "inapproprie"  # photo ou texte choquant
    autre = "autre"


class StatutSignalement(enum.StrEnum):
    ouvert = "ouvert"
    retenu = "retenu"  # contenu retiré ou compte suspendu
    rejete = "rejete"


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
    # Portable au format international (+33612345678), facultatif : SMS quand une boucle est proposée.
    # Jamais montré aux autres membres.
    telephone: Mapped[str | None] = mapped_column(String(16))
    fiabilite: Mapped[float] = mapped_column(Float, default=1.0, server_default="1")
    # Engagements tenus (objet déposé) et manqués (pas de réponse dans les 48 h, objet accepté non déposé) :
    # la fiabilité en découle (services.noter_engagement). Un refus n'est pas un manquement.
    engagements_tenus: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    engagements_manques: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Réponses données aux boucles du Grand Troc (hors « j'accepte d'office » et accords du Match) : le math trade
    # en tire la chance qu'il dise oui à la prochaine (services.acceptation).
    reponses_oui: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reponses_non: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Compte suspendu par la modération : plus de connexion, objets retirés des échanges.
    suspendu_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Mot de passe facultatif (empreinte scrypt, voir motdepasse.py) : sans lui, on se connecte par lien magique.
    # Après 5 essais faux, la connexion par mot de passe est bloquée 15 minutes (le lien magique reste possible).
    mot_de_passe: Mapped[str | None] = mapped_column(String(200))
    essais_mot_de_passe: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    bloque_jusqu_au: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    objets: Mapped[list[Objet]] = relationship(back_populates="proprietaire", cascade="all, delete-orphan")
    souhaits: Mapped[list[Souhait]] = relationship(
        back_populates="utilisateur", cascade="all, delete-orphan", order_by="Souhait.rang"
    )

    @property
    def a_un_mot_de_passe(self) -> bool:
        return self.mot_de_passe is not None

    __table_args__ = (
        CheckConstraint("fiabilite >= 0 AND fiabilite <= 1", name="fiabilite_0_1"),
        CheckConstraint("engagements_tenus >= 0 AND engagements_manques >= 0", name="engagements_positifs"),
        CheckConstraint("reponses_oui >= 0 AND reponses_non >= 0", name="reponses_positives"),
        # E-mail unique sans tenir compte de la casse.
        Index("uq_utilisateurs_email_lower", func.lower(email), unique=True),
    )


class Objet(Horodatage, Base):
    __tablename__ = "objets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proprietaire_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True)
    categorie_slug: Mapped[str] = mapped_column(ForeignKey("categories.slug"), index=True)
    # Sous-catégorie et caractéristiques (taille, âge, marque…) : voir nomenclature.py, qui les valide.
    sous_categorie_slug: Mapped[str | None] = mapped_column(String(50))
    caracteristiques: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, server_default="{}")
    titre: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    etat: Mapped[EtatObjet | None] = mapped_column(_enum(EtatObjet, "etat_objet"))
    # Photo hébergée chez Cloudinary : l'adresse publique et l'identifiant (pour la supprimer).
    photo_url: Mapped[str | None] = mapped_column(String(500))
    photo_id: Mapped[str | None] = mapped_column(String(200))
    # Annonce Vinted ou Leboncoin d'où l'objet a été recopié à la main (référence privée du propriétaire).
    annonce_origine: Mapped[str | None] = mapped_column(String(500))
    statut: Mapped[StatutObjet] = mapped_column(
        _enum(StatutObjet, "statut_objet"),
        default=StatutObjet.disponible,
        server_default=StatutObjet.disponible.value,
        index=True,
    )

    # « Je le donne contre… » (comme les listes par objet de BoardGameGeek) : des souhaits de son propriétaire.
    # Aucun : contre n'importe lequel de ses souhaits. ``contre_strict`` : seulement contre ceux-là ; sinon ce
    # n'est qu'une préférence, et l'objet peut partir contre un autre de ses souhaits.
    contre_strict: Mapped[bool] = mapped_column(default=False, server_default="false")
    # Modes d'échange possibles (nomenclature.MODES_ECHANGE) ; vide : tous.
    modes_echange: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")

    proprietaire: Mapped[Utilisateur] = relationship(back_populates="objets")
    contre: Mapped[list[Souhait]] = relationship(secondary="objets_contre", order_by="Souhait.id")

    @property
    def contre_souhait_ids(self) -> list[int]:
        return [s.id for s in self.contre]

    __table_args__ = (
        CheckConstraint("length(trim(titre)) > 0", name="titre_non_vide"),
        # Pas d'objet proposé à l'échange sans photo ni état (les objets d'avant cette règle ont été retirés).
        CheckConstraint(
            "statut <> 'disponible' OR (photo_url IS NOT NULL AND etat IS NOT NULL)", name="photo_et_etat_si_disponible"
        ),
    )


class Souhait(Horodatage, Base):
    """Ce qui serait utile à un utilisateur : une catégorie entière, ou un objet précis."""

    __tablename__ = "souhaits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True)
    categorie_slug: Mapped[str | None] = mapped_column(ForeignKey("categories.slug"))
    objet_id: Mapped[int | None] = mapped_column(ForeignKey("objets.id", ondelete="CASCADE"))
    # « Je demande » en détail : une sous-catégorie, des critères obligatoires (``caracteristiques`` : un objet
    # de la catégorie doit indiquer ces valeurs) et préférentiels (``preferences`` : ils améliorent l'échange
    # sans écarter d'objet), voir nomenclature.py, et une description libre de ce qui est cherché.
    sous_categorie_slug: Mapped[str | None] = mapped_column(String(50))
    caracteristiques: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, server_default="{}")
    preferences: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, server_default="{}")
    precisions: Mapped[str | None] = mapped_column(Text)
    etat_min: Mapped[EtatObjet | None] = mapped_column(_enum(EtatObjet, "etat_min"))
    mode_recherche: Mapped[ModeRecherche] = mapped_column(
        _enum(ModeRecherche, "mode_recherche"), default=ModeRecherche.flexible, server_default="flexible"
    )
    # Autres catégories ou sous-catégories acceptées : [{"categorie_slug": …, "sous_categorie_slug": … ou null}].
    alternatives: Mapped[list[dict]] = mapped_column(JSONB, default=list, server_default="[]")
    # Logistique : modes d'échange acceptés (vide : tous) et zones acceptées (vide : sa propre zone).
    modes_echange: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    zones: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    rang: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    quantite: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    acceptation_auto: Mapped[bool] = mapped_column(default=False, server_default="false")

    utilisateur: Mapped[Utilisateur] = relationship(back_populates="souhaits")

    __table_args__ = (
        CheckConstraint("(categorie_slug IS NULL) <> (objet_id IS NULL)", name="categorie_ou_objet"),
        CheckConstraint(
            "sous_categorie_slug IS NULL OR categorie_slug IS NOT NULL", name="sous_categorie_d_une_categorie"
        ),
        CheckConstraint("rang >= 1", name="rang_positif"),
        CheckConstraint("quantite >= 1", name="quantite_positive"),
    )


class ObjetContre(Base):
    """Un souhait contre lequel le propriétaire de l'objet accepte de le donner."""

    __tablename__ = "objets_contre"

    objet_id: Mapped[int] = mapped_column(ForeignKey("objets.id", ondelete="CASCADE"), primary_key=True)
    souhait_id: Mapped[int] = mapped_column(ForeignKey("souhaits.id", ondelete="CASCADE"), primary_key=True, index=True)


class GrandTroc(Horodatage, Base):
    """Un passage du Grand Troc du dimanche : le math trade lancé une fois par semaine sur tout le stock."""

    __tablename__ = "grands_trocs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Date du dimanche (heure de Paris) : unique, pour qu'une tâche relancée ne propose pas deux fois.
    jour: Mapped[date] = mapped_column(Date, unique=True)
    optimal: Mapped[bool] = mapped_column(Boolean)
    duree_s: Mapped[float] = mapped_column(Float)
    nb_boucles: Mapped[int] = mapped_column(Integer)
    nb_objets: Mapped[int] = mapped_column(Integer)
    nb_participants: Mapped[int] = mapped_column(Integer)
    # Repêchage du mardi 18 h : seconde passe sur ce qui s'est libéré (refus, absences de réponse).
    repeche_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    nb_objets_repeches: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Trace de chaque calcul (``services.trace_du_calcul``) : moteur utilisé (exact ou heuristique), longueur
    # de boucle retenue, statuts de CP-SAT, durée… Pour savoir si la production a basculé en mode dégradé.
    calcul: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    calcul_repechage: Mapped[dict | None] = mapped_column(JSONB)

    echanges: Mapped[list[Echange]] = relationship(back_populates="grand_troc")


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
    # Fin du délai en cours : réponses (48 h) tant que « propose », dépôts (dans la semaine) une fois « accepte ».
    expire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rappel_envoye_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Accord 1 à 1 conclu après un match (coups de cœur réciproques), à tout moment de la semaine.
    par_match: Mapped[bool] = mapped_column(default=False, server_default="false")
    # Le Grand Troc qui a trouvé cette boucle (vide pour une boucle choisie à la demande ou un accord de match).
    grand_troc_id: Mapped[int | None] = mapped_column(ForeignKey("grands_trocs.id", ondelete="SET NULL"), index=True)
    grand_troc: Mapped[GrandTroc | None] = relationship(back_populates="echanges")

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
    # Le souhait du receveur que ce transfert sert : tant que l'échange n'est pas annulé, il compte dans la
    # quantité du souhait (une poussette reçue n'en appelle pas une deuxième). Vide pour un « J'aime » du Match.
    souhait_id: Mapped[int | None] = mapped_column(ForeignKey("souhaits.id", ondelete="SET NULL"), index=True)
    reponse: Mapped[Reponse] = mapped_column(
        _enum(Reponse, "reponse"), default=Reponse.en_attente, server_default=Reponse.en_attente.value
    )
    repondu_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Le donneur a déposé l'objet au point de dépôt, emballé et marqué de ce code ; le receveur le
    # présente pour le récupérer.
    depose_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    code_retrait: Mapped[str] = mapped_column(String(12))

    echange: Mapped[Echange] = relationship(back_populates="transferts")
    objet: Mapped[Objet] = relationship()
    donneur: Mapped[Utilisateur] = relationship(foreign_keys=[donneur_id])
    receveur: Mapped[Utilisateur] = relationship(foreign_keys=[receveur_id])

    __table_args__ = (
        UniqueConstraint("echange_id", "position", name="uq_transferts_echange_position"),
        UniqueConstraint("echange_id", "objet_id", name="uq_transferts_echange_objet"),
        CheckConstraint("donneur_id <> receveur_id", name="donneur_different_receveur"),
        # Jusqu'à 6 personnes, la limite du moteur (troc_echanges.boucles.LONGUEUR_MAX_ABSOLUE).
        CheckConstraint("position >= 0 AND position < 6", name="boucle_max_6"),
    )


class Avis(Horodatage, Base):
    """Le Match : « J'aime » ou « Non merci » sur un objet d'un autre membre, depuis le carrousel.

    Deux personnes qui aiment chacune un objet de l'autre ont un match : elles peuvent conclure un accord
    1 à 1 tout de suite. Au Grand Troc, un « J'aime » compte comme un souhait et un « Non merci » comme un refus.
    """

    __tablename__ = "avis"

    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"), primary_key=True)
    objet_id: Mapped[int] = mapped_column(ForeignKey("objets.id", ondelete="CASCADE"), primary_key=True, index=True)
    aime: Mapped[bool] = mapped_column(Boolean)

    objet: Mapped[Objet] = relationship()


class JetonConnexion(Base):
    """Lien magique envoyé par e-mail : à usage unique, valable 20 minutes. Seule l'empreinte est stockée."""

    __tablename__ = "jetons_connexion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    empreinte: Mapped[str] = mapped_column(String(64), unique=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    utilise_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SessionUtilisateur(Base):
    """Session ouverte par un lien magique ; le navigateur garde le jeton, la base son empreinte."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"), index=True)
    empreinte: Mapped[str] = mapped_column(String(64), unique=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    utilisateur: Mapped[Utilisateur] = relationship()


class Signalement(Horodatage, Base):
    """Notification d'un contenu illicite ou contraire aux règles (DSA, art. 16), et la décision prise."""

    __tablename__ = "signalements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    objet_id: Mapped[int | None] = mapped_column(ForeignKey("objets.id", ondelete="SET NULL"), index=True)
    utilisateur_vise_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"))
    auteur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"))
    email_contact: Mapped[str | None] = mapped_column(String(254))  # pour un auteur sans compte
    motif: Mapped[MotifSignalement] = mapped_column(_enum(MotifSignalement, "motif_signalement"))
    explication: Mapped[str] = mapped_column(Text)
    statut: Mapped[StatutSignalement] = mapped_column(
        _enum(StatutSignalement, "statut_signalement"),
        default=StatutSignalement.ouvert,
        server_default=StatutSignalement.ouvert.value,
        index=True,
    )
    decision: Mapped[str | None] = mapped_column(Text)  # motivation envoyée aux personnes concernées
    traite_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    traite_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"))

    objet: Mapped[Objet | None] = relationship()
    utilisateur_vise: Mapped[Utilisateur | None] = relationship(foreign_keys=[utilisateur_vise_id])
    auteur: Mapped[Utilisateur | None] = relationship(foreign_keys=[auteur_id])

    # La cible et l'auteur sont vérifiés par l'API, pas par la base : un signalement survit (pour
    # l'historique de modération) à la suppression de l'objet ou du compte, qui met ces liens à NULL.
    __table_args__ = (CheckConstraint("length(trim(explication)) >= 10", name="explication_utile"),)
