"""Parcours complets à travers l'API : objets, souhaits, boucles, réponses, dépôts, tâches planifiées."""

from datetime import UTC, datetime, timedelta

from conftest import PHOTO
from sqlalchemy import text

from montroc_api import courriels
from montroc_api.db import engine

TACHES = {"X-Taches-Secret": "secret-des-taches"}


def sujets(email):
    return [c.sujet for c in courriels.ENVOYES if c.destinataire == email]


def test_sante(client):
    assert client.get("/sante").json()["statut"] == "ok"


def test_photo_et_etat_obligatoires(client, creer):
    alice = creer.utilisateur("alice")
    base = {"categorie_slug": "velo", "titre": "Vélo"}
    for manque in ({"etat": "bon"}, {"photo_url": PHOTO}):
        assert client.post("/moi/objets", json={**base, **manque}, headers=alice.headers).status_code == 422
    ailleurs = {**base, "etat": "bon", "photo_url": "https://exemple.fr/photo.jpg"}
    assert client.post("/moi/objets", json=ailleurs, headers=alice.headers).status_code == 422
    assert (
        client.post(
            "/moi/objets", json={**base, "etat": "abime", "photo_url": PHOTO}, headers=alice.headers
        ).status_code
        == 422
    )
    r = client.post("/moi/objets", json={**base, "etat": "tres_bon", "photo_url": PHOTO}, headers=alice.headers)
    assert r.status_code == 201 and r.json()["photo_url"] == PHOTO and r.json()["etat"] == "tres_bon"


def test_signature_cloudinary(client, creer):
    alice = creer.utilisateur("alice")
    s = client.get("/moi/photos/signature", headers=alice.headers).json()
    assert s["url_envoi"] == "https://api.cloudinary.com/v1_1/troc-test/image/upload"
    assert s["api_key"] == "cle" and s["folder"] == "objets" and len(s["signature"]) == 40


def test_on_ne_touche_qu_a_ses_objets(client, creer):
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    o = creer.objet(alice, "velo")
    assert client.patch(f"/moi/objets/{o}", json={"titre": "X"}, headers=bruno.headers).status_code == 404
    assert (
        client.patch(f"/moi/objets/{o}", json={"statut": "retire"}, headers=alice.headers).json()["statut"] == "retire"
    )
    assert client.get("/objets").json() == []
    assert client.patch(f"/moi/objets/{o}", json={"statut": "disponible"}, headers=alice.headers).status_code == 200
    s = creer.souhait(alice, "livres")
    assert client.delete(f"/moi/souhaits/{s}", headers=bruno.headers).status_code == 404
    assert client.delete(f"/moi/souhaits/{s}", headers=alice.headers).status_code == 204


def test_souhait_invalide(client, creer):
    a = creer.utilisateur("alice")
    o = creer.objet(a, "velo")
    assert client.post("/moi/souhaits", json={}, headers=a.headers).status_code == 422
    assert client.post("/moi/souhaits", json={"objet_id": o}, headers=a.headers).status_code == 409
    assert client.post("/moi/souhaits", json={"categorie_slug": "inconnue"}, headers=a.headers).status_code == 404


def test_filtrer_objets(client, creer):
    a = creer.utilisateur("alice", zone="Marseille")
    b = creer.utilisateur("bruno", zone="Paris")
    creer.objet(a, "velo")
    creer.objet(b, "velo")
    creer.objet(b, "livres")
    assert len(client.get("/objets", params={"categorie": "velo"}).json()) == 2
    assert len(client.get("/objets", params={"zone": "Paris"}).json()) == 2


def test_boucle_a_trois_de_bout_en_bout(client, creer):
    (a, b, c), objets = creer.boucle_abc()

    suggestions = client.get("/moi/boucles", headers=a.headers).json()
    assert len(suggestions) == 1 and suggestions[0]["longueur"] == 3
    etape = suggestions[0]["etapes"][0]
    assert etape["donneur_pseudo"] == "alice" and etape["objet"]["photo_url"] == PHOTO
    ordre = [e["objet"]["id"] for e in suggestions[0]["etapes"]]

    echange = client.post("/echanges", json={"objets": ordre}, headers=a.headers).json()
    assert echange["statut"] == "propose"
    # Choisir la boucle vaut accord pour Alice ; Bruno et Chloé sont prévenus.
    reponses = {t["receveur_pseudo"]: t["reponse"] for t in echange["transferts"]}
    assert reponses == {"alice": "acceptee", "bruno": "en_attente", "chloe": "en_attente"}
    assert sujets(b.email)[-1] == sujets(c.email)[-1] == "Une boucle vous attend"
    assert "Une boucle vous attend" not in sujets(a.email)

    assert {o["statut"] for o in client.get("/moi/objets", headers=a.headers).json()} == {"reserve"}
    # Les objets réservés ne sont plus proposés ailleurs.
    assert client.get("/moi/boucles", headers=b.headers).json() == []
    assert client.post("/echanges", json={"objets": ordre}, headers=b.headers).status_code == 409
    # Un échange n'est visible que de ses participants.
    intrus = creer.utilisateur("david")
    assert client.get(f"/echanges/{echange['id']}", headers=intrus.headers).status_code == 404
    assert (
        client.post(f"/echanges/{echange['id']}/reponse", json={"accepte": True}, headers=intrus.headers).status_code
        == 404
    )

    for p in (b, c):
        r = client.post(f"/echanges/{echange['id']}/reponse", json={"accepte": True}, headers=p.headers)
        assert r.status_code == 200, r.text
    assert r.json()["statut"] == "accepte"
    assert sujets(a.email)[-1] == "C'est oui pour tout le monde : à vous de déposer"

    # Pendant les dépôts, chacun ne voit que le code de son propre paquet.
    vu_par_a = client.get(f"/echanges/{echange['id']}", headers=a.headers).json()
    codes = {t["donneur_pseudo"]: t["code_retrait"] for t in vu_par_a["transferts"]}
    assert codes["alice"].startswith("TRC-") and codes["bruno"] is None and codes["chloe"] is None

    assert client.post(f"/echanges/{echange['id']}/depot", headers=b.headers).json()["statut"] == "accepte"
    assert client.post(f"/echanges/{echange['id']}/depot", headers=b.headers).status_code == 409
    assert sujets(a.email)[-1] == sujets(c.email)[-1] == "bruno a déposé"
    client.post(f"/echanges/{echange['id']}/depot", headers=a.headers)
    fini = client.post(f"/echanges/{echange['id']}/depot", headers=c.headers).json()
    assert fini["statut"] == "termine"
    assert sujets(c.email)[-1] == "Tout est déposé : votre objet vous attend"

    # Une fois tout déposé, le receveur obtient le code pour récupérer son objet.
    recu_par_a = next(t for t in fini["transferts"] if t["receveur_id"] == c.id)
    assert recu_par_a["code_retrait"] is not None
    assert client.get("/moi/objets", headers=c.headers).json() == []
    assert set(objets) == set(ordre)
    assert [e["statut"] for e in client.get("/moi/echanges", headers=a.headers).json()] == ["termine"]


def test_refus_libere_les_objets(client, creer):
    (a, b, c), echange = creer.echange_abc()
    assert client.post(f"/echanges/{echange['id']}/depot", headers=b.headers).status_code == 409
    r = client.post(f"/echanges/{echange['id']}/reponse", json={"accepte": False}, headers=b.headers)
    assert r.json()["statut"] == "annule"
    assert sujets(c.email)[-1] == "Échange annulé"
    assert len(client.get("/objets").json()) == 3


def test_acceptation_automatique(client, creer):
    _, echange = creer.echange_abc(auto=True)
    assert echange["statut"] == "accepte"


def test_objets_qui_ne_bouclent_pas(client, creer):
    # Alice donne la poussette à Chloé, qui donne le vélo à Bruno : [p, v, s] boucle, [p, s, v] non.
    (a, _, _), (p, s, v) = creer.boucle_abc()
    assert client.post("/echanges", json={"objets": [p, s, v]}, headers=a.headers).status_code == 409
    # On ne propose que des boucles dont on fait partie.
    d = creer.utilisateur("david")
    assert client.post("/echanges", json={"objets": [p, v, s]}, headers=d.headers).status_code == 409


def test_math_trade_reserve_aux_taches_planifiees(client, creer):
    creer.boucle_abc()
    d, e = creer.utilisateur("david"), creer.utilisateur("emma")
    creer.objet(d, "livres")
    creer.objet(e, "jouets")
    creer.souhait(d, "jouets")
    creer.souhait(e, "livres")

    assert client.post("/taches/math-trade").status_code == 403
    assert client.post("/taches/math-trade", headers={"X-Taches-Secret": "faux"}).status_code == 403
    r = client.post("/taches/math-trade", headers=TACHES).json()
    assert r["nb_objets_echanges"] == 5 and r["optimal"]
    assert sorted(len(x["transferts"]) for x in r["echanges"]) == [2, 3]
    assert all(t["code_retrait"] is None for x in r["echanges"] for t in x["transferts"])
    assert client.get("/objets").json() == []
    assert sujets(e.email) == ["Votre lien de connexion à Troc", "Une boucle vous attend"]
    # Relancer ne propose rien de plus : tout est réservé.
    assert client.post("/taches/math-trade", headers=TACHES).json()["echanges"] == []


def _decaler(echange_id, heures):
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE echanges SET expire_le = :t WHERE id = :id"),
            {"t": datetime.now(UTC) + timedelta(hours=heures), "id": echange_id},
        )


def test_rappel_puis_expiration(client, creer):
    (a, b, c), echange = creer.echange_abc()
    client.post(f"/echanges/{echange['id']}/reponse", json={"accepte": True}, headers=b.headers)

    assert client.post("/taches/horaires", headers=TACHES).json() == {"rappels_envoyes": 0, "echanges_expires": 0}
    _decaler(echange["id"], 11)
    assert client.post("/taches/horaires", headers=TACHES).json() == {"rappels_envoyes": 1, "echanges_expires": 0}
    assert sujets(c.email)[-1] == "Plus que 12 h pour répondre"
    assert "Plus que 12 h pour répondre" not in sujets(b.email)
    # Un seul rappel par échange.
    assert client.post("/taches/horaires", headers=TACHES).json()["rappels_envoyes"] == 0

    _decaler(echange["id"], -1)
    assert client.post("/taches/horaires", headers=TACHES).json()["echanges_expires"] == 1
    assert client.get(f"/echanges/{echange['id']}", headers=a.headers).json()["statut"] == "annule"
    assert len(client.get("/objets").json()) == 3


def test_depots_non_faits_dans_les_7_jours(client, creer):
    (a, _, _), echange = creer.echange_abc(auto=True)
    client.post(f"/echanges/{echange['id']}/depot", headers=a.headers)
    _decaler(echange["id"], -1)
    assert client.post("/taches/horaires", headers=TACHES).json()["echanges_expires"] == 1
    assert "chacun récupère le sien" in courriels.ENVOYES[-1].texte


def test_quitter_troc_annule_mes_echanges(client, creer):
    (a, b, _), echange = creer.echange_abc()
    assert client.delete("/moi", headers=b.headers).status_code == 204
    assert client.get(f"/echanges/{echange['id']}", headers=a.headers).json()["statut"] == "annule"
    assert {o["statut"] for o in client.get("/moi/objets", headers=a.headers).json()} == {"disponible"}
    assert sujets(a.email)[-1] == "Échange annulé"
