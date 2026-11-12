"""Revenus de TopTroc sans Premium : offres Entreprises et Collectivités (devis, impact) et étiquettes de colis."""

from test_api import sujets
from test_business_model_v2 import COURS_JULIEN, LYON, VIEUX_PORT, _objet, _stripe

from montroc_api import courriels
from montroc_api.config import get_settings

DEMANDE = {
    "type": "collectivite",
    "formule": "territoire",
    "organisation": "Mairie des 6e et 8e",
    "nom": "Camille",
    "email": "camille@mairie.fr",
    "taille": "80 000 habitants",
    "message": "Un Grand Troc pour le 6e.",
}


def test_demande_de_devis(client):
    r = client.post("/partenaires/demande", json=DEMANDE)
    assert r.status_code == 202
    assert (
        sujets(get_settings().contact_partenaires)[-1]
        == "Demande de devis : Mairie des 6e et 8e (Territoire (collectivité))"
    )
    assert sujets("camille@mairie.fr")[-1] == "Votre demande à TopTroc"
    assert client.post("/partenaires/demande", json={**DEMANDE, "email": "pas-un-email"}).status_code == 422
    assert client.post("/partenaires/demande", json={**DEMANDE, "formule": "or"}).status_code == 422


def test_demande_de_devis_robot_ignoree(client):
    avant = len(courriels.ENVOYES)
    assert client.post("/partenaires/demande", json={**DEMANDE, "site_web": "http://spam"}).status_code == 202
    assert len(courriels.ENVOYES) == avant


def _echange_par_colis(client, creer):
    lea, bruno = creer.utilisateur("lea", zone="Lyon"), creer.utilisateur("bruno")
    a_lea = _objet(client, lea, "sport", LYON, modes_echange=["colis"], format_colis="petit")
    a_bruno = _objet(client, bruno, "maison", VIEUX_PORT, modes_echange=["colis"], format_colis="moyen")
    creer.souhait(lea, "maison")
    creer.souhait(bruno, "sport")
    lyon = {"libelle": "Lyon", "latitude": LYON[0], "longitude": LYON[1], "rayon_km": 10}
    client.patch("/moi", json={"zones_interet": [lyon], "toute_la_france": True}, headers=lea.headers)
    client.patch("/moi", json={"zones_interet": [COURS_JULIEN], "toute_la_france": True}, headers=bruno.headers)
    ordre = [e["objet"]["id"] for e in client.get("/moi/boucles", headers=bruno.headers).json()[0]["etapes"]]
    assert set(ordre) == {a_lea, a_bruno}
    echange = client.post("/echanges", json={"objets": ordre}, headers=bruno.headers).json()
    client.post(f"/echanges/{echange['id']}/reponse", json={"accepte": True}, headers=lea.headers)
    return lea, bruno, echange


def test_catalogue_des_envois(client, monkeypatch):
    monkeypatch.setattr(
        get_settings(), "stripe_liens", "envoi_petit = https://buy.stripe.com/p ; garantie = https://buy.stripe.com/g"
    )
    c = client.get("/premium").json()
    envois = {e["format"]: e for e in c["envois"]}
    assert set(envois) == {"petit", "moyen", "grand"}  # pas d'encombrant : main propre seulement
    assert envois["petit"] == {"format": "petit", "prix": 4.9, "lien": "https://buy.stripe.com/p"}
    assert envois["moyen"]["lien"] is None
    assert (c["garantie_prix"], c["garantie_lien"]) == (0.99, "https://buy.stripe.com/g")


def test_etiquette_et_garantie_payees(client, creer, monkeypatch):
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", "whsec_test")
    lea, bruno, echange = _echange_par_colis(client, creer)
    envoi_lea = next(t for t in echange["transferts"] if t["donneur_pseudo"] == "lea")

    def paiement(qui, achat, **objet):
        evenement = {
            "type": "checkout.session.completed",
            "data": {"object": {"client_reference_id": f"{qui.id}-{achat}", **objet}},
        }
        return _stripe(client, evenement)

    assert paiement(bruno, f"envoi{envoi_lea['id']}").status_code == 400  # pas son envoi
    adresse = {
        "customer_details": {"address": {"line1": "3 rue de la République", "postal_code": "69002", "city": "Lyon"}}
    }
    assert paiement(lea, f"envoi{envoi_lea['id']}", **adresse).status_code == 200
    assert paiement(lea, f"garantie{envoi_lea['id']}").status_code == 200
    vu = client.get(f"/echanges/{echange['id']}", headers=lea.headers).json()
    t = next(t for t in vu["transferts"] if t["id"] == envoi_lea["id"])
    assert t["envoi_paye_le"] and t["envoi_format"] == "petit" and t["garantie"]
    a_preparer = [c for c in courriels.ENVOYES if c.destinataire == get_settings().contact_partenaires]
    assert "69002, Lyon" in a_preparer[-1].texte
    assert sujets(lea.email)[-1] == "Votre étiquette TopTroc arrive"


def test_impact(client, creer, monkeypatch):
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", "whsec_test")
    lea, bruno, echange = _echange_par_colis(client, creer)
    for qui in (lea, bruno):
        client.post(
            f"/echanges/{echange['id']}/depot",
            json={"transporteur": "Colissimo", "numero_suivi": "X1"},
            headers=qui.headers,
        )
    tout = client.get("/impact").json()
    assert (tout["echanges_termines"], tout["objets_reemployes"], tout["membres_participants"]) == (1, 2, 2)
    assert tout["kg_evites_estimes"] == 5.0  # sport 3 kg + maison 2 kg
    marseille = client.get(
        "/impact", params={"latitude": VIEUX_PORT[0], "longitude": VIEUX_PORT[1], "rayon_km": 10}
    ).json()
    assert marseille["objets_reemployes"] == 1 and marseille["kg_evites_estimes"] == 2.0
