"""Connexion : un lien magique envoyé par e-mail, ou un mot de passe une fois choisi, ouvre une session de 30 jours."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import object_session

from .. import courriels, motdepasse, premium
from .. import models as m
from ..config import get_settings
from ..deps import SessionDep, UtilisateurConnecte, empreinte, est_moderateur
from ..schemas import ChoixMotDePasse, ConnexionMotDePasse, DemandeLien, Moi, ResultatConnexion, Verification

router = APIRouter(prefix="/auth", tags=["connexion"])

DUREE_LIEN = timedelta(minutes=20)
DUREE_SESSION = timedelta(days=30)
LIENS_PAR_HEURE = 5
ESSAIS_MOT_DE_PASSE = 5
DUREE_BLOCAGE = timedelta(minutes=15)


def moi(utilisateur: m.Utilisateur) -> Moi:
    formule = premium.formule_active(utilisateur)
    session = object_session(utilisateur)
    return Moi.model_validate(utilisateur).model_copy(
        update={
            "est_moderateur": est_moderateur(utilisateur),
            "formule": formule.cle if formule else None,
            "premium_jusqu_au": utilisateur.premium_jusqu_au
            if formule and utilisateur.formule == formule.cle
            else None,
            "avantages": sorted(formule.avantages) if formule else [],
            "essai_disponible": bool(get_settings().jours_essai_premium)
            and utilisateur.essai_premium_le is None
            and formule is None,
            "super_jaime_restants": premium.super_jaime_restants(session, utilisateur) if session else 0,
            "zones_max": premium.zones_max(utilisateur),
        }
    )


def ouvrir_session(session, utilisateur: m.Utilisateur) -> ResultatConnexion:
    utilisateur.essais_mot_de_passe, utilisateur.bloque_jusqu_au = 0, None
    jeton = secrets.token_urlsafe(32)
    session.add(
        m.SessionUtilisateur(
            utilisateur=utilisateur, empreinte=empreinte(jeton), expire_le=datetime.now(UTC) + DUREE_SESSION
        )
    )
    session.commit()
    return ResultatConnexion(jeton=jeton, utilisateur=moi(utilisateur))


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
    prefixe = {"fr": "", "en": "/english", "es": "/espanol"}[donnees.langue]
    lien = f"{get_settings().site_url.rstrip('/')}{prefixe}/#connexion={jeton}"
    courriels.apres_validation(session, courriels.lien_magique, email, lien)
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
        utilisateur = m.Utilisateur(
            email=lien.email,
            pseudo=donnees.pseudo.strip(),
            zone=donnees.zone,
            telephone=donnees.telephone,
            mot_de_passe=motdepasse.chiffrer(donnees.mot_de_passe) if donnees.mot_de_passe else None,
        )
        session.add(utilisateur)
    elif utilisateur.suspendu_le is not None:
        raise HTTPException(403, "Ce compte est suspendu.")

    lien.utilise_le = datetime.now(UTC)
    return ouvrir_session(session, utilisateur)


@router.post("/connexion", response_model=ResultatConnexion)
def connexion(donnees: ConnexionMotDePasse, session: SessionDep):
    """Connexion par mot de passe, pour les comptes qui en ont choisi un. Même erreur si le compte n'existe pas."""
    email = str(donnees.email).lower()
    utilisateur = session.scalar(
        select(m.Utilisateur).where(func.lower(m.Utilisateur.email) == email).with_for_update()
    )
    maintenant = datetime.now(UTC)
    if utilisateur is not None and utilisateur.bloque_jusqu_au and utilisateur.bloque_jusqu_au > maintenant:
        raise HTTPException(
            429, "Trop d'essais : réessayez dans 15 minutes, ou recevez un lien de connexion par e-mail."
        )
    if utilisateur is None or not motdepasse.verifier(donnees.mot_de_passe, utilisateur.mot_de_passe):
        if utilisateur is not None and utilisateur.mot_de_passe is not None:
            utilisateur.essais_mot_de_passe += 1
            if utilisateur.essais_mot_de_passe >= ESSAIS_MOT_DE_PASSE:
                utilisateur.essais_mot_de_passe, utilisateur.bloque_jusqu_au = 0, maintenant + DUREE_BLOCAGE
            session.commit()
        raise HTTPException(401, "E-mail ou mot de passe incorrect.")
    if utilisateur.suspendu_le is not None:
        raise HTTPException(403, "Ce compte est suspendu.")
    return ouvrir_session(session, utilisateur)


@router.put("/mot-de-passe", response_model=Moi)
def choisir_mot_de_passe(donnees: ChoixMotDePasse, utilisateur: UtilisateurConnecte, session: SessionDep):
    """Choisit ou change le mot de passe. Être connecté suffit : le lien magique sert de « mot de passe oublié »."""
    utilisateur.mot_de_passe = motdepasse.chiffrer(donnees.mot_de_passe)
    utilisateur.essais_mot_de_passe, utilisateur.bloque_jusqu_au = 0, None
    session.commit()
    return moi(utilisateur)


@router.post("/deconnexion", status_code=204)
def deconnexion(utilisateur: UtilisateurConnecte, session: SessionDep):
    """Ferme toutes les sessions du compte (sur tous les appareils)."""
    for s in session.scalars(select(m.SessionUtilisateur).where(m.SessionUtilisateur.utilisateur_id == utilisateur.id)):
        session.delete(s)
    session.commit()
