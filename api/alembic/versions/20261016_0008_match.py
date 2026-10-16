"""Le Match : « J'aime » / « Non merci » sur les objets, accords 1 à 1 à tout moment.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "avis",
        sa.Column("utilisateur_id", sa.Integer(), nullable=False),
        sa.Column("objet_id", sa.Integer(), nullable=False),
        sa.Column("aime", sa.Boolean(), nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["objet_id"], ["objets.id"], name=op.f("fk_avis_objet_id_objets"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["utilisateur_id"],
            ["utilisateurs.id"],
            name=op.f("fk_avis_utilisateur_id_utilisateurs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("utilisateur_id", "objet_id", name=op.f("pk_avis")),
    )
    op.create_index(op.f("ix_avis_objet_id"), "avis", ["objet_id"], unique=False)
    op.add_column("echanges", sa.Column("par_match", sa.Boolean(), server_default="false", nullable=False))


def downgrade() -> None:
    op.drop_column("echanges", "par_match")
    op.drop_index(op.f("ix_avis_objet_id"), table_name="avis")
    op.drop_table("avis")
