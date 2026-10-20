"""Souhaits comblés : chaque transfert garde le souhait du receveur qu'il sert.

Un souhait de quantité 1 ne reçoit plus un deuxième objet au repêchage, au Grand Troc suivant ou pendant
un accord du Match : les transferts d'échanges non annulés comptent dans sa quantité.

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | Sequence[str] | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transferts", sa.Column("souhait_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_transferts_souhait_id_souhaits"), "transferts", "souhaits", ["souhait_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index(op.f("ix_transferts_souhait_id"), "transferts", ["souhait_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_transferts_souhait_id"), table_name="transferts")
    op.drop_constraint(op.f("fk_transferts_souhait_id_souhaits"), "transferts", type_="foreignkey")
    op.drop_column("transferts", "souhait_id")
