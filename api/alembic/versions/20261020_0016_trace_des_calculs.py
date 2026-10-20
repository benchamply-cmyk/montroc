"""Trace des calculs du Grand Troc : moteur utilisé, longueur retenue, statuts de CP-SAT.

``grands_trocs.calcul`` pour le dimanche, ``grands_trocs.calcul_repechage`` pour le mardi.

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | Sequence[str] | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "grands_trocs",
        sa.Column("calcul", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
    )
    op.add_column("grands_trocs", sa.Column("calcul_repechage", postgresql.JSONB(astext_type=sa.Text())))


def downgrade() -> None:
    op.drop_column("grands_trocs", "calcul_repechage")
    op.drop_column("grands_trocs", "calcul")
