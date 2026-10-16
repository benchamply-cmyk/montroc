"""« Je propose » / « Je demande » en détail : sous-catégories, caractéristiques et description libre."""

from conftest import PHOTO


def _objet(client, qui, categorie, **detail):
    corps = {"categorie_slug": categorie, "titre": categorie, "etat": "bon", "photo_url": PHOTO, **detail}
    return client.post("/moi/objets", json=corps, headers=qui.headers)


def _souhait(client, qui, categorie, **detail):
    return client.post("/moi/souhaits", json={"categorie_slug": categorie, **detail}, headers=qui.headers)


def test_categories_avec_sous_categories_et_caracteristiques(client):
    cats = {c["slug"]: c for c in client.get("/categories").json()}
    poussette = cats["poussette"]
    assert {"slug": "poussette-canne", "libelle": "Canne"} in poussette["sous_categories"]
    caracs = {c["cle"]: c for c in cats["vetements-enfant"]["caracteristiques"]}
    assert "4 ans" in caracs["taille"]["options"] and caracs["marque"]["options"] is None


def test_objet_detaille_et_validation(client, creer):
    alice = creer.utilisateur("alice")
    r = _objet(
        client,
        alice,
        "vetements-enfant",
        sous_categorie_slug="vetements-enfant-manteaux",
        caracteristiques={"taille": "4 ans", "marque": " Petit Bateau ", "pointure": ""},
    )
    assert r.status_code == 201, r.text
    objet = r.json()
    assert objet["sous_categorie_slug"] == "vetements-enfant-manteaux"
    assert objet["caracteristiques"] == {"taille": "4 ans", "marque": "Petit Bateau"}
    assert client.get(f"/objets/{objet['id']}").json()["caracteristiques"]["taille"] == "4 ans"

    # Sous-catégorie d'une autre catégorie, caractéristique inconnue, valeur hors liste : refusées.
    assert _objet(client, alice, "poussette", sous_categorie_slug="velo-vtt").status_code == 422
    assert _objet(client, alice, "poussette", caracteristiques={"pointure": "30"}).status_code == 422
    assert _objet(client, alice, "vetements-enfant", caracteristiques={"taille": "4 ans 1/2"}).status_code == 422

    # Un objet déjà publié peut être précisé ensuite.
    r = client.patch(
        f"/moi/objets/{objet['id']}", json={"caracteristiques": {"taille": "5 ans"}}, headers=alice.headers
    )
    assert r.status_code == 200 and r.json()["caracteristiques"] == {"taille": "5 ans"}
    assert r.json()["sous_categorie_slug"] == "vetements-enfant-manteaux"
    r = client.patch(
        f"/moi/objets/{objet['id']}", json={"sous_categorie_slug": "poussette-canne"}, headers=alice.headers
    )
    assert r.status_code == 422


def test_demande_detaillee_avec_description_libre(client, creer):
    alice = creer.utilisateur("alice")
    r = _souhait(
        client,
        alice,
        "poussette",
        sous_categorie_slug="poussette-canne",
        caracteristiques={"age": "Dès la naissance"},
        precisions="  Légère, qui se plie d'une main, pour prendre le métro.  ",
    )
    assert r.status_code == 201, r.text
    souhait = r.json()
    assert souhait["precisions"] == "Légère, qui se plie d'une main, pour prendre le métro."
    assert client.get("/moi/souhaits", headers=alice.headers).json()[0]["sous_categorie_slug"] == "poussette-canne"
    # Une demande ne filtre que sur des choix fixes : pas de marque.
    assert _souhait(client, alice, "poussette", caracteristiques={"marque": "Yoyo"}).status_code == 422
    # Un souhait d'objet précis n'a pas de sous-catégorie.
    r = client.post(
        "/moi/souhaits", json={"objet_id": 1, "sous_categorie_slug": "poussette-canne"}, headers=alice.headers
    )
    assert r.status_code == 422


def test_la_demande_detaillee_filtre_les_echanges_et_le_match(client, creer):
    """Bruno demande un manteau en 4 ans : le 8 ans d'Alice n'est pas proposé, celui de Chloé (4 ans) oui,
    celui sans taille de Denis aussi."""
    alice, bruno, chloe, denis = (creer.utilisateur(p) for p in ("alice", "bruno", "chloe", "denis"))
    manteau = {"sous_categorie_slug": "vetements-enfant-manteaux"}
    a = _objet(client, alice, "vetements-enfant", **manteau, caracteristiques={"taille": "8 ans"}).json()["id"]
    c = _objet(client, chloe, "vetements-enfant", **manteau, caracteristiques={"taille": "4 ans"}).json()["id"]
    d = _objet(client, denis, "vetements-enfant", **manteau).json()["id"]
    pull = _objet(client, denis, "vetements-enfant", sous_categorie_slug="vetements-enfant-hauts").json()["id"]
    creer.objet(bruno, "velo")
    _souhait(client, bruno, "vetements-enfant", **manteau, caracteristiques={"taille": "4 ans"})
    for qui in (alice, chloe, denis):
        creer.souhait(qui, "velo")
    eva = creer.utilisateur("eva")  # Eva ne cherche rien de ce qu'a Bruno : le carrousel suit la demande
    e = _objet(client, eva, "vetements-enfant", **manteau, caracteristiques={"taille": "8 ans"}).json()["id"]

    boucles = client.get("/moi/boucles", headers=bruno.headers).json()
    recus = {e["objet"]["id"] for b in boucles for e in b["etapes"] if e["receveur_id"] == bruno.id}
    assert recus == {c, d}
    cartes = {x["objet"]["id"]: x for x in client.get("/match/carrousel", headers=bruno.headers).json()}
    # Le manteau en 8 ans et le pull restent montrés, mais seulement parce qu'Alice et Denis cherchent un vélo
    # comme celui de Bruno : ils ne répondent pas à sa demande.
    assert not cartes[a]["correspond_a_mes_souhaits"] and not cartes[pull]["correspond_a_mes_souhaits"]
    assert cartes[c]["correspond_a_mes_souhaits"] and cartes[d]["correspond_a_mes_souhaits"]
    assert cartes[c]["souhait_sous_categorie"] == "vetements-enfant-manteaux"
    assert e not in cartes
    # Ce que Bruno a écrit dans « Je demande » est montré à ceux qui ont ce qu'il cherche.
    client.post(
        "/moi/souhaits",
        json={"categorie_slug": "jouets", "precisions": "Des briques pour un enfant de 6 ans"},
        headers=bruno.headers,
    )
    jouet = _objet(client, chloe, "jouets").json()["id"]
    carte = next(
        x for x in client.get("/match/carrousel", headers=chloe.headers).json() if x["proprietaire"]["id"] == bruno.id
    )
    assert carte["sa_demande"] == "Des briques pour un enfant de 6 ans" and jouet in [
        o["id"] for o in carte["il_cherche"]
    ]
