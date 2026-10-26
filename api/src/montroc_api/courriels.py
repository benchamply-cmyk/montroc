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
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid, parseaddr
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

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
    if reglages.courriels_vers:
        destinataire, sujet = reglages.courriels_vers, f"[pour {destinataire}] {sujet}"
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
    message["Message-ID"] = make_msgid(domain="toptroc.com")
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
        "sender": {"name": nom or "TopTroc", "email": adresse},
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
TopTroc, l'échange sans prix ni monnaie
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
        "Votre lien de connexion à TopTroc",
        "Bonjour,\n\nPour vous connecter à TopTroc, ouvrez ce lien (valable 20 minutes, une seule fois) :"
        f"\n\n{lien}\n\n"
        "Si vous n'avez rien demandé, ignorez simplement cet e-mail : personne ne peut se connecter sans ce lien.",
    )


JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")


def quand(moment: datetime) -> str:
    """« dimanche 25/10 à 12 h », à l'heure de Paris."""
    local = moment.astimezone(ZoneInfo("Europe/Paris"))
    minutes = f"{local.minute:02d}" if local.minute else ""
    return f"{JOURS[local.weekday()]} {local:%d/%m} à {local.hour} h{minutes}"


def boucle_vous_attend(email: str, pseudo: str, donne: str, recoit: str, lien: str, grand_troc: bool = False) -> None:
    trouve = "Le Grand Troc du dimanche a trouvé" if grand_troc else "TopTroc a trouvé"
    envoyer(
        email,
        "Grand Troc : une boucle vous attend" if grand_troc else "Une boucle vous attend",
        f"Bonjour {pseudo},\n\n{trouve} un échange pour vous : vous donnez « {donne} » et vous recevez "
        f"« {recoit} ».\n\nVous avez 48 h pour dire oui ou non : {lien}",
    )


def c_est_un_match(email: str, pseudo: str, avec: str, lien: str) -> None:
    envoyer(
        email,
        f"C'est un match avec {avec}",
        f"Bonjour {pseudo},\n\n{avec} aime un de vos objets, et vous aimez un des siens. Vous pouvez conclure "
        f"l'échange tout de suite, sans attendre dimanche : {lien}",
    )


def accord_propose(email: str, pseudo: str, avec: str, donne: str, recoit: str, lien: str) -> None:
    envoyer(
        email,
        f"{avec} vous propose un échange",
        f"Bonjour {pseudo},\n\nVous avez un match avec {avec}, qui vous propose un échange : vous donnez "
        f"« {donne} » et vous recevez « {recoit} ».\n\nVous avez 48 h pour dire oui ou non : {lien}",
    )


def plus_que_12_h(email: str, pseudo: str, recoit: str, lien: str) -> None:
    envoyer(
        email,
        "Plus que 12 h pour répondre",
        f"Bonjour {pseudo},\n\nL'échange qui vous donnerait « {recoit} » attend encore votre réponse. "
        f"Sans réponse dans 12 h, il sera annulé pour tout le monde.\n\nRépondre : {lien}",
    )


def echange_accepte(
    email: str, pseudo: str, donne: str, code: str, mode: str, lieu: str, receveur: str, lien: str, limite: datetime
) -> None:
    """Au donneur, quand tout le monde a dit oui : comment faire parvenir son objet, selon le mode de remise."""
    if mode == "colis":
        sujet = "C'est oui pour tout le monde : à vous d'envoyer"
        consigne = (
            f"Envoyez « {donne} » à {receveur} par colis, à vos frais, avant {quand(limite)}. L'adresse ou le point "
            f"relais de livraison s'affiche sur TopTroc dès que {receveur} l'a indiqué. Photographiez l'objet "
            "avant de fermer le colis, puis saisissez le transporteur et le numéro de suivi sur TopTroc."
        )
    elif mode == "point_relais":
        sujet = "C'est oui pour tout le monde : à vous de déposer"
        consigne = (
            f"Déposez « {donne} » avant {quand(limite)}, emballé et marqué du code {code}, puis indiquez-le sur "
            f"TopTroc.\n\n{f'Point de dépôt : {lieu}' if lieu else ''}"
        )
    else:
        sujet = "C'est oui pour tout le monde : rencontrez-vous"
        conseil = f"Lieu public conseillé : {lieu}\n\n" if lieu else ""
        consigne = (
            f"Convenez d'un rendez-vous avec {receveur} pour lui remettre « {donne} » en main propre avant "
            f"{quand(limite)}, de préférence dans un lieu public, puis indiquez la remise sur TopTroc.\n\n{conseil}"
        )
    envoyer(
        email,
        sujet,
        f"Bonjour {pseudo},\n\nTout le monde a accepté l'échange. {consigne.strip()}\n\nL'échange est terminé "
        f"quand chacun a remis ou envoyé son objet.\n\nVoir l'échange : {lien}",
    )


def a_depose(email: str, pseudo: str, deposant: str, restants: int, lien: str) -> None:
    suite = "Plus que vous !" if restants == 1 else f"Encore {restants} remises avant la fin de l'échange."
    envoyer(
        email,
        f"{deposant} a remis ou envoyé son objet",
        f"Bonjour {pseudo},\n\n{deposant} a remis ou envoyé son objet. {suite}\n\n{lien}",
    )


def tout_est_depose(
    email: str, pseudo: str, recoit: str, code: str, mode: str, lieu: str, suivi: str | None = None
) -> None:
    if mode == "point_relais":
        ou = f" au point de dépôt ({lieu})" if lieu else " au point de dépôt"
        sujet, texte = (
            "Tout est déposé : votre objet vous attend",
            f"Tout le monde a déposé. Récupérez « {recoit} »{ou} avec le code {code}.",
        )
    elif mode == "colis":
        sujet = "Tout est envoyé : votre colis arrive"
        texte = f"Tout le monde a remis ou envoyé son objet. « {recoit} » arrive par colis" + (
            f" (suivi : {suivi})." if suivi else "."
        )
        texte += " Signalez tout problème dans les 48 h après réception."
    else:
        sujet, texte = "Échange terminé", f"Tout le monde a remis son objet : « {recoit} » est à vous."
    envoyer(email, sujet, f"Bonjour {pseudo},\n\n{texte}\n\nMerci d'avoir troqué !")


def super_jaime(email: str, pseudo: str, de: str, objet: str, lien: str) -> None:
    envoyer(
        email,
        f"{de} a eu un coup de cœur pour « {objet} »",
        f"Bonjour {pseudo},\n\n{de} vous envoie un Super J'aime pour « {objet} ». Regardez ses objets : s'il y en "
        f"a un qui vous plaît, c'est un match.\n\n{lien}",
    )


def echange_annule(email: str, pseudo: str, raison: str, lien: str) -> None:
    envoyer(
        email,
        "Échange annulé",
        f"Bonjour {pseudo},\n\n{raison} Vos objets redeviennent disponibles et TopTroc cherche déjà d'autres "
        f"échanges.\n\n{lien}",
    )


def decision_moderation(email: str, sujet: str, texte: str) -> None:
    envoyer(email, sujet, texte)
