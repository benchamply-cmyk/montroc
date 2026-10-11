"""Catégories de base proposées au lancement.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATEGORIES = [
    ("poussette", "Poussette"),
    ("siege-auto", "Siège auto"),
    ("lit-bebe", "Lit bébé"),
    ("vetements-enfant", "Vêtements enfant"),
    ("jouets", "Jouets"),
    ("livres", "Livres"),
    ("jeux-de-societe", "Jeux de société"),
    ("velo", "Vélo"),
    ("sport", "Sport et plein air"),
    ("outillage", "Outillage"),
    ("electromenager", "Électroménager"),
    ("meubles", "Meubles"),
    ("deco", "Décoration"),
    ("multimedia", "Multimédia"),
]

categories = sa.table("categories", sa.column("slug", sa.String), sa.column("libelle", sa.String))


def upgrade() -> None:
    op.bulk_insert(categories, [{"slug": s, "libelle": libelle} for s, libelle in CATEGORIES])


def downgrade() -> None:
    op.execute(categories.delete().where(categories.c.slug.in_([s for s, _ in CATEGORIES])))
