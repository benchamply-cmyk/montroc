"""Auteur d'une proposition d'échange (quota de propositions en attente des comptes gratuits).

Revision ID: 0025
Revises: 0024
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | Sequence[str] | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("echanges", sa.Column("auteur_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_echanges_auteur_id"), "echanges", ["auteur_id"])
    op.create_foreign_key(
        op.f("fk_echanges_auteur_id_utilisateurs"),
        "echanges",
        "utilisateurs",
        ["auteur_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_echanges_auteur_id_utilisateurs"), "echanges", type_="foreignkey")
    op.drop_index(op.f("ix_echanges_auteur_id"), table_name="echanges")
    op.drop_column("echanges", "auteur_id")
