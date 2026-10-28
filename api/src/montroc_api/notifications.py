"""Notifications push de l'app mobile, par le service d'Expo (https://exp.host), qui les relaie à Apple et Google.

L'app envoie son jeton Expo à la connexion (``POST /moi/appareils``). Sans envoi actif (tests), rien ne part : la
notification est écrite dans le journal et gardée dans ``ENVOYES``. Comme les e-mails, elles partent après la
validation de la transaction (``courriels.apres_validation``).
"""

import json
import logging
from dataclasses import dataclass, field
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import courriels
from . import models as m
from .config import get_settings
from .db import SessionLocal

journal = logging.getLogger("montroc.notifications")

URL_EXPO = "https://exp.host/--/api/v2/push/send"


@dataclass
class Notification:
    jetons: list[str]
    titre: str
    texte: str
    donnees: dict = field(default_factory=dict)


ENVOYES: list[Notification] = []


def pousser(session: Session, utilisateur: m.Utilisateur, titre: str, texte: str, chemin: str) -> None:
    """Prévient ce membre sur ses téléphones ; ``chemin`` est l'écran de l'app à ouvrir (« /echanges »…)."""
    reglages = get_settings()
    if reglages.courriels_vers and utilisateur.email.lower() != reglages.courriels_vers.lower():
        return  # pré-production : jamais de notification à un vrai membre
    jetons = session.scalars(select(m.AppareilPush.jeton).where(m.AppareilPush.utilisateur_id == utilisateur.id)).all()
    if jetons:
        courriels.apres_validation(session, envoyer, Notification(list(jetons), titre, texte, {"chemin": chemin}))


def envoyer(notification: Notification) -> None:
    """Un message par téléphone. Une panne est journalisée sans faire échouer la requête ; un jeton qu'Expo dit
    périmé (app désinstallée, notifications coupées) est oublié."""
    if not get_settings().push_actifs:
        ENVOYES.append(notification)
        journal.warning("Notification non envoyée (push coupé) : %s — %s", notification.titre, notification.texte)
        return
    messages = [
        {
            "to": j,
            "title": notification.titre,
            "body": notification.texte,
            "data": notification.donnees,
            "sound": "default",
        }
        for j in notification.jetons
    ]
    requete = Request(
        URL_EXPO,
        data=json.dumps(messages).encode(),
        headers={"content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(requete, timeout=20) as reponse:
            tickets = json.loads(reponse.read() or b"{}").get("data", [])
    except HTTPError as e:
        journal.error("Expo refuse la notification « %s » (%s) : %s", notification.titre, e.code, e.read()[:500])
        return
    except OSError:
        journal.exception("Échec d'envoi de la notification « %s »", notification.titre)
        return
    perimes = [
        jeton
        for jeton, ticket in zip(notification.jetons, tickets, strict=False)
        if ticket.get("details", {}).get("error") == "DeviceNotRegistered"
    ]
    if perimes:
        with SessionLocal() as session:
            session.execute(delete(m.AppareilPush).where(m.AppareilPush.jeton.in_(perimes)))
            session.commit()
        journal.info("%d jeton(s) push périmé(s) oublié(s)", len(perimes))
