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
    # « vélos » trouve « Vélo », « jeux » trouve « jeu de société » : on cherche le singulier.
    mots = [mot[:-1] if len(mot) > 3 and mot[-1] in "sx" else mot for mot in texte.split()]
    # Les jokers de LIKE sont pris au pied de la lettre.
    return [mot.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") for mot in mots][:8]


def requete_objets(categorie: str | None = None, zone: str | None = None, q: str | None = None):
    """Objets disponibles de comptes non suspendus, filtrés par catégorie, ville et mots-clés, les plus récents
    d'abord. Sert aussi aux alertes du mode visiteur (suivis.py)."""
    requete = (
        select(m.Objet)
        .join(m.Objet.proprietaire)
        .where(m.Objet.statut == m.StatutObjet.disponible, m.Utilisateur.suspendu_le.is_(None))
        .order_by(m.Objet.cree_le.desc(), m.Objet.id.desc())
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
    return requete


@router.get("", response_model=list[ObjetLecture])
def lister(
    session: SessionDep,
    categorie: str | None = None,
    zone: str | None = None,
    q: str | None = Query(
        default=None, max_length=100, description="Mots cherchés dans le titre, la description et la catégorie."
    ),
    decalage: int = Query(default=0, ge=0, description="Objets à sauter : la page suivante commence après eux."),
    limite: int = Query(default=200, ge=1, le=200),
):
    """Objets disponibles, filtrables par catégorie, par ville et par mots-clés, par pages de ``limite``.

    Public : seuls les objets en ligne de comptes non suspendus sont renvoyés, sans données personnelles.
    Le mode visiteur parcourt ainsi tout le catalogue, page après page (« Voir plus »).
    """
    return session.scalars(requete_objets(categorie, zone, q).offset(decalage).limit(limite)).all()


@router.get("/{objet_id}", response_model=ObjetLecture)
def lire(objet_id: int, session: SessionDep):
    objet = session.get(m.Objet, objet_id)
    if objet is None or objet.statut == m.StatutObjet.modere:
        raise HTTPException(404, "Objet introuvable.")
    return objet
