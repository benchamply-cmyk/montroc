"""Parcours complets à travers l'API."""


def test_sante(client):
    assert client.get("/sante").json()["statut"] == "ok"


def test_inscription_unique(client, creer):
    creer.utilisateur("alice")
    r = client.post("/utilisateurs", json={"email": "Alice@Exemple.fr", "pseudo": "alice2"})
    assert r.status_code == 409
    r = client.post("/utilisateurs", json={"email": "nouveau@exemple.fr", "pseudo": "alice"})
    assert r.status_code == 409
    assert client.post("/utilisateurs", json={"email": "pas-un-email", "pseudo": "bob"}).status_code == 422


def test_souhait_invalide(client, creer):
    a = creer.utilisateur("alice")
    o = creer.objet(a, "velo")
    assert client.post(f"/utilisateurs/{a}/souhaits", json={}).status_code == 422
    assert client.post(f"/utilisateurs/{a}/souhaits", json={"objet_id": o}).status_code == 409
    assert client.post(f"/utilisateurs/{a}/souhaits", json={"categorie_slug": "inconnue"}).status_code == 404


def test_filtrer_objets(client, creer):
    a = creer.utilisateur("alice", zone="Lyon")
    b = creer.utilisateur("bruno", zone="Paris")
    creer.objet(a, "velo")
    creer.objet(b, "velo")
    creer.objet(b, "livres")
    assert len(client.get("/objets", params={"categorie": "velo"}).json()) == 2
    assert len(client.get("/objets", params={"zone": "Paris"}).json()) == 2


def test_boucle_a_trois_de_bout_en_bout(client, creer):
    (a, b, c), objets = creer.boucle_abc()

    suggestions = client.get(f"/utilisateurs/{a}/boucles").json()
    assert len(suggestions) == 1 and suggestions[0]["longueur"] == 3
    ordre = [e["objet_id"] for e in suggestions[0]["etapes"]]

    echange = client.post("/echanges", json={"objets": ordre}).json()
    assert echange["statut"] == "propose"
    assert {o["statut"] for o in client.get(f"/utilisateurs/{a}/objets").json()} == {"reserve"}
    # Les objets réservés ne sont plus proposés ailleurs.
    assert client.get(f"/utilisateurs/{b}/boucles").json() == []
    assert client.post("/echanges", json={"objets": ordre}).status_code == 409

    for t in echange["transferts"]:
        r = client.post(
            f"/echanges/{echange['id']}/transferts/{t['id']}/reponse",
            json={"utilisateur_id": t["receveur_id"], "accepte": True},
        )
        assert r.status_code == 200, r.text
    assert r.json()["statut"] == "accepte"

    fini = client.post(f"/echanges/{echange['id']}/terminer").json()
    assert fini["statut"] == "termine"
    assert client.get(f"/utilisateurs/{c}/objets").json()[0]["statut"] == "echange"
    assert set(objets) == set(ordre)


def test_refus_libere_les_objets(client, creer):
    (a, _, _), _ = creer.boucle_abc()
    ordre = [e["objet_id"] for e in client.get(f"/utilisateurs/{a}/boucles").json()[0]["etapes"]]
    echange = client.post("/echanges", json={"objets": ordre}).json()
    t = echange["transferts"][0]

    intrus = client.post(
        f"/echanges/{echange['id']}/transferts/{t['id']}/reponse",
        json={"utilisateur_id": t["donneur_id"], "accepte": True},
    )
    assert intrus.status_code == 409  # seul le receveur répond

    r = client.post(
        f"/echanges/{echange['id']}/transferts/{t['id']}/reponse",
        json={"utilisateur_id": t["receveur_id"], "accepte": False},
    )
    assert r.json()["statut"] == "annule"
    assert len(client.get("/objets").json()) == 3
    assert client.post(f"/echanges/{echange['id']}/terminer").status_code == 409


def test_acceptation_automatique(client, creer):
    (a, _, _), _ = creer.boucle_abc(auto=True)
    ordre = [e["objet_id"] for e in client.get(f"/utilisateurs/{a}/boucles").json()[0]["etapes"]]
    assert client.post("/echanges", json={"objets": ordre}).json()["statut"] == "accepte"


def test_objets_qui_ne_bouclent_pas(client, creer):
    # Alice donne la poussette à Chloé, qui donne le vélo à Bruno : [p, v, s] boucle, [p, s, v] non.
    (_, _, _), (p, s, v) = creer.boucle_abc()
    assert client.post("/echanges", json={"objets": [p, s, v]}).status_code == 409


def test_math_trade_enregistre_les_echanges(client, creer):
    creer.boucle_abc()
    d, e = creer.utilisateur("david"), creer.utilisateur("emma")
    creer.objet(d, "livres")
    creer.objet(e, "jouets")
    creer.souhait(d, "jouets")
    creer.souhait(e, "livres")

    r = client.post("/echanges/math-trade").json()
    assert r["nb_objets_echanges"] == 5 and r["optimal"]
    assert sorted(len(x["transferts"]) for x in r["echanges"]) == [2, 3]
    assert client.get("/objets").json() == []
    # Relancer ne propose rien de plus : tout est réservé.
    assert client.post("/echanges/math-trade").json()["echanges"] == []


def test_objet_reserve_non_modifiable(client, creer):
    (a, _, _), (p, _, _) = creer.boucle_abc()
    client.post("/echanges/math-trade")
    assert client.patch(f"/objets/{p}", json={"statut": "retire"}).status_code == 409
    assert client.patch(f"/objets/{p}", json={"statut": "echange"}).status_code == 422
