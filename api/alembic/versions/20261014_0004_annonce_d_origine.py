"""Objets recopiés d'une annonce Vinted ou Leboncoin : lien de l'annonce d'origine.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("objets", sa.Column("annonce_origine", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("objets", "annonce_origine")
