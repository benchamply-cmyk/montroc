"""Téléphone portable facultatif, pour prévenir par SMS quand une boucle est proposée.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("utilisateurs", sa.Column("telephone", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("utilisateurs", "telephone")
