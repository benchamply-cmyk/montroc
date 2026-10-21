"""Réponses de chaque membre aux boucles proposées : son taux de « oui » remplace les 70 % communs.

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | Sequence[str] | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("utilisateurs", sa.Column("reponses_oui", sa.Integer(), server_default="0", nullable=False))
    op.add_column("utilisateurs", sa.Column("reponses_non", sa.Integer(), server_default="0", nullable=False))
    op.create_check_constraint(
        op.f("ck_utilisateurs_reponses_positives"), "utilisateurs", "reponses_oui >= 0 AND reponses_non >= 0"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_utilisateurs_reponses_positives"), "utilisateurs", type_="check")
    op.drop_column("utilisateurs", "reponses_non")
    op.drop_column("utilisateurs", "reponses_oui")
