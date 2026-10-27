"""Mode visiteur : catalogue complet sans compte, favoris des membres, suivi par e-mail ou SMS sans compte."""

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from montroc_api import courriels, sms
from montroc_api.db import engine

TACHES = {"X-Taches-Secret": "secret-des-taches"}


def _jeton_de_suivi(texte: str) -> str:
    return re.search(r"#suivi=(\S+)", texte).group(1)


def _vieillir(sql: str, **params):
    with engine.begin() as conn:
        conn.execute(text(sql), params)


def test_catalogue_complet_par_pages_sans_compte(client, creer):
    alice = creer.utilisateur("alice")
    ids = [creer.objet(alice, "sport", titre=f"vélo {i}") for i in range(5)]
    page1 = client.get("/objets", params={"limite": 2}).json()
    page2 = client.get("/objets", params={"limite": 2, "decalage": 2}).json()
    page3 = client.get("/objets", params={"limite": 2, "decalage": 4}).json()
    vus = [o["id"] for o in page1 + page2 + page3]
    assert sorted(vus) == sorted(ids) and len(set(vus)) == 5
    assert client.get("/objets", params={"limite": 500}).status_code == 422


def test_favoris_d_un_membre_et_retrait_du_coeur(client, creer):
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    velo, lampe = creer.objet(alice, "sport", titre="vélo"), creer.objet(alice, "maison", titre="lampe")
    for objet_id in (velo, lampe):
        assert (
            client.post("/match/avis", json={"objet_id": objet_id, "aime": True}, headers=bruno.headers).status_code
            == 200
        )
    assert [o["id"] for o in client.get("/match/favoris", headers=bruno.headers).json()] == [lampe, velo]
    assert client.delete(f"/match/avis/{lampe}", headers=bruno.headers).status_code == 204
    assert [o["id"] for o in client.get("/match/favoris", headers=bruno.headers).json()] == [velo]
    assert client.get("/match/favoris").status_code == 401


def test_suivi_par_email_confirme_puis_alerte(client, creer):
    maintenant = datetime.now(UTC)
    r = client.post(
        "/suivis",
        json={
            "email": "Visiteur@Exemple.fr",
            "recherches": [{"q": "vélo"}, {"q": "", "categorie": "enfant"}, {"q": " "}],
            "favoris": [{"objet_id": 1, "ajoute_le": maintenant.isoformat()}],
        },
    )
    assert r.status_code == 202
    confirmation = courriels.ENVOYES[-1]
    assert confirmation.destinataire == "visiteur@exemple.fr" and "Confirmez" in confirmation.sujet
    jeton = _jeton_de_suivi(confirmation.texte)

    # Avant confirmation, rien ne part.
    alice = creer.utilisateur("alice")
    creer.objet(alice, "sport", titre="vélo rouge")
    courriels.ENVOYES.clear()
    assert client.post("/taches/horaires", headers=TACHES).json()["alertes_visiteurs"] == 0

    lu = client.post(f"/suivis/{jeton}/confirmer").json()
    assert lu["email"] == "visiteur@exemple.fr" and lu["confirme_le"]
    assert [x["q"] for x in lu["recherches"]] == ["vélo", ""]  # la recherche vide est ignorée

    # Les objets publiés après la confirmation déclenchent une alerte, une seule par jour.
    velo = creer.objet(alice, "sport", titre="vélo bleu")
    creer.objet(alice, "maison", titre="lampe")
    poussette = creer.objet(alice, "enfant", titre="poussette")
    courriels.ENVOYES.clear()
    assert client.post("/taches/horaires", headers=TACHES).json()["alertes_visiteurs"] == 1
    alerte = next(c for c in courriels.ENVOYES if c.destinataire == "visiteur@exemple.fr")
    assert f"#objet-{velo}" in alerte.texte and f"#objet-{poussette}" in alerte.texte and "lampe" not in alerte.texte
    assert "vélo rouge" not in alerte.texte
    arret = re.search(r"#suivi-arret=(\S+)", alerte.texte).group(1)
    creer.objet(alice, "sport", titre="vélo vert")
    assert client.post("/taches/horaires", headers=TACHES).json()["alertes_visiteurs"] == 0

    # Mise à jour depuis le navigateur, puis « Ne plus recevoir ces alertes ».
    r = client.put(f"/suivis/{jeton}", json={"recherches": [{"q": "lampe"}], "favoris": []})
    assert r.status_code == 200 and r.json()["recherches"] == [{"q": "lampe", "categorie": None}]
    assert client.post(f"/suivis/arret/{arret}").status_code == 204
    assert client.get(f"/suivis/{jeton}").status_code == 404
    assert client.post("/suivis/arret/inconnu").status_code == 204


def test_rappel_avant_que_les_favoris_s_effacent(client):
    il_y_a_20_h = (datetime.now(UTC) - timedelta(hours=20)).isoformat()
    client.post("/suivis", json={"email": "v@exemple.fr", "favoris": [{"objet_id": 3, "ajoute_le": il_y_a_20_h}]})
    jeton = _jeton_de_suivi(courriels.ENVOYES[-1].texte)
    client.post(f"/suivis/{jeton}/confirmer")
    courriels.ENVOYES.clear()
    assert client.post("/taches/horaires", headers=TACHES).json()["alertes_visiteurs"] == 1
    assert courriels.ENVOYES[-1].sujet == "Vos favoris TopTroc vont s'effacer"
    assert "Créez votre compte" in courriels.ENVOYES[-1].texte
    # Le même favori n'est rappelé qu'une fois, même le lendemain.
    _vieillir("UPDATE suivis_visiteurs SET derniere_alerte_le = now() - interval '1 day'")
    assert client.post("/taches/horaires", headers=TACHES).json()["alertes_visiteurs"] == 0


def test_suivi_par_sms_et_limites(client):
    assert client.post("/suivis", json={"recherches": [{"q": "vélo"}]}).status_code == 422  # ni e-mail ni téléphone
    assert client.post("/suivis", json={"telephone": "12"}).status_code == 422
    assert (
        client.post("/suivis", json={"telephone": "06 12 34 56 78", "recherches": [{"q": "vélo"}]}).status_code == 202
    )
    assert sms.ENVOYES[-1].numero == "+33612345678" and "#suivi=" in sms.ENVOYES[-1].texte
    jeton = _jeton_de_suivi(sms.ENVOYES[-1].texte)
    for _ in range(2):
        assert client.post("/suivis", json={"telephone": "0612345678"}).status_code == 202
    assert client.post("/suivis", json={"telephone": "0612345678"}).status_code == 409  # 3 demandes par heure

    # Confirmer le premier lien efface les autres demandes du même numéro.
    assert client.post(f"/suivis/{jeton}/confirmer").json()["telephone"] == "+33612345678"
    with engine.begin() as conn:
        assert conn.execute(text("SELECT count(*) FROM suivis_visiteurs")).scalar() == 1
    assert client.delete(f"/suivis/{jeton}").status_code == 204
    assert client.post(f"/suivis/{jeton}/confirmer").status_code == 404


def test_purge_des_demandes_jamais_confirmees(client):
    client.post("/suivis", json={"email": "oubli@exemple.fr"})
    jeton = _jeton_de_suivi(courriels.ENVOYES[-1].texte)
    _vieillir("UPDATE suivis_visiteurs SET cree_le = now() - interval '8 days'")
    assert client.post(f"/suivis/{jeton}/confirmer").status_code == 404
    client.post("/taches/horaires", headers=TACHES)
    with engine.begin() as conn:
        assert conn.execute(text("SELECT count(*) FROM suivis_visiteurs")).scalar() == 0
