"""Tâches planifiées, appelées par GitHub Actions avec le secret TACHES_SECRET (voir .github/workflows/taches.yml)."""

from fastapi import APIRouter

from .. import services, suivis, vues
from ..deps import SecretTaches, SessionDep
from ..schemas import GrandTrocLecture, ResultatGrandTroc, ResultatTaches
from .echanges import metier

router = APIRouter(prefix="/taches", tags=["tâches planifiées"], dependencies=[SecretTaches])


@router.post("/horaires", response_model=ResultatTaches)
def horaires(session: SessionDep):
    """Toutes les heures : rappels « plus que 12 h », annulation des échanges dont le délai est dépassé,
    remplaçants pour qui a été lâché par un refus, puis repêchage du mardi une fois toutes les réponses au
    Grand Troc rentrées, et les alertes du mode visiteur."""
    rappels, expires = services.taches_horaires(session)
    session.flush()
    remplaces = services.remplacements(session)
    session.flush()
    repeches = services.repechage(session)
    services.annoncer_grand_troc(session)  # l'annonce de 18 h, si l'appel du dimanche l'a manquée
    alertes = suivis.alerter(session)  # mode visiteur : nouveaux objets et favoris qui vont s'effacer
    session.commit()
    return ResultatTaches(
        rappels_envoyes=rappels,
        echanges_expires=expires,
        objets_remplaces=remplaces,
        objets_repeches=repeches,
        alertes_visiteurs=alertes,
    )


@router.post("/grand-troc", response_model=ResultatGrandTroc)
def grand_troc(session: SessionDep, force: bool = False):
    """Le dimanche à partir de 17 h (heure de Paris) : maximum d'objets échangés sur tout le stock, montré d'abord
    aux Premium (avant-première), puis annoncé à tous à 18 h.

    Sans effet avant l'heure ou si le Grand Troc du jour a déjà eu lieu ; ``force`` le lance tout de suite.
    """
    resultat, echanges, lance, message = metier(services.lancer_grand_troc, session, force)
    return ResultatGrandTroc(
        lance=lance,
        message=message,
        grand_troc=GrandTrocLecture.model_validate(resultat) if resultat else None,
        echanges=[vues.echange(e) for e in echanges],
    )
