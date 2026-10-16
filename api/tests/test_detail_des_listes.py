"""« Je propose » / « Je demande » en détail : sous-catégories, caractéristiques et description libre."""

from conftest import PHOTO


def _objet(client, qui, categorie, **detail):
    corps = {"categorie_slug": categorie, "titre": categorie, "etat": "bon", "photo_url": PHOTO, **detail}
    return client.post("/moi/objets", json=corps, headers=qui.headers)


def _souhait(client, qui, categorie, **detail):
    return client.post("/moi/souhaits", json={"categorie_slug": categorie, **detail}, headers=qui.headers)


def test_categories_avec_sous_categories_et_caracteristiques(client):
    cats = {c["slug"]: c for c in client.get("/categories").json()}
    assert list(cats)[:3] == ["mode", "high-tech", "enfant"]  # l'ordre de la nomenclature, pas l'alphabet
    assert sum(len(c["sous_categories"]) for c in cats.values()) == 107
    assert {"slug": "enfant-poussettes", "libelle": "Poussettes et accessoires"} in cats["enfant"]["sous_categories"]
    caracs = {c["cle"]: c for c in cats["enfant"]["caracteristiques"]}
    assert "4 ans" in caracs["taille"]["options"] and caracs["marque"]["options"] is None
    assert caracs["taille"]["pour"] == ["enfant-vetements-bebe", "enfant-vetements"] and caracs["age"]["pour"] is None


def test_objet_detaille_et_validation(client, creer):
    alice = creer.utilisateur("alice")
    vetement = {"sous_categorie_slug": "enfant-vetements"}
    r = _objet(
        client,
        alice,
        "enfant",
        **vetement,
        caracteristiques={"taille": "4 ans", "marque": " Petit Bateau ", "pointure": ""},
    )
    assert r.status_code == 201, r.text
    objet = r.json()
    assert objet["sous_categorie_slug"] == "enfant-vetements"
    assert objet["caracteristiques"] == {"taille": "4 ans", "marque": "Petit Bateau"}
    assert client.get(f"/objets/{objet['id']}").json()["caracteristiques"]["taille"] == "4 ans"

    # Sous-catégorie d'une autre catégorie, caractéristique inconnue, valeur hors liste : refusées.
    assert _objet(client, alice, "enfant", sous_categorie_slug="sport-velos").status_code == 422
    assert _objet(client, alice, "enfant", caracteristiques={"couleur": "Rouge"}).status_code == 422
    assert _objet(client, alice, "enfant", **vetement, caracteristiques={"taille": "4 ans 1/2"}).status_code == 422
    # La pointure ne se précise que pour des chaussures.
    assert _objet(client, alice, "enfant", **vetement, caracteristiques={"pointure": "30"}).status_code == 422
    assert _objet(client, alice, "enfant", caracteristiques={"pointure": "30"}).status_code == 422
    chaussures = {"sous_categorie_slug": "enfant-chaussures"}
    assert _objet(client, alice, "enfant", **chaussures, caracteristiques={"pointure": "30"}).status_code == 201

    # Un objet déjà publié peut être précisé ensuite.
    r = client.patch(
        f"/moi/objets/{objet['id']}", json={"caracteristiques": {"taille": "5 ans"}}, headers=alice.headers
    )
    assert r.status_code == 200 and r.json()["caracteristiques"] == {"taille": "5 ans"}
    assert r.json()["sous_categorie_slug"] == "enfant-vetements"
    r = client.patch(f"/moi/objets/{objet['id']}", json={"sous_categorie_slug": "sport-velos"}, headers=alice.headers)
    assert r.status_code == 422


def test_demande_detaillee_avec_description_libre(client, creer):
    alice = creer.utilisateur("alice")
    r = _souhait(
        client,
        alice,
        "enfant",
        sous_categorie_slug="enfant-poussettes",
        caracteristiques={"type_poussette": "Canne", "age": "Naissance"},
        precisions="  Légère, qui se plie d'une main, pour prendre le métro.  ",
    )
    assert r.status_code == 201, r.text
    souhait = r.json()
    assert souhait["precisions"] == "Légère, qui se plie d'une main, pour prendre le métro."
    assert client.get("/moi/souhaits", headers=alice.headers).json()[0]["sous_categorie_slug"] == "enfant-poussettes"
    # La marque (saisie libre) peut aussi se demander ; une caractéristique d'une autre catégorie, non.
    assert _souhait(client, alice, "enfant", caracteristiques={"marque": "Yoyo"}).status_code == 201
    assert _souhait(client, alice, "enfant", caracteristiques={"plateforme": "PC"}).status_code == 422
    # Un souhait d'objet précis n'a pas de sous-catégorie.
    r = client.post(
        "/moi/souhaits", json={"objet_id": 1, "sous_categorie_slug": "enfant-poussettes"}, headers=alice.headers
    )
    assert r.status_code == 422


def test_la_demande_detaillee_filtre_les_echanges_et_le_match(client, creer):
    """Bruno demande un manteau en 4 ans (critère obligatoire) : le 8 ans d'Alice n'est pas proposé, celui de
    Chloé (4 ans) oui, celui sans taille de Denis non plus. En critère préférentiel, tous le sont, celui de
    Chloé en premier."""
    alice, bruno, chloe, denis = (creer.utilisateur(p) for p in ("alice", "bruno", "chloe", "denis"))
    manteau = {"sous_categorie_slug": "enfant-vetements"}
    a = _objet(client, alice, "enfant", **manteau, caracteristiques={"taille": "8 ans"}).json()["id"]
    c = _objet(client, chloe, "enfant", **manteau, caracteristiques={"taille": "4 ans"}).json()["id"]
    d = _objet(client, denis, "enfant", **manteau).json()["id"]
    pull = _objet(client, denis, "enfant", sous_categorie_slug="enfant-vetements-bebe").json()["id"]
    creer.objet(bruno, "sport")
    souhait = _souhait(client, bruno, "enfant", **manteau, caracteristiques={"taille": "4 ans"}).json()["id"]
    for qui in (alice, chloe, denis):
        creer.souhait(qui, "sport")
    eva = creer.utilisateur("eva")  # Eva ne cherche rien de ce qu'a Bruno : le carrousel suit la demande
    e = _objet(client, eva, "enfant", **manteau, caracteristiques={"taille": "8 ans"}).json()["id"]

    boucles = client.get("/moi/boucles", headers=bruno.headers).json()
    recus = {e["objet"]["id"] for b in boucles for e in b["etapes"] if e["receveur_id"] == bruno.id}
    assert recus == {c}
    cartes = {x["objet"]["id"]: x for x in client.get("/match/carrousel", headers=bruno.headers).json()}
    # Les manteaux en 8 ans et sans taille, et le pull, restent montrés, mais seulement parce qu'Alice et Denis
    # cherchent un vélo comme celui de Bruno : ils ne répondent pas à sa demande.
    assert not any(cartes[x]["correspond_a_mes_souhaits"] for x in (a, d, pull))
    assert cartes[c]["correspond_a_mes_souhaits"]
    assert cartes[c]["souhait_sous_categorie"] == "enfant-vetements"
    assert e not in cartes

    client.delete(f"/moi/souhaits/{souhait}", headers=bruno.headers)
    _souhait(client, bruno, "enfant", **manteau, preferences={"taille": "4 ans"})
    boucles = client.get("/moi/boucles", headers=bruno.headers).json()
    recus = [e["objet"]["id"] for b in boucles for e in b["etapes"] if e["receveur_id"] == bruno.id]
    assert set(recus) == {a, c, d} and recus[0] == c
    # Ce que Bruno a écrit dans « Je demande » est montré à ceux qui ont ce qu'il cherche.
    client.post(
        "/moi/souhaits",
        json={"categorie_slug": "divers", "precisions": "Des briques pour un enfant de 6 ans"},
        headers=bruno.headers,
    )
    jouet = _objet(client, chloe, "divers").json()["id"]
    carte = next(
        x for x in client.get("/match/carrousel", headers=chloe.headers).json() if x["proprietaire"]["id"] == bruno.id
    )
    assert carte["sa_demande"] == "Des briques pour un enfant de 6 ans" and jouet in [
        o["id"] for o in carte["il_cherche"]
    ]
