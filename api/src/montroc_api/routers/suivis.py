"""Mode visiteur : suivre ses recherches et ses favoris par e-mail ou par SMS, sans compte (voir suivis.py)."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .. import models as m
from .. import suivis
from ..deps import SessionDep
from ..schemas import DemandeSuivi, ListesSuivies, SuiviLecture
from .echanges import metier

router = APIRouter(prefix="/suivis", tags=["mode visiteur"])


def _lecture(suivi: m.SuiviVisiteur) -> SuiviLecture:
    return SuiviLecture(
        email=suivi.email,
        telephone=suivi.telephone,
        confirme_le=suivi.confirme_le,
        recherches=suivi.recherches,
        favoris=suivi.favoris,
    )


def _suivi(session, jeton: str) -> m.SuiviVisiteur:
    suivi = suivis.trouver(session, jeton)
    if suivi is None:
        raise HTTPException(
            404, "Ce lien de suivi n'est plus valable : renseignez à nouveau votre e-mail ou téléphone."
        )
    return suivi


@router.post("", status_code=202)
def demander(donnees: DemandeSuivi, session: SessionDep):
    """Envoie le lien de confirmation. Rien d'autre ne part tant qu'il n'a pas été ouvert."""
    metier(suivis.demander, session, donnees)
    return {"message": "Lien de confirmation envoyé."}


@router.post("/{jeton}/confirmer", response_model=SuiviLecture)
def confirmer(jeton: str, session: SessionDep):
    suivi = _suivi(session, jeton)
    suivis.confirmer(session, suivi)
    session.commit()
    return _lecture(suivi)


@router.get("/{jeton}", response_model=SuiviLecture)
def lire(jeton: str, session: SessionDep):
    return _lecture(_suivi(session, jeton))


@router.put("/{jeton}", response_model=SuiviLecture)
def mettre_a_jour(jeton: str, donnees: ListesSuivies, session: SessionDep):
    """Le navigateur envoie ses recherches et ses favoris à jour : les alertes suivent."""
    suivi = _suivi(session, jeton)
    suivis.mettre_a_jour(suivi, donnees)
    session.commit()
    return _lecture(suivi)


@router.delete("/{jeton}", status_code=204)
def arreter(jeton: str, session: SessionDep):
    """Ne plus être suivi : tout est effacé (depuis le site, avec le jeton du navigateur)."""
    session.delete(_suivi(session, jeton))
    session.commit()


@router.post("/arret/{jeton_arret}", status_code=204)
def arreter_par_lien(jeton_arret: str, session: SessionDep):
    """Le lien « Ne plus recevoir ces alertes » de chaque e-mail. Même réponse si le suivi n'existe plus."""
    suivi = session.scalar(select(m.SuiviVisiteur).where(m.SuiviVisiteur.jeton_arret == jeton_arret))
    if suivi is not None:
        session.delete(suivi)
        session.commit()
