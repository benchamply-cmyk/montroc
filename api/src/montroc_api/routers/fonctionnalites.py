"""Feature Flag engine : l'état des fonctionnalités, lu par le site et réglé depuis l'onglet Modération."""

from fastapi import APIRouter, HTTPException

from .. import fonctionnalites
from .. import models as m
from ..deps import Moderateur, SessionDep
from ..schemas import FonctionnaliteLecture, FonctionnaliteReglage

router = APIRouter(tags=["fonctionnalités"])


@router.get("/fonctionnalites", response_model=dict[str, bool])
def etats(session: SessionDep):
    """Public : quelles fonctionnalités sont allumées (le site masque les autres)."""
    return fonctionnalites.etats(session)


def _lecture(session, cle: str) -> FonctionnaliteLecture:
    f, choisi = fonctionnalites.CATALOGUE[cle], session.get(m.EtatFonctionnalite, cle)
    return FonctionnaliteLecture(
        cle=cle,
        nom=f.nom,
        description=f.description,
        active=choisi.active if choisi else f.par_defaut,
        par_defaut=f.par_defaut,
        modifie_le=choisi.modifie_le if choisi else None,
        modifie_par=choisi.modifie_par if choisi else None,
    )


@router.get("/moderation/fonctionnalites", response_model=list[FonctionnaliteLecture])
def lister(_: Moderateur, session: SessionDep):
    return [_lecture(session, cle) for cle in fonctionnalites.CATALOGUE]


@router.put("/moderation/fonctionnalites/{cle}", response_model=FonctionnaliteLecture)
def regler(cle: str, donnees: FonctionnaliteReglage, moderateur: Moderateur, session: SessionDep):
    """Allume ou éteint une fonctionnalité, tout de suite, pour tout le monde."""
    if cle not in fonctionnalites.CATALOGUE:
        raise HTTPException(404, f"Fonctionnalité {cle} inconnue.")
    fonctionnalites.regler(session, cle, donnees.active, moderateur.email)
    session.commit()
    return _lecture(session, cle)
