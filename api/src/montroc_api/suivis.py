"""Mode visiteur : suivre ses recherches et ses favoris sans compte, par e-mail ou par SMS.

Le navigateur du visiteur garde ses recherches et ses favoris (24 h) ; il peut en confier une copie à TopTroc avec
un e-mail ou un téléphone. Après confirmation (double opt-in), la tâche horaire lui écrit au plus une fois par jour :
les nouveaux objets qui répondent à ses recherches, et un rappel avant que ses favoris s'effacent, pour l'inviter à
créer son compte. Les demandes non confirmées s'effacent après 7 jours, les suivis sans nouvelles après 6 mois.
"""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from . import courriels, sms
from . import models as m
from .config import get_settings
from .deps import empreinte
from .routers.objets import requete_objets
from .schemas import DemandeSuivi, ListesSuivies
from .services import ErreurMetier

DUREE_FAVORI = timedelta(hours=24)  # comme dans le navigateur (web/visiteur.js)
RAPPEL_FAVORIS_APRES = timedelta(hours=18)  # le rappel part dans les 6 dernières heures d'un favori
ECART_ALERTES = timedelta(hours=20)  # au plus une alerte par jour
DEMANDES_PAR_HEURE = 3
DUREE_CONFIRMATION = timedelta(days=7)
DUREE_SANS_NOUVELLES = timedelta(days=180)
NOUVEAUTES_MAX = 10


def _maintenant() -> datetime:
    return datetime.now(UTC)


def _lien(fragment: str) -> str:
    return f"{get_settings().site_url}/#{fragment}"


def _listes(donnees: ListesSuivies) -> tuple[list, list]:
    return (
        [r.model_dump() for r in donnees.recherches if r.q.strip() or r.categorie],
        [{"objet_id": f.objet_id, "ajoute_le": f.ajoute_le.isoformat()} for f in donnees.favoris],
    )


def demander(session: Session, donnees: DemandeSuivi) -> None:
    """Enregistre une demande de suivi et envoie le lien de confirmation (par e-mail, sinon par SMS)."""
    email = str(donnees.email).lower() if donnees.email else None
    contact = m.SuiviVisiteur.email == email if email else m.SuiviVisiteur.telephone == donnees.telephone
    recentes = session.scalar(
        select(func.count()).where(contact, m.SuiviVisiteur.cree_le > _maintenant() - timedelta(hours=1))
    )
    if recentes >= DEMANDES_PAR_HEURE:
        raise ErreurMetier(
            "Plusieurs demandes viennent d'être envoyées : regardez vos messages, ou réessayez dans une heure."
        )
    jeton = secrets.token_urlsafe(32)
    recherches, favoris = _listes(donnees)
    session.add(
        m.SuiviVisiteur(
            email=email,
            telephone=None if email else donnees.telephone,
            empreinte=empreinte(jeton),
            jeton_arret=secrets.token_urlsafe(24),
            recherches=recherches,
            favoris=favoris,
        )
    )
    lien = _lien(f"suivi={jeton}")
    if email:
        courriels.apres_validation(session, courriels.suivi_a_confirmer, email, lien)
    else:
        courriels.apres_validation(session, sms.suivi_a_confirmer, donnees.telephone, lien)


def trouver(session: Session, jeton: str) -> m.SuiviVisiteur | None:
    suivi = session.scalar(select(m.SuiviVisiteur).where(m.SuiviVisiteur.empreinte == empreinte(jeton)))
    if suivi and suivi.confirme_le is None and suivi.cree_le < _maintenant() - DUREE_CONFIRMATION:
        return None
    return suivi


def confirmer(session: Session, suivi: m.SuiviVisiteur) -> None:
    """Le clic sur le lien reçu : le suivi devient actif et remplace les précédents du même contact."""
    if suivi.confirme_le is None:
        suivi.confirme_le = _maintenant()
        contact = m.SuiviVisiteur.email == suivi.email if suivi.email else m.SuiviVisiteur.telephone == suivi.telephone
        session.execute(delete(m.SuiviVisiteur).where(contact, m.SuiviVisiteur.id != suivi.id))


def mettre_a_jour(suivi: m.SuiviVisiteur, donnees: ListesSuivies) -> None:
    suivi.recherches, suivi.favoris = _listes(donnees)
    suivi.mis_a_jour_le = _maintenant()


def _nouveautes(session: Session, suivi: m.SuiviVisiteur, depuis: datetime) -> list[m.Objet]:
    vus: dict[int, m.Objet] = {}
    for r in suivi.recherches:
        requete = requete_objets(r.get("categorie"), None, r.get("q")).where(m.Objet.cree_le > depuis)
        for objet in session.scalars(requete.limit(NOUVEAUTES_MAX)):
            vus.setdefault(objet.id, objet)
    return sorted(vus.values(), key=lambda o: o.cree_le, reverse=True)[:NOUVEAUTES_MAX]


def _favoris_bientot_effaces(suivi: m.SuiviVisiteur, maintenant: datetime) -> list[datetime]:
    """Favoris dans leurs 6 dernières heures, pas encore rappelés."""
    dates = []
    for f in suivi.favoris:
        ajoute = datetime.fromisoformat(f["ajoute_le"])
        if ajoute.tzinfo is None:
            ajoute = ajoute.replace(tzinfo=UTC)
        rappele = suivi.rappel_favoris_le is not None and suivi.rappel_favoris_le >= ajoute
        if maintenant - DUREE_FAVORI < ajoute <= maintenant - RAPPEL_FAVORIS_APRES and not rappele:
            dates.append(ajoute)
    return dates


def alerter(session: Session) -> int:
    """Tâche horaire : purge, puis une alerte par visiteur confirmé qui a du nouveau. Renvoie le nombre d'alertes."""
    maintenant = _maintenant()
    session.execute(
        delete(m.SuiviVisiteur).where(
            or_(
                (m.SuiviVisiteur.confirme_le.is_(None)) & (m.SuiviVisiteur.cree_le < maintenant - DUREE_CONFIRMATION),
                m.SuiviVisiteur.mis_a_jour_le < maintenant - DUREE_SANS_NOUVELLES,
            )
        )
    )
    suivis = session.scalars(
        select(m.SuiviVisiteur).where(
            m.SuiviVisiteur.confirme_le.is_not(None),
            or_(
                m.SuiviVisiteur.derniere_alerte_le.is_(None),
                m.SuiviVisiteur.derniere_alerte_le < maintenant - ECART_ALERTES,
            ),
        )
    ).all()
    envoyees = 0
    for suivi in suivis:
        depuis = max(d for d in (suivi.confirme_le, suivi.derniere_alerte_le) if d is not None)
        objets = _nouveautes(session, suivi, depuis)
        effaces = _favoris_bientot_effaces(suivi, maintenant)
        if not objets and not effaces:
            continue
        lien = _lien("favoris")
        if suivi.email:
            courriels.apres_validation(
                session,
                courriels.alerte_visiteur,
                suivi.email,
                [f"{o.titre} : {_lien(f'objet-{o.id}')}" for o in objets],
                len(effaces),
                lien,
                _lien(f"suivi-arret={suivi.jeton_arret}"),
            )
        else:
            courriels.apres_validation(session, sms.alerte_visiteur, suivi.telephone, len(objets), len(effaces), lien)
        suivi.derniere_alerte_le = maintenant
        if effaces:
            suivi.rappel_favoris_le = max(effaces)
        envoyees += 1
    return envoyees
