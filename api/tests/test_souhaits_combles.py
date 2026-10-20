"""Un souhait comblé ne reçoit pas plus que sa quantité : ni au repêchage, ni au Grand Troc suivant,
ni pendant un accord du Match."""

from sqlalchemy import text
from test_api import TACHES, _dimanche

from montroc_api import services
from montroc_api.db import engine


def _deux_poussettes_pour_une_lampe(creer):
    """Alice a deux poussettes et ne veut qu'une lampe ; Bruno et Chloé ont chacun une lampe et veulent une
    poussette."""
    a, b, c = creer.utilisateur("alice"), creer.utilisateur("bruno"), creer.utilisateur("chloe")
    creer.objet(a, "enfant", "Poussette 1")
    creer.objet(a, "enfant", "Poussette 2")
    lampe = creer.souhait(a, "maison", acceptation_auto=True)
    for p in (b, c):
        creer.objet(p, "maison", f"Lampe de {p.pseudo}")
        creer.souhait(p, "enfant", acceptation_auto=True)
    return a, b, c, lampe


def test_pas_de_deuxieme_lampe_au_repechage_ni_le_dimanche_suivant(client, creer, monkeypatch):
    a, _, _, lampe = _deux_poussettes_pour_une_lampe(creer)
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 5))
    (echange,) = client.post("/taches/grand-troc", headers=TACHES).json()["echanges"]
    assert echange["statut"] == "accepte"  # acceptations automatiques
    with engine.begin() as conn:
        conn.execute(text("UPDATE grands_trocs SET cree_le = :t"), {"t": _dimanche(18, 5)})
        conn.execute(text("UPDATE objets SET cree_le = :t"), {"t": _dimanche(10)})
        recu = conn.execute(text("SELECT souhait_id FROM transferts WHERE receveur_id = :a"), {"a": a.id}).scalar()
    assert recu == lampe

    # Mardi 18 h 17 : la seconde poussette reste, mais le souhait « une lampe » est déjà comblé.
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 17, jour=20))
    assert client.post("/taches/horaires", headers=TACHES).json()["objets_repeches"] == 0
    # Le dimanche suivant non plus.
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 5, jour=25))
    r = client.post("/taches/grand-troc", headers=TACHES).json()
    assert r["lance"] and r["echanges"] == []


def test_un_echange_annule_libere_le_souhait(client, creer, monkeypatch):
    _deux_poussettes_pour_une_lampe(creer)
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 5))
    client.post("/taches/grand-troc", headers=TACHES)
    with engine.begin() as conn:
        conn.execute(text("UPDATE echanges SET statut = 'annule'"))
    monkeypatch.setattr(services, "_maintenant", lambda: _dimanche(18, 5, jour=25))
    assert len(client.post("/taches/grand-troc", headers=TACHES).json()["echanges"]) == 1


def test_un_accord_du_match_compte_dans_le_souhait(client, creer):
    a, b, c, lampe = _deux_poussettes_pour_une_lampe(creer)
    poussette = next(o["id"] for o in client.get("/moi/objets", headers=a.headers).json())
    lampe_bruno = next(o["id"] for o in client.get("/moi/objets", headers=b.headers).json())
    for qui, objet in ((b, poussette), (a, lampe_bruno)):
        r = client.post("/match/avis", json={"objet_id": objet, "aime": True}, headers=qui.headers)
        assert r.status_code == 200, r.text
    r = client.post("/match/accord", json={"mon_objet_id": poussette, "son_objet_id": lampe_bruno}, headers=a.headers)
    assert r.status_code == 201, r.text
    with engine.begin() as conn:
        servis = dict(conn.execute(text("SELECT receveur_id, souhait_id FROM transferts")).all())
    assert servis[a.id] == lampe and servis[b.id] is not None

    # L'accord attend la réponse de Bruno : le Grand Troc ne propose pas pour autant la lampe de Chloé à Alice.
    r = client.post("/taches/grand-troc?force=true", headers=TACHES).json()
    assert r["lance"] and r["echanges"] == []
