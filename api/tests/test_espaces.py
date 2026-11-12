"""Espace réservé aux salariés (offre Espace salariés, ou Résidences) : rejoindre avec son e-mail professionnel,
objets réservés aux collègues, remise sur place, bilan de l'espace."""

from conftest import PHOTO

MODO = {"email": "modo@exemple.fr"}
ACME = {"slug": "acme", "nom": "ACME Marseille", "domaines": ["@ACME.fr"], "lieu_de_remise": "Accueil du siège, bât. B"}


def _objet(client, qui, categorie, reserve=False):
    corps = {
        "categorie_slug": categorie,
        "titre": categorie,
        "etat": "bon",
        "photo_url": PHOTO,
        "reserve_espace": reserve,
    }
    r = client.post("/moi/objets", json=corps, headers=qui.headers)
    assert r.status_code == 201, r.text
    return r.json()


def _espace(client, creer):
    modo = creer.utilisateur("modo", email="modo@exemple.fr")
    r = client.post("/moderation/espaces", json=ACME, headers=modo.headers)
    assert r.status_code == 201, r.text
    assert r.json()["domaines"] == ["acme.fr"]
    return modo, r.json()


def test_creer_et_rejoindre(client, creer):
    modo, espace = _espace(client, creer)
    alice = creer.utilisateur("alice", email="alice@acme.fr")
    bob = creer.utilisateur("bob")
    assert client.post("/moderation/espaces", json=ACME, headers=alice.headers).status_code == 403
    assert client.post("/moderation/espaces", json=ACME, headers=modo.headers).status_code == 409
    assert client.get("/espaces/acme").json()["lieu_de_remise"] == "Accueil du siège, bât. B"
    assert client.post("/espaces/acme/rejoindre", headers=bob.headers).status_code == 403
    r = client.post("/espaces/acme/rejoindre", headers=alice.headers)
    assert r.status_code == 200 and r.json()["espace"]["nom"] == "ACME Marseille"
    assert client.get("/moi", headers=alice.headers).json()["espace"]["slug"] == "acme"
    assert client.get("/moderation/espaces", headers=modo.headers).json()[0]["membres"] == 1
    # Un espace fermé ne se rejoint plus.
    client.put(f"/moderation/espaces/{espace['id']}", json={**ACME, "actif": False}, headers=modo.headers)
    assert client.get("/espaces/acme").status_code == 404


def test_objets_reserves_aux_collegues(client, creer):
    modo, _ = _espace(client, creer)
    alice = creer.utilisateur("alice", email="alice@acme.fr")
    carole = creer.utilisateur("carole", email="carole@acme.fr")
    bob = creer.utilisateur("bob")
    assert (
        client.post(
            "/moi/objets",
            json={"categorie_slug": "maison", "titre": "x", "etat": "bon", "photo_url": PHOTO, "reserve_espace": True},
            headers=bob.headers,
        ).status_code
        == 409
    )  # bob n'a pas d'espace
    for qui in (alice, carole):
        client.post("/espaces/acme/rejoindre", headers=qui.headers)
    reserve = _objet(client, alice, "enfant", reserve=True)
    ouvert = _objet(client, alice, "sport")
    assert reserve["reserve_espace"] and not ouvert["reserve_espace"]

    def ids(qui=None, **params):
        return {o["id"] for o in client.get("/objets", params=params, headers=qui.headers if qui else {}).json()}

    assert ids() == {ouvert["id"]}  # sans compte
    assert ids(bob) == {ouvert["id"]}
    assert ids(carole) == {reserve["id"], ouvert["id"]}
    assert ids(carole, espace=True) == {reserve["id"]}
    assert client.get(f"/objets/{reserve['id']}").status_code == 404
    assert client.get(f"/objets/{reserve['id']}", headers=carole.headers).status_code == 200

    # Le Match : bob ne voit pas l'objet réservé, carole oui.
    for qui in (bob, carole):
        creer.souhait(qui, "enfant")
    carte = lambda qui: {c["objet"]["id"] for c in client.get("/match/carrousel", headers=qui.headers).json()}  # noqa: E731
    assert reserve["id"] not in carte(bob)
    assert reserve["id"] in carte(carole)

    # Une boucle entre collègues se remet sur place, au lieu de remise de l'espace.
    _objet(client, carole, "maison", reserve=True)
    creer.souhait(alice, "maison")
    boucles = client.get("/moi/boucles", headers=carole.headers).json()
    assert boucles
    ordre = [e["objet"]["id"] for e in boucles[0]["etapes"]]
    assert reserve["id"] in ordre
    echange = client.post("/echanges", json={"objets": ordre}, headers=carole.headers).json()
    assert {t["mode"] for t in echange["transferts"]} == {"main_propre"}
    assert echange["lieu_de_rencontre"] == "Accueil du siège, bât. B"
    assert not any(
        b
        for b in client.get("/moi/boucles", headers=bob.headers).json()
        if reserve["id"] in [e["objet"]["id"] for e in b["etapes"]]
    )

    # Bilan de l'espace : pour ses membres et la modération seulement.
    assert client.get("/impact", params={"espace": "acme"}, headers=bob.headers).status_code == 404
    assert client.get("/impact", params={"espace": "acme"}, headers=alice.headers).status_code == 200
    assert (
        client.get("/impact", params={"espace": "acme"}, headers=modo.headers).json()["objets_en_ligne"] == 0
    )  # tous deux engagés dans l'échange

    # Quitter l'espace : mes objets réservés redeviennent ouverts à tous.
    assert client.delete("/moi/espace", headers=alice.headers).json()["espace"] is None
    mes_objets = client.get("/moi/objets", headers=alice.headers).json()
    assert not any(o["reserve_espace"] for o in mes_objets)
