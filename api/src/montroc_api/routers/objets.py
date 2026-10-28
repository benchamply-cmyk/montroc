"""Catalogue public des objets disponibles (consultable sans compte)."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select

from .. import models as m
from .. import nomenclature
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


def _caracteristiques(categorie: str | None, sous_categorie: str | None, filtres: list[str]) -> dict[str, list[str]]:
    """``["taille:M", "taille:L", "couleur:Noir"]`` -> ``{"taille": ["M", "L"], "couleur": ["Noir"]}``.

    Lève ``HTTPException(422)`` pour un filtre mal écrit, ou une caractéristique que la catégorie n'a pas."""
    if filtres and not categorie:
        raise HTTPException(422, "Les caractéristiques se filtrent dans une catégorie.")
    connues = {c.cle: c for c in nomenclature.caracteristiques(categorie)} if categorie else {}
    valeurs: dict[str, list[str]] = {}
    for filtre in filtres:
        cle, deux_points, valeur = filtre.partition(":")
        cle, valeur = cle.strip(), valeur.strip()
        if not deux_points or not cle or not valeur:
            raise HTTPException(422, f"Filtre à écrire « clé:valeur » : {filtre}.")
        c = connues.get(cle)
        if c is None:
            raise HTTPException(422, f"Caractéristique inconnue pour cette catégorie : {cle}.")
        if c.pour is not None and sous_categorie is not None and sous_categorie not in c.pour:
            raise HTTPException(422, f"« {c.libelle} » ne se précise pas pour cette sous-catégorie.")
        valeurs.setdefault(cle, []).append(valeur)
    return valeurs


def requete_objets(
    categorie: str | None = None,
    zone: str | None = None,
    q: str | None = None,
    *,
    sous_categorie: str | None = None,
    etats: list[m.EtatObjet] | None = None,
    caracteristiques: dict[str, list[str]] | None = None,
    plus_anciens: bool = False,
):
    """Objets disponibles de comptes non suspendus, filtrés par catégorie, sous-catégorie, état, caractéristiques,
    ville et mots-clés, les plus récents d'abord (ou les plus anciens). Sert aussi aux alertes du mode visiteur
    (suivis.py).

    Dans ``caracteristiques``, plusieurs valeurs d'une même clé s'additionnent (taille M ou L), des clés
    différentes se cumulent (taille M et couleur noire), comme les filtres de la page d'une catégorie."""
    ordre = (m.Objet.cree_le.asc(), m.Objet.id.asc()) if plus_anciens else (m.Objet.cree_le.desc(), m.Objet.id.desc())
    requete = (
        select(m.Objet)
        .join(m.Objet.proprietaire)
        .where(m.Objet.statut == m.StatutObjet.disponible, m.Utilisateur.suspendu_le.is_(None))
        .order_by(*ordre)
    )
    if categorie:
        requete = requete.where(m.Objet.categorie_slug == categorie)
    if sous_categorie:
        requete = requete.where(m.Objet.sous_categorie_slug == sous_categorie)
    if etats:
        requete = requete.where(m.Objet.etat.in_(etats))
    for cle, valeurs in (caracteristiques or {}).items():
        requete = requete.where(m.Objet.caracteristiques[cle].astext.in_(valeurs))
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
    sous_categorie: str | None = Query(
        default=None, max_length=50, description="Slug d'une sous-catégorie de la catégorie (voir /categories)."
    ),
    etat: Annotated[
        list[m.EtatObjet] | None, Query(description="États acceptés, répétable : ?etat=neuf&etat=bon.")
    ] = None,
    caracteristique: Annotated[
        list[str] | None,
        Query(
            max_length=30,
            description="« clé:valeur », répétable : ?caracteristique=taille:M&caracteristique=taille:L"
            "&caracteristique=couleur:Noir (taille M ou L, et noir). Demande une catégorie.",
        ),
    ] = None,
    tri: Literal["recent", "ancien"] = Query(default="recent", description="Plus récents ou plus anciens d'abord."),
    decalage: int = Query(default=0, ge=0, description="Objets à sauter : la page suivante commence après eux."),
    limite: int = Query(default=200, ge=1, le=200),
):
    """Objets disponibles, filtrables par catégorie, sous-catégorie, état, caractéristiques, ville et mots-clés,
    par pages de ``limite``.

    Public : seuls les objets en ligne de comptes non suspendus sont renvoyés, sans données personnelles.
    Le mode visiteur parcourt ainsi tout le catalogue, page après page (« Voir plus »), et la page d'une
    catégorie filtre ici plutôt que dans le navigateur.
    """
    if sous_categorie and categorie and sous_categorie not in dict(nomenclature.sous_categories(categorie)):
        raise HTTPException(422, "Cette sous-catégorie n'existe pas dans cette catégorie.")
    requete = requete_objets(
        categorie,
        zone,
        q,
        sous_categorie=sous_categorie,
        etats=etat,
        caracteristiques=_caracteristiques(categorie, sous_categorie, caracteristique or []),
        plus_anciens=tri == "ancien",
    )
    return session.scalars(requete.offset(decalage).limit(limite)).all()


@router.get("/{objet_id}", response_model=ObjetLecture)
def lire(objet_id: int, session: SessionDep):
    objet = session.get(m.Objet, objet_id)
    if objet is None or objet.statut == m.StatutObjet.modere:
        raise HTTPException(404, "Objet introuvable.")
    return objet
