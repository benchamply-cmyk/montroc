"""« Je le donne contre… » par objet, fiabilité tirée des engagements, repêchage du mardi.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "objets_contre",
        sa.Column("objet_id", sa.Integer(), nullable=False),
        sa.Column("souhait_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["objet_id"], ["objets.id"], name=op.f("fk_objets_contre_objet_id_objets"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["souhait_id"], ["souhaits.id"], name=op.f("fk_objets_contre_souhait_id_souhaits"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("objet_id", "souhait_id", name=op.f("pk_objets_contre")),
    )
    op.create_index(op.f("ix_objets_contre_souhait_id"), "objets_contre", ["souhait_id"], unique=False)
    op.add_column("objets", sa.Column("contre_strict", sa.Boolean(), server_default="false", nullable=False))

    op.add_column("utilisateurs", sa.Column("engagements_tenus", sa.Integer(), server_default="0", nullable=False))
    op.add_column("utilisateurs", sa.Column("engagements_manques", sa.Integer(), server_default="0", nullable=False))
    op.create_check_constraint(
        op.f("ck_utilisateurs_engagements_positifs"),
        "utilisateurs",
        "engagements_tenus >= 0 AND engagements_manques >= 0",
    )

    op.add_column("grands_trocs", sa.Column("repeche_le", sa.DateTime(timezone=True), nullable=True))
    op.add_column("grands_trocs", sa.Column("nb_objets_repeches", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("grands_trocs", "nb_objets_repeches")
    op.drop_column("grands_trocs", "repeche_le")
    op.drop_constraint(op.f("ck_utilisateurs_engagements_positifs"), "utilisateurs", type_="check")
    op.drop_column("utilisateurs", "engagements_manques")
    op.drop_column("utilisateurs", "engagements_tenus")
    op.drop_column("objets", "contre_strict")
    op.drop_index(op.f("ix_objets_contre_souhait_id"), table_name="objets_contre")
    op.drop_table("objets_contre")
