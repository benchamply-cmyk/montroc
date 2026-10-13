"""Signalements (ouverts à tous) et décisions de modération motivées."""

from montroc_api import courriels

MOTIF = {"motif": "dangereux", "explication": "Ce siège auto fait l'objet d'un rappel."}


def test_signaler_avec_ou_sans_compte(client, creer):
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    o = creer.objet(alice, "siege-auto")
    r = client.post("/signalements", json={"objet_id": o, **MOTIF}, headers=bruno.headers)
    assert r.status_code == 201 and r.json()["statut"] == "ouvert"
    assert courriels.ENVOYES[-2].sujet == "Signalement reçu" and courriels.ENVOYES[-2].destinataire == bruno.email
    assert courriels.ENVOYES[-1].destinataire == "modo@exemple.fr"

    # Sans compte, il faut une adresse pour recevoir la décision.
    assert client.post("/signalements", json={"objet_id": o, **MOTIF}).status_code == 422
    r = client.post("/signalements", json={"objet_id": o, **MOTIF, "email_contact": "passant@exemple.fr"})
    assert r.status_code == 201
    assert client.post("/signalements", json={"objet_id": 999, **MOTIF}, headers=bruno.headers).status_code == 404
    trop_court = {**MOTIF, "explication": "bof"}
    assert client.post("/signalements", json={"objet_id": o, **trop_court}, headers=bruno.headers).status_code == 422
    deux_cibles = {"objet_id": o, "utilisateur_id": alice.id, **MOTIF}
    assert client.post("/signalements", json=deux_cibles, headers=bruno.headers).status_code == 422


def test_moderation_reservee(client, creer):
    alice = creer.utilisateur("alice")
    assert client.get("/moderation/signalements", headers=alice.headers).status_code == 403
    assert client.post("/categories", json={"slug": "x", "libelle": "X"}, headers=alice.headers).status_code == 403
    modo = creer.utilisateur("modo", email="modo@exemple.fr")
    assert client.get("/moi", headers=modo.headers).json()["est_moderateur"]
    assert client.post("/categories", json={"slug": "x", "libelle": "X"}, headers=modo.headers).status_code == 201


def test_retenir_retire_l_objet_et_annule_l_echange(client, creer):
    (a, b, c), echange = creer.echange_abc()
    poussette = next(t["objet"]["id"] for t in echange["transferts"] if t["donneur_id"] == a.id)
    s = client.post("/signalements", json={"objet_id": poussette, **MOTIF}, headers=b.headers).json()
    modo = creer.utilisateur("modo", email="modo@exemple.fr")

    ouverts = client.get("/moderation/signalements", headers=modo.headers).json()
    assert [x["id"] for x in ouverts] == [s["id"]] and ouverts[0]["objet"]["titre"] == "poussette"

    decision = {"retenir": True, "motivation": "Modèle rappelé par le fabricant en 2025."}
    r = client.post(f"/moderation/signalements/{s['id']}/decision", json=decision, headers=modo.headers)
    assert r.status_code == 200 and r.json()["statut"] == "retenu"
    assert (
        client.post(f"/moderation/signalements/{s['id']}/decision", json=decision, headers=modo.headers).status_code
        == 409
    )

    assert client.get(f"/echanges/{echange['id']}", headers=c.headers).json()["statut"] == "annule"
    assert client.get(f"/objets/{poussette}").status_code == 404
    # Le propriétaire ne peut pas remettre l'objet en ligne lui-même.
    assert client.patch(f"/moi/objets/{poussette}", json={"statut": "disponible"}, headers=a.headers).status_code == 409
    # Exposé des motifs au propriétaire, réponse à l'auteur du signalement.
    pour_alice = [x for x in courriels.ENVOYES if x.destinataire == a.email and x.sujet == "Décision de modération"]
    assert "Modèle rappelé" in pour_alice[0].texte and "contester" in pour_alice[0].texte
    assert any(x.destinataire == b.email and x.sujet == "Suite donnée à votre signalement" for x in courriels.ENVOYES)
    assert client.get("/moderation/signalements", headers=modo.headers).json() == []


def test_suspendre_un_compte(client, creer):
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    creer.objet(alice, "velo")
    s = client.post(
        "/signalements",
        json={"utilisateur_id": alice.id, "motif": "arnaque", "explication": "Demande de l'argent en message privé."},
        headers=bruno.headers,
    ).json()
    modo = creer.utilisateur("modo", email="modo@exemple.fr")
    decision = {"retenir": True, "motivation": "Tentative d'arnaque avérée."}
    assert (
        client.post(f"/moderation/signalements/{s['id']}/decision", json=decision, headers=modo.headers).status_code
        == 200
    )
    assert client.get("/moi", headers=alice.headers).status_code == 401  # sessions fermées
    assert client.get("/objets").json() == []
    # Un compte suspendu ne reçoit plus de lien de connexion.
    avant = len(courriels.ENVOYES)
    assert client.post("/auth/lien", json={"email": alice.email}).status_code == 202
    assert len(courriels.ENVOYES) == avant


def test_rejeter(client, creer):
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    o = creer.objet(alice, "velo")
    s = client.post("/signalements", json={"objet_id": o, **MOTIF}, headers=bruno.headers).json()
    modo = creer.utilisateur("modo", email="modo@exemple.fr")
    decision = {"retenir": False, "motivation": "L'objet est conforme à nos règles."}
    assert (
        client.post(f"/moderation/signalements/{s['id']}/decision", json=decision, headers=modo.headers).json()[
            "statut"
        ]
        == "rejete"
    )
    assert len(client.get("/objets").json()) == 1
    assert courriels.ENVOYES[-1].destinataire == bruno.email and "n'a pas été retenu" in courriels.ENVOYES[-1].texte
