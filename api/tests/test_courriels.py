"""Envoi réel des e-mails par l'API Brevo (sans réseau : l'appel HTTP est intercepté)."""

import json

from montroc_api import courriels
from montroc_api.config import get_settings


class FausseReponse:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return b'{"messageId":"<x@brevo>"}'


def test_envoi_par_brevo(monkeypatch):
    envoyes = []

    def faux_urlopen(requete, timeout):
        envoyes.append(requete)
        return FausseReponse()

    monkeypatch.setattr(get_settings(), "brevo_api_key", "cle-brevo")
    monkeypatch.setattr(courriels, "urlopen", faux_urlopen)
    courriels.envoyer("ines@exemple.fr", "Une boucle vous attend", "Bonjour Inès")

    assert courriels.ENVOYES == []
    (requete,) = envoyes
    assert requete.full_url == "https://api.brevo.com/v3/smtp/email"
    assert requete.get_header("Api-key") == "cle-brevo"
    corps = json.loads(requete.data)
    assert corps["sender"] == {"name": "Troc", "email": "bonjour@troctroc.fr"}
    assert corps["to"] == [{"email": "ines@exemple.fr"}] and corps["subject"] == "Une boucle vous attend"
    assert corps["textContent"].startswith("Bonjour Inès")
