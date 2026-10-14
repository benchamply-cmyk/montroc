"""Tâches planifiées, appelées par GitHub Actions avec le secret TACHES_SECRET (voir .github/workflows/taches.yml)."""

from fastapi import APIRouter

from .. import services, vues
from ..deps import SecretTaches, SessionDep
from ..schemas import GrandTrocLecture, ResultatGrandTroc, ResultatTaches
from .echanges import metier

router = APIRouter(prefix="/taches", tags=["tâches planifiées"], dependencies=[SecretTaches])


@router.post("/horaires", response_model=ResultatTaches)
def horaires(session: SessionDep):
    """Toutes les heures : rappels « plus que 12 h », annulation des échanges dont le délai est dépassé."""
    rappels, expires = services.taches_horaires(session)
    session.commit()
    return ResultatTaches(rappels_envoyes=rappels, echanges_expires=expires)


@router.post("/grand-troc", response_model=ResultatGrandTroc)
def grand_troc(session: SessionDep, force: bool = False):
    """Le dimanche à partir de 18 h (heure de Paris) : maximum d'objets échangés sur tout le stock.

    Sans effet avant l'heure ou si le Grand Troc du jour a déjà eu lieu ; ``force`` le lance tout de suite.
    """
    resultat, echanges, lance, message = metier(services.lancer_grand_troc, session, force)
    return ResultatGrandTroc(
        lance=lance,
        message=message,
        grand_troc=GrandTrocLecture.model_validate(resultat) if resultat else None,
        echanges=[vues.echange(e) for e in echanges],
    )
