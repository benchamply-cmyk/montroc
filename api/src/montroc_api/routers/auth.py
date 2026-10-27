"""Connexion : un mot de passe, ou un code à 6 chiffres envoyé par e-mail avec un lien magique, ouvre une session
de 30 jours. Le code se tape dans la fenêtre de connexion ; le lien marche depuis n'importe quel appareil."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import object_session

from .. import courriels, motdepasse, premium
from .. import models as m
from ..config import get_settings
from ..deps import SessionDep, UtilisateurConnecte, empreinte, est_moderateur
from ..schemas import (
    ChoixMotDePasse,
    ConnexionMotDePasse,
    DemandeInscription,
    DemandeLien,
    Moi,
    ResultatConnexion,
    Verification,
    VerificationCode,
)

router = APIRouter(prefix="/auth", tags=["connexion"])

DUREE_LIEN = timedelta(minutes=20)
DUREE_SESSION = timedelta(days=30)
LIENS_PAR_HEURE = 5
ESSAIS_MOT_DE_PASSE = 5
DUREE_BLOCAGE = timedelta(minutes=15)
ESSAIS_CODE = 5


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


def par_email(session, email: str) -> m.Utilisateur | None:
    return session.scalar(select(m.Utilisateur).where(func.lower(m.Utilisateur.email) == email))


def pseudo_pris(session, pseudo: str) -> bool:
    return session.scalar(select(m.Utilisateur.id).where(func.lower(m.Utilisateur.pseudo) == pseudo.strip().lower()))


def empreinte_code(lien_empreinte: str, code: str) -> str:
    # Salé par l'empreinte du lien : deux personnes qui reçoivent le même code n'ont pas la même empreinte.
    return empreinte(f"{lien_empreinte}:{code}")


def envoyer_lien(session, email: str, langue: str) -> None:
    """Envoie un code à 6 chiffres et un lien de connexion, valables 20 minutes, au plus 5 par heure."""
    il_y_a_une_heure = datetime.now(UTC) - timedelta(hours=1)
    recents = session.scalar(
        select(func.count())
        .select_from(m.JetonConnexion)
        .where(m.JetonConnexion.email == email, m.JetonConnexion.cree_le > il_y_a_une_heure)
    )
    if recents >= LIENS_PAR_HEURE:
        raise HTTPException(429, "Trop de codes demandés pour cette adresse : réessayez dans une heure.")
    jeton, code = secrets.token_urlsafe(32), f"{secrets.randbelow(10**6):06d}"
    lien_empreinte = empreinte(jeton)
    session.add(
        m.JetonConnexion(
            email=email,
            empreinte=lien_empreinte,
            code_empreinte=empreinte_code(lien_empreinte, code),
            expire_le=datetime.now(UTC) + DUREE_LIEN,
        )
    )
    prefixe = {"fr": "", "en": "/english", "es": "/espanol"}[langue]
    lien = f"{get_settings().site_url.rstrip('/')}{prefixe}/#connexion={jeton}"
    courriels.apres_validation(session, courriels.lien_magique, email, lien, code)
    session.commit()


@router.post("/lien", status_code=202)
def demander_lien(donnees: DemandeLien, session: SessionDep):
    """Envoie un code et un lien de connexion (mot de passe oublié, compte sans mot de passe)."""
    email = str(donnees.email).lower()
    utilisateur = par_email(session, email)
    if utilisateur is not None and utilisateur.suspendu_le is not None:
        return {"envoye": True}
    envoyer_lien(session, email, donnees.langue)
    return {"envoye": True}


@router.post("/inscription", status_code=202)
def demander_inscription(donnees: DemandeInscription, session: SessionDep):
    """Première étape de l'inscription : l'e-mail et le pseudo sont libres, le code part par e-mail.
    Le compte est créé par ``/auth/code``, avec le pseudo, la ville et le mot de passe."""
    email = str(donnees.email).lower()
    if par_email(session, email) is not None:
        raise HTTPException(409, "Un compte existe déjà avec cet e-mail : connectez-vous.")
    if pseudo_pris(session, donnees.pseudo):
        raise HTTPException(409, "Ce pseudo est déjà pris.")
    envoyer_lien(session, email, donnees.langue)
    return {"envoye": True}


@router.get("/pseudo")
def pseudo_libre(pseudo: str, session: SessionDep):
    """Le pseudo est-il libre ? Vérifié pendant la saisie, à l'inscription."""
    pseudo = pseudo.strip()
    return {"libre": 2 <= len(pseudo) <= 40 and not pseudo_pris(session, pseudo)}


def entrer(session, lien: m.JetonConnexion, donnees: Verification | VerificationCode) -> ResultatConnexion:
    """Lien ou code valide : ouvre la session, ou crée le compte à la première connexion."""
    utilisateur = par_email(session, lien.email)
    if utilisateur is None:
        if donnees.pseudo is None:
            # Le lien n'est pas consommé : il resservira avec le pseudo choisi.
            session.commit()
            return ResultatConnexion(inscription_requise=True, email=lien.email)
        if pseudo_pris(session, donnees.pseudo):
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


@router.post("/verifier", response_model=ResultatConnexion)
def verifier(donnees: Verification, session: SessionDep):
    """Échange le lien magique contre une session. À la première connexion, demande un pseudo."""
    lien = session.scalar(
        select(m.JetonConnexion).where(m.JetonConnexion.empreinte == empreinte(donnees.jeton)).with_for_update()
    )
    if lien is None or lien.utilise_le is not None or lien.expire_le < datetime.now(UTC):
        raise HTTPException(400, "Ce lien a expiré ou a déjà servi : demandez-en un nouveau.")
    return entrer(session, lien, donnees)


@router.post("/code", response_model=ResultatConnexion)
def verifier_code(donnees: VerificationCode, session: SessionDep):
    """Échange le code à 6 chiffres contre une session.
    Seul le dernier code envoyé compte ; 5 essais faux l'annulent."""
    email = str(donnees.email).lower()
    lien = session.scalar(
        select(m.JetonConnexion)
        .where(
            m.JetonConnexion.email == email,
            m.JetonConnexion.code_empreinte.is_not(None),
            m.JetonConnexion.utilise_le.is_(None),
            m.JetonConnexion.expire_le > datetime.now(UTC),
        )
        .order_by(m.JetonConnexion.cree_le.desc(), m.JetonConnexion.id.desc())
        .limit(1)
        .with_for_update()
    )
    if lien is None:
        raise HTTPException(400, "Ce code a expiré : demandez-en un nouveau.")
    if not secrets.compare_digest(lien.code_empreinte, empreinte_code(lien.empreinte, donnees.code)):
        lien.essais_code += 1
        if lien.essais_code >= ESSAIS_CODE:
            lien.utilise_le = datetime.now(UTC)
            session.commit()
            raise HTTPException(400, "Trop d'essais : ce code ne marche plus, demandez-en un nouveau.")
        session.commit()
        raise HTTPException(400, "Ce code ne correspond pas : vérifiez le dernier e-mail reçu.")
    return entrer(session, lien, donnees)


@router.post("/connexion", response_model=ResultatConnexion)
def connexion(donnees: ConnexionMotDePasse, session: SessionDep):
    """Connexion par mot de passe, pour les comptes qui en ont choisi un."""
    email = str(donnees.email).lower()
    utilisateur = session.scalar(
        select(m.Utilisateur).where(func.lower(m.Utilisateur.email) == email).with_for_update()
    )
    maintenant = datetime.now(UTC)
    if utilisateur is not None and utilisateur.bloque_jusqu_au and utilisateur.bloque_jusqu_au > maintenant:
        raise HTTPException(429, "Trop d'essais : réessayez dans 15 minutes, ou recevez un code par e-mail.")
    # Messages clairs plutôt que neutres (choix de Ben, 27/10) : chacun sait s'il doit créer un compte
    # ou recevoir un code.
    if utilisateur is None:
        raise HTTPException(404, "Aucun compte avec cet e-mail.")
    if utilisateur.mot_de_passe is None:
        raise HTTPException(409, "Ce compte n'a pas encore de mot de passe : recevez un code par e-mail.")
    if not motdepasse.verifier(donnees.mot_de_passe, utilisateur.mot_de_passe):
        utilisateur.essais_mot_de_passe += 1
        if utilisateur.essais_mot_de_passe >= ESSAIS_MOT_DE_PASSE:
            utilisateur.essais_mot_de_passe, utilisateur.bloque_jusqu_au = 0, maintenant + DUREE_BLOCAGE
        session.commit()
        raise HTTPException(401, "Mot de passe incorrect.")
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
