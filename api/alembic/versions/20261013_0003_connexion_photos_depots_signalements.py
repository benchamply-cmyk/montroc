"""Étape 1 : connexion par lien magique, photo et état des objets, dépôts, signalements.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUTS_OBJET = ("disponible", "reserve", "echange", "retire")


def _enum(nom: str, *valeurs: str) -> sa.Enum:
    return sa.Enum(*valeurs, name=nom, native_enum=False, create_constraint=True, length=20)


def _check_statut_objet(valeurs) -> None:
    op.drop_constraint(op.f("ck_objets_statut_objet"), "objets", type_="check")
    liste = ", ".join(f"'{v}'" for v in valeurs)
    op.create_check_constraint(op.f("ck_objets_statut_objet"), "objets", f"statut IN ({liste})")


def upgrade() -> None:
    op.create_table(
        "jetons_connexion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("empreinte", sa.String(length=64), nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expire_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("utilise_le", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jetons_connexion")),
        sa.UniqueConstraint("empreinte", name=op.f("uq_jetons_connexion_empreinte")),
    )
    op.create_index(op.f("ix_jetons_connexion_email"), "jetons_connexion", ["email"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("utilisateur_id", sa.Integer(), nullable=False),
        sa.Column("empreinte", sa.String(length=64), nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expire_le", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["utilisateur_id"],
            ["utilisateurs.id"],
            name=op.f("fk_sessions_utilisateur_id_utilisateurs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("empreinte", name=op.f("uq_sessions_empreinte")),
    )
    op.create_index(op.f("ix_sessions_utilisateur_id"), "sessions", ["utilisateur_id"], unique=False)

    op.create_table(
        "signalements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("objet_id", sa.Integer(), nullable=True),
        sa.Column("utilisateur_vise_id", sa.Integer(), nullable=True),
        sa.Column("auteur_id", sa.Integer(), nullable=True),
        sa.Column("email_contact", sa.String(length=254), nullable=True),
        sa.Column(
            "motif",
            _enum("motif_signalement", "illegal", "dangereux", "contrefacon", "arnaque", "inapproprie", "autre"),
            nullable=False,
        ),
        sa.Column("explication", sa.Text(), nullable=False),
        sa.Column(
            "statut", _enum("statut_signalement", "ouvert", "retenu", "rejete"), server_default="ouvert", nullable=False
        ),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("traite_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("traite_par_id", sa.Integer(), nullable=True),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(trim(explication)) >= 10", name=op.f("ck_signalements_explication_utile")),
        sa.ForeignKeyConstraint(
            ["auteur_id"], ["utilisateurs.id"], name=op.f("fk_signalements_auteur_id_utilisateurs"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["objet_id"], ["objets.id"], name=op.f("fk_signalements_objet_id_objets"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["traite_par_id"],
            ["utilisateurs.id"],
            name=op.f("fk_signalements_traite_par_id_utilisateurs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["utilisateur_vise_id"],
            ["utilisateurs.id"],
            name=op.f("fk_signalements_utilisateur_vise_id_utilisateurs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signalements")),
    )
    op.create_index(op.f("ix_signalements_objet_id"), "signalements", ["objet_id"], unique=False)
    op.create_index(op.f("ix_signalements_statut"), "signalements", ["statut"], unique=False)

    op.add_column("utilisateurs", sa.Column("suspendu_le", sa.DateTime(timezone=True), nullable=True))
    op.add_column("echanges", sa.Column("rappel_envoye_le", sa.DateTime(timezone=True), nullable=True))
    op.add_column("transferts", sa.Column("depose_le", sa.DateTime(timezone=True), nullable=True))
    # Les transferts déjà en base reçoivent un code au hasard, puis la colonne devient obligatoire.
    op.add_column("transferts", sa.Column("code_retrait", sa.String(length=12), nullable=True))
    op.execute("UPDATE transferts SET code_retrait = 'TRC-' || upper(substr(md5(random()::text), 1, 5))")
    op.alter_column("transferts", "code_retrait", nullable=False)

    op.add_column("objets", sa.Column("etat", _enum("etat_objet", "neuf", "tres_bon", "bon", "usage"), nullable=True))
    op.add_column("objets", sa.Column("photo_url", sa.String(length=500), nullable=True))
    op.add_column("objets", sa.Column("photo_id", sa.String(length=200), nullable=True))
    _check_statut_objet((*STATUTS_OBJET, "modere"))
    # Photo et état deviennent obligatoires : les objets publiés sans sont retirés, leur propriétaire
    # pourra les compléter puis les remettre en ligne.
    op.execute(
        "UPDATE objets SET statut = 'retire' WHERE statut = 'disponible' AND (photo_url IS NULL OR etat IS NULL)"
    )
    op.create_check_constraint(
        op.f("ck_objets_photo_et_etat_si_disponible"),
        "objets",
        "statut <> 'disponible' OR (photo_url IS NOT NULL AND etat IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_objets_photo_et_etat_si_disponible"), "objets", type_="check")
    op.execute("UPDATE objets SET statut = 'retire' WHERE statut = 'modere'")
    _check_statut_objet(STATUTS_OBJET)
    op.drop_column("objets", "photo_id")
    op.drop_column("objets", "photo_url")
    op.drop_column("objets", "etat")
    op.drop_column("transferts", "code_retrait")
    op.drop_column("transferts", "depose_le")
    op.drop_column("echanges", "rappel_envoye_le")
    op.drop_column("utilisateurs", "suspendu_le")
    op.drop_index(op.f("ix_signalements_statut"), table_name="signalements")
    op.drop_index(op.f("ix_signalements_objet_id"), table_name="signalements")
    op.drop_table("signalements")
    op.drop_index(op.f("ix_sessions_utilisateur_id"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_index(op.f("ix_jetons_connexion_email"), table_name="jetons_connexion")
    op.drop_table("jetons_connexion")
