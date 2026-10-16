"""Feature Flag engine : allumer et éteindre une fonctionnalité sans redéployer."""

from test_api import TACHES


def test_etat_par_defaut_public(client):
    assert client.get("/fonctionnalites").json() == {"match": True, "grand_troc": True, "import_annonce": True}


def test_eteindre_le_match_ferme_ses_routes(client, creer):
    modo = creer.utilisateur("modo", email="modo@exemple.fr")
    alice = creer.utilisateur("alice")
    assert client.get("/match", headers=alice.headers).status_code == 200

    r = client.put("/moderation/fonctionnalites/match", json={"active": False}, headers=modo.headers)
    assert r.status_code == 200, r.text
    assert r.json()["active"] is False and r.json()["modifie_par"] == "modo@exemple.fr"
    assert client.get("/fonctionnalites").json()["match"] is False
    r = client.get("/match/carrousel", headers=alice.headers)
    assert r.status_code == 404 and "désactivé" in r.json()["detail"]

    client.put("/moderation/fonctionnalites/match", json={"active": True}, headers=modo.headers)
    assert client.get("/match", headers=alice.headers).status_code == 200


def test_grand_troc_eteint_ne_lance_rien(client, creer):
    modo = creer.utilisateur("modo", email="modo@exemple.fr")
    client.put("/moderation/fonctionnalites/grand_troc", json={"active": False}, headers=modo.headers)
    r = client.post("/taches/grand-troc?force=true", headers=TACHES).json()
    assert r["lance"] is False and r["message"] == "Le Grand Troc est désactivé."
    assert client.post("/taches/horaires", headers=TACHES).json()["objets_repeches"] is None


def test_reserve_a_la_moderation(client, creer):
    alice = creer.utilisateur("alice")
    assert client.get("/moderation/fonctionnalites", headers=alice.headers).status_code == 403
    assert (
        client.put("/moderation/fonctionnalites/match", json={"active": False}, headers=alice.headers).status_code
        == 403
    )
    modo = creer.utilisateur("modo", email="modo@exemple.fr")
    liste = client.get("/moderation/fonctionnalites", headers=modo.headers).json()
    assert [f["cle"] for f in liste] == ["match", "grand_troc", "import_annonce"]
    assert (
        client.put("/moderation/fonctionnalites/inconnue", json={"active": True}, headers=modo.headers).status_code
        == 404
    )
