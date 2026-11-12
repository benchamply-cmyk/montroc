"""Quotas des comptes gratuits : seules les actions qu'on lance soi-même sont limitées (« J'aime » du jour,
propositions en attente) ; chercher, publier, répondre restent illimités, et Troc Premium lève les quotas."""

from test_business_model_v2 import _formule

from montroc_api import services


def _jaime(client, qui, objet_id, aime=True):
    return client.post("/match/avis", json={"objet_id": objet_id, "aime": aime}, headers=qui.headers)


def test_sans_reglage_pas_de_quota(client, creer):
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    for i in range(5):
        assert _jaime(client, alice, creer.objet(bruno, "sport", f"Vélo {i}")).status_code == 200
    moi = client.get("/moi", headers=alice.headers).json()
    assert moi["jaime_restants"] is None and moi["propositions_restantes"] is None


def test_quota_de_j_aime_par_jour(client, creer, monkeypatch):
    monkeypatch.setattr(services.get_settings(), "quota_jaime_par_jour", 2)
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    objets = [creer.objet(bruno, "sport", f"Vélo {i}") for i in range(4)]
    assert _jaime(client, alice, objets[0]).status_code == 200
    assert client.get("/moi", headers=alice.headers).json()["jaime_restants"] == 1
    assert _jaime(client, alice, objets[1]).status_code == 200
    r = _jaime(client, alice, objets[2])
    assert r.status_code == 409 and "Plus de J'aime" in r.json()["detail"]
    # « Non merci » et un « J'aime » déjà donné ne comptent pas.
    assert _jaime(client, alice, objets[2], aime=False).status_code == 200
    assert _jaime(client, alice, objets[0]).status_code == 200
    # Troc Premium : illimité.
    _formule(alice.id, "essentiel")
    assert _jaime(client, alice, objets[3]).status_code == 200
    assert client.get("/moi", headers=alice.headers).json()["jaime_restants"] is None


def test_quota_de_propositions_en_attente(client, creer, monkeypatch):
    reglages = services.get_settings()
    monkeypatch.setattr(reglages, "quota_propositions_en_cours", 1)
    alice, bruno, chloe = creer.utilisateur("alice"), creer.utilisateur("bruno"), creer.utilisateur("chloe")
    a1, a2 = creer.objet(alice, "enfant", "Poussette"), creer.objet(alice, "maison", "Lampe")
    velo, livre = creer.objet(bruno, "sport", "Vélo"), creer.objet(chloe, "sport", "Raquette")
    for qui, objet in ((bruno, a1), (chloe, a2), (alice, velo), (alice, livre)):
        assert _jaime(client, qui, objet).status_code == 200

    def accord(mien, sien):
        return client.post("/match/accord", json={"mon_objet_id": mien, "son_objet_id": sien}, headers=alice.headers)

    r = accord(a1, velo)
    assert r.status_code == 201, r.text
    assert client.get("/moi", headers=alice.headers).json()["propositions_restantes"] == 0
    refus = accord(a2, livre)
    assert refus.status_code == 409 and "en attente" in refus.json()["detail"]
    # Répondre reste illimité ; une réponse libère la place.
    echange = r.json()["id"]
    assert client.post(f"/echanges/{echange}/reponse", json={"accepte": True}, headers=bruno.headers).status_code == 200
    assert accord(a2, livre).status_code == 201
