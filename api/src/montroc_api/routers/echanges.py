"""Échanges : enregistrer une boucle, répondre, terminer, et la passe globale « math trade »."""

from fastapi import APIRouter, HTTPException

from .. import models as m
from .. import services
from ..deps import SessionDep, obtenir_ou_404
from ..schemas import EchangeCreation, EchangeLecture, ReponseTransfert, ResultatMathTrade

router = APIRouter(prefix="/echanges", tags=["échanges"])


def _metier(fonction, session, *args):
    """Exécute une opération métier dans une transaction ; une règle non respectée devient un 409."""
    try:
        resultat = fonction(session, *args)
        session.commit()
        return resultat
    except services.ErreurMetier as e:
        session.commit()  # garde une éventuelle annulation (délai dépassé)
        raise HTTPException(409, str(e)) from e


@router.post("", response_model=EchangeLecture, status_code=201)
def creer(donnees: EchangeCreation, session: SessionDep):
    return _metier(services.proposer_par_objets, session, donnees.objets)


@router.get("/{echange_id}", response_model=EchangeLecture)
def lire(echange_id: int, session: SessionDep):
    return obtenir_ou_404(session, m.Echange, echange_id)


@router.post("/{echange_id}/transferts/{transfert_id}/reponse", response_model=EchangeLecture)
def repondre(echange_id: int, transfert_id: int, donnees: ReponseTransfert, session: SessionDep):
    echange = obtenir_ou_404(session, m.Echange, echange_id)
    return _metier(services.repondre, session, echange, transfert_id, donnees.utilisateur_id, donnees.accepte)


@router.post("/{echange_id}/terminer", response_model=EchangeLecture)
def terminer(echange_id: int, session: SessionDep):
    echange = obtenir_ou_404(session, m.Echange, echange_id)
    return _metier(lambda _s, e: services.terminer(e), session, echange)


@router.post("/math-trade", response_model=ResultatMathTrade)
def math_trade(session: SessionDep):
    """Passe globale : maximum d'objets échangés sur tout le marché (à lancer chaque nuit)."""
    solution, echanges = _metier(services.lancer_math_trade, session)
    return ResultatMathTrade(
        optimal=solution.optimal,
        duree_s=solution.duree_s,
        nb_objets_echanges=solution.nb_objets_echanges,
        echanges=[EchangeLecture.model_validate(e) for e in echanges],
    )
