"""Feature Flag engine : l'état choisi de chaque fonctionnalité (Match, Grand Troc…).

Revision ID: 0009
Revises: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fonctionnalites",
        sa.Column("cle", sa.String(length=50), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("modifie_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("modifie_par", sa.String(length=320), nullable=False),
        sa.PrimaryKeyConstraint("cle", name=op.f("pk_fonctionnalites")),
    )


def downgrade() -> None:
    op.drop_table("fonctionnalites")
