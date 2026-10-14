"""Grand Troc du dimanche : un passage hebdomadaire du math trade, et le lien de chaque échange à son passage.

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
    op.create_table(
        "grands_trocs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jour", sa.Date(), nullable=False),
        sa.Column("optimal", sa.Boolean(), nullable=False),
        sa.Column("duree_s", sa.Float(), nullable=False),
        sa.Column("nb_boucles", sa.Integer(), nullable=False),
        sa.Column("nb_objets", sa.Integer(), nullable=False),
        sa.Column("nb_participants", sa.Integer(), nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grands_trocs")),
        sa.UniqueConstraint("jour", name=op.f("uq_grands_trocs_jour")),
    )
    op.add_column("echanges", sa.Column("grand_troc_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_echanges_grand_troc_id"), "echanges", ["grand_troc_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_echanges_grand_troc_id_grands_trocs"),
        "echanges",
        "grands_trocs",
        ["grand_troc_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_echanges_grand_troc_id_grands_trocs"), "echanges", type_="foreignkey")
    op.drop_index(op.f("ix_echanges_grand_troc_id"), table_name="echanges")
    op.drop_column("echanges", "grand_troc_id")
    op.drop_table("grands_trocs")
