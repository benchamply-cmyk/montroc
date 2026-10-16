"""Mot de passe facultatif, en plus du lien magique, et blocage après 5 essais faux.

Revision ID: 0010
Revises: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("utilisateurs", sa.Column("mot_de_passe", sa.String(length=200), nullable=True))
    op.add_column("utilisateurs", sa.Column("essais_mot_de_passe", sa.Integer(), server_default="0", nullable=False))
    op.add_column("utilisateurs", sa.Column("bloque_jusqu_au", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("utilisateurs", "bloque_jusqu_au")
    op.drop_column("utilisateurs", "essais_mot_de_passe")
    op.drop_column("utilisateurs", "mot_de_passe")
