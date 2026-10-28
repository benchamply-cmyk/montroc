"""L'assistant du site (sans réseau : le client Anthropic est remplacé par un faux)."""

from types import SimpleNamespace

import pytest

from montroc_api import assistant
from montroc_api.config import get_settings


class FauxMessages:
    def __init__(self, texte="Le Grand Troc a lieu chaque dimanche à 18 h.", stop="end_turn"):
        self.appels, self.texte, self.stop = [], texte, stop

    def create(self, **requete):
        self.appels.append(requete)
        return SimpleNamespace(
            model=requete["model"],
            stop_reason=self.stop,
            content=[SimpleNamespace(type="text", text=self.texte)] if self.stop != "refusal" else [],
            usage=SimpleNamespace(input_tokens=10, cache_read_input_tokens=3000, output_tokens=20),
        )


@pytest.fixture
def faux(monkeypatch):
    messages = FauxMessages()
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "cle-anthropic")
    monkeypatch.setattr(assistant, "_client", lambda cle: SimpleNamespace(beta=SimpleNamespace(messages=messages)))
    assistant.QUOTAS.vider()
    yield messages
    assistant.QUOTAS.vider()


def question(texte="C'est quoi le Grand Troc ?", **extra):
    return {"messages": [{"role": "user", "contenu": texte}], **extra}


def test_eteint_sans_cle(client):
    assert client.get("/assistant").json() == {"actif": False}
    assert client.post("/assistant", json=question()).status_code == 503


def test_repond_avec_le_contexte_de_toptroc(client, faux):
    assert client.get("/assistant").json() == {"actif": True}
    r = client.post("/assistant", json=question(langue="en", page="/english/grand-troc/"))
    assert r.status_code == 200, r.text
    assert r.json() == {"reponse": "Le Grand Troc a lieu chaque dimanche à 18 h."}
    (appel,) = faux.appels
    assert appel["model"] == "claude-opus-5-5"
    assert appel["output_config"] == {"effort": "low"}
    assert appel["fallbacks"] == "default" and appel["betas"] == ["server-side-fallback-2026-07-01"]
    consignes, contexte = appel["system"]
    # Le texte système est identique d'une question à l'autre (mis en cache) et contient les connaissances.
    assert consignes["cache_control"] == {"type": "ephemeral"}
    for mot in ("Grand Troc", "Match", "Troc Premium", "Bricolage & Jardin", "contact@toptroc.com", "5,99 €"):
        assert mot in consignes["text"]
    assert "anglais" in contexte["text"] and "/english/grand-troc/" in contexte["text"]
    assert appel["messages"] == [{"role": "user", "content": "C'est quoi le Grand Troc ?"}]


def test_coordonnees_masquees_avant_envoi(client, faux):
    texte = "Je suis ines@exemple.fr, appelez-moi au 06 12 34 56 78 ou au +33 6 12 34 56 78"
    client.post("/assistant", json=question(texte))
    envoye = faux.appels[0]["messages"][0]["content"]
    assert "ines@exemple.fr" not in envoye and "12 34" not in envoye
    assert envoye.count("[téléphone masqué]") == 2 and "[e-mail masqué]" in envoye


def test_conversation_validee(client, faux):
    longue = {"messages": [{"role": "user", "contenu": "x"}, {"role": "assistant", "contenu": "y"}] * 10 + []}
    assert client.post("/assistant", json=longue).status_code == 422  # se termine par l'assistant
    assert client.post("/assistant", json=question("x" * 1001)).status_code == 422
    trop = {"messages": [{"role": "user", "contenu": "x"}] * 21}
    assert client.post("/assistant", json=trop).status_code == 422
    assert client.post("/assistant", json=question(langue="de")).status_code == 422
    assert faux.appels == []


def test_quotas_par_ip_et_par_jour(client, faux, monkeypatch):
    monkeypatch.setattr(get_settings(), "assistant_questions_par_heure", 2)
    entete = {"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}
    assert client.post("/assistant", json=question(), headers=entete).status_code == 200
    assert client.post("/assistant", json=question(), headers=entete).status_code == 200
    assert client.post("/assistant", json=question(), headers=entete).status_code == 429
    # Une autre adresse passe encore, jusqu'au plafond du jour.
    monkeypatch.setattr(get_settings(), "assistant_questions_par_jour", 3)
    assert client.post("/assistant", json=question(), headers={"X-Forwarded-For": "198.51.100.2"}).status_code == 200
    r = client.post("/assistant", json=question(), headers={"X-Forwarded-For": "198.51.100.3"})
    assert r.status_code == 429 and "demain" in r.json()["detail"]


def test_refus_et_haiku_sans_repli(client, faux, monkeypatch):
    faux.stop = "refusal"
    r = client.post("/assistant", json=question(langue="es"))
    assert r.json()["reponse"].startswith("No puedo responder")
    monkeypatch.setattr(get_settings(), "assistant_modele", "claude-haiku-5-5")
    faux.stop = "end_turn"
    client.post("/assistant", json=question())
    assert "fallbacks" not in faux.appels[-1] and "betas" not in faux.appels[-1]


def test_erreur_anthropic(client, faux, monkeypatch):
    import anthropic

    def panne(**_):
        raise anthropic.APIConnectionError(request=None)

    monkeypatch.setattr(faux, "create", panne)
    assert client.post("/assistant", json=question()).status_code == 503
