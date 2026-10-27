"""Mode visiteur : favoris des membres (l'étoile), et suivi des recherches et des favoris par e-mail ou téléphone,
sans compte.

Revision ID: 0020
Revises: 0019
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str | Sequence[str] | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "favoris",
        sa.Column("utilisateur_id", sa.Integer(), nullable=False),
        sa.Column("objet_id", sa.Integer(), nullable=False),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["objet_id"], ["objets.id"], name=op.f("fk_favoris_objet_id_objets"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["utilisateur_id"],
            ["utilisateurs.id"],
            name=op.f("fk_favoris_utilisateur_id_utilisateurs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("utilisateur_id", "objet_id", name=op.f("pk_favoris")),
    )
    op.create_index(op.f("ix_favoris_objet_id"), "favoris", ["objet_id"])
    op.create_table(
        "suivis_visiteurs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("telephone", sa.String(length=20), nullable=True),
        sa.Column("empreinte", sa.String(length=64), nullable=False),
        sa.Column("jeton_arret", sa.String(length=64), nullable=False),
        sa.Column("recherches", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("favoris", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("confirme_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mis_a_jour_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("derniere_alerte_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rappel_favoris_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cree_le", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("email IS NOT NULL OR telephone IS NOT NULL", name=op.f("ck_suivis_visiteurs_un_contact")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suivis_visiteurs")),
        sa.UniqueConstraint("empreinte", name=op.f("uq_suivis_visiteurs_empreinte")),
        sa.UniqueConstraint("jeton_arret", name=op.f("uq_suivis_visiteurs_jeton_arret")),
    )
    op.create_index(op.f("ix_suivis_visiteurs_email"), "suivis_visiteurs", ["email"])
    op.create_index(op.f("ix_suivis_visiteurs_telephone"), "suivis_visiteurs", ["telephone"])


def downgrade() -> None:
    op.drop_index(op.f("ix_suivis_visiteurs_telephone"), table_name="suivis_visiteurs")
    op.drop_index(op.f("ix_suivis_visiteurs_email"), table_name="suivis_visiteurs")
    op.drop_table("suivis_visiteurs")
    op.drop_index(op.f("ix_favoris_objet_id"), table_name="favoris")
    op.drop_table("favoris")
