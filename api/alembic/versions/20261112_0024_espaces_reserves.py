"""Espaces réservés (entreprises, résidences) : membres reconnus à leur e-mail, objets visibles d'eux seuls.

Revision ID: 0024
Revises: 0023
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: str | Sequence[str] | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "espaces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("nom", sa.String(length=120), nullable=False),
        sa.Column("domaines", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("lieu_de_remise", sa.String(length=200), nullable=True),
        sa.Column("formule", sa.String(length=30), nullable=True),
        sa.Column("actif", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_espaces")),
        sa.UniqueConstraint("slug", name=op.f("uq_espaces_slug")),
    )
    for table in ("utilisateurs", "objets"):
        op.add_column(table, sa.Column("espace_id", sa.Integer(), nullable=True))
        op.create_index(op.f(f"ix_{table}_espace_id"), table, ["espace_id"])
        op.create_foreign_key(
            op.f(f"fk_{table}_espace_id_espaces"), table, "espaces", ["espace_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    for table in ("objets", "utilisateurs"):
        op.drop_constraint(op.f(f"fk_{table}_espace_id_espaces"), table, type_="foreignkey")
        op.drop_index(op.f(f"ix_{table}_espace_id"), table_name=table)
        op.drop_column(table, "espace_id")
    op.drop_table("espaces")
