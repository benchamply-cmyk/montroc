"""Business model V2 : zones d'intérêt et localisation des objets, colis, Troc Premium, avant-première.

Revision ID: 0019
Revises: 0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: str | Sequence[str] | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "utilisateurs",
        sa.Column("zones_interet", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
    )
    op.add_column("utilisateurs", sa.Column("toute_la_france", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("utilisateurs", sa.Column("formule", sa.String(length=20), nullable=True))
    op.add_column("utilisateurs", sa.Column("premium_jusqu_au", sa.DateTime(timezone=True), nullable=True))
    op.add_column("utilisateurs", sa.Column("essai_premium_le", sa.DateTime(timezone=True), nullable=True))
    op.add_column("utilisateurs", sa.Column("payeur_famille_id", sa.Integer(), nullable=True))
    op.add_column("utilisateurs", sa.Column("stripe_client", sa.String(length=100), nullable=True))
    op.add_column("utilisateurs", sa.Column("verifie_le", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        op.f("fk_utilisateurs_payeur_famille_id_utilisateurs"),
        "utilisateurs",
        "utilisateurs",
        ["payeur_famille_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_utilisateurs_stripe_client"), "utilisateurs", ["stripe_client"])
    op.create_check_constraint(
        op.f("ck_utilisateurs_formule_connue"),
        "utilisateurs",
        "formule IS NULL OR formule IN ('essentiel', 'plus', 'famille', 'pro', 'pass')",
    )
    op.create_check_constraint(
        op.f("ck_utilisateurs_pas_sa_propre_famille"),
        "utilisateurs",
        "payeur_famille_id IS NULL OR payeur_famille_id <> id",
    )

    op.add_column("objets", sa.Column("lieu", sa.String(length=120), nullable=True))
    op.add_column("objets", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("objets", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("objets", sa.Column("format_colis", sa.String(length=20), nullable=True))
    op.create_check_constraint(
        op.f("ck_objets_position_complete"), "objets", "(latitude IS NULL) = (longitude IS NULL)"
    )
    op.create_check_constraint(
        op.f("ck_objets_position_valide"),
        "objets",
        "latitude IS NULL OR (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)",
    )

    op.add_column("grands_trocs", sa.Column("annonce_le", sa.DateTime(timezone=True), nullable=True))
    # Les Grands Trocs passés ont été annoncés à leur création.
    op.execute("UPDATE grands_trocs SET annonce_le = cree_le")

    op.add_column("transferts", sa.Column("mode", sa.String(length=20), server_default="main_propre", nullable=False))
    op.add_column("transferts", sa.Column("transporteur", sa.String(length=40), nullable=True))
    op.add_column("transferts", sa.Column("numero_suivi", sa.String(length=60), nullable=True))
    op.add_column("transferts", sa.Column("adresse_livraison", sa.String(length=300), nullable=True))
    op.add_column("transferts", sa.Column("garantie", sa.Boolean(), server_default="false", nullable=False))
    op.create_check_constraint(
        op.f("ck_transferts_mode_connu"), "transferts", "mode IN ('main_propre', 'colis', 'point_relais')"
    )
    # Les échanges d'avant passaient par le point de dépôt.
    op.execute("UPDATE transferts SET mode = 'point_relais'")

    op.add_column("avis", sa.Column("super", sa.Boolean(), server_default="false", nullable=False))
    op.create_check_constraint(op.f("ck_avis_super_si_aime"), "avis", "aime OR NOT super")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_avis_super_si_aime"), "avis", type_="check")
    op.drop_column("avis", "super")
    op.drop_constraint(op.f("ck_transferts_mode_connu"), "transferts", type_="check")
    for colonne in ("garantie", "adresse_livraison", "numero_suivi", "transporteur", "mode"):
        op.drop_column("transferts", colonne)
    op.drop_column("grands_trocs", "annonce_le")
    op.drop_constraint(op.f("ck_objets_position_valide"), "objets", type_="check")
    op.drop_constraint(op.f("ck_objets_position_complete"), "objets", type_="check")
    for colonne in ("format_colis", "longitude", "latitude", "lieu"):
        op.drop_column("objets", colonne)
    op.drop_constraint(op.f("ck_utilisateurs_pas_sa_propre_famille"), "utilisateurs", type_="check")
    op.drop_constraint(op.f("ck_utilisateurs_formule_connue"), "utilisateurs", type_="check")
    op.drop_index(op.f("ix_utilisateurs_stripe_client"), table_name="utilisateurs")
    op.drop_constraint(op.f("fk_utilisateurs_payeur_famille_id_utilisateurs"), "utilisateurs", type_="foreignkey")
    for colonne in (
        "verifie_le",
        "stripe_client",
        "payeur_famille_id",
        "essai_premium_le",
        "premium_jusqu_au",
        "formule",
        "toute_la_france",
        "zones_interet",
    ):
        op.drop_column("utilisateurs", colonne)
