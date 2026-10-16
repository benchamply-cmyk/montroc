"""Le Match : le carrousel d'objets, « J'aime » / « Non merci », mes matchs et l'accord 1 à 1."""

from fastapi import APIRouter, Query

from .. import matchs, vues
from ..deps import SessionDep, UtilisateurConnecte, exiger
from ..schemas import AccordCreation, AvisCreation, CarteMatch, EchangeLecture, MatchLecture, ResultatAvis
from .echanges import metier

router = APIRouter(prefix="/match", tags=["match"], dependencies=[exiger("match")])


@router.get("/carrousel", response_model=list[CarteMatch])
def carrousel(utilisateur: UtilisateurConnecte, session: SessionDep, limite: int = Query(20, ge=1, le=50)):
    """Les objets qui correspondent à mes souhaits, ceux qui feraient un match tout de suite d'abord."""
    return [vues.carte(c) for c in matchs.carrousel(session, utilisateur, limite)]


@router.post("/avis", response_model=ResultatAvis)
def donner_avis(donnees: AvisCreation, utilisateur: UtilisateurConnecte, session: SessionDep):
    """« J'aime » ou « Non merci ». Si l'autre aime déjà un de mes objets, c'est un match."""
    match = metier(matchs.donner_avis, session, utilisateur, donnees.objet_id, donnees.aime)
    return ResultatAvis(match=vues.match(match) if match else None)


@router.get("", response_model=list[MatchLecture])
def mes_matchs(utilisateur: UtilisateurConnecte, session: SessionDep):
    return [vues.match(x) for x in matchs.matchs(session, utilisateur)]


@router.post("/accord", response_model=EchangeLecture, status_code=201)
def conclure(donnees: AccordCreation, utilisateur: UtilisateurConnecte, session: SessionDep):
    """Je propose l'échange 1 à 1 à mon match : ma part est acceptée, l'autre a 48 h pour dire oui."""
    echange = metier(matchs.conclure, session, utilisateur, donnees.mon_objet_id, donnees.son_objet_id)
    return vues.echange(echange, utilisateur.id)
