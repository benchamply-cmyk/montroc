"""Filtres de la page d'une catégorie, faits par l'API : sous-catégorie, état, caractéristiques et tri."""

from conftest import PHOTO


def _objet(client, compte, titre, sous_categorie=None, etat="bon", **caracteristiques):
    r = client.post(
        "/moi/objets",
        json={
            "categorie_slug": "mode",
            "sous_categorie_slug": sous_categorie,
            "titre": titre,
            "etat": etat,
            "photo_url": PHOTO,
            "caracteristiques": caracteristiques,
        },
        headers=compte.headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _titres(client, **params):
    r = client.get("/objets", params={"categorie": "mode", **params})
    assert r.status_code == 200, r.text
    return [o["titre"] for o in r.json()]


def _catalogue(client, creer):
    a = creer.utilisateur("alice")
    _objet(client, a, "Robe M noire", "mode-vetements-femme", "neuf", taille="M", couleur="Noir")
    _objet(client, a, "Robe L rouge", "mode-vetements-femme", "bon", taille="L", couleur="Rouge")
    _objet(client, a, "Chemise M", "mode-vetements-homme", "comme_neuf", taille="M", couleur="Noir")
    _objet(client, a, "Baskets 42", "mode-chaussures-homme", "bon", pointure="42")
    _objet(client, a, "Sac sans détail")
    creer.objet(a, "sport", titre="Vélo")


def test_filtre_par_sous_categorie(client, creer):
    _catalogue(client, creer)
    assert sorted(_titres(client, sous_categorie="mode-vetements-femme")) == ["Robe L rouge", "Robe M noire"]
    assert _titres(client, sous_categorie="mode-chaussures-homme") == ["Baskets 42"]
    assert _titres(client, sous_categorie="mode-sacs") == []
    assert len(_titres(client)) == 5


def test_sous_categorie_d_une_autre_categorie_refusee(client, creer):
    r = client.get("/objets", params={"categorie": "mode", "sous_categorie": "sport-velos"})
    assert r.status_code == 422
    assert "sous-catégorie" in r.json()["detail"]


def test_filtre_par_etat(client, creer):
    _catalogue(client, creer)
    assert sorted(_titres(client, etat=["neuf", "comme_neuf"])) == ["Chemise M", "Robe M noire"]
    assert client.get("/objets", params={"etat": "abime"}).status_code == 422


def test_filtre_par_caracteristiques(client, creer):
    _catalogue(client, creer)
    # Deux valeurs d'une même caractéristique : l'une ou l'autre.
    assert sorted(_titres(client, caracteristique=["taille:M", "taille:L"])) == [
        "Chemise M",
        "Robe L rouge",
        "Robe M noire",
    ]
    # Deux caractéristiques : les deux à la fois.
    assert sorted(_titres(client, caracteristique=["taille:M", "couleur:Noir"])) == ["Chemise M", "Robe M noire"]
    assert _titres(client, caracteristique=["couleur:Rouge", "taille:M"]) == []
    # Avec la sous-catégorie, comme sur la page d'une catégorie.
    assert _titres(client, sous_categorie="mode-vetements-femme", caracteristique="taille:M") == ["Robe M noire"]


def test_filtres_de_caracteristiques_mal_formes(client):
    assert client.get("/objets", params={"categorie": "mode", "caracteristique": "taille"}).status_code == 422
    assert client.get("/objets", params={"categorie": "mode", "caracteristique": "inconnue:x"}).status_code == 422
    assert client.get("/objets", params={"caracteristique": "taille:M"}).status_code == 422
    r = client.get(
        "/objets",
        params={"categorie": "mode", "sous_categorie": "mode-sacs", "caracteristique": "pointure:42"},
    )
    assert r.status_code == 422


def test_tri_plus_anciens(client, creer):
    _catalogue(client, creer)
    recents = _titres(client)
    assert recents[0] == "Sac sans détail"
    assert _titres(client, tri="ancien") == list(reversed(recents))
    assert client.get("/objets", params={"tri": "prix"}).status_code == 422


def test_pages_avec_filtres(client, creer):
    _catalogue(client, creer)
    premiere = _titres(client, caracteristique="taille:M", limite=1)
    suivante = _titres(client, caracteristique="taille:M", limite=1, decalage=1)
    assert len(premiere) == len(suivante) == 1
    assert premiere != suivante
