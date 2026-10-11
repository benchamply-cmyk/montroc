"""Catalogue des objets et souhaits."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .. import models as m
from ..deps import SessionDep, obtenir_ou_404
from ..schemas import ObjetLecture, ObjetModification

router = APIRouter(tags=["objets"])


@router.get("/objets", response_model=list[ObjetLecture])
def lister(session: SessionDep, categorie: str | None = None, zone: str | None = None):
    """Objets disponibles, filtrables par catégorie et par ville."""
    requete = select(m.Objet).where(m.Objet.statut == m.StatutObjet.disponible).order_by(m.Objet.cree_le.desc())
    if categorie:
        requete = requete.where(m.Objet.categorie_slug == categorie)
    if zone:
        requete = requete.join(m.Objet.proprietaire).where(m.Utilisateur.zone == zone)
    return session.scalars(requete.limit(200)).all()


@router.patch("/objets/{objet_id}", response_model=ObjetLecture)
def modifier(objet_id: int, donnees: ObjetModification, session: SessionDep):
    objet = obtenir_ou_404(session, m.Objet, objet_id)
    changements = donnees.model_dump(exclude_unset=True)
    if "statut" in changements and objet.statut not in (m.StatutObjet.disponible, m.StatutObjet.retire):
        raise HTTPException(409, "Cet objet est engagé dans un échange.")
    for champ, valeur in changements.items():
        setattr(objet, champ, valeur)
    session.commit()
    return objet


@router.delete("/souhaits/{souhait_id}", status_code=204)
def supprimer_souhait(souhait_id: int, session: SessionDep):
    session.delete(obtenir_ou_404(session, m.Souhait, souhait_id))
    session.commit()
