"""Étiquettes de colis TopTroc : le donneur paie l'envoi à TopTroc (tarif négocié + frais de service).

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


def upgrade() -> None:
    op.add_column("transferts", sa.Column("envoi_paye_le", sa.DateTime(timezone=True), nullable=True))
    op.add_column("transferts", sa.Column("envoi_format", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("transferts", "envoi_format")
    op.drop_column("transferts", "envoi_paye_le")
