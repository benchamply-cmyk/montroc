"""Business model V2 : zones d'intérêt et localisation des objets, main propre ou colis, Troc Premium."""

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta

from conftest import PHOTO
from test_api import TACHES, _dimanche, sujets

from montroc_api import courriels, premium, services
from montroc_api.config import get_settings
from montroc_api.db import SessionLocal
from montroc_api.models import Utilisateur

COURS_JULIEN = {"libelle": "Cours Julien", "latitude": 43.2937, "longitude": 5.3836, "rayon_km": 5}
VIEUX_PORT = (43.2951, 5.3740)
LYON = (45.7640, 4.8357)


def _objet(client, qui, categorie, position=None, **detail):
    corps = {"categorie_slug": categorie, "titre": categorie, "etat": "bon", "photo_url": PHOTO, **detail}
    if position:
        corps |= {"lieu": "ici", "latitude": position[0], "longitude": position[1]}
    r = client.post("/moi/objets", json=corps, headers=qui.headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _carrousel(client, qui):
    return {c["objet"]["id"]: c for c in client.get("/match/carrousel", headers=qui.headers).json()}


def _formule(utilisateur_id, cle="plus", jours=30):
    with SessionLocal() as session:
        u = session.get(Utilisateur, utilisateur_id)
        premium.activer(u, cle, timedelta(days=jours))
        session.commit()


def test_localisation_arrondie_et_format_de_colis(client, creer):
    alice = creer.utilisateur("alice")
    r = client.post(
        "/moi/objets",
        json={
            "categorie_slug": "sport",
            "titre": "Vélo",
            "etat": "bon",
            "photo_url": PHOTO,
            "lieu": "Marseille 6e",
            "latitude": 43.293712,
            "longitude": 5.383655,
            "modes_echange": ["main_propre", "colis"],
            "format_colis": "grand",
        },
        headers=alice.headers,
    )
    assert r.status_code == 201, r.text
    lu = r.json()
    # On ne garde jamais une position précise : environ 1 km.
    assert (lu["latitude"], lu["longitude"], lu["lieu"]) == (43.29, 5.38, "Marseille 6e")
    assert lu["modes_echange"] == ["colis", "main_propre"] and lu["format_colis"] == "grand"
    # Les autres voient le lieu, pas les coordonnées.
    assert "latitude" not in client.get(f"/objets/{lu['id']}").json()

    for invalide in (
        {"modes_echange": ["colis"]},  # sans format
        {"modes_echange": ["colis"], "format_colis": "encombrant"},  # trop gros pour un colis
        {"format_colis": "geant"},
        {"latitude": 43.29},  # sans longitude
    ):
        corps = {"categorie_slug": "sport", "titre": "x", "etat": "bon", "photo_url": PHOTO, **invalide}
        assert client.post("/moi/objets", json=corps, headers=alice.headers).status_code == 422, invalide
    # Les modes par défaut (main propre, point de dépôt) cochés : aucun précisé, sans colis.
    objet = _objet(client, alice, "maison", modes_echange=["main_propre", "point_relais"])
    assert client.get(f"/objets/{objet}").json()["modes_echange"] == []
    r = client.patch(f"/moi/objets/{objet}", json={"modes_echange": ["colis"]}, headers=alice.headers)
    assert r.status_code == 422


def test_zones_d_interet(client, creer):
    """Bruno troque autour du Cours Julien ; l'objet du Vieux-Port lui est proposé, celui de Lyon seulement s'il
    accepte toute la France et que l'objet peut partir en colis."""
    alice, lea, bruno = creer.utilisateur("alice"), creer.utilisateur("lea", zone="Lyon"), creer.utilisateur("bruno")
    pres = _objet(client, alice, "sport", VIEUX_PORT)
    loin = _objet(client, lea, "sport", LYON)
    loin_colis = _objet(client, lea, "sport", LYON, modes_echange=["main_propre", "colis"], format_colis="moyen")
    creer.objet(bruno, "maison")
    creer.souhait(bruno, "sport")

    # Une seule zone sans Premium.
    deux = [COURS_JULIEN, {**COURS_JULIEN, "libelle": "Aix", "latitude": 43.53, "longitude": 5.45}]
    assert client.patch("/moi", json={"zones_interet": deux}, headers=bruno.headers).status_code == 409
    r = client.patch("/moi", json={"zones_interet": [COURS_JULIEN]}, headers=bruno.headers)
    assert r.status_code == 200 and r.json()["zones_interet"][0]["latitude"] == 43.29 and r.json()["zones_max"] == 1
    cartes = _carrousel(client, bruno)
    assert set(cartes) == {pres} and cartes[pres]["distance_km"] < 2 and not cartes[pres]["par_colis"]

    client.patch("/moi", json={"toute_la_france": True}, headers=bruno.headers)
    cartes = _carrousel(client, bruno)
    assert set(cartes) == {pres, loin_colis} and cartes[loin_colis]["par_colis"]
    assert loin not in cartes

    # Avec Premium Plus : jusqu'à trois zones.
    _formule(bruno.id)
    r = client.patch("/moi", json={"zones_interet": deux}, headers=bruno.headers)
    assert r.status_code == 200 and r.json()["zones_max"] == 3


def test_echange_par_colis(client, creer):
    """Lea (Lyon) envoie son objet par colis à Bruno (Marseille, toute la France) ; Bruno remet le sien à Lea…
    par colis aussi, puisque Marseille est hors de la zone de Lea."""
    lea, bruno = creer.utilisateur("lea", zone="Lyon"), creer.utilisateur("bruno")
    a_lea = _objet(client, lea, "sport", LYON, modes_echange=["colis"], format_colis="petit")
    a_bruno = _objet(client, bruno, "maison", VIEUX_PORT, modes_echange=["colis", "main_propre"], format_colis="moyen")
    creer.souhait(lea, "maison")
    creer.souhait(bruno, "sport")
    lyon = {"libelle": "Lyon", "latitude": LYON[0], "longitude": LYON[1], "rayon_km": 10}
    client.patch("/moi", json={"zones_interet": [lyon], "toute_la_france": True}, headers=lea.headers)
    client.patch("/moi", json={"zones_interet": [COURS_JULIEN], "toute_la_france": True}, headers=bruno.headers)
    _formule(lea.id)  # Garantie TopTroc incluse dans Premium Plus

    ordre = [e["objet"]["id"] for e in client.get("/moi/boucles", headers=bruno.headers).json()[0]["etapes"]]
    assert set(ordre) == {a_lea, a_bruno}
    echange = client.post("/echanges", json={"objets": ordre}, headers=bruno.headers).json()
    assert {t["mode"] for t in echange["transferts"]} == {"colis"}
    garanties = {t["donneur_pseudo"]: t["garantie"] for t in echange["transferts"]}
    assert garanties == {"lea": True, "bruno": False}
    r = client.post(f"/echanges/{echange['id']}/reponse", json={"accepte": True}, headers=lea.headers)
    assert r.json()["statut"] == "accepte"
    assert sujets(lea.email)[-1] == "C'est oui pour tout le monde : à vous d'envoyer"

    # Bruno indique où recevoir le colis : seuls lui et Lea (qui l'envoie) la voient.
    r = client.post(
        f"/echanges/{echange['id']}/adresse", json={"adresse": "Relais Cours Julien"}, headers=bruno.headers
    )
    assert r.status_code == 200
    vu_par_lea = client.get(f"/echanges/{echange['id']}", headers=lea.headers).json()
    assert next(t for t in vu_par_lea["transferts"] if t["receveur_pseudo"] == "bruno")["adresse_livraison"]

    # Un colis part avec son numéro de suivi.
    assert client.post(f"/echanges/{echange['id']}/depot", headers=lea.headers).status_code == 409
    suivi = {"transporteur": "Mondial Relay", "numero_suivi": "MR123"}
    r = client.post(f"/echanges/{echange['id']}/depot", json=suivi, headers=lea.headers)
    assert r.status_code == 200 and sujets(bruno.email)[-1] == "lea a remis ou envoyé son objet"
    r = client.post(f"/echanges/{echange['id']}/depot", json={**suivi, "numero_suivi": "MR456"}, headers=bruno.headers)
    assert r.json()["statut"] == "termine"
    assert sujets(bruno.email)[-1] == "Tout est envoyé : votre colis arrive"
    assert any("Mondial Relay MR123" in c.texte for c in courriels.ENVOYES if c.destinataire == bruno.email)


def test_lieu_de_rencontre_conseille(client, creer, monkeypatch):
    monkeypatch.setattr(get_settings(), "lieux_de_rencontre", "Marseille = Place Jean-Jaurès")
    (a, _b, _c), echange = creer.echange_abc()
    lu = client.get(f"/echanges/{echange['id']}", headers=a.headers).json()
    assert lu["lieu_de_rencontre"] == "Place Jean-Jaurès" and lu["point_de_depot"] is None


def test_catalogue_et_essai(client, creer, monkeypatch):
    monkeypatch.setattr(
        get_settings(), "stripe_liens", "plus_mois = https://buy.stripe.com/p ; pass = https://buy.stripe.com/d"
    )
    monkeypatch.setattr(get_settings(), "encart_publicite", "Ressourcerie du 6e | https://exemple.fr")
    catalogue = client.get("/premium").json()
    formules = {f["cle"]: f for f in catalogue["formules"]}
    assert set(formules) == {"essentiel", "plus", "famille", "pro", "pass"}
    assert formules["plus"]["prix_mois"] == 5.99 and formules["plus"]["liens"] == {"mois": "https://buy.stripe.com/p"}
    assert formules["pass"]["prix_unique"] == 1.99 and formules["pass"]["liens"] == {"pass": "https://buy.stripe.com/d"}
    assert "priorite" in formules["plus"]["avantages"] and "priorite" not in formules["essentiel"]["avantages"]
    assert catalogue["publicite_lien"] == "https://exemple.fr"
    assert [f["poids_max_kg"] for f in catalogue["formats_colis"]] == [1, 5, 30, None]

    alice = creer.utilisateur("alice")
    lu = client.get("/moi", headers=alice.headers).json()
    assert lu["formule"] is None and lu["essai_disponible"] and lu["avantages"] == []
    r = client.post("/premium/essai", headers=alice.headers)
    assert r.status_code == 200 and r.json()["formule"] == "plus" and "shortlist" in r.json()["avantages"]
    assert r.json()["super_jaime_restants"] == 3 and not r.json()["essai_disponible"]
    assert client.post("/premium/essai", headers=alice.headers).status_code == 409


def test_super_j_aime_et_retour_arriere(client, creer):
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    objets = [_objet(client, alice, "sport", titre=f"vélo {i}") for i in range(3)]
    creer.objet(bruno, "maison")
    creer.souhait(bruno, "sport")

    # Sans Premium : pas de Super J'aime ni de retour arrière.
    r = client.post(
        "/match/avis", json={"objet_id": objets[0], "aime": True, "super_jaime": True}, headers=bruno.headers
    )
    assert r.status_code == 409
    client.post("/match/avis", json={"objet_id": objets[1], "aime": False}, headers=bruno.headers)
    assert client.delete(f"/match/avis/{objets[1]}", headers=bruno.headers).status_code == 409

    _formule(bruno.id, "essentiel")  # 1 Super J'aime par semaine
    r = client.post(
        "/match/avis", json={"objet_id": objets[0], "aime": True, "super_jaime": True}, headers=bruno.headers
    )
    assert r.status_code == 200 and sujets(alice.email)[-1] == "bruno a eu un coup de cœur pour « vélo 0 »"
    r = client.post(
        "/match/avis", json={"objet_id": objets[2], "aime": True, "super_jaime": True}, headers=bruno.headers
    )
    assert r.status_code == 409
    assert client.get("/moi", headers=bruno.headers).json()["super_jaime_restants"] == 0

    assert objets[1] not in _carrousel(client, bruno)
    assert client.delete(f"/match/avis/{objets[1]}", headers=bruno.headers).status_code == 204
    assert objets[1] in _carrousel(client, bruno)
    # Retirer un « J'aime » (le cœur) est libre.
    assert client.delete(f"/match/avis/{objets[0]}", headers=bruno.headers).status_code == 204


def test_shortlist_des_objets_convoites(client, creer):
    alice = creer.utilisateur("alice")
    velo = _objet(client, alice, "sport")
    fans = [creer.utilisateur(f"fan{i}") for i in range(6)]
    for fan in fans:
        creer.objet(fan, "maison")
    for fan in fans[:4]:
        client.post("/match/avis", json={"objet_id": velo, "aime": True}, headers=fan.headers)
    # Pas encore convoité (4 « J'aime ») : la liste reste privée sans Premium.
    lu = client.get(f"/moi/objets/{velo}/interesses", headers=alice.headers).json()
    assert lu == {"nb_jaime": 4, "convoite": False, "interesses": []}

    _formule(fans[5].id)  # Premium Plus : sa demande passe en tête de la ShortList
    for fan in fans[4:]:
        client.post("/match/avis", json={"objet_id": velo, "aime": True}, headers=fan.headers)
    lu = client.get(f"/moi/objets/{velo}/interesses", headers=alice.headers).json()
    assert lu["nb_jaime"] == 6 and lu["convoite"]
    pseudos = [i["membre"]["pseudo"] for i in lu["interesses"]]
    assert pseudos == ["fan5", "fan0", "fan1", "fan2", "fan3"]
    assert lu["interesses"][0]["en_tete"] and lu["interesses"][0]["ses_objets"]
    # Seul le propriétaire voit qui aime son objet.
    assert client.get(f"/moi/objets/{velo}/interesses", headers=fans[0].headers).status_code == 404
    # « Voir qui a aimé » (Premium) : tous les intéressés.
    _formule(alice.id, "essentiel")
    assert len(client.get(f"/moi/objets/{velo}/interesses", headers=alice.headers).json()["interesses"]) == 6


def test_priorite_premium_seulement_pour_departager():
    with SessionLocal() as session:
        u = Utilisateur(email="x@exemple.fr", pseudo="x")
        assert services.priorite_premium(u, 4) == 4
        premium.activer(u, "plus", timedelta(days=1))
        assert services.priorite_premium(u, 4) == 4 + premium.BONUS_PRIORITE
        premium.activer(u, "essentiel", timedelta(days=1))
        assert services.priorite_premium(u, 1) == 1
        session.rollback()


def test_avant_premiere_du_grand_troc(client, creer, monkeypatch):
    (a, b, c), _ = creer.boucle_abc()
    _formule(a.id)  # Alice a Premium Plus
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(17, 5))
    r = client.post("/taches/grand-troc", headers=TACHES).json()
    assert r["lance"] and "Avant-première" in r["message"]
    assert sujets(a.email)[-1] == "Grand Troc : une boucle vous attend"
    assert "Grand Troc : une boucle vous attend" not in sujets(b.email)
    assert len(client.get("/moi/echanges", headers=a.headers).json()) == 1
    assert client.get("/moi/echanges", headers=b.headers).json() == []
    echange_id = r["echanges"][0]["id"]
    assert client.get(f"/echanges/{echange_id}", headers=b.headers).status_code == 404
    assert client.get(f"/echanges/{echange_id}", headers=a.headers).json()["avant_premiere"]

    # À 18 h, la tâche horaire (ou celle du Grand Troc) annonce la boucle à tous, une seule fois.
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 7))
    client.post("/taches/horaires", headers=TACHES)
    assert sujets(b.email)[-1] == sujets(c.email)[-1] == "Grand Troc : une boucle vous attend"
    assert sujets(a.email).count("Grand Troc : une boucle vous attend") == 1
    assert len(client.get("/moi/echanges", headers=b.headers).json()) == 1
    assert not client.get(f"/echanges/{echange_id}", headers=b.headers).json()["avant_premiere"]
    client.post("/taches/grand-troc", headers=TACHES)
    assert sujets(b.email).count("Grand Troc : une boucle vous attend") == 1


def _stripe(client, evenement, secret="whsec_test", horodatage=None):
    corps = json.dumps(evenement).encode()
    t = horodatage or int(time.time())
    signature = hmac.new(secret.encode(), f"{t}.".encode() + corps, hashlib.sha256).hexdigest()
    return client.post("/premium/stripe", content=corps, headers={"Stripe-Signature": f"t={t},v1={signature}"})


def test_paiement_stripe(client, creer, monkeypatch):
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", "whsec_test")
    alice = creer.utilisateur("alice")
    achat = {
        "type": "checkout.session.completed",
        "data": {"object": {"client_reference_id": f"{alice.id}-plus_an", "customer": "cus_1"}},
    }
    assert _stripe(client, achat, secret="faux").status_code == 400
    assert _stripe(client, achat, horodatage=int(time.time()) - 3600).status_code == 400
    assert _stripe(client, achat).status_code == 200
    lu = client.get("/moi", headers=alice.headers).json()
    assert lu["formule"] == "plus"
    fin = datetime.fromisoformat(lu["premium_jusqu_au"])
    assert timedelta(days=365) < fin - datetime.now(UTC) < timedelta(days=367)

    # Renouvellement : la fin de la nouvelle période, plus deux jours de marge.
    dans_deux_ans = int((datetime.now(UTC) + timedelta(days=730)).timestamp())
    renouvellement = {
        "type": "invoice.paid",
        "data": {"object": {"customer": "cus_1", "lines": {"data": [{"period": {"end": dans_deux_ans}}]}}},
    }
    assert _stripe(client, renouvellement).status_code == 200
    fin = datetime.fromisoformat(client.get("/moi", headers=alice.headers).json()["premium_jusqu_au"])
    assert abs((fin - datetime.fromtimestamp(dans_deux_ans, UTC)) - timedelta(days=2)) < timedelta(seconds=1)
    inconnu = {"type": "checkout.session.completed", "data": {"object": {"client_reference_id": f"{alice.id}-or"}}}
    assert _stripe(client, inconnu).status_code == 400


def test_famille(client, creer):
    papa, ado = creer.utilisateur("papa"), creer.utilisateur("ado")
    assert client.post("/premium/famille", json={"email": ado.email}, headers=papa.headers).status_code == 409
    _formule(papa.id, "famille")
    r = client.post("/premium/famille", json={"email": ado.email}, headers=papa.headers)
    assert r.status_code == 201 and [x["pseudo"] for x in r.json()] == ["ado"]
    lu = client.get("/moi", headers=ado.headers).json()
    assert lu["formule"] == "famille" and "avant_premiere" in lu["avantages"]
    assert client.delete(f"/premium/famille/{ado.id}", headers=ado.headers).status_code == 204
    assert client.get("/moi", headers=ado.headers).json()["formule"] is None


def test_moderation_premium_et_verification(client, creer):
    modo, alice = creer.utilisateur("modo", email="modo@exemple.fr"), creer.utilisateur("alice")
    fin = (datetime.now(UTC) + timedelta(days=10)).isoformat()
    url = f"/moderation/utilisateurs/{alice.id}"
    assert (
        client.put(f"{url}/premium", json={"formule": "pro", "jusqu_au": fin}, headers=alice.headers).status_code == 403
    )
    assert (
        client.put(f"{url}/premium", json={"formule": "pro", "jusqu_au": fin}, headers=modo.headers).status_code == 200
    )
    assert client.get("/moi", headers=alice.headers).json()["formule"] == "pro"
    assert client.put(f"{url}/verification", json={"verifie": True}, headers=modo.headers).status_code == 200
    assert client.get("/moi", headers=alice.headers).json()["verifie"]
    assert client.put(f"{url}/premium", json={"formule": None}, headers=modo.headers).status_code == 200
    assert client.get("/moi", headers=alice.headers).json()["formule"] is None
