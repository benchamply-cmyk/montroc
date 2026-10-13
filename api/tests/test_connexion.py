"""Connexion par lien magique et protection des routes personnelles."""

from datetime import UTC, datetime, timedelta

from conftest import jeton_du_dernier_lien
from sqlalchemy import text

from montroc_api import courriels
from montroc_api.db import engine


def test_premiere_connexion_demande_un_pseudo(client):
    assert client.post("/auth/lien", json={"email": "Ines@Exemple.fr"}).status_code == 202
    courriel = courriels.ENVOYES[-1]
    assert courriel.destinataire == "ines@exemple.fr" and courriel.sujet == "Votre lien de connexion à Troc"
    assert "https://troctroc.fr/#connexion=" in courriel.texte
    jeton = jeton_du_dernier_lien("ines@exemple.fr")

    r = client.post("/auth/verifier", json={"jeton": jeton}).json()
    assert r == {"inscription_requise": True, "email": "ines@exemple.fr", "jeton": None, "utilisateur": None}

    r = client.post("/auth/verifier", json={"jeton": jeton, "pseudo": "Inès", "zone": "Marseille"})
    assert r.status_code == 200
    corps = r.json()
    assert corps["utilisateur"]["pseudo"] == "Inès" and not corps["utilisateur"]["est_moderateur"]
    moi = client.get("/moi", headers={"Authorization": f"Bearer {corps['jeton']}"}).json()
    assert moi["email"] == "ines@exemple.fr"

    # Le lien ne sert qu'une fois.
    assert client.post("/auth/verifier", json={"jeton": jeton, "pseudo": "Autre"}).status_code == 400


def test_reconnexion_sans_pseudo(client, creer):
    alice = creer.utilisateur("alice")
    client.post("/auth/lien", json={"email": "ALICE@exemple.fr"})
    r = client.post("/auth/verifier", json={"jeton": jeton_du_dernier_lien("alice@exemple.fr")}).json()
    assert r["utilisateur"]["id"] == alice.id and r["jeton"]


def test_lien_expire_ou_faux(client):
    client.post("/auth/lien", json={"email": "bob@exemple.fr"})
    jeton = jeton_du_dernier_lien("bob@exemple.fr")
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE jetons_connexion SET expire_le = :t"), {"t": datetime.now(UTC) - timedelta(seconds=1)}
        )
    assert client.post("/auth/verifier", json={"jeton": jeton, "pseudo": "bob"}).status_code == 400
    assert client.post("/auth/verifier", json={"jeton": "x" * 43, "pseudo": "bob"}).status_code == 400


def test_pseudo_deja_pris(client, creer):
    creer.utilisateur("alice")
    client.post("/auth/lien", json={"email": "autre@exemple.fr"})
    r = client.post("/auth/verifier", json={"jeton": jeton_du_dernier_lien("autre@exemple.fr"), "pseudo": "ALICE"})
    assert r.status_code == 409


def test_trop_de_liens(client):
    for _ in range(5):
        assert client.post("/auth/lien", json={"email": "bob@exemple.fr"}).status_code == 202
    assert client.post("/auth/lien", json={"email": "bob@exemple.fr"}).status_code == 429
    assert client.post("/auth/lien", json={"email": "pas-un-email"}).status_code == 422


def test_routes_personnelles_protegees(client, creer):
    assert client.get("/moi").status_code == 401
    assert client.get("/moi/objets").status_code == 401
    assert client.post("/echanges", json={"objets": [1, 2]}).status_code == 401
    assert client.get("/moi", headers={"Authorization": "Bearer invente"}).status_code == 401
    alice = creer.utilisateur("alice")
    assert client.post("/auth/deconnexion", headers=alice.headers).status_code == 204
    assert client.get("/moi", headers=alice.headers).status_code == 401


def test_modifier_et_supprimer_mon_compte(client, creer):
    alice = creer.utilisateur("alice")
    creer.utilisateur("bruno")
    assert client.patch("/moi", json={"pseudo": "Bruno"}, headers=alice.headers).status_code == 409
    assert client.patch("/moi", json={"zone": "Paris"}, headers=alice.headers).json()["zone"] == "Paris"
    assert client.delete("/moi", headers=alice.headers).status_code == 204
    assert client.get(f"/utilisateurs/{alice.id}").status_code == 404
