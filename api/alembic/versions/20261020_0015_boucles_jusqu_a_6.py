"""Boucles de plus de 3 personnes : la base accepte jusqu'à 6 transferts par échange.

La contrainte d'origine (« position < 3 ») faisait échouer tout le Grand Troc dès qu'il trouvait une
boucle de 4, ce qu'il cherche depuis les règles du matching (0013). La limite suit maintenant celle du
moteur (``LONGUEUR_MAX_ABSOLUE`` = 6).

Le retour en arrière échoue s'il existe déjà des boucles de plus de 3 personnes.

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0015"
down_revision: str | Sequence[str] | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_transferts_boucle_max_3"), "transferts", type_="check")
    op.create_check_constraint(op.f("ck_transferts_boucle_max_6"), "transferts", "position >= 0 AND position < 6")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_transferts_boucle_max_6"), "transferts", type_="check")
    op.create_check_constraint(op.f("ck_transferts_boucle_max_3"), "transferts", "position >= 0 AND position < 3")
