"""Les règles métier sont garanties par la base elle-même, pas seulement par l'API."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from montroc_api.db import engine


def executer(sql):
    with engine.begin() as conn:
        conn.execute(text(sql))


def test_categories_de_base_presentes(client):
    slugs = {c["slug"] for c in client.get("/categories").json()}
    assert {"mode", "enfant", "sport", "divers"} <= slugs


@pytest.mark.parametrize(
    "sql",
    [
        # Un souhait porte soit sur une catégorie, soit sur un objet, jamais les deux ni aucun.
        "INSERT INTO souhaits (utilisateur_id) VALUES (1)",
        "INSERT INTO souhaits (utilisateur_id, categorie_slug, rang) VALUES (1, 'velo', 0)",
        "INSERT INTO utilisateurs (email, pseudo, fiabilite) VALUES ('x@y.fr', 'x', 1.5)",
        "INSERT INTO utilisateurs (email, pseudo, engagements_manques) VALUES ('x@y.fr', 'x', -1)",
        "INSERT INTO utilisateurs (email, pseudo) VALUES ('ALICE@exemple.fr', 'autre')",  # e-mail sans casse
        "INSERT INTO objets (proprietaire_id, categorie_slug, titre, statut) VALUES (1, 'velo', 'V', 'vendu')",
        "INSERT INTO objets (proprietaire_id, categorie_slug, titre) VALUES (1, 'inconnue', 'V')",
        "INSERT INTO categories (slug, libelle) VALUES ('Pas Un Slug', 'x')",
        # Pas d'objet disponible sans photo ni état.
        "INSERT INTO objets (proprietaire_id, categorie_slug, titre, etat) VALUES (1, 'velo', 'V', 'bon')",
        "INSERT INTO objets (proprietaire_id, categorie_slug, titre, photo_url) VALUES (1, 'velo', 'V', 'https://x')",
        "INSERT INTO objets (proprietaire_id, categorie_slug, titre, photo_url, etat) "
        "VALUES (1, 'velo', 'V', 'https://x', 'abime')",
    ],
)
def test_contraintes_refusent_les_donnees_incoherentes(creer, sql):
    creer.utilisateur("alice")
    with pytest.raises(IntegrityError):
        executer(sql)


def test_suppression_utilisateur_en_cascade(client, creer):
    a = creer.utilisateur("alice")
    creer.objet(a, "sport")
    creer.souhait(a, "enfant")
    assert client.delete("/moi", headers=a.headers).status_code == 204
    assert client.get("/objets").json() == []
