"""Parcours complets à travers l'API : objets, souhaits, boucles, réponses, dépôts, tâches planifiées."""

from datetime import UTC, datetime, timedelta

from conftest import PHOTO
from sqlalchemy import text

from montroc_api import courriels, services, sms
from montroc_api.config import get_settings
from montroc_api.db import engine

TACHES = {"X-Taches-Secret": "secret-des-taches"}


def sujets(email):
    return [c.sujet for c in courriels.ENVOYES if c.destinataire == email]


def test_sante(client):
    assert client.get("/sante").json()["statut"] == "ok"


def test_cors_apercus_netlify(client):
    def autorise(origine):
        r = client.options("/auth/connexion", headers={"Origin": origine, "Access-Control-Request-Method": "POST"})
        return r.headers.get("access-control-allow-origin") == origine

    assert autorise("https://troctroc.fr")
    assert autorise("https://deploy-preview-29--troctroc.netlify.app")
    assert autorise("https://troctroc.netlify.app")
    assert not autorise("https://troctroc.netlify.app.pirate.fr")
    assert not autorise("https://autre-site.netlify.app")


def test_photo_et_etat_obligatoires(client, creer):
    alice = creer.utilisateur("alice")
    base = {"categorie_slug": "sport", "titre": "Vélo"}
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


def test_objet_recopie_d_une_annonce(client, creer):
    """Le lien Vinted ou Leboncoin est gardé, nettoyé, et visible du seul propriétaire."""
    alice = creer.utilisateur("alice")
    base = {"categorie_slug": "sport", "titre": "Vélo", "etat": "bon", "photo_url": PHOTO}
    mauvais_liens = ("https://ebay.fr/itm/1", "https://www.vinted.fr/", "javascript:alert(1)", "vinted.fr/items/1")
    for mauvais in mauvais_liens:
        r = client.post("/moi/objets", json={**base, "annonce_origine": mauvais}, headers=alice.headers)
        assert r.status_code == 422, mauvais
    lien = "https://www.vinted.fr/items/123-velo-enfant?referrer=catalog#photos"
    r = client.post("/moi/objets", json={**base, "annonce_origine": lien}, headers=alice.headers)
    assert r.status_code == 201 and r.json()["annonce_origine"] == "https://www.vinted.fr/items/123-velo-enfant"
    lbc = {**base, "annonce_origine": "https://www.leboncoin.fr/ad/velos/2712345678"}
    assert client.post("/moi/objets", json=lbc, headers=alice.headers).status_code == 201
    sans = client.post("/moi/objets", json={**base, "annonce_origine": " "}, headers=alice.headers)
    assert sans.status_code == 201 and sans.json()["annonce_origine"] is None
    assert len([o for o in client.get("/moi/objets", headers=alice.headers).json() if o["annonce_origine"]]) == 2
    assert all("annonce_origine" not in o for o in client.get("/objets").json())


def test_signature_cloudinary(client, creer):
    alice = creer.utilisateur("alice")
    s = client.get("/moi/photos/signature", headers=alice.headers).json()
    assert s["url_envoi"] == "https://api.cloudinary.com/v1_1/troc-test/image/upload"
    assert s["api_key"] == "cle" and s["folder"] == "objets" and len(s["signature"]) == 40


def test_on_ne_touche_qu_a_ses_objets(client, creer):
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    o = creer.objet(alice, "sport")
    assert client.patch(f"/moi/objets/{o}", json={"titre": "X"}, headers=bruno.headers).status_code == 404
    assert (
        client.patch(f"/moi/objets/{o}", json={"statut": "retire"}, headers=alice.headers).json()["statut"] == "retire"
    )
    assert client.get("/objets").json() == []
    assert client.patch(f"/moi/objets/{o}", json={"statut": "disponible"}, headers=alice.headers).status_code == 200
    s = creer.souhait(alice, "culture")
    assert client.delete(f"/moi/souhaits/{s}", headers=bruno.headers).status_code == 404
    assert client.delete(f"/moi/souhaits/{s}", headers=alice.headers).status_code == 204


def test_souhait_invalide(client, creer):
    a = creer.utilisateur("alice")
    o = creer.objet(a, "sport")
    assert client.post("/moi/souhaits", json={}, headers=a.headers).status_code == 422
    assert client.post("/moi/souhaits", json={"objet_id": o}, headers=a.headers).status_code == 409
    assert client.post("/moi/souhaits", json={"categorie_slug": "inconnue"}, headers=a.headers).status_code == 404


def test_filtrer_objets(client, creer):
    a = creer.utilisateur("alice", zone="Marseille")
    b = creer.utilisateur("bruno", zone="Paris")
    creer.objet(a, "sport")
    creer.objet(b, "sport")
    creer.objet(b, "culture")
    assert len(client.get("/objets", params={"categorie": "sport"}).json()) == 2
    assert len(client.get("/objets", params={"zone": "Paris"}).json()) == 2


def test_recherche_libre_sans_compte(client, creer):
    a = creer.utilisateur("alice")
    b = creer.utilisateur("bruno")
    velo = creer.objet(a, "sport", titre="Vélo enfant 16 pouces")
    creer.objet(a, "culture", titre="Lot de BD")
    r = client.post(
        "/moi/objets",
        json={
            "categorie_slug": "culture",
            "titre": "Romans",
            "description": "Trois ÉLÉPHANTS et un 50% polar",
            "etat": "bon",
            "photo_url": PHOTO,
        },
        headers=b.headers,
    )
    romans = r.json()["id"]

    def chercher(q):
        r = client.get("/objets", params={"q": q})
        assert r.status_code == 200, r.text
        return [o["id"] for o in r.json()]

    # Sans en-tête d'authentification, sans accents ni majuscules, dans le titre ou la description.
    assert chercher("velo") == [velo]
    assert chercher("VÉLO enfant") == [velo]
    assert chercher("Vélos") == [velo] and chercher("pouces") == [velo]  # pluriels
    assert chercher("elephants") == [romans]
    assert chercher("velo bd") == []  # tous les mots doivent correspondre
    assert chercher("50%") == [romans] and chercher("%") == [romans]  # pas de joker
    assert chercher("   ") == chercher("") and len(chercher("")) == 3
    # Le libellé de la catégorie compte aussi.
    libelle = client.get("/categories").json()
    livres = next(c["libelle"] for c in libelle if c["slug"] == "culture")
    assert set(chercher(livres.split()[0].strip(","))) >= {romans}
    assert "email" not in client.get("/objets", params={"q": "velo"}).json()[0]
    # Retiré ou compte suspendu : plus trouvable.
    client.patch(f"/moi/objets/{velo}", json={"statut": "retire"}, headers=a.headers)
    assert chercher("velo") == []
    with engine.begin() as conn:
        conn.execute(text("UPDATE utilisateurs SET suspendu_le = now() WHERE pseudo = 'bruno'"))
    assert chercher("romans") == []
    assert client.get("/objets", params={"q": "x" * 101}).status_code == 422


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


def _dimanche(heure, minute=0, jour=18):
    """Un moment à Paris ; le 18 octobre 2026 est un dimanche."""
    return datetime(2026, 10, jour, heure, minute, tzinfo=services.PARIS)


def test_date_du_prochain_grand_troc():
    prochain = services.prochain_grand_troc
    # Un mercredi : le dimanche qui suit, 18 h à Paris (16 h UTC, heure d'été).
    premier = prochain(datetime(2026, 10, 14, 3, tzinfo=UTC))
    assert premier == _dimanche(18) and premier.utcoffset() == timedelta(hours=2)
    assert prochain(_dimanche(17, 59)) == _dimanche(18)
    # Juste après : la semaine suivante, toujours 18 h à Paris malgré le passage à l'heure d'hiver.
    suivant = prochain(_dimanche(18))
    assert suivant == _dimanche(18, jour=25) and suivant.utcoffset() == timedelta(hours=1)


def test_grand_troc_du_dimanche(client, creer, monkeypatch):
    (a, b, c), _ = creer.boucle_abc()
    d, e = creer.utilisateur("david"), creer.utilisateur("emma")
    creer.objet(d, "culture")
    creer.objet(e, "mode")
    creer.souhait(d, "mode")
    creer.souhait(e, "culture")

    assert client.post("/taches/grand-troc").status_code == 403
    assert client.post("/taches/grand-troc", headers={"X-Taches-Secret": "faux"}).status_code == 403

    # Avant 18 h, la tâche ne fait rien (elle passe deux fois le dimanche à cause de l'heure d'été).
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(17, 5))
    r = client.post("/taches/grand-troc", headers=TACHES).json()
    assert not r["lance"] and r["echanges"] == [] and "18/10 à 18 h" in r["message"]
    assert client.get("/grand-troc").json()["dernier"] is None

    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 5))
    r = client.post("/taches/grand-troc", headers=TACHES).json()
    assert r["lance"] and r["grand_troc"]["nb_objets"] == 5 and r["grand_troc"]["optimal"]
    assert sorted(len(x["transferts"]) for x in r["echanges"]) == [2, 3]
    assert {x["grand_troc_jour"] for x in r["echanges"]} == {"2026-10-18"}
    assert all(t["code_retrait"] is None for x in r["echanges"] for t in x["transferts"])
    assert client.get("/objets").json() == []
    assert sujets(e.email) == ["Votre lien de connexion à TrocTroc", "Grand Troc : une boucle vous attend"]
    assert "Le Grand Troc du dimanche a trouvé" in courriels.ENVOYES[-1].texte

    # Une seule fois par dimanche, même si la tâche est relancée.
    r = client.post("/taches/grand-troc", headers=TACHES).json()
    assert not r["lance"] and r["echanges"] == [] and r["grand_troc"]["nb_boucles"] == 2

    infos = client.get("/grand-troc").json()
    assert infos["dernier"]["jour"] == "2026-10-18" and infos["dernier"]["nb_participants"] == 5
    assert datetime.fromisoformat(infos["prochain"]) > datetime.now(UTC)


def test_grand_troc_force_et_depots_dans_la_semaine(client, creer, monkeypatch):
    creer.boucle_abc(auto=True)
    # Un mercredi : sans « force », rien ; avec, le Grand Troc a lieu tout de suite.
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(10, jour=14))
    assert not client.post("/taches/grand-troc", headers=TACHES).json()["lance"]
    r = client.post("/taches/grand-troc?force=true", headers=TACHES).json()
    assert r["lance"] and len(r["echanges"]) == 1
    # Acceptation automatique : dépôts jusqu'au dimanche suivant midi, avant le prochain Grand Troc.
    echange = r["echanges"][0]
    assert echange["statut"] == "accepte"
    assert datetime.fromisoformat(echange["expire_le"]) == datetime(2026, 10, 21, 12, tzinfo=services.PARIS)
    assert "avant mercredi 21/10 à 12 h" in courriels.ENVOYES[-1].texte


def test_sms_quand_le_grand_troc_propose(client, creer, monkeypatch):
    # Alice (avec portable) est dans deux boucles, Bruno (avec portable) dans une, les autres sans numéro.
    a = creer.utilisateur("alice", telephone="06 12 34 56 78")
    b = creer.utilisateur("bruno", telephone="+33 7 11 22 33 44")
    c, d = creer.utilisateur("chloe"), creer.utilisateur("david")
    creer.objet(a, "enfant")
    creer.objet(a, "culture")
    creer.objet(b, "sport")
    creer.objet(c, "maison")
    creer.objet(d, "mode")
    creer.souhait(a, "sport")
    creer.souhait(b, "enfant")
    creer.souhait(a, "mode")
    creer.souhait(d, "culture")
    creer.souhait(c, "mode")  # Chloé ne boucle avec personne
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 5))
    r = client.post("/taches/grand-troc", headers=TACHES).json()
    assert len(r["echanges"]) == 2
    envoyes = {x.numero: x.texte for x in sms.ENVOYES}
    assert set(envoyes) == {"+33612345678", "+33711223344"}
    assert envoyes["+33612345678"].startswith("Le Grand Troc vous propose 2 échanges.")
    assert envoyes["+33612345678"].endswith("/#echanges")
    assert "un échange" in envoyes["+33711223344"] and "#echange-" in envoyes["+33711223344"]


def test_telephone_a_l_inscription_et_dans_le_compte(client, creer):
    a = creer.utilisateur("alice", telephone="0033 6 12 34 56 78")
    assert client.get("/moi", headers=a.headers).json()["telephone"] == "+33612345678"
    # Jamais visible des autres.
    assert "telephone" not in client.get(f"/utilisateurs/{a.id}").json()
    r = client.patch("/moi", json={"telephone": "12"}, headers=a.headers)
    assert r.status_code == 422
    assert client.patch("/moi", json={"telephone": "07.98.76.54.32"}, headers=a.headers).json()["telephone"] == (
        "+33798765432"
    )
    assert client.patch("/moi", json={"telephone": ""}, headers=a.headers).json()["telephone"] is None
    # Boucle proposée à la demande par Alice (sans numéro) : SMS pour Bruno seulement, Chloé n'a que l'e-mail.
    creer.utilisateur("bruno", telephone="06 00 00 00 01")
    creer.echange_abc()
    assert [x.numero for x in sms.ENVOYES] == ["+33600000001"]
    assert sms.ENVOYES[0].texte.startswith("TrocTroc vous propose un échange.")


def test_echanges_a_la_demande_desactives_par_defaut(client, creer, monkeypatch):
    monkeypatch.setattr(get_settings(), "echanges_a_la_demande", False)
    (a, _, _), _ = creer.boucle_abc()
    # Les boucles possibles restent visibles, comme un aperçu de dimanche…
    boucles = client.get("/moi/boucles", headers=a.headers).json()
    assert len(boucles) == 1
    # … mais on ne peut plus en proposer une tout de suite.
    ordre = [e["objet"]["id"] for e in boucles[0]["etapes"]]
    r = client.post("/echanges", json={"objets": ordre}, headers=a.headers)
    assert r.status_code == 409 and "Grand Troc du dimanche" in r.json()["detail"]
    assert client.get("/grand-troc").json()["echanges_a_la_demande"] is False


def _decaler(echange_id, heures):
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE echanges SET expire_le = :t WHERE id = :id"),
            {"t": datetime.now(UTC) + timedelta(hours=heures), "id": echange_id},
        )


def test_rappel_puis_expiration(client, creer):
    (a, b, c), echange = creer.echange_abc()
    client.post(f"/echanges/{echange['id']}/reponse", json={"accepte": True}, headers=b.headers)

    rien = {"rappels_envoyes": 0, "echanges_expires": 0, "objets_repeches": None}
    assert client.post("/taches/horaires", headers=TACHES).json() == rien
    _decaler(echange["id"], 11)
    assert client.post("/taches/horaires", headers=TACHES).json() == {**rien, "rappels_envoyes": 1}
    assert sujets(c.email)[-1] == "Plus que 12 h pour répondre"
    assert "Plus que 12 h pour répondre" not in sujets(b.email)
    # Un seul rappel par échange.
    assert client.post("/taches/horaires", headers=TACHES).json()["rappels_envoyes"] == 0

    _decaler(echange["id"], -1)
    assert client.post("/taches/horaires", headers=TACHES).json()["echanges_expires"] == 1
    assert client.get(f"/echanges/{echange['id']}", headers=a.headers).json()["statut"] == "annule"
    assert len(client.get("/objets").json()) == 3
    # Chloé n'a pas répondu : un engagement manqué, sa fiabilité baisse. Bruno a répondu : rien ne change.
    assert client.get("/moi", headers=c.headers).json()["fiabilite"] == 0.9
    assert client.get("/moi", headers=b.headers).json()["fiabilite"] == 1


def test_depots_non_faits_dans_les_7_jours(client, creer):
    (a, b, c), echange = creer.echange_abc(auto=True)
    client.post(f"/echanges/{echange['id']}/depot", headers=a.headers)
    _decaler(echange["id"], -1)
    assert client.post("/taches/horaires", headers=TACHES).json()["echanges_expires"] == 1
    assert "chacun récupère le sien" in courriels.ENVOYES[-1].texte
    # Alice a déposé (engagement tenu), Bruno et Chloé non (manqué).
    fiabilites = [client.get("/moi", headers=p.headers).json()["fiabilite"] for p in (a, b, c)]
    assert fiabilites == [1, 0.9, 0.9]


def test_quitter_troc_annule_mes_echanges(client, creer):
    (a, b, _), echange = creer.echange_abc()
    assert client.delete("/moi", headers=b.headers).status_code == 204
    assert client.get(f"/echanges/{echange['id']}", headers=a.headers).json()["statut"] == "annule"
    assert {o["statut"] for o in client.get("/moi/objets", headers=a.headers).json()} == {"disponible"}
    assert sujets(a.email)[-1] == "Échange annulé"


def test_je_le_donne_contre(client, creer):
    a, b = creer.utilisateur("alice"), creer.utilisateur("bruno")
    siege = creer.souhait(a, "maison")
    livres = creer.souhait(a, "culture")
    poussette = creer.objet(a, "enfant")
    creer.objet(b, "culture")
    creer.souhait(b, "enfant")
    assert client.get("/moi/objets", headers=a.headers).json()[0]["contre_souhait_ids"] == []
    assert len(client.get("/moi/boucles", headers=a.headers).json()) == 1

    # Seulement contre un siège auto : la boucle avec le livre de Bruno disparaît.
    r = client.patch(
        f"/moi/objets/{poussette}", json={"contre_souhait_ids": [siege], "contre_strict": True}, headers=a.headers
    )
    assert r.status_code == 200 and r.json()["contre_souhait_ids"] == [siege] and r.json()["contre_strict"]
    assert client.get("/moi/boucles", headers=a.headers).json() == []
    # De préférence seulement : elle revient.
    client.patch(f"/moi/objets/{poussette}", json={"contre_strict": False}, headers=a.headers)
    assert len(client.get("/moi/boucles", headers=a.headers).json()) == 1
    assert client.get("/moi/objets", headers=a.headers).json()[0]["contre_souhait_ids"] == [siege]

    # Seulement ses propres souhaits ; les autres ne voient pas la liste.
    souhait_de_bruno = client.get("/moi/souhaits", headers=b.headers).json()[0]["id"]
    r = client.patch(f"/moi/objets/{poussette}", json={"contre_souhait_ids": [souhait_de_bruno]}, headers=a.headers)
    assert r.status_code == 409
    assert "contre_souhait_ids" not in client.get(f"/objets/{poussette}").json()
    # À la création aussi ; un souhait supprimé sort de la liste.
    r = client.post(
        "/moi/objets",
        json={
            "categorie_slug": "mode",
            "titre": "Lego",
            "etat": "bon",
            "photo_url": PHOTO,
            "contre_souhait_ids": [siege, livres],
            "contre_strict": True,
        },
        headers=a.headers,
    )
    assert r.status_code == 201 and r.json()["contre_souhait_ids"] == sorted([siege, livres])
    client.delete(f"/moi/souhaits/{siege}", headers=a.headers)
    lego = next(o for o in client.get("/moi/objets", headers=a.headers).json() if o["titre"] == "Lego")
    assert lego["contre_souhait_ids"] == [livres]


def test_repechage_du_mardi(client, creer, monkeypatch):
    # Alice a une poussette et veut un siège ; Bruno et Chloé ont chacun un siège et veulent la poussette.
    a, b, c = creer.utilisateur("alice"), creer.utilisateur("bruno"), creer.utilisateur("chloe")
    creer.objet(a, "enfant")
    creer.souhait(a, "maison")
    for p in (b, c):
        creer.objet(p, "maison")
        creer.souhait(p, "enfant")
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 5))
    (echange,) = client.post("/taches/grand-troc", headers=TACHES).json()["echanges"]
    with engine.begin() as conn:
        conn.execute(text("UPDATE grands_trocs SET cree_le = :t"), {"t": _dimanche(18, 5)})
        conn.execute(text("UPDATE objets SET cree_le = :t"), {"t": _dimanche(10)})
    # Un objet publié après le Grand Troc attend le dimanche suivant.
    david = creer.utilisateur("david")
    creer.objet(david, "maison")
    creer.souhait(david, "enfant")
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE objets SET cree_le = :t WHERE proprietaire_id = :d"),
            {"t": _dimanche(9, jour=19), "d": david.id},
        )

    # Le partenaire d'Alice refuse la poussette.
    partenaire = b if any(t["receveur_id"] == b.id for t in echange["transferts"]) else c
    autre = c if partenaire is b else b
    client.post(f"/echanges/{echange['id']}/reponse", json={"accepte": False}, headers=partenaire.headers)

    # Lundi : trop tôt. Mardi 18 h 17 : le repêchage propose la poussette à l'autre, une seule fois.
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(12, jour=19))
    assert client.post("/taches/horaires", headers=TACHES).json()["objets_repeches"] is None
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 17, jour=20))
    assert client.post("/taches/horaires", headers=TACHES).json()["objets_repeches"] == 2
    assert client.post("/taches/horaires", headers=TACHES).json()["objets_repeches"] is None
    (repeche,) = [e for e in client.get("/moi/echanges", headers=a.headers).json() if e["statut"] == "propose"]
    assert {t["receveur_id"] for t in repeche["transferts"]} == {a.id, autre.id}
    assert repeche["grand_troc_jour"] == "2026-10-18"
    assert client.get("/grand-troc").json()["dernier"]["nb_objets_repeches"] == 2
    with engine.begin() as conn:
        assert conn.execute(text("SELECT calcul_repechage FROM grands_trocs")).scalar()["moteur"]


def test_grand_troc_boucle_a_quatre(client, creer, monkeypatch):
    """Le Grand Troc cherche des boucles de 4 : la base doit pouvoir les enregistrer."""
    categories = ("enfant", "maison", "sport", "culture")
    gens = [creer.utilisateur(p) for p in ("alice", "bruno", "chloe", "david")]
    for k, p in enumerate(gens):
        creer.objet(p, categories[k])
        creer.souhait(p, categories[(k + 1) % 4])
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 5))
    r = client.post("/taches/grand-troc", headers=TACHES)
    assert r.status_code == 200, r.text
    (echange,) = r.json()["echanges"]
    assert sorted(t["position"] for t in echange["transferts"]) == [0, 1, 2, 3]


def test_grand_troc_garde_la_trace_du_calcul(client, creer, monkeypatch):
    creer.boucle_abc()
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 5))
    assert client.post("/taches/grand-troc", headers=TACHES).json()["lance"]
    with engine.begin() as conn:
        calcul, repechage = conn.execute(text("SELECT calcul, calcul_repechage FROM grands_trocs")).one()
    assert calcul["moteur"] in ("exact", "heuristique") and calcul["longueur_max"] == 4
    assert calcul["objectif"] == "esperance"
    assert calcul["optimal"] is True and "duree_s" in calcul
    if calcul["moteur"] == "exact":
        assert calcul["etapes"][0] == "OPTIMAL"
    assert repechage is None  # rempli par le repêchage du mardi


def test_grand_troc_saute_une_boucle_devenue_impossible(client, creer, monkeypatch):
    """Un objet réservé pendant le calcul (accord du Match, par exemple) : sa boucle est sautée, pas le Grand Troc."""
    for k, (x, y) in enumerate((("enfant", "maison"), ("sport", "culture"))):  # deux échanges à deux, séparés
        a, b = creer.utilisateur(f"a{k}"), creer.utilisateur(f"b{k}")
        creer.objet(a, x)
        creer.souhait(a, y)
        creer.objet(b, y)
        creer.souhait(b, x)
    calcul = services.math_trade

    def puis_un_objet_reserve(*args, **kwargs):
        solution = calcul(*args, **kwargs)
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE objets SET statut = 'reserve' WHERE id = :o"),
                {"o": int(solution.boucles[0].objets[0])},
            )
        return solution

    monkeypatch.setattr(services, "math_trade", puis_un_objet_reserve)
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 5))
    r = client.post("/taches/grand-troc", headers=TACHES)
    assert r.status_code == 200, r.text
    assert len(r.json()["echanges"]) == 1
    assert (r.json()["grand_troc"]["nb_boucles"], r.json()["grand_troc"]["nb_objets"]) == (1, 2)


def test_plafond_d_echanges_par_personne(client, creer, monkeypatch):
    """Un gros déposant ne reçoit pas plus de PLAFOND_ECHANGES_GRAND_TROC objets au même Grand Troc."""
    monkeypatch.setattr(services.get_settings(), "plafond_echanges_grand_troc", 2)
    gros = creer.utilisateur("gros")
    creer.souhait(gros, "maison", quantite=4)
    for k in range(4):
        p = creer.utilisateur(f"membre{k}")
        creer.objet(gros, "enfant", f"Jouet {k}")
        creer.objet(p, "maison", f"Lampe {k}")
        creer.souhait(p, "enfant")
    r = client.post("/taches/grand-troc?force=true", headers=TACHES)
    assert r.status_code == 200, r.text
    assert len(r.json()["echanges"]) == 2
