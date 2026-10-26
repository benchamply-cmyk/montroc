"""Envoi réel des e-mails par l'API Brevo (sans réseau : l'appel HTTP est intercepté)."""

import json

from montroc_api import courriels, sms
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
    assert corps["sender"] == {"name": "TrocTroc", "email": "bonjour@troctroc.fr"}
    assert corps["to"] == [{"email": "ines@exemple.fr"}] and corps["subject"] == "Une boucle vous attend"
    assert corps["textContent"].startswith("Bonjour Inès")


def test_preproduction_redirige_les_courriels(monkeypatch):
    """En pré-production, tout part à une seule adresse : jamais aux membres de la copie de la base."""
    monkeypatch.setattr(get_settings(), "courriels_vers", "ben@exemple.fr")
    courriels.envoyer("ines@exemple.fr", "Une boucle vous attend", "Bonjour Inès")

    (courriel,) = [c for c in courriels.ENVOYES if c.sujet.endswith("Une boucle vous attend")]
    assert courriel.destinataire == "ben@exemple.fr"
    assert courriel.sujet == "[pour ines@exemple.fr] Une boucle vous attend"


def test_preproduction_coupe_les_sms(monkeypatch):
    envoyes = []
    monkeypatch.setattr(get_settings(), "brevo_api_key", "cle-brevo")
    monkeypatch.setattr(get_settings(), "sms_actifs", False)
    monkeypatch.setattr(sms, "urlopen", lambda requete, timeout: envoyes.append(requete))
    sms.envoyer("+33600000000", "Le Grand Troc vous propose un échange")

    assert envoyes == []
    assert sms.ENVOYES[-1].numero == "+33600000000"
