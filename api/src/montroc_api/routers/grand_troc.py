"""Le Grand Troc du dimanche : le rendez-vous hebdomadaire où toutes les boucles sont proposées."""

from datetime import UTC, datetime

from fastapi import APIRouter

from .. import services
from ..config import get_settings
from ..deps import SessionDep
from ..schemas import GrandTrocLecture, InfosGrandTroc

router = APIRouter(prefix="/grand-troc", tags=["grand troc"])


@router.get("", response_model=InfosGrandTroc)
def infos(session: SessionDep):
    """Date du prochain Grand Troc et bilan du dernier (public, pour le compte à rebours de l'accueil)."""
    dernier = services.dernier_grand_troc(session)
    return InfosGrandTroc(
        prochain=services.prochain_grand_troc(datetime.now(UTC)),
        dernier=GrandTrocLecture.model_validate(dernier) if dernier else None,
        echanges_a_la_demande=get_settings().echanges_a_la_demande,
    )
