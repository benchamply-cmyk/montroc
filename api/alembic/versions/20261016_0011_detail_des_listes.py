"""« Je propose » / « Je demande » en détail : sous-catégories, caractéristiques et description libre.

Revision ID: 0011
Revises: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("objets", "souhaits"):
        op.add_column(table, sa.Column("sous_categorie_slug", sa.String(length=50), nullable=True))
        op.add_column(
            table,
            sa.Column("caracteristiques", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        )
    op.add_column("souhaits", sa.Column("precisions", sa.Text(), nullable=True))
    op.create_check_constraint(
        op.f("ck_souhaits_sous_categorie_d_une_categorie"),
        "souhaits",
        "sous_categorie_slug IS NULL OR categorie_slug IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_souhaits_sous_categorie_d_une_categorie"), "souhaits", type_="check")
    op.drop_column("souhaits", "precisions")
    for table in ("objets", "souhaits"):
        op.drop_column(table, "caracteristiques")
        op.drop_column(table, "sous_categorie_slug")
