"""Le Match : le carrousel d'objets, « J'aime » / « Non merci », mes matchs et l'accord 1 à 1."""

from fastapi import APIRouter, Query
from sqlalchemy import select

from .. import matchs, vues
from .. import models as m
from ..deps import SessionDep, UtilisateurConnecte
from ..schemas import (
    AccordCreation,
    AvisCreation,
    BoucleProposee,
    CarteMatch,
    EchangeCreation,
    EchangeLecture,
    MatchLecture,
    ResultatAvis,
)
from .echanges import metier

router = APIRouter(prefix="/match", tags=["match"])


@router.get("/carrousel", response_model=list[CarteMatch])
def carrousel(utilisateur: UtilisateurConnecte, session: SessionDep, limite: int = Query(20, ge=1, le=50)):
    """Les objets qui correspondent à mes souhaits, ceux qui feraient un match tout de suite d'abord."""
    return [vues.carte(c, utilisateur) for c in matchs.carrousel(session, utilisateur, limite)]


@router.post("/avis", response_model=ResultatAvis)
def donner_avis(donnees: AvisCreation, utilisateur: UtilisateurConnecte, session: SessionDep):
    """« J'aime » ou « Non merci ». Si l'autre aime déjà un de mes objets, c'est un match."""
    match = metier(matchs.donner_avis, session, utilisateur, donnees.objet_id, donnees.aime, donnees.super_jaime)
    return ResultatAvis(match=vues.match(match) if match else None)


@router.get("/avis", response_model=list[int])
def mes_j_aime(utilisateur: UtilisateurConnecte, session: SessionDep):
    """Les objets que j'aime (le cœur), pour l'afficher plein sur les cartes."""
    return session.scalars(
        select(m.Avis.objet_id).where(m.Avis.utilisateur_id == utilisateur.id, m.Avis.aime.is_(True))
    ).all()


@router.delete("/avis/{objet_id}", status_code=204)
def retour_arriere(objet_id: int, utilisateur: UtilisateurConnecte, session: SessionDep):
    """Retire un « J'aime » (le cœur), ou annule un « Non merci » (retour arrière, Troc Premium)."""
    metier(matchs.retour_arriere, session, utilisateur, objet_id)


@router.get("", response_model=list[MatchLecture])
def mes_matchs(utilisateur: UtilisateurConnecte, session: SessionDep):
    return [vues.match(x) for x in matchs.matchs(session, utilisateur)]


@router.post("/accord", response_model=EchangeLecture, status_code=201)
def conclure(donnees: AccordCreation, utilisateur: UtilisateurConnecte, session: SessionDep):
    """Je propose l'échange 1 à 1 à mon match : ma part est acceptée, l'autre a 48 h pour dire oui."""
    echange = metier(matchs.conclure, session, utilisateur, donnees.mon_objet_id, donnees.son_objet_id)
    return vues.echange(echange, utilisateur.id)


@router.get("/boucles", response_model=list[BoucleProposee])
def boucles_a_trois(utilisateur: UtilisateurConnecte, session: SessionDep, limite: int = Query(5, ge=1, le=20)):
    """Le Match à trois : les boucles à trois possibles tout de suite, où chacun reçoit ce qu'il a demandé ou aimé."""
    return vues.boucles(session, matchs.boucles_a_trois(session, utilisateur, limite))


@router.post("/boucle", response_model=EchangeLecture, status_code=201)
def conclure_boucle(donnees: EchangeCreation, utilisateur: UtilisateurConnecte, session: SessionDep):
    """Je propose une boucle à trois (ses objets dans l'ordre) : ma part est acceptée, les autres ont 48 h."""
    echange = metier(matchs.conclure_boucle, session, utilisateur, donnees.objets)
    return vues.echange(echange, utilisateur.id)
