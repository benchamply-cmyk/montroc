"""Migration 0012 : les objets et demandes des 14 anciennes catégories passent dans les 10 nouvelles."""

import importlib.util

from alembic import command
from alembic.config import Config
from conftest import RACINE_API
from sqlalchemy import text

from montroc_api import nomenclature
from montroc_api.db import engine

_spec = importlib.util.spec_from_file_location(
    "migration_0012", RACINE_API / "alembic" / "versions" / "20261016_0012_nouvelles_categories.py"
)
migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migration)


def _config():
    config = Config(str(RACINE_API / "alembic.ini"))
    config.set_main_option("script_location", str(RACINE_API / "alembic"))
    return config


def test_chaque_ancienne_sous_categorie_et_caracteristique_a_une_place_valide():
    for ancienne, (categorie, sous, ajoutees) in migration.SOUS_CATEGORIES.items():
        assert sous is None or sous in dict(nomenclature.sous_categories(categorie)), ancienne
        assert nomenclature.verifier(categorie, sous, ajoutees, demande=False) == ajoutees, ancienne
    for categorie, sous in migration.PAR_DEFAUT.values():
        assert categorie in nomenclature.DETAIL and (
            sous is None or sous in dict(nomenclature.sous_categories(categorie))
        )
    assert set(migration.PAR_DEFAUT) == set(migration.ANCIENNES)


def test_conversion():
    assert migration.convertir(
        "poussette", "poussette-canne", {"age": "Dès la naissance", "marque": "Yoyo"}, False
    ) == (
        "enfant",
        "enfant-poussettes",
        {"age": "Naissance", "marque": "Yoyo", "type_poussette": "Canne"},
    )
    # Une demande ne garde que les choix fixes ; une valeur qui n'existe plus est retirée.
    assert migration.convertir("jouets", None, {"age": "0-2 ans"}, True) == ("enfant", None, {})
    assert migration.convertir("jeux-de-societe", "jeux-de-societe-cartes", {"complet": "Pièces manquantes"}, True) == (
        "culture",
        "culture-jeux-ambiance",
        {"contenu": "Incomplet", "type": "Jeu"},
    )
    # La pointure suit les chaussures ; sans sous-catégorie de chaussures, elle ne se garde pas.
    assert migration.convertir("vetements-enfant", "vetements-enfant-chaussures", {"pointure": "30"}, False)[2] == {
        "pointure": "30"
    }
    assert migration.convertir("vetements-enfant", None, {"pointure": "30", "taille": "4 ans"}, False)[2] == {}
    assert migration.convertir("vetements-enfant", "vetements-enfant-deguisements", {"taille": "4 ans"}, False) == (
        "divers",
        "divers-fete-deguisements",
        {},
    )


def test_migration_des_donnees_existantes(creer):
    alice, bruno = creer.utilisateur("alice"), creer.utilisateur("bruno")
    objet = creer.objet(alice, "enfant")
    souhait = creer.souhait(bruno, "enfant")
    autre = creer.souhait(bruno, "culture")
    config = _config()
    command.downgrade(config, "0011")
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE objets SET categorie_slug = 'poussette', sous_categorie_slug = 'poussette-double', "
                    """caracteristiques = '{"marque": "Bugaboo", "age": "Dès 6 mois"}' WHERE id = :id"""
                ),
                {"id": objet},
            )
            conn.execute(
                text(
                    "UPDATE souhaits SET categorie_slug = 'velo', sous_categorie_slug = 'velo-vtt', "
                    """caracteristiques = '{"roues": "26\\""}' WHERE id = :id"""
                ),
                {"id": souhait},
            )
            conn.execute(text("UPDATE souhaits SET categorie_slug = 'livres' WHERE id = :id"), {"id": autre})
    finally:
        command.upgrade(config, "head")
    with engine.connect() as conn:
        o = conn.execute(
            text("SELECT categorie_slug, sous_categorie_slug, caracteristiques FROM objets WHERE id = :id"),
            {"id": objet},
        ).one()
        s = {
            r.id: (r.categorie_slug, r.sous_categorie_slug, r.caracteristiques)
            for r in conn.execute(
                text("SELECT id, categorie_slug, sous_categorie_slug, caracteristiques FROM souhaits")
            )
        }
        slugs = set(conn.scalars(text("SELECT slug FROM categories")))
    assert tuple(o) == (
        "enfant",
        "enfant-poussettes",
        {"marque": "Bugaboo", "age": "6–12 mois", "type_poussette": "Double"},
    )
    assert s[souhait] == ("sport", "sport-velos", {"sport": "Vélo"})
    assert s[autre] == ("culture", None, {})
    assert slugs == set(nomenclature.DETAIL)
