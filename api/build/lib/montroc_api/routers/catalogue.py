"""Catégories d'objets."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .. import models as m
from .. import nomenclature
from ..deps import Moderateur, SessionDep
from ..schemas import CategorieCreation, CategorieDetaillee, CategorieLecture

router = APIRouter(prefix="/categories", tags=["catégories"])


@router.get("", response_model=list[CategorieDetaillee])
def lister(session: SessionDep):
    """Les catégories, dans l'ordre de la nomenclature, avec leurs sous-catégories et caractéristiques."""
    return [
        CategorieDetaillee(
            slug=c.slug,
            libelle=c.libelle,
            sous_categories=[{"slug": s, "libelle": libelle} for s, libelle in nomenclature.sous_categories(c.slug)],
            caracteristiques=[
                {
                    "cle": x.cle,
                    "libelle": x.libelle,
                    "options": list(x.options) if x.options else None,
                    "pour": list(x.pour) if x.pour else None,
                }
                for x in nomenclature.caracteristiques(c.slug)
            ],
        )
        for c in sorted(
            session.scalars(select(m.Categorie)),
            key=lambda c: (nomenclature.ORDRE.get(c.slug, len(nomenclature.ORDRE)), c.libelle),
        )
    ]


@router.post("", response_model=CategorieLecture, status_code=201)
def creer(donnees: CategorieCreation, _moderateur: Moderateur, session: SessionDep):
    if session.get(m.Categorie, donnees.slug):
        raise HTTPException(409, "Cette catégorie existe déjà.")
    categorie = m.Categorie(**donnees.model_dump())
    session.add(categorie)
    session.commit()
    return categorie
