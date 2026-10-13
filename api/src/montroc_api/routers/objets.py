"""Catalogue public des objets disponibles."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .. import models as m
from ..deps import SessionDep
from ..schemas import ObjetLecture

router = APIRouter(prefix="/objets", tags=["objets"])


@router.get("", response_model=list[ObjetLecture])
def lister(session: SessionDep, categorie: str | None = None, zone: str | None = None):
    """Objets disponibles, filtrables par catégorie et par ville."""
    requete = select(m.Objet).where(m.Objet.statut == m.StatutObjet.disponible).order_by(m.Objet.cree_le.desc())
    if categorie:
        requete = requete.where(m.Objet.categorie_slug == categorie)
    if zone:
        requete = requete.join(m.Objet.proprietaire).where(m.Utilisateur.zone == zone)
    return session.scalars(requete.limit(200)).all()


@router.get("/{objet_id}", response_model=ObjetLecture)
def lire(objet_id: int, session: SessionDep):
    objet = session.get(m.Objet, objet_id)
    if objet is None or objet.statut == m.StatutObjet.modere:
        raise HTTPException(404, "Objet introuvable.")
    return objet
