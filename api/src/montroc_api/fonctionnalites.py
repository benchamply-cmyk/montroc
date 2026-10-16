"""Feature Flag engine : chaque fonctionnalité du site s'allume ou s'éteint à tout moment, sans redéployer.

Le catalogue ci-dessous déclare les fonctionnalités et leur état par défaut. L'état réel est gardé en base
(table ``fonctionnalites``) dès qu'une modératrice l'a changé depuis l'onglet Modération du site : il
s'applique tout de suite à l'API (les routes de la fonctionnalité répondent 404) et au site (les blocs
marqués ``data-fonctionnalite="…"`` disparaissent). Ajouter une fonctionnalité : voir docs/07-fonctionnalites.md.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m


@dataclass(frozen=True)
class Fonctionnalite:
    cle: str
    nom: str
    description: str
    par_defaut: bool


CATALOGUE: dict[str, Fonctionnalite] = {
    f.cle: f
    for f in (
        Fonctionnalite(
            "match",
            "Le Match",
            "Carrousel « J'aime » / « Non merci » et accords 1 à 1 à tout moment (onglet Match, carte de l'accueil).",
            True,
        ),
        Fonctionnalite(
            "grand_troc",
            "Le Grand Troc du dimanche",
            "Math trade hebdomadaire et repêchage du mardi ; éteint, la tâche planifiée ne lance plus rien.",
            True,
        ),
        Fonctionnalite(
            "import_annonce",
            "Troquer une annonce Vinted ou Leboncoin",
            "Le bloc « Votre annonce ne part pas ? » de l'accueil et le champ « annonce d'origine » d'un objet.",
            True,
        ),
    )
}


def etats(session: Session) -> dict[str, bool]:
    """L'état de chaque fonctionnalité du catalogue : celui choisi en base, sinon celui par défaut."""
    choisis = dict(session.execute(select(m.EtatFonctionnalite.cle, m.EtatFonctionnalite.active)).all())
    return {cle: choisis.get(cle, f.par_defaut) for cle, f in CATALOGUE.items()}


def est_active(session: Session, cle: str) -> bool:
    choisi = session.get(m.EtatFonctionnalite, cle)
    return choisi.active if choisi is not None else CATALOGUE[cle].par_defaut


def regler(session: Session, cle: str, active: bool, par: str) -> m.EtatFonctionnalite:
    etat = session.get(m.EtatFonctionnalite, cle) or m.EtatFonctionnalite(cle=cle)
    etat.active, etat.modifie_par, etat.modifie_le = active, par, datetime.now(UTC)
    session.add(etat)
    return etat
