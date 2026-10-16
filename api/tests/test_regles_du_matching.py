"""Les règles du matching (document « Catégories et caractéristiques », section 13) vues depuis l'API :
état minimum, critères, alternatives, modes de recherche, logistique et équité."""

from alembic import command
from alembic.config import Config
from conftest import PHOTO, RACINE_API
from sqlalchemy import text

from montroc_api import services
from montroc_api.db import SessionLocal, engine


def _objet(client, qui, categorie, **detail):
    corps = {"categorie_slug": categorie, "titre": categorie, "etat": "bon", "photo_url": PHOTO, **detail}
    r = client.post("/moi/objets", json=corps, headers=qui.headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _souhait(client, qui, categorie, **detail):
    return client.post("/moi/souhaits", json={"categorie_slug": categorie, **detail}, headers=qui.headers)


def _recus(client, qui) -> set[int]:
    boucles = client.get("/moi/boucles", headers=qui.headers).json()
    return {e["objet"]["id"] for b in boucles for e in b["etapes"] if e["receveur_id"] == qui.id}


def test_etat_minimum_modes_d_echange_et_alternatives(client, creer):
    """Bruno cherche une perceuse en très bon état minimum, remise en main propre ; il accepte aussi une lampe."""
    alice, bruno, chloe, denis = (creer.utilisateur(p) for p in ("alice", "bruno", "chloe", "denis"))
    perceuses = {"sous_categorie_slug": "bricolage-electroportatif"}
    usee = _objet(client, alice, "bricolage", **perceuses, etat="correct")
    neuve_relais = _objet(client, chloe, "bricolage", **perceuses, etat="neuf", modes_echange=["point_relais"])
    comme_neuve = _objet(client, denis, "bricolage", **perceuses, etat="comme_neuf")
    lampe = _objet(client, denis, "maison", sous_categorie_slug="maison-luminaires", etat="tres_bon")
    creer.objet(bruno, "sport")
    for qui in (alice, chloe, denis):
        creer.souhait(qui, "sport")
    r = _souhait(
        client,
        bruno,
        "bricolage",
        **perceuses,
        etat_min="tres_bon",
        modes_echange=["main_propre"],
        alternatives=[{"categorie_slug": "maison", "sous_categorie_slug": "maison-luminaires"}],
    )
    assert r.status_code == 201, r.text
    assert r.json()["mode_recherche"] == "flexible" and r.json()["etat_min"] == "tres_bon"
    assert _recus(client, bruno) == {comme_neuve, lampe}
    assert usee not in _recus(client, bruno) and neuve_relais not in _recus(client, bruno)

    # En recherche précise, l'alternative ne compte plus.
    client.delete(f"/moi/souhaits/{r.json()['id']}", headers=bruno.headers)
    _souhait(client, bruno, "bricolage", **perceuses, etat_min="tres_bon", mode_recherche="precise",
             alternatives=[{"categorie_slug": "maison"}])  # fmt: skip
    assert _recus(client, bruno) == {comme_neuve, neuve_relais}


def test_demande_invalide(client, creer):
    bruno = creer.utilisateur("bruno")
    for detail in (
        {"modes_echange": ["colis"]},
        {"etat_min": "usage"},
        {"mode_recherche": "au hasard"},
        {"caracteristiques": {"marque": "Bosch"}, "preferences": {"marque": "Makita"}},
        {"alternatives": [{"categorie_slug": "maison", "sous_categorie_slug": "bricolage-electroportatif"}]},
    ):
        assert _souhait(client, bruno, "bricolage", **detail).status_code == 422, detail
    assert _souhait(client, bruno, "bricolage", alternatives=[{"categorie_slug": "inconnue"}]).status_code == 404
    # Tous les modes cochés : aucun précisé.
    r = _souhait(client, bruno, "bricolage", modes_echange=["main_propre", "point_relais"])
    assert r.json()["modes_echange"] == []


def test_zones_acceptees(client, creer):
    """Bruno, à Marseille, accepte aussi les objets d'Aix : celui d'Alice (Aix) lui est proposé, pas celui de Lyon."""
    alice = creer.utilisateur("alice", zone="Aix-en-Provence")
    lea = creer.utilisateur("lea", zone="Lyon")
    bruno = creer.utilisateur("bruno")
    a, lyon = _objet(client, alice, "bricolage"), _objet(client, lea, "bricolage")
    creer.objet(bruno, "sport")
    for qui in (alice, lea):
        creer.souhait(qui, "sport", zones=["Marseille"])
    assert _recus(client, bruno) == set()
    assert _souhait(client, bruno, "bricolage", zones=["  aix-en-provence "]).status_code == 201
    assert _recus(client, bruno) == {a}
    assert lyon not in _recus(client, bruno)


def test_equite(client, creer):
    """Qui vient de recevoir un objet passe après les autres, à nombre d'échanges égal : priorité 3 au lieu de 4."""
    (a, b, c), _ = creer.echange_abc()
    denis = creer.utilisateur("denis")
    with SessionLocal() as session:
        marche = services.construire_marche(session)
    priorites = {u.pseudo: marche.utilisateurs[str(u.id)].priorite for u in (a, b, c, denis)}
    assert priorites == {"alice": 3, "bruno": 3, "chloe": 3, "denis": 4}


def test_migration_de_l_etat_usage(creer):
    """Migration 0013 : « Usagé, fonctionne » devient « Correct »."""
    objet = creer.objet(creer.utilisateur("alice"), "enfant")
    config = Config(str(RACINE_API / "alembic.ini"))
    config.set_main_option("script_location", str(RACINE_API / "alembic"))
    command.downgrade(config, "0012")
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE objets SET etat = 'usage' WHERE id = :id"), {"id": objet})
    finally:
        command.upgrade(config, "head")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT etat FROM objets WHERE id = :id"), {"id": objet}) == "correct"
