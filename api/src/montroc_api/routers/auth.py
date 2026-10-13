"""Connexion sans mot de passe : un lien magique envoyé par e-mail ouvre une session de 30 jours."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from .. import courriels
from .. import models as m
from ..config import get_settings
from ..deps import SessionDep, UtilisateurConnecte, empreinte, est_moderateur
from ..schemas import DemandeLien, Moi, ResultatConnexion, Verification

router = APIRouter(prefix="/auth", tags=["connexion"])

DUREE_LIEN = timedelta(minutes=20)
DUREE_SESSION = timedelta(days=30)
LIENS_PAR_HEURE = 5


def moi(utilisateur: m.Utilisateur) -> Moi:
    return Moi.model_validate(utilisateur).model_copy(update={"est_moderateur": est_moderateur(utilisateur)})


@router.post("/lien", status_code=202)
def demander_lien(donnees: DemandeLien, session: SessionDep):
    """Envoie un lien de connexion. La réponse est la même que le compte existe ou non."""
    email = str(donnees.email).lower()
    il_y_a_une_heure = datetime.now(UTC) - timedelta(hours=1)
    recents = session.scalar(
        select(func.count())
        .select_from(m.JetonConnexion)
        .where(m.JetonConnexion.email == email, m.JetonConnexion.cree_le > il_y_a_une_heure)
    )
    if recents >= LIENS_PAR_HEURE:
        raise HTTPException(429, "Trop de liens demandés pour cette adresse : réessayez dans une heure.")
    utilisateur = session.scalar(select(m.Utilisateur).where(func.lower(m.Utilisateur.email) == email))
    if utilisateur is not None and utilisateur.suspendu_le is not None:
        return {"envoye": True}

    jeton = secrets.token_urlsafe(32)
    session.add(m.JetonConnexion(email=email, empreinte=empreinte(jeton), expire_le=datetime.now(UTC) + DUREE_LIEN))
    courriels.apres_validation(session, courriels.lien_magique, email, f"{get_settings().site_url}/#connexion={jeton}")
    session.commit()
    return {"envoye": True}


@router.post("/verifier", response_model=ResultatConnexion)
def verifier(donnees: Verification, session: SessionDep):
    """Échange le lien magique contre une session. À la première connexion, demande un pseudo."""
    lien = session.scalar(
        select(m.JetonConnexion).where(m.JetonConnexion.empreinte == empreinte(donnees.jeton)).with_for_update()
    )
    if lien is None or lien.utilise_le is not None or lien.expire_le < datetime.now(UTC):
        raise HTTPException(400, "Ce lien a expiré ou a déjà servi : demandez-en un nouveau.")

    utilisateur = session.scalar(select(m.Utilisateur).where(func.lower(m.Utilisateur.email) == lien.email))
    if utilisateur is None:
        if donnees.pseudo is None:
            # Le lien n'est pas consommé : il resservira avec le pseudo choisi.
            return ResultatConnexion(inscription_requise=True, email=lien.email)
        if session.scalar(select(m.Utilisateur.id).where(func.lower(m.Utilisateur.pseudo) == donnees.pseudo.lower())):
            raise HTTPException(409, "Ce pseudo est déjà pris.")
        utilisateur = m.Utilisateur(email=lien.email, pseudo=donnees.pseudo.strip(), zone=donnees.zone)
        session.add(utilisateur)
    elif utilisateur.suspendu_le is not None:
        raise HTTPException(403, "Ce compte est suspendu.")

    lien.utilise_le = datetime.now(UTC)
    jeton = secrets.token_urlsafe(32)
    session.add(
        m.SessionUtilisateur(
            utilisateur=utilisateur, empreinte=empreinte(jeton), expire_le=datetime.now(UTC) + DUREE_SESSION
        )
    )
    session.commit()
    return ResultatConnexion(jeton=jeton, utilisateur=moi(utilisateur))


@router.post("/deconnexion", status_code=204)
def deconnexion(utilisateur: UtilisateurConnecte, session: SessionDep):
    """Ferme toutes les sessions du compte (sur tous les appareils)."""
    for s in session.scalars(select(m.SessionUtilisateur).where(m.SessionUtilisateur.utilisateur_id == utilisateur.id)):
        session.delete(s)
    session.commit()
