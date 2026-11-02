"""Troc & Services : professionnels certifiés, services échangés comme des objets, négociation et contrat."""

from conftest import PHOTO

JUSTIFICATIF = "https://res.cloudinary.com/troc-test/image/upload/v1/pros/kbis.pdf"
DOSSIER = {
    "metier": "services-plomberie",
    "nom_commercial": "Plomberie du Cours Julien",
    "siret": "123 456 789 00012",
    "description": "Plombier depuis 12 ans : fuites, robinetterie, chauffe-eau, petites rénovations de salle de bains.",
    "experience_annees": 12,
    "zone_intervention": "Marseille 6e",
    "assurance": "MAAF RC Pro n° 123",
    "justificatifs": [JUSTIFICATIF],
}


def _modo(creer):
    return creer.utilisateur("modo", email="modo@exemple.fr")


def _certifier(client, modo, profil_id, oui=True, motif=None):
    r = client.post(
        f"/moderation/pros/{profil_id}/decision", json={"certifier": oui, "motif": motif}, headers=modo.headers
    )
    assert r.status_code == 200, r.text
    return r.json()


def _service(client, pro, titre="Réparer une fuite", metier="services-plomberie"):
    return client.post(
        "/moi/objets",
        json={"categorie_slug": "services", "sous_categorie_slug": metier, "titre": titre, "photo_url": PHOTO},
        headers=pro.headers,
    )


def test_metiers_et_categorie(client):
    metiers = client.get("/services/metiers").json()
    assert [x["libelle"] for x in metiers] == [
        "Déménagement", "Maçonnerie", "Électricité", "Plomberie", "Peinture", "Jardinage", "Transporteur / chauffeur",
    ]  # fmt: skip
    assert all(x["justificatifs"] for x in metiers)
    services = next(c for c in client.get("/categories").json() if c["slug"] == "services")
    assert services["libelle"] == "Troc & Services"


def test_un_service_demande_une_certification(client, creer):
    pro = creer.utilisateur("paul")
    modo = _modo(creer)
    assert _service(client, pro).status_code == 403
    profil = client.post("/moi/pro", json=DOSSIER, headers=pro.headers).json()
    assert profil["statut"] == "en_attente" and profil["siret"] == "12345678900012"
    assert _service(client, pro).status_code == 403
    # Seule la modération voit les dossiers et décide.
    assert client.get("/moderation/pros", headers=pro.headers).status_code == 403
    assert [p["pseudo"] for p in client.get("/moderation/pros", headers=modo.headers).json()] == ["paul"]
    _certifier(client, modo, profil["id"])
    r = _service(client, pro)
    assert r.status_code == 201, r.text
    assert r.json()["etat"] is None and r.json()["modes_echange"] == ["main_propre"]
    # Un autre métier n'est pas couvert par cette certification.
    assert _service(client, pro, metier="services-electricite").status_code == 403
    publics = client.get("/services/pros", params={"metier": "services-plomberie"}).json()
    assert [(p["pseudo"], len(p["services"])) for p in publics] == [("paul", 1)]
    assert "siret" not in publics[0] and "justificatifs" not in publics[0]
    assert [o["titre"] for o in client.get("/objets", params={"categorie": "services"}).json()] == ["Réparer une fuite"]


def test_refus_motive_et_retrait_des_offres(client, creer):
    pro, modo = creer.utilisateur("paul"), _modo(creer)
    profil_id = client.post("/moi/pro", json=DOSSIER, headers=pro.headers).json()["id"]
    _certifier(client, modo, profil_id)
    service_id = _service(client, pro).json()["id"]
    r = client.post(f"/moderation/pros/{profil_id}/decision", json={"certifier": False}, headers=modo.headers)
    assert r.status_code == 422
    _certifier(client, modo, profil_id, oui=False, motif="L'attestation d'assurance est expirée.")
    assert client.get(f"/objets/{service_id}").json()["statut"] == "retire"
    assert client.get("/services/pros").json() == []
    # Le dossier complété repart en vérification.
    r = client.post("/moi/pro", json={**DOSSIER, "assurance": "AXA RC Pro n° 456"}, headers=pro.headers)
    assert r.json()["statut"] == "en_attente" and r.json()["motif"] is None


def test_negociation_jusqu_au_contrat(client, creer):
    pro, modo = creer.utilisateur("paul"), _modo(creer)
    profil_id = client.post("/moi/pro", json=DOSSIER, headers=pro.headers).json()["id"]
    _certifier(client, modo, profil_id)
    service_id = _service(client, pro).json()["id"]
    alice = creer.utilisateur("alice")
    velo = creer.objet(alice, "sport", "Vélo de ville")
    lampe = creer.objet(alice, "maison", "Lampe")

    # Des objets seuls ne passent pas par Troc & Services.
    autre = creer.utilisateur("bruno")
    livre = creer.objet(autre, "culture", "Livre")
    r = client.post(
        "/negociations", json={"objet_id": livre, "contreparties": [lampe], "message": "?"}, headers=alice.headers
    )
    assert r.status_code == 409

    r = client.post(
        "/negociations",
        json={"objet_id": service_id, "contreparties": [velo], "message": "Bonjour, une fuite sous l'évier ?"},
        headers=alice.headers,
    )
    assert r.status_code == 201, r.text
    n = r.json()
    assert n["destinataire"]["pseudo"] == "paul" and [o["titre"] for o in n["contreparties"]] == ["Vélo de ville"]
    assert client.get(f"/negociations/{n['id']}", headers=autre.headers).status_code == 404
    resume = client.get("/moi/negociations", headers=pro.headers).json()
    assert resume[0]["a_moi_de_repondre"] and resume[0]["avec"]["pseudo"] == "alice"

    client.post(
        f"/negociations/{n['id']}/messages", json={"texte": "Avec la lampe en plus, ça marche."}, headers=pro.headers
    )
    conditions = {
        "prestation": "Réparation de la fuite sous l'évier, joints compris",
        "date_prevue": "2026-11-14",
        "lieu": "Marseille 6e",
        "duree": "Demi-journée",
        "contreparties": [velo, lampe],
    }
    r = client.post(f"/negociations/{n['id']}/accord", json=conditions, headers=pro.headers)
    assert r.status_code == 200, r.text
    assert r.json()["statut"] == "accord_propose"
    assert client.post(f"/negociations/{n['id']}/accepter", headers=pro.headers).status_code == 409

    r = client.post(f"/negociations/{n['id']}/accepter", headers=alice.headers)
    assert r.status_code == 200, r.text
    n = r.json()
    contrat = n["contrat"]
    assert n["statut"] == "conclue" and contrat["numero"].startswith("TT-")
    assert "Réparation de la fuite" in contrat["texte"] and "« Vélo de ville »" in contrat["texte"]
    assert "paul s'engage à" in contrat["texte"] and "alice s'engage à" in contrat["texte"]
    # Les articles promis sont réservés ; le service reste proposé à d'autres.
    assert client.get(f"/objets/{velo}").json()["statut"] == "reserve"
    assert client.get(f"/objets/{service_id}").json()["statut"] == "disponible"

    client.post(f"/contrats/{contrat['id']}/confirmer", headers=alice.headers)
    r = client.post(f"/contrats/{contrat['id']}/confirmer", headers=pro.headers)
    assert r.json()["contrat"]["statut"] == "realise"
    assert client.get(f"/objets/{lampe}").json()["statut"] == "echange"
    assert client.get("/moi", headers=pro.headers).json()["echanges_menes"] == 1


def test_service_contre_service_et_boucle(client, creer):
    """Un service entre dans les boucles comme un objet : ici un jardinier et un plombier s'échangent leurs services."""
    modo = _modo(creer)
    plombier, jardinier = creer.utilisateur("paul"), creer.utilisateur("jade")
    p1 = client.post("/moi/pro", json=DOSSIER, headers=plombier.headers).json()["id"]
    p2 = client.post("/moi/pro", json={**DOSSIER, "metier": "services-jardinage"}, headers=jardinier.headers).json()[
        "id"
    ]
    _certifier(client, modo, p1)
    _certifier(client, modo, p2)
    plomberie = _service(client, plombier).json()["id"]
    jardin = _service(client, jardinier, "Tailler une haie", "services-jardinage").json()["id"]
    creer.souhait(plombier, "services", sous_categorie_slug="services-jardinage")
    creer.souhait(jardinier, "services", sous_categorie_slug="services-plomberie")
    boucles = client.get("/moi/boucles", headers=plombier.headers).json()
    assert {e["objet"]["id"] for e in boucles[0]["etapes"]} == {plomberie, jardin}
    r = client.post(
        "/negociations",
        json={"objet_id": jardin, "contreparties": [plomberie], "message": "Échange de bons procédés ?"},
        headers=plombier.headers,
    )
    assert r.status_code == 201, r.text
