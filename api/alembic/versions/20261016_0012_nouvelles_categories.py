"""Les 10 catégories de TrocTroc et leurs 107 sous-catégories, à la place des 14 catégories du lancement.

Chaque objet et chaque demande passe dans sa nouvelle catégorie, avec la sous-catégorie qui correspond
quand elle est sûre (une poussette canne devient « Poussettes et accessoires », type Canne). Les
caractéristiques sont reprises quand elles existent encore, sous leur nouveau nom ; les autres sont
retirées (une demande sans elles est simplement plus large). Les catégories créées par la modération
ne bougent pas.

Les valeurs gardées sont vérifiées par la nomenclature du moment où la migration tourne : seules les
données présentes à ce moment comptent, une base neuve n'en a pas.

Le retour en arrière remet les 14 anciennes catégories, sans sous-catégories ni caractéristiques.

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from montroc_api import nomenclature

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ANCIENNES = {
    "poussette": "Poussette",
    "siege-auto": "Siège auto",
    "lit-bebe": "Lit bébé",
    "vetements-enfant": "Vêtements enfant",
    "jouets": "Jouets",
    "livres": "Livres",
    "jeux-de-societe": "Jeux de société",
    "velo": "Vélo",
    "sport": "Sport et plein air",
    "outillage": "Outillage",
    "electromenager": "Électroménager",
    "meubles": "Meubles",
    "deco": "Décoration",
    "multimedia": "Multimédia",
}

# Ancienne catégorie -> (nouvelle catégorie, sous-catégorie quand l'ancienne n'en précisait pas).
PAR_DEFAUT = {
    "poussette": ("enfant", "enfant-poussettes"),
    "siege-auto": ("enfant", "enfant-sieges-auto"),
    "lit-bebe": ("enfant", "enfant-lits-mobilier"),
    "vetements-enfant": ("enfant", None),
    "jouets": ("enfant", None),
    "livres": ("culture", None),
    "jeux-de-societe": ("culture", None),
    "velo": ("sport", "sport-velos"),
    "sport": ("sport", None),
    "outillage": ("bricolage", None),
    "electromenager": ("electromenager", None),
    "meubles": ("maison", None),
    "deco": ("maison", None),
    "multimedia": ("high-tech", None),
}

# Ancienne sous-catégorie -> (nouvelle catégorie, nouvelle sous-catégorie ou None si ambiguë,
# caractéristiques ajoutées).
SOUS_CATEGORIES = {
    "poussette-canne": ("enfant", "enfant-poussettes", {"type_poussette": "Canne"}),
    "poussette-citadine": ("enfant", "enfant-poussettes", {"type_poussette": "Citadine"}),
    "poussette-combinee": ("enfant", "enfant-poussettes", {"type_poussette": "Combinée"}),
    "poussette-double": ("enfant", "enfant-poussettes", {"type_poussette": "Double"}),
    "poussette-tout-terrain": ("enfant", "enfant-poussettes", {"type_poussette": "Tout-terrain"}),
    "poussette-nacelle": ("enfant", "enfant-poussettes", {}),
    **{
        s: ("enfant", "enfant-sieges-auto", {})
        for s in (
            "siege-auto-coque",
            "siege-auto-0-1",
            "siege-auto-1",
            "siege-auto-2-3",
            "siege-auto-evolutif",
        )
    },  # fmt: skip
    **{
        s: ("enfant", "enfant-lits-mobilier", {})
        for s in (
            "lit-bebe-barreaux",
            "lit-bebe-parapluie",
            "lit-bebe-berceau",
            "lit-bebe-cododo",
            "lit-bebe-evolutif",
            "lit-bebe-literie",
        )
    },  # fmt: skip
    "vetements-enfant-bodies": ("enfant", "enfant-vetements-bebe", {}),
    "vetements-enfant-hauts": ("enfant", "enfant-vetements", {}),
    "vetements-enfant-bas": ("enfant", "enfant-vetements", {}),
    "vetements-enfant-robes": ("enfant", "enfant-vetements", {}),
    "vetements-enfant-manteaux": ("enfant", "enfant-vetements", {}),
    "vetements-enfant-chaussures": ("enfant", "enfant-chaussures", {}),
    "vetements-enfant-deguisements": ("divers", "divers-fete-deguisements", {}),
    "vetements-enfant-lot": ("enfant", "enfant-vetements", {}),
    "jouets-eveil": ("enfant", "enfant-eveil", {}),
    "jouets-peluches-poupees": ("enfant", "enfant-peluches-poupees", {}),
    "jouets-construction": ("enfant", "enfant-construction", {}),
    "jouets-vehicules": ("enfant", "enfant-figurines-vehicules", {}),
    "jouets-imitation": ("enfant", "enfant-imitation", {}),
    "jouets-exterieur": ("enfant", "enfant-exterieur", {}),
    "jouets-puzzles": ("enfant", "enfant-educatifs", {}),
    "jouets-figurines": ("enfant", "enfant-figurines-vehicules", {}),
    "livres-albums": ("culture", "culture-jeunesse", {"type": "Livre"}),
    "livres-romans-jeunesse": ("culture", "culture-jeunesse", {"type": "Livre"}),
    "livres-bd-manga": ("culture", "culture-bd-mangas", {"type": "Livre"}),
    "livres-romans": ("culture", "culture-romans", {"type": "Livre"}),
    "livres-polars": ("culture", "culture-polars", {"type": "Livre"}),
    "livres-pratique": ("culture", "culture-pratiques", {"type": "Livre"}),
    "livres-scolaires": ("culture", "culture-scolaires", {"type": "Livre"}),
    "livres-documentaires": ("culture", "culture-pratiques", {"type": "Livre"}),
    "jeux-de-societe-famille": ("culture", "culture-jeux-famille", {"type": "Jeu"}),
    "jeux-de-societe-ambiance": ("culture", "culture-jeux-ambiance", {"type": "Jeu"}),
    "jeux-de-societe-strategie": ("culture", "culture-jeux-strategie", {"type": "Jeu"}),
    "jeux-de-societe-enfants": ("culture", "culture-jeux-famille", {"type": "Jeu"}),
    "jeux-de-societe-cooperatifs": ("culture", "culture-jeux-cooperatifs", {"type": "Jeu"}),
    "jeux-de-societe-cartes": ("culture", "culture-jeux-ambiance", {"type": "Jeu"}),
    "jeux-de-societe-puzzles": ("culture", "culture-puzzles", {"type": "Jeu"}),
    **{
        s: ("sport", "sport-velos", {"sport": "Vélo"})
        for s in (
            "velo-draisienne",
            "velo-enfant",
            "velo-ville",
            "velo-vtt",
            "velo-route",
            "velo-electrique",
            "velo-accessoires",
        )
    },  # fmt: skip
    "sport-fitness": ("sport", "sport-fitness", {}),
    "sport-randonnee": ("sport", "sport-randonnee", {}),
    "sport-raquettes": ("sport", "sport-raquettes", {}),
    "sport-eau": ("sport", "sport-nautique", {}),
    "sport-glisse": ("sport", "sport-glisse", {}),
    "sport-collectifs": ("sport", "sport-collectifs", {}),
    "sport-roulettes": ("sport", "sport-roulettes", {}),
    "sport-vetements": ("sport", "sport-vetements", {}),
    "outillage-electroportatif": ("bricolage", "bricolage-electroportatif", {}),
    "outillage-main": ("bricolage", "bricolage-outils-main", {}),
    "outillage-jardin": ("bricolage", "bricolage-jardinage", {}),
    "outillage-echelles": ("bricolage", "bricolage-echelles", {}),
    "outillage-mesure": ("bricolage", "bricolage-mesure", {}),
    "outillage-rangement": ("bricolage", "bricolage-etablis", {}),
    "electromenager-cuisine": ("electromenager", "electromenager-cuisine", {}),
    "electromenager-gros": ("electromenager", None, {}),
    "electromenager-entretien": ("electromenager", "electromenager-aspirateurs", {}),
    "electromenager-soin": ("electromenager", "electromenager-soin", {}),
    "electromenager-climat": ("electromenager", "electromenager-chauffage", {}),
    "meubles-assises": ("maison", None, {}),
    "meubles-tables": ("maison", "maison-tables-bureaux", {}),
    "meubles-rangements": ("maison", "maison-rangements", {}),
    "meubles-lits": ("maison", None, {}),
    "meubles-enfant": ("enfant", "enfant-lits-mobilier", {}),
    "meubles-exterieur": ("maison", "maison-exterieur", {}),
    "deco-luminaires": ("maison", "maison-luminaires", {}),
    "deco-miroirs-cadres": ("maison", "maison-miroirs-cadres", {}),
    "deco-textiles": ("maison", "maison-textiles", {}),
    "deco-vaisselle": ("maison", "maison-vaisselle", {}),
    "deco-plantes": ("maison", "maison-plantes", {}),
    "deco-objets": ("maison", "maison-objets-deco", {}),
    "multimedia-telephones": ("high-tech", "high-tech-smartphones", {}),
    "multimedia-ordinateurs": ("high-tech", None, {}),
    "multimedia-tv": ("high-tech", "high-tech-tv", {}),
    "multimedia-audio": ("high-tech", "high-tech-audio", {}),
    "multimedia-jeux-video": ("high-tech", None, {}),
    "multimedia-photo": ("high-tech", "high-tech-photo", {}),
    "multimedia-accessoires": ("high-tech", "high-tech-accessoires", {}),
}

# (ancienne catégorie, ancienne clé) -> (nouvelle clé, correspondance des valeurs ; None : valeurs gardées).
CARACTERISTIQUES = {
    ("poussette", "age"): ("age", {"Dès la naissance": "Naissance", "Dès 6 mois": "6–12 mois"}),
    ("siege-auto", "fixation"): ("fixation", None),
    ("vetements-enfant", "taille"): ("taille", None),
    ("vetements-enfant", "pointure"): ("pointure", None),
    ("jouets", "age"): (
        "age",
        {"3-5 ans": "3–5 ans", "6-8 ans": "6–8 ans", "9-12 ans": "9–12 ans", "12 ans et plus": "12–16 ans"},
    ),  # fmt: skip
    ("livres", "public"): ("public", {"Ados": "Adolescents"}),
    ("livres", "langue"): ("langue", {"Autre langue": "Autre"}),
    ("livres", "auteur"): ("auteur", None),
    ("jeux-de-societe", "joueurs"): (
        "joueurs",
        {"Seul": "1", "2 joueurs": "2", "2 à 4 joueurs": "2–4", "5 joueurs et plus": "5 et plus"},
    ),  # fmt: skip
    ("jeux-de-societe", "age"): (
        "age",
        {"Dès 3 ans": "3+", "Dès 6 ans": "6+", "Dès 8 ans": "8+", "Dès 12 ans": "12+", "Adultes": "18+"},
    ),  # fmt: skip
    ("jeux-de-societe", "complet"): ("contenu", {"Complet": "Complet", "Pièces manquantes": "Incomplet"}),
    ("sport", "taille"): ("taille", None),
    ("sport", "pointure"): ("pointure", None),
    ("outillage", "alimentation"): ("alimentation", {"Sans fil": "Batterie"}),
    ("meubles", "matiere"): ("matiere", None),
    ("meubles", "dimensions"): ("dimensions", None),
    ("deco", "couleur"): ("couleur", None),
    ("multimedia", "plateforme"): ("plateforme", None),
    **{
        (c, "marque"): ("marque", None)
        for c in (
            "poussette",
            "siege-auto",
            "lit-bebe",
            "vetements-enfant",
            "jouets",
            "velo",
            "sport",
            "outillage",
            "electromenager",
            "multimedia",
        )
    },  # fmt: skip
}


def _garder(categorie: str, sous_categorie: str | None, valeurs: dict[str, str], demande: bool) -> dict:
    """Les caractéristiques que la nouvelle nomenclature accepte, les autres retirées."""
    connues = {c.cle: c for c in nomenclature.caracteristiques(categorie)}
    gardees = {}
    for cle, valeur in valeurs.items():
        c = connues.get(cle)
        if c is None or (demande and c.options is None) or (c.pour is not None and sous_categorie not in c.pour):
            continue
        if (c.options is None and len(valeur) <= nomenclature.LONGUEUR_LIBRE) or (c.options and valeur in c.options):
            gardees[cle] = valeur
    return gardees


def convertir(categorie: str, sous_categorie: str | None, valeurs: dict[str, str], demande: bool):
    """Ancienne (catégorie, sous-catégorie, caractéristiques) -> nouvelle."""
    nouvelle, nouvelle_sous = PAR_DEFAUT[categorie]
    ajoutees: dict[str, str] = {}
    if sous_categorie in SOUS_CATEGORIES:
        nouvelle, nouvelle_sous, ajoutees = SOUS_CATEGORIES[sous_categorie]
    reprises = {}
    for cle, valeur in valeurs.items():
        if (categorie, cle) in CARACTERISTIQUES:
            nouvelle_cle, correspondance = CARACTERISTIQUES[(categorie, cle)]
            reprises[nouvelle_cle] = correspondance.get(valeur, valeur) if correspondance else valeur
    return nouvelle, nouvelle_sous, _garder(nouvelle, nouvelle_sous, {**reprises, **ajoutees}, demande)


def _tables():
    categories = sa.table("categories", sa.column("slug", sa.String), sa.column("libelle", sa.String))
    lignes = {
        nom: sa.table(
            nom,
            sa.column("id", sa.Integer),
            sa.column("categorie_slug", sa.String),
            sa.column("sous_categorie_slug", sa.String),
            sa.column("caracteristiques", postgresql.JSONB),
        )
        for nom in ("objets", "souhaits")
    }
    return categories, lignes


def upgrade() -> None:
    conn = op.get_bind()
    categories, lignes = _tables()
    existantes = set(conn.scalars(sa.select(categories.c.slug)))
    for slug, (libelle, _, _) in nomenclature.DETAIL.items():
        if slug in existantes:
            conn.execute(categories.update().where(categories.c.slug == slug).values(libelle=libelle))
        else:
            conn.execute(categories.insert().values(slug=slug, libelle=libelle))

    for nom, t in lignes.items():
        rangs = conn.execute(
            sa.select(t.c.id, t.c.categorie_slug, t.c.sous_categorie_slug, t.c.caracteristiques).where(
                t.c.categorie_slug.in_(list(ANCIENNES))
            )
        ).all()
        for id_, categorie, sous, valeurs in rangs:
            nouvelle, nouvelle_sous, nouvelles_valeurs = convertir(categorie, sous, valeurs or {}, nom == "souhaits")
            conn.execute(
                t.update()
                .where(t.c.id == id_)
                .values(categorie_slug=nouvelle, sous_categorie_slug=nouvelle_sous, caracteristiques=nouvelles_valeurs)
            )

    retirees = [s for s in ANCIENNES if s not in nomenclature.DETAIL]
    conn.execute(categories.delete().where(categories.c.slug.in_(retirees)))


# Retour en arrière : chaque nouvelle catégorie vers une ancienne, sans sous-catégorie ni caractéristique.
RETOUR = {
    "mode": "vetements-enfant",
    "high-tech": "multimedia",
    "enfant": "jouets",
    "maison": "meubles",
    "sport": "sport",
    "culture": "livres",
    "bricolage": "outillage",
    "electromenager": "electromenager",
    "auto-moto": "outillage",
    "divers": "deco",
}
RETOUR_SOUS = {
    "enfant-poussettes": "poussette",
    "enfant-sieges-auto": "siege-auto",
    "enfant-lits-mobilier": "lit-bebe",
    "enfant-vetements-bebe": "vetements-enfant",
    "enfant-vetements": "vetements-enfant",
    "enfant-chaussures": "vetements-enfant",
    "sport-velos": "velo",
    **{
        s: "jeux-de-societe"
        for s in (
            "culture-jeux-famille",
            "culture-jeux-strategie",
            "culture-jeux-ambiance",
            "culture-jeux-cooperatifs",
            "culture-puzzles",
        )
    },  # fmt: skip
    **{
        s: "deco"
        for s in (
            "maison-luminaires",
            "maison-miroirs-cadres",
            "maison-textiles",
            "maison-vaisselle",
            "maison-objets-deco",
            "maison-plantes",
        )
    },  # fmt: skip
}


def downgrade() -> None:
    conn = op.get_bind()
    categories, lignes = _tables()
    existantes = set(conn.scalars(sa.select(categories.c.slug)))
    for slug, libelle in ANCIENNES.items():
        if slug in existantes:
            conn.execute(categories.update().where(categories.c.slug == slug).values(libelle=libelle))
        else:
            conn.execute(categories.insert().values(slug=slug, libelle=libelle))
    for t in lignes.values():
        rangs = conn.execute(
            sa.select(t.c.id, t.c.categorie_slug, t.c.sous_categorie_slug).where(t.c.categorie_slug.in_(list(RETOUR)))
        ).all()
        for id_, categorie, sous in rangs:
            conn.execute(
                t.update()
                .where(t.c.id == id_)
                .values(
                    categorie_slug=RETOUR_SOUS.get(sous, RETOUR[categorie]),
                    sous_categorie_slug=None,
                    caracteristiques={},
                )
            )
    conn.execute(categories.delete().where(categories.c.slug.in_([s for s in RETOUR if s not in ANCIENNES])))
