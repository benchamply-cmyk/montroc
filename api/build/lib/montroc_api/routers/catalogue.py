"""Catégories d'objets."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .. import models as m
from ..deps import Moderateur, SessionDep
from ..schemas import CategorieCreation, CategorieLecture

router = APIRouter(prefix="/categories", tags=["catégories"])


@router.get("", response_model=list[CategorieLecture])
def lister(session: SessionDep):
    return session.scalars(select(m.Categorie).order_by(m.Categorie.libelle)).all()


@router.post("", response_model=CategorieLecture, status_code=201)
def creer(donnees: CategorieCreation, _moderateur: Moderateur, session: SessionDep):
    if session.get(m.Categorie, donnees.slug):
        raise HTTPException(409, "Cette catégorie existe déjà.")
    categorie = m.Categorie(**donnees.model_dump())
    session.add(categorie)
    session.commit()
    return categorie
