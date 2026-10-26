"""SMS envoyés quand une boucle est proposée, par l'API SMS transactionnels de Brevo.

Il faut des crédits SMS sur le compte Brevo (même clé BREVO_API_KEY que les e-mails). Sans clé (en local,
dans les tests), rien ne part : le SMS est écrit dans le journal et gardé dans ``ENVOYES``.
"""

import json
import logging
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .config import get_settings

journal = logging.getLogger("montroc.sms")


@dataclass
class Sms:
    numero: str
    texte: str


ENVOYES: list[Sms] = []


def envoyer(numero: str, texte: str) -> None:
    """Envoie un SMS au numéro international (+33…). Une panne est journalisée sans faire échouer la requête."""
    reglages = get_settings()
    if not reglages.brevo_api_key or not reglages.sms_actifs:
        ENVOYES.append(Sms(numero, texte))
        journal.warning("SMS non envoyé (Brevo non configuré ou SMS coupés) à %s : %s", numero, texte)
        return
    corps = {
        "type": "transactional",
        "sender": reglages.sms_expediteur,
        "recipient": numero.lstrip("+"),
        "content": texte,
    }
    requete = Request(
        "https://api.brevo.com/v3/transactionalSMS/send",
        data=json.dumps(corps).encode(),
        headers={"api-key": reglages.brevo_api_key, "content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(requete, timeout=20) as reponse:
            reponse.read()
    except HTTPError as e:
        # Brevo explique son refus (plus de crédits SMS, expéditeur refusé…) : le garder dans le journal.
        journal.error("Brevo refuse le SMS (%s) : %s", e.code, e.read()[:500])
    except OSError:
        journal.exception("Échec d'envoi (Brevo) du SMS à %s", numero)


# Les textes : courts (un SMS fait 70 caractères avec des accents, au-delà il compte double).


def boucle_proposee(numero: str, nb_echanges: int, lien: str, grand_troc: bool) -> None:
    qui = "Le Grand Troc" if grand_troc else "TrocTroc"
    quoi = "un échange" if nb_echanges == 1 else f"{nb_echanges} échanges"
    envoyer(numero, f"{qui} vous propose {quoi}. Vous avez 48 h pour répondre : {lien}")
