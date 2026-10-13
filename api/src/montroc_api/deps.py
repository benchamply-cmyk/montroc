"""Dépendances partagées par les routes : base, utilisateur connecté, droits de modération."""

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m
from .config import get_settings
from .db import get_session

SessionDep = Annotated[Session, Depends(get_session)]

_bearer = HTTPBearer(auto_error=False)


def empreinte(jeton: str) -> str:
    """La base ne garde que l'empreinte des jetons : une fuite de la base ne donne accès à aucun compte."""
    return hashlib.sha256(jeton.encode()).hexdigest()


def obtenir_ou_404(session: Session, modele, id_: int):
    obj = session.get(modele, id_)
    if obj is None:
        raise HTTPException(404, f"{modele.__name__} {id_} introuvable.")
    return obj


def _utilisateur_optionnel(
    session: SessionDep, identifiants: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> m.Utilisateur | None:
    if identifiants is None:
        return None
    ouverte = session.scalar(
        select(m.SessionUtilisateur).where(
            m.SessionUtilisateur.empreinte == empreinte(identifiants.credentials),
            m.SessionUtilisateur.expire_le > datetime.now(UTC),
        )
    )
    if ouverte is None:
        raise HTTPException(401, "Session expirée : reconnectez-vous avec un nouveau lien.")
    if ouverte.utilisateur.suspendu_le is not None:
        raise HTTPException(403, "Ce compte est suspendu.")
    return ouverte.utilisateur


def _utilisateur_requis(utilisateur: Annotated[m.Utilisateur | None, Depends(_utilisateur_optionnel)]) -> m.Utilisateur:
    if utilisateur is None:
        raise HTTPException(401, "Connexion requise.")
    return utilisateur


def est_moderateur(utilisateur: m.Utilisateur) -> bool:
    return utilisateur.email.lower() in get_settings().liste_moderateurs


def _moderateur(utilisateur: Annotated[m.Utilisateur, Depends(_utilisateur_requis)]) -> m.Utilisateur:
    if not est_moderateur(utilisateur):
        raise HTTPException(403, "Réservé à la modération.")
    return utilisateur


def _secret_taches(x_taches_secret: Annotated[str, Header()] = "") -> None:
    attendu = get_settings().taches_secret
    if not attendu or not hmac.compare_digest(x_taches_secret, attendu):
        raise HTTPException(403, "Secret des tâches planifiées absent ou incorrect.")


UtilisateurOptionnel = Annotated[m.Utilisateur | None, Depends(_utilisateur_optionnel)]
UtilisateurConnecte = Annotated[m.Utilisateur, Depends(_utilisateur_requis)]
Moderateur = Annotated[m.Utilisateur, Depends(_moderateur)]
SecretTaches = Depends(_secret_taches)
