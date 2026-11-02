"""TopTroc Pro : profil professionnel, catégories réservées à chaque secteur, vérification du SIRET."""

import pytest
from conftest import PHOTO

from montroc_api import nomenclature
from montroc_api.schemas import siret_valide

SIRET = "73282932000074"  # SIRET valide (clé de Luhn juste)


def _pro(client, qui, secteur="batiment", siret=SIRET, **autres):
    corps = {"secteur": secteur, "raison_sociale": f"Entreprise {qui.pseudo}", "siret": siret, **autres}
    return client.put("/pro/profil", json=corps, headers=qui.headers)


def _objet(client, qui, categorie, **detail):
    corps = {"categorie_slug": categorie, "titre": "Lot", "etat": "neuf", "photo_url": PHOTO, **detail}
    return client.post("/moi/objets", json=corps, headers=qui.headers)


def test_siret_verifie_par_la_cle_de_luhn():
    assert siret_valide("732 829 320 00074") == SIRET
    with pytest.raises(ValueError):
        siret_valide("73282932000075")
    with pytest.raises(ValueError):
        siret_valide("1234")


def test_secteurs_et_categories_pro_a_part(client):
    secteurs = client.get("/pro/secteurs").json()
    assert [s["secteur"] for s in secteurs] == ["batiment", "auto_moto", "alimentaire"]
    publiques = {c["slug"] for c in client.get("/categories").json()}
    assert not publiques & set(nomenclature.CATEGORIES_PRO)
    toutes = {c["slug"]: c for c in client.get("/categories?pro=true").json()}
    assert toutes["pro-auto-moto"]["secteur_pro"] == "auto_moto"
    assert toutes["mode"]["secteur_pro"] is None
    assert {"slug": "pro-auto-moto-freinage", "libelle": "Freinage"} in toutes["pro-auto-moto"]["sous_categories"]


def test_profil_pro_cree_puis_verifie_par_la_moderation(client, creer):
    artisan = creer.utilisateur("artisan")
    modo = creer.utilisateur("modo", email="modo@exemple.fr")
    assert client.get("/moi", headers=artisan.headers).json()["pro"] is None
    assert _pro(client, artisan, siret="12345678901234").status_code == 422

    r = _pro(client, artisan, metier="Plombier")
    assert r.status_code == 200, r.text
    pro = r.json()["pro"]
    assert pro == {
        "secteur": "batiment",
        "raison_sociale": "Entreprise artisan",
        "metier": "Plombier",
        "verifie": False,
        "siret": SIRET,
        "categorie_slug": "pro-batiment",
    }
    assert client.post(f"/pro/{artisan.id}/verification", headers=artisan.headers).status_code == 403
    assert client.post(f"/pro/{artisan.id}/verification", headers=modo.headers).status_code == 200
    public = client.get(f"/utilisateurs/{artisan.id}").json()["pro"]
    assert public == {
        "secteur": "batiment",
        "raison_sociale": "Entreprise artisan",
        "metier": "Plombier",
        "verifie": True,
    }
    assert "siret" not in public


def test_categorie_pro_reservee_au_secteur(client, creer):
    particulier = creer.utilisateur("particulier")
    garage = creer.utilisateur("garage")
    _pro(client, garage, secteur="auto_moto")

    refus = _objet(client, particulier, "pro-auto-moto")
    assert refus.status_code == 403 and "TopTroc Pro" in refus.json()["detail"]
    assert _objet(client, garage, "pro-batiment").status_code == 403  # pas son secteur
    r = _objet(
        client,
        garage,
        "pro-auto-moto",
        sous_categorie_slug="pro-auto-moto-freinage",
        caracteristiques={"origine": "Origine constructeur", "reference": "7701208265"},
    )
    assert r.status_code == 201, r.text
    objet = r.json()["id"]

    # Ni demande, ni J'aime d'un particulier ; l'objet n'est pas dans le fil des particuliers.
    assert (
        client.post("/moi/souhaits", json={"categorie_slug": "pro-auto-moto"}, headers=particulier.headers).status_code
        == 403
    )
    assert client.post("/moi/souhaits", json={"objet_id": objet}, headers=particulier.headers).status_code == 403
    assert (
        client.post("/match/avis", json={"objet_id": objet, "aime": True}, headers=particulier.headers).status_code
        == 409
    )
    assert objet not in {o["id"] for o in client.get("/objets").json()}
    assert objet in {o["id"] for o in client.get("/objets?categorie=pro-auto-moto").json()}


def test_echange_entre_deux_garages(client, creer):
    a, b = creer.utilisateur("garage-a"), creer.utilisateur("garage-b")
    for g in (a, b):
        _pro(client, g, secteur="auto_moto")
    disques = _objet(client, a, "pro-auto-moto", sous_categorie_slug="pro-auto-moto-freinage").json()["id"]
    filtre = _objet(client, b, "pro-auto-moto", sous_categorie_slug="pro-auto-moto-filtration-entretien").json()["id"]
    for qui, sous in ((a, "pro-auto-moto-filtration-entretien"), (b, "pro-auto-moto-freinage")):
        r = client.post(
            "/moi/souhaits",
            json={"categorie_slug": "pro-auto-moto", "sous_categorie_slug": sous, "mode_recherche": "precise"},
            headers=qui.headers,
        )
        assert r.status_code == 201, r.text
    assert filtre in {c["objet"]["id"] for c in client.get("/match/carrousel", headers=a.headers).json()}
    assert client.post("/match/avis", json={"objet_id": filtre, "aime": True}, headers=a.headers).status_code == 200
    r = client.post("/match/avis", json={"objet_id": disques, "aime": True}, headers=b.headers)
    assert r.json()["match"] is not None


def test_quitter_pro_demande_de_retirer_ses_objets(client, creer):
    artisan = creer.utilisateur("artisan")
    _pro(client, artisan)
    objet = _objet(client, artisan, "pro-batiment").json()["id"]
    assert client.delete("/pro/profil", headers=artisan.headers).status_code == 409
    assert _pro(client, artisan, secteur="alimentaire").status_code == 409
    client.patch(f"/moi/objets/{objet}", json={"statut": "retire"}, headers=artisan.headers)
    r = client.delete("/pro/profil", headers=artisan.headers)
    assert r.status_code == 200 and r.json()["pro"] is None
