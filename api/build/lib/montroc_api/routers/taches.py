"""Tâches planifiées, appelées par GitHub Actions avec le secret TACHES_SECRET (voir .github/workflows/taches.yml)."""

from fastapi import APIRouter

from .. import services, vues
from ..deps import SecretTaches, SessionDep
from ..schemas import ResultatMathTrade, ResultatTaches
from .echanges import metier

router = APIRouter(prefix="/taches", tags=["tâches planifiées"], dependencies=[SecretTaches])


@router.post("/horaires", response_model=ResultatTaches)
def horaires(session: SessionDep):
    """Toutes les heures : rappels « plus que 12 h », annulation des échanges dont le délai est dépassé."""
    rappels, expires = services.taches_horaires(session)
    session.commit()
    return ResultatTaches(rappels_envoyes=rappels, echanges_expires=expires)


@router.post("/math-trade", response_model=ResultatMathTrade)
def math_trade(session: SessionDep):
    """Chaque nuit : maximum d'objets échangés sur tout le marché ; chaque participant est prévenu."""
    solution, echanges = metier(services.lancer_math_trade, session)
    return ResultatMathTrade(
        optimal=solution.optimal,
        duree_s=solution.duree_s,
        nb_objets_echanges=solution.nb_objets_echanges,
        echanges=[vues.echange(e) for e in echanges],
    )
