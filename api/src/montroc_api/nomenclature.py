"""Le détail des catégories : sous-catégories et caractéristiques (taille, âge, marque…).

Une seule source, ici : l'API la sert avec les catégories (GET /categories) et valide ce que chacun
enregistre. Les sous-catégories affinent les souhaits (« Je demande une poussette ») ; les
caractéristiques à choix fixes (taille, âge…) aussi : un objet qui précise une autre valeur n'est pas
proposé, un objet qui ne la précise pas l'est encore. Les caractéristiques libres (marque…) ne servent
qu'à décrire un objet. Une caractéristique peut ne valoir que pour certaines sous-catégories (la
pointure pour les chaussures) : elle n'est alors demandée qu'une fois l'une d'elles choisie.

Les catégories elles-mêmes sont en base (table ``categories``) : les 10 d'ici y sont créées par la
migration 0012, dans l'ordre de ``DETAIL``, qui est aussi celui du site. Une catégorie créée par la
modération et absente d'ici n'a ni sous-catégorie ni caractéristique.
Renommer un libellé est sans risque ; changer un slug ou une valeur laisse les anciens objets avec
l'ancienne valeur (il faut alors une migration, comme 0012).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Caracteristique:
    cle: str
    libelle: str
    # Choix fixes (liste déroulante) ; None : texte libre, qui ne sert qu'à décrire un objet.
    options: tuple[str, ...] | None = None
    # Sous-catégories (slugs) où elle a un sens ; None : toute la catégorie.
    pour: tuple[str, ...] | None = None


LONGUEUR_LIBRE = 60
OUI_NON = ("Oui", "Non")
MARQUE = Caracteristique("marque", "Marque")
MODELE = Caracteristique("modele", "Modèle")
DIMENSIONS = Caracteristique("dimensions", "Dimensions (L × H × P, en cm)")
COULEUR = Caracteristique(
    "couleur",
    "Couleur",
    (
        "Blanc", "Noir", "Gris", "Beige", "Marron", "Bois", "Bleu", "Vert", "Rouge", "Rose", "Jaune", "Orange",
        "Violet", "Doré", "Argenté", "Multicolore",
    ),
)  # fmt: skip
FONCTIONNEMENT = Caracteristique(
    "fonctionnement", "État de fonctionnement", ("Fonctionnel", "Fonctionnel avec défauts", "Hors service")
)
ACCESSOIRES_INCLUS = Caracteristique("accessoires_inclus", "Accessoires inclus", OUI_NON)
CONTENU = ("Complet", "Incomplet")
TAILLES_ENFANT = (
    "Naissance", "1 mois", "3 mois", "6 mois", "9 mois", "12 mois", "18 mois", "2 ans", "3 ans", "4 ans",
    "5 ans", "6 ans", "8 ans", "10 ans", "12 ans", "14 ans", "16 ans",
)  # fmt: skip


def pointures(de: int, a: int) -> tuple[str, ...]:
    return tuple(str(p) for p in range(de, a + 1))


def _sous(prefixe: str, *libelles: tuple[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple((f"{prefixe}-{fin}", libelle) for fin, libelle in libelles)


# slug de la catégorie -> (libellé, sous-catégories (slug, libellé), caractéristiques), dans l'ordre du site.
DETAIL: dict[str, tuple[str, tuple[tuple[str, str], ...], tuple[Caracteristique, ...]]] = {
    "mode": (
        "Mode & Accessoires",
        _sous(
            "mode",
            ("vetements-femme", "Vêtements femme"),
            ("vetements-homme", "Vêtements homme"),
            ("chaussures-femme", "Chaussures femme"),
            ("chaussures-homme", "Chaussures homme"),
            ("sacs", "Sacs et maroquinerie"),
            ("bijoux-montres", "Bijoux et montres"),
            ("accessoires", "Accessoires de mode"),
            ("sport", "Vêtements et accessoires de sport"),
        ),
        (
            Caracteristique(
                "taille",
                "Taille",
                ("XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL"),
                ("mode-vetements-femme", "mode-vetements-homme", "mode-sport"),
            ),
            Caracteristique(
                "taille_numerique",
                "Taille numérique",
                tuple(str(t) for t in range(32, 58, 2)),
                ("mode-vetements-femme", "mode-vetements-homme", "mode-sport"),
            ),
            Caracteristique(
                "pointure",
                "Pointure",
                pointures(35, 48),
                ("mode-chaussures-femme", "mode-chaussures-homme", "mode-sport"),
            ),
            Caracteristique("genre", "Genre", ("Femme", "Homme", "Unisexe")),
            Caracteristique("saison", "Saison", ("Été", "Hiver", "Mi-saison", "Toutes saisons")),
            COULEUR,
            MARQUE,
        ),
    ),
    "high-tech": (
        "High-tech & Multimédia",
        _sous(
            "high-tech",
            ("smartphones", "Smartphones et téléphones"),
            ("ordinateurs", "Ordinateurs"),
            ("tablettes", "Tablettes et liseuses"),
            ("tv", "Télévisions et vidéoprojecteurs"),
            ("consoles", "Consoles de jeux"),
            ("jeux-video", "Jeux vidéo"),
            ("audio", "Audio, enceintes et casques"),
            ("photo", "Appareils photo et vidéo"),
            ("montres", "Montres connectées"),
            ("accessoires", "Accessoires informatiques et électroniques"),
        ),
        (
            MARQUE,
            MODELE,
            Caracteristique("plateforme", "Plateforme", ("PlayStation", "Xbox", "Nintendo", "PC", "Apple", "Android")),
            Caracteristique(
                "stockage",
                "Capacité de stockage",
                ("32 Go", "64 Go", "128 Go", "256 Go", "512 Go", "1 To et plus"),
                (
                    "high-tech-smartphones",
                    "high-tech-ordinateurs",
                    "high-tech-tablettes",
                    "high-tech-consoles",
                    "high-tech-photo",
                    "high-tech-montres",
                ),
            ),  # fmt: skip
            FONCTIONNEMENT,
            ACCESSOIRES_INCLUS,
            COULEUR,
        ),
    ),
    "enfant": (
        "Bébé, Enfant & Jouets",
        _sous(
            "enfant",
            ("vetements-bebe", "Vêtements bébé (0–3 ans)"),
            ("vetements", "Vêtements enfant (3–16 ans)"),
            ("chaussures", "Chaussures enfant"),
            ("poussettes", "Poussettes et accessoires"),
            ("sieges-auto", "Sièges auto et rehausseurs"),
            ("lits-mobilier", "Lits bébé et mobilier enfant"),
            ("puericulture", "Équipements de puériculture"),
            ("eveil", "Jeux d'éveil et premier âge"),
            ("peluches-poupees", "Peluches et poupées"),
            ("construction", "Jeux de construction"),
            ("figurines-vehicules", "Figurines et véhicules miniatures"),
            ("educatifs", "Jeux éducatifs"),
            ("imitation", "Jeux d'imitation"),
            ("exterieur", "Jeux d'extérieur et porteurs"),
        ),
        (
            Caracteristique(
                "age",
                "Âge",
                ("Naissance", "0–6 mois", "6–12 mois", "1–2 ans", "3–5 ans", "6–8 ans", "9–12 ans", "12–16 ans"),
            ),
            Caracteristique("taille", "Taille", TAILLES_ENFANT, ("enfant-vetements-bebe", "enfant-vetements")),
            Caracteristique("pointure", "Pointure", pointures(16, 38), ("enfant-chaussures",)),
            Caracteristique(
                "type_poussette",
                "Type de poussette",
                ("Canne", "Citadine", "Combinée", "Double", "Tout-terrain"),
                ("enfant-poussettes",),
            ),
            Caracteristique("fixation", "Fixation", ("Isofix", "Ceinture"), ("enfant-sieges-auto",)),
            Caracteristique("norme", "Norme", ("R44/04", "R129 (i-Size)"), ("enfant-sieges-auto",)),
            Caracteristique(
                "contenu",
                "Contenu",
                CONTENU,
                (
                    "enfant-eveil",
                    "enfant-peluches-poupees",
                    "enfant-construction",
                    "enfant-figurines-vehicules",
                    "enfant-educatifs",
                    "enfant-imitation",
                    "enfant-exterieur",
                ),
            ),  # fmt: skip
            MARQUE,
        ),
    ),
    "maison": (
        "Maison & Décoration",
        _sous(
            "maison",
            ("canapes-fauteuils", "Canapés et fauteuils"),
            ("tables-bureaux", "Tables et bureaux"),
            ("chaises", "Chaises et tabourets"),
            ("lits-matelas", "Lits et matelas"),
            ("rangements", "Armoires, commodes et rangements"),
            ("etageres", "Étagères et bibliothèques"),
            ("exterieur", "Mobilier d'extérieur"),
            ("luminaires", "Luminaires"),
            ("miroirs-cadres", "Miroirs et cadres"),
            ("textiles", "Tapis, rideaux et coussins"),
            ("vaisselle", "Vaisselle et arts de la table"),
            ("objets-deco", "Objets décoratifs"),
            ("plantes", "Plantes et pots"),
        ),
        (
            Caracteristique("matiere", "Matière", ("Bois", "Métal", "Plastique", "Tissu", "Verre", "Mixte")),
            COULEUR,
            DIMENSIONS,
            Caracteristique("style", "Style", ("Moderne", "Vintage", "Industriel", "Scandinave", "Classique", "Autre")),
            MARQUE,
        ),
    ),
    "sport": (
        "Sport & Loisirs",
        _sous(
            "sport",
            ("velos", "Vélos et accessoires"),
            ("fitness", "Fitness et musculation"),
            ("randonnee", "Randonnée et camping"),
            ("raquettes", "Sports de raquette"),
            ("nautique", "Sports nautiques et plage"),
            ("glisse", "Ski et sports de glisse"),
            ("collectifs", "Sports collectifs"),
            ("roulettes", "Trottinettes, rollers et skateboards"),
            ("loisirs-exterieur", "Équipements de loisirs extérieurs"),
            ("vetements", "Vêtements et chaussures de sport"),
        ),
        (
            Caracteristique(
                "sport", "Sport", ("Vélo", "Fitness", "Randonnée", "Tennis", "Natation", "Ski", "Football", "Autre")
            ),
            Caracteristique("taille", "Taille", ("Enfant", "XS", "S", "M", "L", "XL", "XXL")),
            Caracteristique(
                "pointure", "Pointure", pointures(16, 48), ("sport-vetements", "sport-glisse", "sport-roulettes")
            ),
            Caracteristique("dimensions", "Dimensions"),
            MARQUE,
            Caracteristique("niveau", "Niveau", ("Débutant", "Intermédiaire", "Confirmé")),
        ),
    ),
    "culture": (
        "Livres, Jeux & Culture",
        _sous(
            "culture",
            ("romans", "Romans et littérature"),
            ("polars", "Polars et thrillers"),
            ("bd-mangas", "BD et mangas"),
            ("jeunesse", "Livres jeunesse"),
            ("scolaires", "Livres scolaires et éducatifs"),
            ("pratiques", "Livres pratiques et documentaires"),
            ("beaux-livres", "Beaux livres et art"),
            ("jeux-famille", "Jeux de société familiaux"),
            ("jeux-strategie", "Jeux de stratégie"),
            ("jeux-ambiance", "Jeux d'ambiance et de cartes"),
            ("jeux-cooperatifs", "Jeux coopératifs"),
            ("puzzles", "Puzzles"),
            ("musique", "Musique, CD et vinyles"),
            ("films", "Films, DVD et Blu-ray"),
        ),
        (
            Caracteristique("type", "Type", ("Livre", "Jeu", "Musique", "Film")),
            Caracteristique("public", "Public", ("Tout-petits", "Enfants", "Adolescents", "Adultes")),
            Caracteristique("langue", "Langue", ("Français", "Anglais", "Espagnol", "Autre")),
            Caracteristique("auteur", "Auteur / Artiste"),
            Caracteristique("titre", "Titre / Série"),
            Caracteristique(
                "isbn",
                "ISBN",
                pour=(
                    "culture-romans",
                    "culture-polars",
                    "culture-bd-mangas",
                    "culture-jeunesse",
                    "culture-scolaires",
                    "culture-pratiques",
                    "culture-beaux-livres",
                ),
            ),  # fmt: skip
            Caracteristique(
                "joueurs",
                "Nombre de joueurs",
                ("1", "2", "2–4", "5 et plus"),
                ("culture-jeux-famille", "culture-jeux-strategie", "culture-jeux-ambiance", "culture-jeux-cooperatifs"),
            ),
            Caracteristique(
                "age",
                "Âge recommandé",
                ("3+", "6+", "8+", "12+", "16+", "18+"),
                (
                    "culture-jeux-famille",
                    "culture-jeux-strategie",
                    "culture-jeux-ambiance",
                    "culture-jeux-cooperatifs",
                    "culture-puzzles",
                ),
            ),  # fmt: skip
            Caracteristique(
                "contenu",
                "Contenu",
                CONTENU,
                (
                    "culture-jeux-famille",
                    "culture-jeux-strategie",
                    "culture-jeux-ambiance",
                    "culture-jeux-cooperatifs",
                    "culture-puzzles",
                ),
            ),  # fmt: skip
        ),
    ),
    "bricolage": (
        "Bricolage & Jardin",
        _sous(
            "bricolage",
            ("electroportatif", "Outils électroportatifs"),
            ("outils-main", "Outils à main"),
            ("jardinage", "Matériel de jardinage"),
            ("machines-jardin", "Machines et équipements de jardin"),
            ("echelles", "Échelles et escabeaux"),
            ("mesure", "Mesure et traçage"),
            ("etablis", "Établis et rangements"),
            ("materiaux", "Matériaux et fournitures"),
            ("protection", "Équipements de protection"),
        ),
        (
            Caracteristique("alimentation", "Alimentation", ("Batterie", "Secteur", "Thermique", "Manuel")),
            MARQUE,
            MODELE,
            Caracteristique("puissance", "Puissance (W)"),
            Caracteristique(
                "batterie_incluse",
                "Batterie incluse",
                ("Oui", "Non", "Non applicable"),
                ("bricolage-electroportatif", "bricolage-machines-jardin"),
            ),
            ACCESSOIRES_INCLUS,
        ),
    ),
    "electromenager": (
        "Électroménager",
        _sous(
            "electromenager",
            ("cuisine", "Petit électroménager de cuisine"),
            ("froid", "Réfrigérateurs et congélateurs"),
            ("lavage", "Lave-linge et sèche-linge"),
            ("lave-vaisselle", "Lave-vaisselle"),
            ("cuisson", "Fours, plaques et micro-ondes"),
            ("aspirateurs", "Aspirateurs et nettoyage"),
            ("repassage", "Repassage et entretien du linge"),
            ("soin", "Soin et beauté"),
            ("chauffage", "Chauffage et ventilation"),
            ("autres", "Autres appareils électroménagers"),
        ),
        (
            MARQUE,
            MODELE,
            DIMENSIONS,
            Caracteristique("capacite", "Capacité"),
            Caracteristique(
                "classe_energie",
                "Classe énergétique",
                ("A", "B", "C", "D", "E", "F", "G", "Non applicable"),
                (
                    "electromenager-froid",
                    "electromenager-lavage",
                    "electromenager-lave-vaisselle",
                    "electromenager-cuisson",
                ),
            ),  # fmt: skip
            FONCTIONNEMENT,
            ACCESSOIRES_INCLUS,
        ),
    ),
    "auto-moto": (
        "Auto, Moto & Mobilité",
        _sous(
            "auto-moto",
            ("accessoires-auto", "Accessoires automobiles"),
            ("pieces-auto", "Pièces détachées automobiles"),
            ("interieur", "Équipements intérieurs"),
            ("exterieur", "Équipements extérieurs"),
            ("pneus-jantes", "Pneus et jantes"),
            ("moto-scooter", "Accessoires moto et scooter"),
            ("casques-protection", "Casques et équipements de protection"),
            ("entretien", "Entretien automobile"),
            ("mobilite-electrique", "Accessoires de mobilité électrique"),
        ),
        (
            Caracteristique("vehicule", "Type de véhicule", ("Voiture", "Moto", "Scooter", "Autre")),
            MARQUE,
            Caracteristique("modele", "Modèle compatible"),
            Caracteristique("annee", "Année de compatibilité"),
            Caracteristique("dimensions", "Dimensions"),
            Caracteristique("reference", "Référence constructeur"),
            Caracteristique("universel", "Compatibilité universelle", OUI_NON),
        ),
    ),
    "divers": (
        "Divers & Collections",
        _sous(
            "divers",
            ("collection", "Objets de collection"),
            ("antiquites", "Antiquités et objets anciens"),
            ("timbres-monnaies", "Timbres et monnaies"),
            ("figurines", "Figurines de collection"),
            ("instruments", "Instruments de musique"),
            ("fete-deguisements", "Articles de fête et déguisements"),
            ("loisirs-creatifs", "Loisirs créatifs"),
            ("bureau", "Fournitures de bureau"),
            ("insolites", "Objets insolites"),
            ("autres", "Autres objets"),
        ),
        (
            Caracteristique("type_objet", "Type d'objet"),
            Caracteristique("marque", "Marque / Fabricant"),
            Caracteristique("epoque", "Époque", ("Ancien", "Vintage", "Contemporain")),
            Caracteristique("matiere", "Matière", ("Bois", "Métal", "Plastique", "Verre", "Tissu", "Autre")),
            Caracteristique("dimensions", "Dimensions"),
            Caracteristique("authenticite", "Authenticité", ("Certifiée", "Non certifiée", "Non applicable")),
        ),
    ),
}

ORDRE = {slug: i for i, slug in enumerate(DETAIL)}


def sous_categories(categorie: str) -> tuple[tuple[str, str], ...]:
    return DETAIL[categorie][1] if categorie in DETAIL else ()


def caracteristiques(categorie: str) -> tuple[Caracteristique, ...]:
    return DETAIL[categorie][2] if categorie in DETAIL else ()


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
        if c.pour is not None and sous_categorie not in c.pour:
            raise ValueError(f"« {c.libelle} » ne se précise pas pour cette sous-catégorie.")
        if c.options is None and len(valeur) > LONGUEUR_LIBRE:
            raise ValueError(f"« {c.libelle} » : {LONGUEUR_LIBRE} caractères au plus.")
        if c.options is not None and valeur not in c.options:
            raise ValueError(f"Valeur inconnue pour « {c.libelle} » : {valeur}.")
        propres[cle] = valeur
    return propres
