"""Troc & Services : catégorie « services », profils pro certifiés, négociations et contrats.

Un service professionnel s'échange comme un objet (catégorie ``services``, une sous-catégorie par métier) : il n'a
pas d'état d'usure, seulement une photo. Les profils pro, vérifiés par la modération, permettent de proposer un
service ; les négociations (conversation, conditions) aboutissent à un contrat généré par TopTroc.

Revision ID: 0023
Revises: 0022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023"
down_revision: str | Sequence[str] | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTRAINTE = "ck_objets_photo_et_etat_si_disponible"
categories = sa.table("categories", sa.column("slug", sa.String), sa.column("libelle", sa.String))


def upgrade() -> None:
    op.create_table(
        "profils_pro",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("utilisateur_id", sa.Integer(), nullable=False),
        sa.Column("metier", sa.String(length=50), nullable=False),
        sa.Column("nom_commercial", sa.String(length=120), nullable=False),
        sa.Column("siret", sa.String(length=14), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("experience_annees", sa.Integer(), server_default="0", nullable=False),
        sa.Column("zone_intervention", sa.String(length=120), nullable=True),
        sa.Column("assurance", sa.String(length=200), nullable=True),
        sa.Column("qualifications", sa.String(length=300), nullable=True),
        sa.Column("justificatifs", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column(
            "statut",
            sa.Enum(
                "en_attente",
                "certifie",
                "refuse",
                name="statut_profil_pro",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            server_default="en_attente",
            nullable=False,
        ),
        sa.Column("motif", sa.Text(), nullable=True),
        sa.Column("certifie_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("certifie_par_id", sa.Integer(), nullable=True),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("siret ~ '^[0-9]{14}$'", name=op.f("ck_profils_pro_siret_14_chiffres")),
        sa.CheckConstraint(
            "statut <> 'certifie' OR certifie_le IS NOT NULL", name=op.f("ck_profils_pro_date_de_certification")
        ),
        sa.CheckConstraint(
            "experience_annees >= 0 AND experience_annees <= 60", name=op.f("ck_profils_pro_experience_plausible")
        ),
        sa.ForeignKeyConstraint(
            ["certifie_par_id"],
            ["utilisateurs.id"],
            name=op.f("fk_profils_pro_certifie_par_id_utilisateurs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["utilisateur_id"],
            ["utilisateurs.id"],
            name=op.f("fk_profils_pro_utilisateur_id_utilisateurs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profils_pro")),
        sa.UniqueConstraint("utilisateur_id", "metier", name="uq_profils_pro_utilisateur_metier"),
    )
    op.create_index(op.f("ix_profils_pro_statut"), "profils_pro", ["statut"], unique=False)
    op.create_index(op.f("ix_profils_pro_utilisateur_id"), "profils_pro", ["utilisateur_id"], unique=False)
    op.create_table(
        "negociations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiateur_id", sa.Integer(), nullable=False),
        sa.Column("destinataire_id", sa.Integer(), nullable=False),
        sa.Column("objet_id", sa.Integer(), nullable=False),
        sa.Column("contreparties", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column(
            "statut",
            sa.Enum(
                "ouverte",
                "accord_propose",
                "conclue",
                "annulee",
                name="statut_negociation",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            server_default="ouverte",
            nullable=False,
        ),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("accord_propose_par_id", sa.Integer(), nullable=True),
        sa.Column("mis_a_jour_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("initiateur_id <> destinataire_id", name=op.f("ck_negociations_deux_membres")),
        sa.ForeignKeyConstraint(
            ["accord_propose_par_id"],
            ["utilisateurs.id"],
            name=op.f("fk_negociations_accord_propose_par_id_utilisateurs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["destinataire_id"],
            ["utilisateurs.id"],
            name=op.f("fk_negociations_destinataire_id_utilisateurs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["initiateur_id"],
            ["utilisateurs.id"],
            name=op.f("fk_negociations_initiateur_id_utilisateurs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["objet_id"], ["objets.id"], name=op.f("fk_negociations_objet_id_objets"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_negociations")),
    )
    op.create_index(op.f("ix_negociations_destinataire_id"), "negociations", ["destinataire_id"], unique=False)
    op.create_index(op.f("ix_negociations_initiateur_id"), "negociations", ["initiateur_id"], unique=False)
    op.create_index(op.f("ix_negociations_objet_id"), "negociations", ["objet_id"], unique=False)
    op.create_index(op.f("ix_negociations_statut"), "negociations", ["statut"], unique=False)
    op.create_table(
        "contrats_service",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("negociation_id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.String(length=20), nullable=False),
        sa.Column("texte", sa.Text(), nullable=False),
        sa.Column(
            "statut",
            sa.Enum(
                "en_cours",
                "realise",
                "annule",
                name="statut_contrat",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            server_default="en_cours",
            nullable=False,
        ),
        sa.Column("confirme_initiateur_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirme_destinataire_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["negociation_id"],
            ["negociations.id"],
            name=op.f("fk_contrats_service_negociation_id_negociations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contrats_service")),
        sa.UniqueConstraint("negociation_id", name=op.f("uq_contrats_service_negociation_id")),
        sa.UniqueConstraint("numero", name=op.f("uq_contrats_service_numero")),
    )
    op.create_index(op.f("ix_contrats_service_statut"), "contrats_service", ["statut"], unique=False)
    op.create_table(
        "messages_negociation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("negociation_id", sa.Integer(), nullable=False),
        sa.Column("auteur_id", sa.Integer(), nullable=True),
        sa.Column("texte", sa.Text(), nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(trim(texte)) > 0", name=op.f("ck_messages_negociation_texte_non_vide")),
        sa.ForeignKeyConstraint(
            ["auteur_id"],
            ["utilisateurs.id"],
            name=op.f("fk_messages_negociation_auteur_id_utilisateurs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["negociation_id"],
            ["negociations.id"],
            name=op.f("fk_messages_negociation_negociation_id_negociations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages_negociation")),
    )
    op.create_index(
        op.f("ix_messages_negociation_negociation_id"), "messages_negociation", ["negociation_id"], unique=False
    )

    # La migration 0012 crée les catégories de nomenclature.DETAIL telle qu'elle est : sur une base neuve, « services »
    # y est déjà.
    op.execute(
        "INSERT INTO categories (slug, libelle) VALUES ('services', 'Troc & Services') ON CONFLICT (slug) DO NOTHING"
    )
    op.drop_constraint(op.f(CONTRAINTE), "objets", type_="check")
    op.create_check_constraint(
        op.f(CONTRAINTE),
        "objets",
        "statut <> 'disponible' OR (photo_url IS NOT NULL AND (etat IS NOT NULL OR categorie_slug = 'services'))",
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_negociation_negociation_id"), table_name="messages_negociation")
    op.drop_table("messages_negociation")
    op.drop_index(op.f("ix_contrats_service_statut"), table_name="contrats_service")
    op.drop_table("contrats_service")
    op.drop_index(op.f("ix_negociations_statut"), table_name="negociations")
    op.drop_index(op.f("ix_negociations_objet_id"), table_name="negociations")
    op.drop_index(op.f("ix_negociations_initiateur_id"), table_name="negociations")
    op.drop_index(op.f("ix_negociations_destinataire_id"), table_name="negociations")
    op.drop_table("negociations")
    op.drop_index(op.f("ix_profils_pro_utilisateur_id"), table_name="profils_pro")
    op.drop_index(op.f("ix_profils_pro_statut"), table_name="profils_pro")
    op.drop_table("profils_pro")
    op.execute("DELETE FROM souhaits WHERE categorie_slug = 'services'")
    op.execute("DELETE FROM objets WHERE categorie_slug = 'services'")
    op.execute(categories.delete().where(categories.c.slug == "services"))
    op.drop_constraint(op.f(CONTRAINTE), "objets", type_="check")
    op.create_check_constraint(
        op.f(CONTRAINTE),
        "objets",
        "statut <> 'disponible' OR (photo_url IS NOT NULL AND etat IS NOT NULL)",
    )
