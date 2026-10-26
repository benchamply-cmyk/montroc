"""Le Match : carrousel, « J'aime » / « Non merci », matchs et accords 1 à 1 ; ce qu'en fait le Grand Troc."""

from test_api import TACHES, sujets

from montroc_api import services


def _avis(client, qui, objet_id, aime=True):
    r = client.post("/match/avis", json={"objet_id": objet_id, "aime": aime}, headers=qui.headers)
    assert r.status_code == 200, r.text
    return r.json()["match"]


def test_carrousel_montre_ce_que_je_cherche(client, creer):
    alice, bruno, chloe = creer.utilisateur("alice"), creer.utilisateur("bruno"), creer.utilisateur("chloe")
    lyon = creer.utilisateur("lea", zone="Lyon")
    creer.objet(alice, "enfant")
    creer.souhait(alice, "sport")
    velo_bruno = creer.objet(bruno, "sport", "Vélo de Bruno")
    velo_chloe = creer.objet(chloe, "sport", "Vélo de Chloé")
    livres_chloe = creer.objet(chloe, "culture")  # pas souhaité par Alice, mais Chloé cherche ce qu'Alice a
    creer.objet(bruno, "culture")  # ni l'un ni l'autre : pas montré
    creer.objet(lyon, "sport")  # une autre ville
    creer.souhait(chloe, "enfant")  # Chloé cherche ce qu'Alice a : son vélo passe devant

    cartes = client.get("/match/carrousel", headers=alice.headers).json()
    assert [c["objet"]["id"] for c in cartes] == [velo_chloe, velo_bruno, livres_chloe]
    assert cartes[0]["il_cherche"][0]["categorie_slug"] == "enfant"
    assert cartes[0]["correspond_a_mes_souhaits"] and cartes[0]["proprietaire"]["pseudo"] == "chloe"

    # Un objet aimé ou écarté ne revient pas.
    assert _avis(client, alice, velo_bruno, aime=False) is None
    restants = client.get("/match/carrousel", headers=alice.headers).json()
    assert [c["objet"]["id"] for c in restants] == [velo_chloe, livres_chloe]
    assert client.get("/match/carrousel").status_code == 401


def test_match_puis_accord_1_a_1_sans_attendre_dimanche(client, creer, monkeypatch):
    monkeypatch.setattr(services.get_settings(), "echanges_a_la_demande", False)  # le Grand Troc reste hebdo
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    poussette = creer.objet(alice, "enfant", "Poussette")
    velo = creer.objet(bruno, "sport", "Vélo")

    assert _avis(client, alice, velo) is None  # Bruno n'a encore rien aimé
    assert client.get("/match", headers=alice.headers).json() == []
    # Bruno voit la poussette en tête : un « J'aime » ferait un match tout de suite.
    carte = client.get("/match/carrousel", headers=bruno.headers).json()[0]
    assert carte["objet"]["id"] == poussette and carte["il_aime"][0]["id"] == velo
    match = _avis(client, bruno, poussette)
    assert match["avec"]["pseudo"] == "alice" and match["ses_objets"][0]["id"] == poussette
    assert "C'est un match avec bruno" in sujets(alice.email)
    assert client.get("/match", headers=alice.headers).json()[0]["avec"]["pseudo"] == "bruno"

    r = client.post("/match/accord", json={"mon_objet_id": poussette, "son_objet_id": velo}, headers=alice.headers)
    assert r.status_code == 201, r.text
    echange = r.json()
    assert echange["par_match"] and echange["statut"] == "propose" and echange["grand_troc_jour"] is None
    assert "alice vous propose un échange" in sujets(bruno.email)
    assert client.get("/match", headers=bruno.headers).json()[0]["echange_id"] == echange["id"]

    r = client.post(f"/echanges/{echange['id']}/reponse", json={"accepte": True}, headers=bruno.headers)
    assert r.json()["statut"] == "accepte"
    for qui in (alice, bruno):
        assert client.post(f"/echanges/{echange['id']}/depot", headers=qui.headers).status_code == 200
    assert client.get(f"/echanges/{echange['id']}", headers=alice.headers).json()["statut"] == "termine"


def test_accord_sans_match_refuse(client, creer):
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    poussette, velo = creer.objet(alice, "enfant"), creer.objet(bruno, "sport")
    r = client.post("/match/accord", json={"mon_objet_id": poussette, "son_objet_id": velo}, headers=alice.headers)
    assert r.status_code == 409 and "Pas encore de match" in r.json()["detail"]
    r = client.post("/match/accord", json={"mon_objet_id": velo, "son_objet_id": poussette}, headers=alice.headers)
    assert r.status_code == 409
    assert client.post(
        "/match/avis", json={"objet_id": poussette, "aime": True}, headers=alice.headers
    ).status_code == (409)


def test_le_grand_troc_tient_compte_du_match(client, creer):
    """Un « J'aime » vaut souhait au Grand Troc, un « Non merci » vaut refus."""
    (a, b, c), objets = creer.boucle_abc()
    poussette, siege, velo = objets
    dino = creer.utilisateur("dino")
    livre = creer.objet(dino, "culture", "Livre de Dino")
    # Chloé écarte la poussette d'Alice : plus de boucle à trois. Elle aime le livre de Dino, qui veut un vélo.
    _avis(client, c, poussette, aime=False)
    _avis(client, c, livre)
    creer.souhait(dino, "sport")
    assert client.get("/moi/boucles", headers=a.headers).json() == []

    r = client.post("/taches/grand-troc?force=true", headers=TACHES)
    assert r.status_code == 200, r.text
    (echange,) = r.json()["echanges"]
    assert {t["objet"]["id"] for t in echange["transferts"]} == {velo, livre}


def test_les_j_aime_ne_font_recevoir_qu_un_objet_par_grand_troc(client, creer):
    """Tous les « J'aime » d'un membre forment un seul souhait, de quantité 1 par défaut."""
    alice, bruno, dino = creer.utilisateur("alice"), creer.utilisateur("bruno"), creer.utilisateur("dino")
    creer.objet(alice, "culture", "Livre 1")
    creer.objet(alice, "culture", "Livre 2")
    velo_bruno = creer.objet(bruno, "sport", "Vélo de Bruno")
    velo_dino = creer.objet(dino, "sport", "Vélo de Dino")
    creer.souhait(bruno, "culture")
    creer.souhait(dino, "culture")
    _avis(client, alice, velo_bruno)
    _avis(client, alice, velo_dino)

    r = client.post("/taches/grand-troc?force=true", headers=TACHES)
    assert r.status_code == 200, r.text
    assert len(r.json()["echanges"]) == 1


def test_reglage_des_j_aime_par_grand_troc(client, creer, monkeypatch):
    monkeypatch.setattr(services.get_settings(), "coups_de_coeur_par_grand_troc", 2)
    alice, bruno, dino = creer.utilisateur("alice"), creer.utilisateur("bruno"), creer.utilisateur("dino")
    creer.objet(alice, "culture", "Livre 1")
    creer.objet(alice, "culture", "Livre 2")
    velo_bruno = creer.objet(bruno, "sport", "Vélo de Bruno")
    velo_dino = creer.objet(dino, "sport", "Vélo de Dino")
    creer.souhait(bruno, "culture")
    creer.souhait(dino, "culture")
    _avis(client, alice, velo_bruno)
    _avis(client, alice, velo_dino)

    r = client.post("/taches/grand-troc?force=true", headers=TACHES)
    assert r.status_code == 200, r.text
    assert len(r.json()["echanges"]) == 2
