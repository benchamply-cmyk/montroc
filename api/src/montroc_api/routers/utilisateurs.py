"""Profil public d'un utilisateur."""

from fastapi import APIRouter

from .. import models as m
from ..deps import SessionDep, obtenir_ou_404
from ..schemas import UtilisateurLecture

router = APIRouter(prefix="/utilisateurs", tags=["utilisateurs"])


@router.get("/{utilisateur_id}", response_model=UtilisateurLecture)
def lire(utilisateur_id: int, session: SessionDep):
    return obtenir_ou_404(session, m.Utilisateur, utilisateur_id)
