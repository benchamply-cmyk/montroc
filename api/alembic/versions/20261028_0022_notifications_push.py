"""Notifications push : les jetons Expo des téléphones où l'app est installée.

Revision ID: 0022
Revises: 0021
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | Sequence[str] | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "appareils_push",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("utilisateur_id", sa.Integer(), nullable=False),
        sa.Column("jeton", sa.String(length=200), nullable=False),
        sa.Column("plateforme", sa.String(length=10), nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("vu_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("plateforme IN ('ios', 'android')", name=op.f("ck_appareils_push_plateforme_connue")),
        sa.ForeignKeyConstraint(
            ["utilisateur_id"],
            ["utilisateurs.id"],
            name=op.f("fk_appareils_push_utilisateur_id_utilisateurs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appareils_push")),
        sa.UniqueConstraint("jeton", name=op.f("uq_appareils_push_jeton")),
    )
    op.create_index(op.f("ix_appareils_push_utilisateur_id"), "appareils_push", ["utilisateur_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_appareils_push_utilisateur_id"), table_name="appareils_push")
    op.drop_table("appareils_push")
