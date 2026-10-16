"""Règles du matching : états, critères préférentiels, alternatives, modes de recherche et logistique.

- États « Comme neuf » et « Correct » (qui remplace « Usagé, fonctionne ») ;
- objet : modes d'échange possibles ;
- demande : critères préférentiels, état minimum, mode de recherche (précise, flexible, ouverte),
  alternatives acceptées, modes d'échange et zones acceptés.

Le retour en arrière remet « Comme neuf » en « Très bon » et « Correct » en « Usagé ».

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ETATS = ("neuf", "comme_neuf", "tres_bon", "bon", "correct")
ANCIENS_ETATS = ("neuf", "tres_bon", "bon", "usage")


def _liste_json(nom: str, defaut: str = "[]") -> sa.Column:
    return sa.Column(nom, postgresql.JSONB(astext_type=sa.Text()), server_default=defaut, nullable=False)


def upgrade() -> None:
    op.drop_constraint(op.f("ck_objets_etat_objet"), "objets", type_="check")
    op.execute("UPDATE objets SET etat = 'correct' WHERE etat = 'usage'")
    liste = ", ".join(f"'{v}'" for v in ETATS)
    op.create_check_constraint(op.f("ck_objets_etat_objet"), "objets", f"etat IN ({liste})")

    op.add_column("objets", _liste_json("modes_echange"))
    op.add_column("souhaits", _liste_json("preferences", "{}"))
    op.add_column(
        "souhaits",
        sa.Column("etat_min", sa.Enum(*ETATS, name="etat_min", native_enum=False, create_constraint=True, length=20)),
    )
    op.add_column(
        "souhaits",
        sa.Column(
            "mode_recherche",
            sa.Enum("precise", "flexible", "ouverte", name="mode_recherche", native_enum=False, create_constraint=True,
                    length=20),
            server_default="flexible",
            nullable=False,
        ),
    )  # fmt: skip
    for nom in ("alternatives", "modes_echange", "zones"):
        op.add_column("souhaits", _liste_json(nom))


def downgrade() -> None:
    for nom in ("zones", "modes_echange", "alternatives", "mode_recherche", "etat_min", "preferences"):
        op.drop_column("souhaits", nom)
    op.drop_column("objets", "modes_echange")
    op.drop_constraint(op.f("ck_objets_etat_objet"), "objets", type_="check")
    op.execute("UPDATE objets SET etat = 'tres_bon' WHERE etat = 'comme_neuf'")
    op.execute("UPDATE objets SET etat = 'usage' WHERE etat = 'correct'")
    liste = ", ".join(f"'{v}'" for v in ANCIENS_ETATS)
    op.create_check_constraint(op.f("ck_objets_etat_objet"), "objets", f"etat IN ({liste})")
