"""E-mails envoyés aux moments clés, par l'API HTTPS de Brevo ou par SMTP (OVH).

Sans réglage d'envoi (en local, dans les tests), rien ne part : le message est écrit dans le
journal et gardé dans ``ENVOYES``, ce qui permet de vérifier les envois dans les tests.
"""

import json
import logging
import smtplib
import ssl
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import make_msgid, parseaddr
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import event
from sqlalchemy.orm import Session

from .config import get_settings

journal = logging.getLogger("montroc.courriels")


@dataclass
class Courriel:
    destinataire: str
    sujet: str
    texte: str


ENVOYES: list[Courriel] = []


def envoyer(destinataire: str, sujet: str, texte: str) -> None:
    """Envoie un e-mail texte. Une panne d'envoi est journalisée sans faire échouer la requête."""
    reglages = get_settings()
    courriel = Courriel(destinataire, sujet, texte + SIGNATURE.format(site=reglages.site_url))
    if not reglages.envoi_configure:
        ENVOYES.append(courriel)
        journal.warning("E-mail non envoyé (envoi non configuré) à %s : %s\n%s", destinataire, sujet, courriel.texte)
        return
    if reglages.brevo_api_key:
        _par_brevo(courriel)
        return

    message = EmailMessage()
    message["From"] = reglages.email_expediteur
    message["To"] = destinataire
    message["Subject"] = sujet
    message["Message-ID"] = make_msgid(domain="troctroc.fr")
    message.set_content(courriel.texte)
    try:
        with smtplib.SMTP_SSL(
            reglages.smtp_hote, reglages.smtp_port, context=ssl.create_default_context(), timeout=20
        ) as smtp:
            smtp.login(reglages.smtp_utilisateur, reglages.smtp_mot_de_passe)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        journal.exception("Échec d'envoi de l'e-mail « %s » à %s", sujet, destinataire)


def _par_brevo(courriel: Courriel) -> None:
    """API transactionnelle de Brevo, en HTTPS : fonctionne là où les ports SMTP sont bloqués."""
    reglages = get_settings()
    nom, adresse = parseaddr(reglages.email_expediteur)
    corps = {
        "sender": {"name": nom or "TrocTroc", "email": adresse},
        "to": [{"email": courriel.destinataire}],
        "subject": courriel.sujet,
        "textContent": courriel.texte,
    }
    requete = Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(corps).encode(),
        headers={"api-key": reglages.brevo_api_key, "content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(requete, timeout=20) as reponse:
            reponse.read()
    except HTTPError as e:
        # Brevo explique son refus (clé invalide, expéditeur non validé…) : le garder dans le journal.
        journal.error("Brevo refuse l'e-mail « %s » (%s) : %s", courriel.sujet, e.code, e.read()[:500])
    except OSError:
        journal.exception("Échec d'envoi (Brevo) de l'e-mail « %s » à %s", courriel.sujet, courriel.destinataire)


SIGNATURE = """

--
TrocTroc, l'échange sans prix ni monnaie
{site}
"""


# Envoi après validation de la transaction : pas d'e-mail pour un échange qui n'a finalement pas été
# enregistré. L'envoi se fait hors de la requête, pour ne pas faire attendre l'utilisateur.
_envois = ThreadPoolExecutor(max_workers=2, thread_name_prefix="courriels")


def apres_validation(session: Session, fonction: Callable[..., None], *args) -> None:
    session.info.setdefault("courriels", []).append((fonction, args))


@event.listens_for(Session, "after_commit")
def _expedier(session: Session) -> None:
    for fonction, args in session.info.pop("courriels", []):
        if get_settings().envoi_configure:
            _envois.submit(fonction, *args)
        else:
            fonction(*args)


@event.listens_for(Session, "after_rollback")
def _oublier(session: Session) -> None:
    session.info.pop("courriels", None)


# Les textes : un seul endroit pour les relire et les corriger.


def lien_magique(email: str, lien: str) -> None:
    envoyer(
        email,
        "Votre lien de connexion à TrocTroc",
        "Bonjour,\n\nPour vous connecter à TrocTroc, ouvrez ce lien (valable 20 minutes, une seule fois) :"
        f"\n\n{lien}\n\n"
        "Si vous n'avez rien demandé, ignorez simplement cet e-mail : personne ne peut se connecter sans ce lien.",
    )


def boucle_vous_attend(email: str, pseudo: str, donne: str, recoit: str, lien: str) -> None:
    envoyer(
        email,
        "Une boucle vous attend",
        f"Bonjour {pseudo},\n\nTroc a trouvé un échange pour vous : vous donnez « {donne} » et vous recevez "
        f"« {recoit} ».\n\nVous avez 48 h pour dire oui ou non : {lien}",
    )


def plus_que_12_h(email: str, pseudo: str, recoit: str, lien: str) -> None:
    envoyer(
        email,
        "Plus que 12 h pour répondre",
        f"Bonjour {pseudo},\n\nL'échange qui vous donnerait « {recoit} » attend encore votre réponse. "
        f"Sans réponse dans 12 h, il sera annulé pour tout le monde.\n\nRépondre : {lien}",
    )


def echange_accepte(email: str, pseudo: str, donne: str, code: str, point_de_depot: str, lien: str) -> None:
    lieu = f"Point de dépôt : {point_de_depot}\n\n" if point_de_depot else ""
    envoyer(
        email,
        "C'est oui pour tout le monde : à vous de déposer",
        f"Bonjour {pseudo},\n\nTout le monde a accepté l'échange. Déposez « {donne} » dans les 7 jours, emballé et "
        f"marqué du code {code}, puis indiquez-le sur TrocTroc.\n\n{lieu}Rien n'est remis tant que tout le monde n'a "
        f"pas déposé.\n\nVoir l'échange : {lien}",
    )


def a_depose(email: str, pseudo: str, deposant: str, restants: int, lien: str) -> None:
    suite = "Plus que vous !" if restants == 1 else f"Encore {restants} dépôts avant de récupérer votre objet."
    envoyer(email, f"{deposant} a déposé", f"Bonjour {pseudo},\n\n{deposant} a déposé son objet. {suite}\n\n{lien}")


def tout_est_depose(email: str, pseudo: str, recoit: str, code: str, point_de_depot: str) -> None:
    lieu = f" au point de dépôt ({point_de_depot})" if point_de_depot else " au point de dépôt"
    envoyer(
        email,
        "Tout est déposé : votre objet vous attend",
        f"Bonjour {pseudo},\n\nTout le monde a déposé. Récupérez « {recoit} »{lieu} avec le code {code}.\n\n"
        "Merci d'avoir troqué !",
    )


def echange_annule(email: str, pseudo: str, raison: str, lien: str) -> None:
    envoyer(
        email,
        "Échange annulé",
        f"Bonjour {pseudo},\n\n{raison} Vos objets redeviennent disponibles et TrocTroc cherche déjà d'autres "
        f"échanges.\n\n{lien}",
    )


def decision_moderation(email: str, sujet: str, texte: str) -> None:
    envoyer(email, sujet, texte)
