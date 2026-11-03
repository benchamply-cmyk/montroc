"""TopTroc Pro : profil professionnel des membres (secteur, entreprise, SIRET) et trois catégories réservées.

Les catégories Pro (bâtiment, auto-moto, alimentaire) ne sont ouvertes qu'aux comptes Pro de leur secteur ;
leurs sous-catégories et caractéristiques sont dans nomenclature.DETAIL_PRO.

Revision ID: 0023
Revises: 0022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | Sequence[str] | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Libellés figés ici : la nomenclature peut les renommer ensuite sans toucher à cette migration.
CATEGORIES = {
    "pro-batiment": "Pro · Bâtiment : outillage et matériaux",
    "pro-auto-moto": "Pro · Auto-moto : pièces et atelier",
    "pro-alimentaire": "Pro · Alimentaire : produits et matériel",
}


def upgrade() -> None:
    op.add_column("utilisateurs", sa.Column("pro_secteur", sa.String(length=20), nullable=True))
    op.add_column("utilisateurs", sa.Column("pro_raison_sociale", sa.String(length=120), nullable=True))
    op.add_column("utilisateurs", sa.Column("pro_siret", sa.String(length=14), nullable=True))
    op.add_column("utilisateurs", sa.Column("pro_metier", sa.String(length=80), nullable=True))
    op.add_column("utilisateurs", sa.Column("pro_verifie_le", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        op.f("ck_utilisateurs_profil_pro_complet"),
        "utilisateurs",
        "pro_secteur IS NULL OR (pro_secteur IN ('batiment', 'auto_moto', 'alimentaire') "
        "AND pro_raison_sociale IS NOT NULL AND pro_siret ~ '^[0-9]{14}$')",
    )
    categories = sa.table("categories", sa.column("slug", sa.String), sa.column("libelle", sa.String))
    conn = op.get_bind()
    existantes = set(conn.scalars(sa.select(categories.c.slug)))
    for slug, libelle in CATEGORIES.items():
        if slug not in existantes:
            conn.execute(categories.insert().values(slug=slug, libelle=libelle))


def downgrade() -> None:
    # Les objets et demandes des catégories Pro disparaissent avec elles (et leurs échanges, en cascade).
    conn = op.get_bind()
    slugs = tuple(CATEGORIES)
    for table in ("souhaits", "objets"):
        conn.execute(
            sa.text(f"DELETE FROM {table} WHERE categorie_slug IN :s").bindparams(sa.bindparam("s", expanding=True)),
            {"s": slugs},
        )
    conn.execute(
        sa.text("DELETE FROM categories WHERE slug IN :s").bindparams(sa.bindparam("s", expanding=True)), {"s": slugs}
    )
    op.drop_constraint(op.f("ck_utilisateurs_profil_pro_complet"), "utilisateurs", type_="check")
    for colonne in ("pro_verifie_le", "pro_metier", "pro_siret", "pro_raison_sociale", "pro_secteur"):
        op.drop_column("utilisateurs", colonne)
