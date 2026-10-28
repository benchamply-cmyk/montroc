"""Notifications push de l'app : jetons des téléphones, envois au match, à une proposition et au Grand Troc."""

from sqlalchemy import select
from test_api import TACHES, _dimanche

from montroc_api import models as m
from montroc_api import notifications, services
from montroc_api.config import get_settings
from montroc_api.db import SessionLocal

JETON_A = "ExponentPushToken[alice-iphone]"
JETON_B = "ExponentPushToken[bruno-android]"


def _appareil(client, qui, jeton, plateforme="ios"):
    r = client.post("/moi/appareils", json={"jeton": jeton, "plateforme": plateforme}, headers=qui.headers)
    assert r.status_code == 204, r.text


def _pour(jeton):
    return [n for n in notifications.ENVOYES if jeton in n.jetons]


def test_jeton_enregistre_une_fois_et_suit_le_dernier_compte(client, creer):
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    assert client.post("/moi/appareils", json={"jeton": JETON_A, "plateforme": "ios"}).status_code == 401
    for invalide in ({"jeton": "n'importe quoi", "plateforme": "ios"}, {"jeton": JETON_A, "plateforme": "web"}):
        assert client.post("/moi/appareils", json=invalide, headers=alice.headers).status_code == 422
    _appareil(client, alice, JETON_A)
    _appareil(client, alice, JETON_A)  # à chaque ouverture de l'app : sans doublon
    # Le même téléphone, connecté ensuite au compte de Bruno, ne prévient plus Alice.
    _appareil(client, bruno, JETON_A)
    poussette = creer.objet(alice, "enfant", "Poussette")
    velo = creer.objet(bruno, "sport", "Vélo")
    client.post("/match/avis", json={"objet_id": velo, "aime": True}, headers=alice.headers)
    client.post("/match/avis", json={"objet_id": poussette, "aime": True}, headers=bruno.headers)
    assert notifications.ENVOYES == []  # le match prévient Alice, qui n'a plus de téléphone


def test_match_puis_proposition(client, creer, monkeypatch):
    monkeypatch.setattr(services.get_settings(), "echanges_a_la_demande", False)
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    _appareil(client, alice, JETON_A)
    _appareil(client, bruno, JETON_B, "android")
    poussette = creer.objet(alice, "enfant", "Poussette")
    velo = creer.objet(bruno, "sport", "Vélo")

    client.post("/match/avis", json={"objet_id": velo, "aime": True}, headers=alice.headers)
    assert notifications.ENVOYES == []  # pas encore de match
    client.post("/match/avis", json={"objet_id": poussette, "aime": True}, headers=bruno.headers)
    (match,) = _pour(JETON_A)
    assert match.titre == "C'est un match !" and "bruno" in match.texte and match.donnees == {"chemin": "/echanges"}
    assert _pour(JETON_B) == []  # Bruno vient d'aimer : il le voit à l'écran

    r = client.post("/match/accord", json={"mon_objet_id": poussette, "son_objet_id": velo}, headers=alice.headers)
    echange_id = r.json()["id"]
    (proposition,) = _pour(JETON_B)
    assert proposition.titre == "alice vous propose un échange" and "« Poussette »" in proposition.texte
    assert proposition.donnees == {"chemin": f"/echange/{echange_id}"}


def test_une_notification_par_personne_au_grand_troc(client, creer, monkeypatch):
    a, b = creer.utilisateur("alice"), creer.utilisateur("bruno")
    c, d = creer.utilisateur("chloe"), creer.utilisateur("david")
    _appareil(client, a, JETON_A)
    _appareil(client, b, JETON_B)
    creer.objet(a, "enfant")
    creer.objet(a, "culture")
    creer.objet(b, "sport")
    creer.objet(c, "maison")
    creer.objet(d, "mode")
    creer.souhait(a, "sport")
    creer.souhait(b, "enfant")
    creer.souhait(a, "mode")
    creer.souhait(d, "culture")
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 5))
    assert len(client.post("/taches/grand-troc", headers=TACHES).json()["echanges"]) == 2
    (pour_alice,) = _pour(JETON_A)
    assert pour_alice.titre == "Le Grand Troc est tombé" and "2 échanges" in pour_alice.texte
    assert pour_alice.donnees == {"chemin": "/echanges"}
    (pour_bruno,) = _pour(JETON_B)
    assert "un échange" in pour_bruno.texte and pour_bruno.donnees["chemin"].startswith("/echange/")


def test_deconnexion_et_preproduction(client, creer, monkeypatch):
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    _appareil(client, alice, JETON_A)
    _appareil(client, bruno, JETON_B)
    # Pré-production : seul le compte de COURRIELS_VERS reçoit des notifications.
    monkeypatch.setattr(get_settings(), "courriels_vers", "bruno@exemple.fr")
    poussette = creer.objet(alice, "enfant")
    velo = creer.objet(bruno, "sport")
    client.post("/match/avis", json={"objet_id": poussette, "aime": True}, headers=bruno.headers)
    client.post("/match/avis", json={"objet_id": velo, "aime": True}, headers=alice.headers)
    assert _pour(JETON_A) == [] and len(_pour(JETON_B)) == 1
    monkeypatch.setattr(get_settings(), "courriels_vers", "")

    # Se déconnecter ferme toutes les sessions : les téléphones ne sont plus prévenus.
    assert client.post("/auth/deconnexion", headers=bruno.headers).status_code == 204
    with SessionLocal() as session:
        assert session.scalars(select(m.AppareilPush.jeton)).all() == [JETON_A]
