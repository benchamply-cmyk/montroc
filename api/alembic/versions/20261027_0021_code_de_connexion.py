"""Code de connexion à 6 chiffres, envoyé avec le lien magique.

Revision ID: 0021
Revises: 0020
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str | Sequence[str] | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jetons_connexion", sa.Column("code_empreinte", sa.String(length=64), nullable=True))
    op.add_column("jetons_connexion", sa.Column("essais_code", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("jetons_connexion", "essais_code")
    op.drop_column("jetons_connexion", "code_empreinte")
