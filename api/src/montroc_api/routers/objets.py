"""Catalogue public des objets disponibles (consultable sans compte)."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select

from .. import models as m
from ..deps import SessionDep
from ..schemas import ObjetLecture

router = APIRouter(prefix="/objets", tags=["objets"])

# Recherche insensible à la casse et aux accents, sans extension PostgreSQL (unaccent).
_ACCENTS, _SANS = "àâäáãåçéèêëíìîïñóòôöõúùûüýÿ", "aaaaaaceeeeiiiinooooouuuuyy"


def _normaliser(colonne):
    return func.translate(func.lower(func.coalesce(colonne, "")), _ACCENTS, _SANS)


def _mots(q: str) -> list[str]:
    texte = q.lower().translate(str.maketrans(_ACCENTS, _SANS))
    # Les jokers de LIKE sont pris au pied de la lettre.
    return [mot.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") for mot in texte.split()][:8]


@router.get("", response_model=list[ObjetLecture])
def lister(
    session: SessionDep,
    categorie: str | None = None,
    zone: str | None = None,
    q: str | None = Query(
        default=None, max_length=100, description="Mots cherchés dans le titre, la description et la catégorie."
    ),
):
    """Objets disponibles, filtrables par catégorie, par ville et par mots-clés.

    Public : seuls les objets en ligne de comptes non suspendus sont renvoyés, sans données personnelles.
    """
    requete = (
        select(m.Objet)
        .join(m.Objet.proprietaire)
        .where(m.Objet.statut == m.StatutObjet.disponible, m.Utilisateur.suspendu_le.is_(None))
        .order_by(m.Objet.cree_le.desc())
    )
    if categorie:
        requete = requete.where(m.Objet.categorie_slug == categorie)
    if zone:
        requete = requete.where(m.Utilisateur.zone == zone)
    if q and (mots := _mots(q)):
        requete = requete.join(m.Categorie, m.Categorie.slug == m.Objet.categorie_slug)
        for mot in mots:
            motif = f"%{mot}%"
            requete = requete.where(
                or_(
                    _normaliser(m.Objet.titre).like(motif, escape="\\"),
                    _normaliser(m.Objet.description).like(motif, escape="\\"),
                    _normaliser(m.Categorie.libelle).like(motif, escape="\\"),
                )
            )
    return session.scalars(requete.limit(200)).all()


@router.get("/{objet_id}", response_model=ObjetLecture)
def lire(objet_id: int, session: SessionDep):
    objet = session.get(m.Objet, objet_id)
    if objet is None or objet.statut == m.StatutObjet.modere:
        raise HTTPException(404, "Objet introuvable.")
    return objet
