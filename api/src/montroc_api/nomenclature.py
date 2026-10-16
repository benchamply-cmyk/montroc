"""Le détail des catégories : sous-catégories et caractéristiques (taille, âge, marque…).

Une seule source, ici : l'API la sert avec les catégories (GET /categories) et valide ce que chacun
enregistre. Les sous-catégories affinent les souhaits (« Je demande une poussette canne ») ; les
caractéristiques à choix fixes (taille, âge…) aussi : un objet qui précise une autre valeur n'est pas
proposé, un objet qui ne la précise pas l'est encore. Les caractéristiques libres (marque…) ne servent
qu'à décrire un objet.

Une catégorie créée par la modération et absente d'ici n'a ni sous-catégorie ni caractéristique.
Renommer un libellé est sans risque ; changer un slug ou une valeur laisse les anciens objets avec
l'ancienne valeur.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Caracteristique:
    cle: str
    libelle: str
    # Choix fixes (liste déroulante) ; None : texte libre, qui ne sert qu'à décrire un objet.
    options: tuple[str, ...] | None = None


LONGUEUR_LIBRE = 60
MARQUE = Caracteristique("marque", "Marque")
AGES_JOUETS = ("0-2 ans", "3-5 ans", "6-8 ans", "9-12 ans", "12 ans et plus")
TAILLES_ENFANT = (
    "Naissance", "1 mois", "3 mois", "6 mois", "9 mois", "12 mois", "18 mois", "2 ans", "3 ans", "4 ans",
    "5 ans", "6 ans", "8 ans", "10 ans", "12 ans", "14 ans", "16 ans",
)  # fmt: skip
POINTURES = tuple(str(p) for p in range(16, 47))
TAILLES_ADULTE = ("Enfant", "XS", "S", "M", "L", "XL", "XXL")

# slug de la catégorie -> (sous-catégories (slug, libellé), caractéristiques)
DETAIL: dict[str, tuple[tuple[tuple[str, str], ...], tuple[Caracteristique, ...]]] = {
    "poussette": (
        (
            ("poussette-canne", "Canne"),
            ("poussette-citadine", "Citadine compacte"),
            ("poussette-combinee", "Combinée 2 en 1 ou trio"),
            ("poussette-double", "Double"),
            ("poussette-tout-terrain", "Tout-terrain ou jogging"),
            ("poussette-nacelle", "Nacelle ou accessoire"),
        ),
        (Caracteristique("age", "Âge de l'enfant", ("Dès la naissance", "Dès 6 mois")), MARQUE),
    ),
    "siege-auto": (
        (
            ("siege-auto-coque", "Coque, 0 à 13 kg"),
            ("siege-auto-0-1", "Groupe 0+/1, 0 à 18 kg"),
            ("siege-auto-1", "Groupe 1, 9 à 18 kg"),
            ("siege-auto-2-3", "Groupe 2/3, réhausseur"),
            ("siege-auto-evolutif", "Évolutif, tous groupes"),
        ),
        (Caracteristique("fixation", "Fixation", ("Isofix", "Ceinture")), MARQUE),
    ),
    "lit-bebe": (
        (
            ("lit-bebe-barreaux", "Lit à barreaux"),
            ("lit-bebe-parapluie", "Lit parapluie"),
            ("lit-bebe-berceau", "Berceau ou couffin"),
            ("lit-bebe-cododo", "Cododo"),
            ("lit-bebe-evolutif", "Lit évolutif"),
            ("lit-bebe-literie", "Matelas, linge, gigoteuse"),
        ),
        (Caracteristique("dimensions", "Dimensions", ("60 × 120 cm", "70 × 140 cm", "Autre")), MARQUE),
    ),
    "vetements-enfant": (
        (
            ("vetements-enfant-bodies", "Bodies et pyjamas"),
            ("vetements-enfant-hauts", "Hauts, pulls, t-shirts"),
            ("vetements-enfant-bas", "Pantalons, jupes, shorts"),
            ("vetements-enfant-robes", "Robes et ensembles"),
            ("vetements-enfant-manteaux", "Manteaux et blousons"),
            ("vetements-enfant-chaussures", "Chaussures"),
            ("vetements-enfant-deguisements", "Déguisements"),
            ("vetements-enfant-lot", "Lot de vêtements"),
        ),
        (
            Caracteristique("taille", "Taille", TAILLES_ENFANT),
            Caracteristique("pointure", "Pointure (chaussures)", POINTURES),
            Caracteristique("saison", "Saison", ("Été", "Hiver", "Mi-saison", "Toutes saisons")),
            MARQUE,
        ),
    ),
    "jouets": (
        (
            ("jouets-eveil", "Éveil et premier âge"),
            ("jouets-peluches-poupees", "Peluches et poupées"),
            ("jouets-construction", "Construction (briques, circuits…)"),
            ("jouets-vehicules", "Voitures, trains, véhicules"),
            ("jouets-imitation", "Jeux d'imitation (cuisine, bricolage…)"),
            ("jouets-exterieur", "Jeux d'extérieur et porteurs"),
            ("jouets-puzzles", "Puzzles et jeux éducatifs"),
            ("jouets-figurines", "Figurines et univers"),
        ),
        (Caracteristique("age", "Âge", AGES_JOUETS), MARQUE),
    ),
    "livres": (
        (
            ("livres-albums", "Albums jeunesse"),
            ("livres-romans-jeunesse", "Romans jeunesse"),
            ("livres-bd-manga", "BD et mangas"),
            ("livres-romans", "Romans"),
            ("livres-polars", "Polars et thrillers"),
            ("livres-pratique", "Cuisine, maison, pratique"),
            ("livres-scolaires", "Scolaires et parascolaires"),
            ("livres-documentaires", "Documentaires et beaux livres"),
        ),
        (
            Caracteristique("public", "Public", ("Tout-petits", "Enfants", "Ados", "Adultes")),
            Caracteristique("langue", "Langue", ("Français", "Anglais", "Autre langue")),
            Caracteristique("auteur", "Auteur ou série"),
        ),
    ),
    "jeux-de-societe": (
        (
            ("jeux-de-societe-famille", "Jeux en famille"),
            ("jeux-de-societe-ambiance", "Jeux d'ambiance"),
            ("jeux-de-societe-strategie", "Stratégie et experts"),
            ("jeux-de-societe-enfants", "Jeux pour enfants"),
            ("jeux-de-societe-cooperatifs", "Jeux coopératifs"),
            ("jeux-de-societe-cartes", "Jeux de cartes"),
            ("jeux-de-societe-puzzles", "Puzzles"),
        ),
        (
            Caracteristique("joueurs", "Joueurs", ("Seul", "2 joueurs", "2 à 4 joueurs", "5 joueurs et plus")),
            Caracteristique("age", "Âge", ("Dès 3 ans", "Dès 6 ans", "Dès 8 ans", "Dès 12 ans", "Adultes")),
            Caracteristique("complet", "Contenu", ("Complet", "Pièces manquantes")),
        ),
    ),
    "velo": (
        (
            ("velo-draisienne", "Draisienne"),
            ("velo-enfant", "Vélo enfant"),
            ("velo-ville", "Vélo de ville"),
            ("velo-vtt", "VTT"),
            ("velo-route", "Vélo de route"),
            ("velo-electrique", "Vélo électrique"),
            ("velo-accessoires", "Casque, siège, antivol, accessoires"),
        ),
        (
            Caracteristique(
                "roues", "Taille des roues", ('12"', '14"', '16"', '20"', '24"', '26"', '27,5"', '28" ou 700', '29"')
            ),
            Caracteristique("cadre", "Taille du cadre", ("Enfant", "XS", "S", "M", "L", "XL")),
            MARQUE,
        ),
    ),
    "sport": (
        (
            ("sport-fitness", "Fitness et musculation"),
            ("sport-randonnee", "Randonnée et camping"),
            ("sport-raquettes", "Sports de raquette"),
            ("sport-eau", "Sports d'eau et plage"),
            ("sport-glisse", "Ski et glisse"),
            ("sport-collectifs", "Sports collectifs"),
            ("sport-roulettes", "Trottinettes, rollers, skates"),
            ("sport-vetements", "Vêtements et chaussures de sport"),
        ),
        (
            Caracteristique("taille", "Taille", TAILLES_ADULTE),
            Caracteristique("pointure", "Pointure (chaussures)", POINTURES),
            MARQUE,
        ),
    ),
    "outillage": (
        (
            ("outillage-electroportatif", "Électroportatif (perceuse, scie…)"),
            ("outillage-main", "Outils à main"),
            ("outillage-jardin", "Jardin"),
            ("outillage-echelles", "Échelles et escabeaux"),
            ("outillage-mesure", "Mesure et traçage"),
            ("outillage-rangement", "Rangement et établis"),
        ),
        (Caracteristique("alimentation", "Alimentation", ("Sans fil", "Secteur", "Thermique", "Manuel")), MARQUE),
    ),
    "electromenager": (
        (
            ("electromenager-cuisine", "Petit électroménager de cuisine"),
            ("electromenager-gros", "Gros électroménager"),
            ("electromenager-entretien", "Aspirateur, fer, entretien"),
            ("electromenager-soin", "Soin et beauté"),
            ("electromenager-climat", "Chauffage et ventilation"),
        ),
        (MARQUE,),
    ),
    "meubles": (
        (
            ("meubles-assises", "Chaises, tabourets, fauteuils"),
            ("meubles-tables", "Tables et bureaux"),
            ("meubles-rangements", "Rangements et étagères"),
            ("meubles-lits", "Lits et canapés"),
            ("meubles-enfant", "Meubles enfant"),
            ("meubles-exterieur", "Mobilier d'extérieur"),
        ),
        (
            Caracteristique("matiere", "Matière", ("Bois", "Métal", "Plastique", "Tissu", "Verre", "Mixte")),
            Caracteristique("dimensions", "Dimensions"),
        ),
    ),
    "deco": (
        (
            ("deco-luminaires", "Luminaires"),
            ("deco-miroirs-cadres", "Miroirs et cadres"),
            ("deco-textiles", "Tapis, rideaux, coussins"),
            ("deco-vaisselle", "Vaisselle et arts de la table"),
            ("deco-plantes", "Pots et plantes"),
            ("deco-objets", "Objets déco"),
        ),
        (
            Caracteristique(
                "couleur", "Couleur", ("Blanc", "Noir", "Gris", "Beige", "Bois", "Couleurs vives", "Multicolore")
            ),
        ),
    ),
    "multimedia": (
        (
            ("multimedia-telephones", "Téléphones"),
            ("multimedia-ordinateurs", "Ordinateurs et tablettes"),
            ("multimedia-tv", "TV et vidéo"),
            ("multimedia-audio", "Audio et casques"),
            ("multimedia-jeux-video", "Consoles et jeux vidéo"),
            ("multimedia-photo", "Photo"),
            ("multimedia-accessoires", "Câbles, chargeurs, accessoires"),
        ),
        (
            Caracteristique("plateforme", "Plateforme", ("PlayStation", "Xbox", "Nintendo", "PC", "Apple", "Android")),
            MARQUE,
        ),
    ),
}


def sous_categories(categorie: str) -> tuple[tuple[str, str], ...]:
    return DETAIL.get(categorie, ((), ()))[0]


def caracteristiques(categorie: str) -> tuple[Caracteristique, ...]:
    return DETAIL.get(categorie, ((), ()))[1]


def verifier(categorie: str | None, sous_categorie: str | None, valeurs: dict[str, str], demande: bool) -> dict:
    """Vérifie une sous-catégorie et des caractéristiques ; renvoie les valeurs nettoyées (vides retirées).

    ``demande`` : pour un souhait, seules les caractéristiques à choix fixes comptent (elles filtrent).
    Lève ``ValueError`` avec un message pour la personne.
    """
    if categorie is None:
        if sous_categorie or any(v.strip() for v in valeurs.values()):
            raise ValueError("Un objet précis se demande sans sous-catégorie ni caractéristique.")
        return {}
    if sous_categorie is not None and sous_categorie not in dict(sous_categories(categorie)):
        raise ValueError("Cette sous-catégorie n'existe pas dans cette catégorie.")
    connues = {c.cle: c for c in caracteristiques(categorie)}
    propres = {}
    for cle, valeur in valeurs.items():
        valeur = valeur.strip()
        if not valeur:
            continue
        c = connues.get(cle)
        if c is None or (demande and c.options is None):
            raise ValueError(f"Caractéristique inconnue pour cette catégorie : {cle}.")
        if c.options is None and len(valeur) > LONGUEUR_LIBRE:
            raise ValueError(f"« {c.libelle} » : {LONGUEUR_LIBRE} caractères au plus.")
        if c.options is not None and valeur not in c.options:
            raise ValueError(f"Valeur inconnue pour « {c.libelle} » : {valeur}.")
        propres[cle] = valeur
    return propres
