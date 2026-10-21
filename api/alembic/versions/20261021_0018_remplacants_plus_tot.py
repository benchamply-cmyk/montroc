"""Remplaçants plus tôt : après un refus, les partenaires lâchés reçoivent une autre boucle dans l'heure.

Revision ID: 0018
Revises: 0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | Sequence[str] | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("echanges", sa.Column("remplacement", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("echanges", sa.Column("remplacants_cherches_le", sa.DateTime(timezone=True), nullable=True))
    op.add_column("grands_trocs", sa.Column("nb_objets_remplaces", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("grands_trocs", "nb_objets_remplaces")
    op.drop_column("echanges", "remplacants_cherches_le")
    op.drop_column("echanges", "remplacement")
