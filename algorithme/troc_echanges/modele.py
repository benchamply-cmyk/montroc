"""Modèle de données du troc : utilisateurs, objets, souhaits, transferts, boucles.

Aucune notion de prix ni de monnaie : un utilisateur publie des objets
disponibles et liste des souhaits (une catégorie, ou un objet précis).
Un échange est une boucle de transferts où chacun donne un objet et en reçoit un.

Les catégories rangent les objets ; un échange peut toujours mêler des
catégories différentes (une poussette contre une perceuse) : seul compte ce
que chacun demande.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import asin, cos, prod, radians, sin, sqrt

# États d'un objet, du moins bon au meilleur : un souhait peut exiger un état minimum.
ETATS = ("correct", "bon", "tres_bon", "comme_neuf", "neuf")
# Recherche précise : l'objet demandé seulement ; flexible : aussi les alternatives acceptées ;
# ouverte : tout objet des catégories d'intérêt (celle du souhait et celles des alternatives).
MODES_RECHERCHE = ("precise", "flexible", "ouverte")
# Qualité d'un transfert (départage, après le nombre d'objets et l'équité) : l'objet visé en premier
# plutôt qu'une alternative, puis chaque critère préférentiel respecté, puis chaque préférence « contre ».
QUALITE_CIBLE = 2
QUALITE_PREFERENCE = 1
QUALITE_CONTRE = 2
# Mode d'échange qui permet de troquer loin de chez soi : un objet hors des zones d'intérêt du receveur ne lui
# parvient que par colis, si l'objet et le souhait l'acceptent tous les deux (``Utilisateur.acces``).
MODE_COLIS = "colis"
RAYON_TERRE_KM = 6371.0


def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distance à vol d'oiseau entre deux points (latitude, longitude), en kilomètres (formule de haversine)."""
    (la1, lo1), (la2, lo2) = ((radians(x), radians(y)) for x, y in (a, b))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 2 * RAYON_TERRE_KM * asin(min(1.0, sqrt(h)))


@dataclass(frozen=True)
class ZoneInteret:
    """Une zone où l'on veut troquer, choisie par chacun (« autour de moi », une ville…) : un centre et un rayon."""
    latitude: float
    longitude: float
    rayon_km: float

    def contient(self, position: tuple[float, float]) -> bool:
        return distance_km((self.latitude, self.longitude), position) <= self.rayon_km


def _norme(valeur: str) -> str:
    """Comparaison des valeurs sans tenir compte de la casse ni des espaces (marques en saisie libre)."""
    return " ".join(str(valeur).split()).casefold()


@dataclass(frozen=True)
class Objet:
    """Un objet disponible à l'échange.

    ``contre`` : les souhaits de son propriétaire (indices dans sa liste) contre
    lesquels il le donne, comme les listes par objet de BoardGameGeek
    (« je donne ce jeu contre A ou B »). Vide : contre n'importe lequel de ses
    souhaits. ``contre_strict`` : seulement contre ceux-là ; sinon ce n'est
    qu'une préférence, et l'objet peut partir contre un autre de ses souhaits.
    """
    id: str
    proprietaire: str
    categorie: str
    titre: str = ""
    contre: frozenset[int] = frozenset()
    contre_strict: bool = False
    # Sous-catégorie (« poussette canne » dans « poussette ») et caractéristiques (taille, âge…),
    # en paires (clé, valeur) : facultatives, elles affinent les souhaits qui les précisent.
    sous_categorie: str | None = None
    caracteristiques: tuple[tuple[str, str], ...] = ()
    # État (une valeur de ``ETATS``), modes d'échange possibles (vide : tous), lieu (vide : la zone
    # de son propriétaire) ; un objet réservé ou échangé n'est pas ``disponible``.
    etat: str | None = None
    modes: frozenset[str] = frozenset()
    zone: str | None = None
    disponible: bool = True
    # Où se trouve l'objet (latitude, longitude), indiqué à la publication ; None : inconnu.
    position: tuple[float, float] | None = None

    def accepte_le_colis(self) -> bool:
        return not self.modes or MODE_COLIS in self.modes

    def accepte(self, recu: Transfert) -> bool:
        """Peut-on donner cet objet en recevant ``recu`` dans la même boucle ?"""
        return not (self.contre and self.contre_strict) or recu.souhait_idx in self.contre

    def prefere(self, recu: Transfert) -> bool:
        """``recu`` fait-il partie des souhaits indiqués pour cet objet ?"""
        return bool(self.contre) and recu.souhait_idx in self.contre


@dataclass(frozen=True)
class Souhait:
    """Ce qui serait utile à l'utilisateur.

    - ``categorie`` : n'importe quel objet de cette catégorie convient
      (souhait « large », recommandé par l'étude) ;
    - ``objet_id`` : un objet précis ;
    - ``rang`` : 1 = souhait préféré (niveau de priorité, sert à départager,
      comme les listes ordonnées de TradeMaximizer) ;
    - ``quantite`` : nombre d'objets que l'utilisateur veut recevoir pour ce
      souhait (évite de recevoir trois poussettes) ;
    - ``acceptation_auto`` : case « j'accepte automatiquement un échange
      contre cet objet » (engagement préalable, section 2 de l'étude) ;
    - ``sous_categorie`` : seulement les objets de cette sous-catégorie ;
    - ``criteres`` : critères obligatoires, paires (clé, valeur), par exemple
      (« taille », « 4 ans ») ou (« marque », « Bosch ») : un objet de la
      catégorie du souhait doit indiquer cette valeur ;
    - ``preferences`` : critères préférentiels, mêmes paires : ils n'écartent
      aucun objet, ils améliorent la qualité de l'échange ;
    - ``etat_min`` : état minimum accepté (une valeur de ``ETATS``) ;
    - ``alternatives`` : autres (catégorie, sous-catégorie ou None) acceptées ;
    - ``mode`` : ``"precise"``, ``"flexible"`` ou ``"ouverte"`` (``MODES_RECHERCHE``) ;
    - ``modes`` : modes d'échange acceptés (main propre, point relais…), vide : tous ;
    - ``zones`` : zones géographiques acceptées ; vide : la règle du marché
      (même zone que soi si ``Marche.meme_zone``) ;
    - ``objets`` : plusieurs objets précis, n'importe lequel convient (les
      « J'aime » du Match regroupés en un seul souhait : avec ``quantite`` 1,
      dix coups de cœur ne font pas recevoir dix objets) ;
    - ``ref`` : identifiant libre de l'application (son numéro en base), repris
      par chaque transfert qui sert ce souhait (``Transfert.souhait_ref``).

    Les critères (obligatoires et préférentiels) portent sur la catégorie du
    souhait ; une alternative d'une autre catégorie n'est jugée que sur sa
    catégorie, sa sous-catégorie, l'état minimum et la logistique.
    """
    categorie: str | None = None
    objet_id: str | None = None
    rang: int = 1
    quantite: int = 1
    acceptation_auto: bool = False
    sous_categorie: str | None = None
    criteres: tuple[tuple[str, str], ...] = ()
    preferences: tuple[tuple[str, str], ...] = ()
    etat_min: str | None = None
    alternatives: tuple[tuple[str, str | None], ...] = ()
    mode: str = "flexible"
    modes: frozenset[str] = frozenset()
    zones: frozenset[str] = frozenset()
    ref: str | None = None
    objets: frozenset[str] = frozenset()

    def __post_init__(self):
        object.__setattr__(self, "objets", frozenset(self.objets))
        if [self.categorie is not None, self.objet_id is not None, bool(self.objets)].count(True) != 1:
            raise ValueError("Un souhait porte soit sur une catégorie, soit sur un objet précis, soit sur des objets précis.")
        if self.rang < 1 or self.quantite < 1:
            raise ValueError("rang et quantite doivent être >= 1.")
        if self.categorie is None and (self.sous_categorie is not None or self.criteres or self.preferences
                                       or self.alternatives):
            raise ValueError("Une sous-catégorie, des critères ou des alternatives précisent un souhait de catégorie.")
        if self.mode not in MODES_RECHERCHE:
            raise ValueError(f"mode doit être parmi {MODES_RECHERCHE}.")
        if self.etat_min is not None and self.etat_min not in ETATS:
            raise ValueError(f"etat_min doit être parmi {ETATS}.")
        object.__setattr__(self, "modes", frozenset(self.modes))
        object.__setattr__(self, "zones", frozenset(self.zones))

    def categories_visees(self) -> set[str]:
        """Les catégories où chercher des objets pour ce souhait."""
        if self.categorie is None:
            return set()
        if self.mode == "precise":
            return {self.categorie}
        return {self.categorie} | {c for c, _ in self.alternatives}

    def _vise(self, objet: Objet) -> bool | None:
        """True : l'objet visé en premier ; False : une alternative acceptée ; None : ni l'un ni l'autre."""
        if objet.categorie == self.categorie and self.sous_categorie in (None, objet.sous_categorie):
            return True
        if self.mode == "precise":
            return None
        if self.mode == "ouverte":
            return False if objet.categorie in self.categories_visees() else None
        if any(objet.categorie == c and sc in (None, objet.sous_categorie) for c, sc in self.alternatives):
            return False
        return None

    def accepte_le_colis(self) -> bool:
        return not self.modes or MODE_COLIS in self.modes

    def correspond(self, objet: Objet) -> bool:
        if self.modes and objet.modes and not (self.modes & objet.modes):
            return False
        if self.objet_id is not None:
            return objet.id == self.objet_id
        if self.objets:
            return objet.id in self.objets
        if self._vise(objet) is None:
            return False
        if self.etat_min is not None and (objet.etat not in ETATS
                                          or ETATS.index(objet.etat) < ETATS.index(self.etat_min)):
            return False
        if objet.categorie != self.categorie:
            return True
        siennes = {cle: _norme(v) for cle, v in objet.caracteristiques}
        return all(siennes.get(cle) == _norme(valeur) for cle, valeur in self.criteres)

    def qualite(self, objet: Objet) -> int:
        """Qualité d'un objet qui correspond : visé en premier, puis critères préférentiels respectés."""
        if self.objet_id is not None or self.objets:
            return QUALITE_CIBLE
        q = QUALITE_CIBLE if self._vise(objet) else 0
        if objet.categorie == self.categorie:
            siennes = {cle: _norme(v) for cle, v in objet.caracteristiques}
            q += QUALITE_PREFERENCE * sum(siennes.get(cle) == _norme(v) for cle, v in self.preferences)
        return q


@dataclass
class Utilisateur:
    id: str
    souhaits: list[Souhait] = field(default_factory=list)
    zone: str | None = None
    # Probabilité qu'il aille au bout (dépôt de l'objet) : sert à estimer la
    # réussite d'une boucle. Peut être alimentée par la réputation.
    fiabilite: float = 1.0
    # Équité : poids de cette personne quand on départage des solutions qui échangent autant d'objets
    # (1 = normal ; plus pour qui a peu reçu récemment, voir l'API).
    priorite: int = 1
    # Probabilité qu'il dise oui à une boucle proposée (son taux de « oui », voir l'API) ;
    # None : la valeur commune du marché (``Marche.p_acceptation``).
    acceptation: float | None = None
    # Nombre maximum de boucles (donc d'objets reçus) pour lui dans une même recherche ; None : pas de plafond.
    # Le nombre d'objets échangés reste maximisé sous ce plafond : un gros déposant ne prend pas tout le dimanche.
    plafond: int | None = None
    # Zones d'intérêt choisies par la personne, et « toute la France » (par colis). Sans aucune des deux :
    # la règle des zones par nom (``zone``, ``Souhait.zones``, ``Marche.meme_zone``).
    zones_interet: tuple[ZoneInteret, ...] = ()
    toute_la_france: bool = False

    @property
    def zones_geographiques(self) -> bool:
        return bool(self.zones_interet) or self.toute_la_france

    def acces(self, objet: Objet) -> str | None:
        """Comment un objet peut lui parvenir, d'après ses zones d'intérêt : « proche » (dans une de ses zones,
        ou lieu inconnu : remise en main propre possible), « loin » (hors de ses zones mais il accepte toute la
        France : par colis seulement), None (hors de ses zones)."""
        if objet.position is None or any(z.contient(objet.position) for z in self.zones_interet):
            return "proche"
        return "loin" if self.toute_la_france else None


@dataclass(frozen=True)
class Transfert:
    """``donneur`` remet ``objet`` à ``receveur``, qui le reçoit au titre de
    son souhait n° ``souhait_idx``."""
    donneur: str
    receveur: str
    objet: Objet
    souhait_idx: int
    rang: int
    auto: bool
    proba_acceptation: float  # probabilité que le receveur dise oui
    qualite: int = 0  # voir Souhait.qualite
    souhait_ref: str | None = None  # Souhait.ref du souhait servi

    @property
    def cle(self) -> tuple[str, str, str]:
        return (self.donneur, self.objet.id, self.receveur)

    @property
    def cle_souhait(self) -> tuple[str, int]:
        return (self.receveur, self.souhait_idx)


@dataclass(frozen=True)
class Boucle:
    """Une boucle d'échange : chaque participant donne un objet au suivant.

    Pour A → B → C → A : A donne à B, B donne à C, C donne à A.
    """
    transferts: tuple[Transfert, ...]
    proba_reussite: float

    @property
    def longueur(self) -> int:
        return len(self.transferts)

    @property
    def participants(self) -> tuple[str, ...]:
        return tuple(t.donneur for t in self.transferts)

    @property
    def objets(self) -> tuple[str, ...]:
        return tuple(t.objet.id for t in self.transferts)

    @property
    def somme_rangs(self) -> int:
        return sum(t.rang for t in self.transferts)

    @property
    def cle(self) -> frozenset:
        return frozenset(t.cle for t in self.transferts)

    @property
    def preferences_respectees(self) -> int:
        """Nombre d'objets donnés contre un des souhaits indiqués sur leur fiche."""
        n = len(self.transferts)
        return sum(self.transferts[k].objet.prefere(self.transferts[k - 1]) for k in range(n))

    @property
    def qualite(self) -> int:
        """Qualité de la boucle : objets visés en premier, critères préférentiels, préférences « contre »."""
        return sum(t.qualite for t in self.transferts) + QUALITE_CONTRE * self.preferences_respectees

    def decrire(self) -> str:
        etapes = [f"{t.donneur} donne « {t.objet.titre or t.objet.id} » à {t.receveur}"
                  for t in self.transferts]
        return f"Boucle à {self.longueur} (réussite estimée {self.proba_reussite:.0%}) : " + " ; ".join(etapes)


@dataclass
class Contraintes:
    """Ce qui est déjà engagé ou refusé, pour relancer une recherche."""
    objets_indisponibles: set[str] = field(default_factory=set)
    souhaits_consommes: dict[tuple[str, int], int] = field(default_factory=dict)
    # (donneur, objet_id, receveur) qu'un receveur a refusés
    transferts_refuses: set[tuple[str, str, str]] = field(default_factory=set)
    utilisateurs_exclus: set[str] = field(default_factory=set)

    def engager(self, boucle: Boucle) -> None:
        for t in boucle.transferts:
            self.objets_indisponibles.add(t.objet.id)
            self.souhaits_consommes[t.cle_souhait] = self.souhaits_consommes.get(t.cle_souhait, 0) + 1


class Marche:
    """L'ensemble des utilisateurs et objets d'une zone (une ville au lancement)."""

    def __init__(self, p_acceptation: float = 0.7, p_auto: float = 0.95, meme_zone: bool = True):
        self.p_acceptation = p_acceptation
        self.p_auto = p_auto
        self.meme_zone = meme_zone
        self.utilisateurs: dict[str, Utilisateur] = {}
        self.objets: dict[str, Objet] = {}

    def ajouter_utilisateur(self, id: str, souhaits=(), zone=None, fiabilite=1.0, priorite=1,
                            acceptation: float | None = None, plafond: int | None = None,
                            zones_interet=(), toute_la_france: bool = False) -> Utilisateur:
        if id in self.utilisateurs:
            raise ValueError(f"Utilisateur {id!r} déjà présent.")
        if priorite < 1:
            raise ValueError("priorite doit être >= 1.")
        if acceptation is not None and not 0 < acceptation <= 1:
            raise ValueError("acceptation doit être dans ]0, 1].")
        if plafond is not None and plafond < 0:
            raise ValueError("plafond doit être >= 0.")
        u = Utilisateur(id, list(souhaits), zone, fiabilite, priorite, acceptation, plafond,
                        tuple(zones_interet), toute_la_france)
        self.utilisateurs[id] = u
        return u

    def ajouter_objet(self, id: str, proprietaire: str, categorie: str, titre: str = "",
                      contre=(), contre_strict: bool = False, sous_categorie: str | None = None,
                      caracteristiques=(), etat: str | None = None, modes=(), zone: str | None = None,
                      disponible: bool = True, position: tuple[float, float] | None = None) -> Objet:
        if id in self.objets:
            raise ValueError(f"Objet {id!r} déjà présent.")
        if proprietaire not in self.utilisateurs:
            raise ValueError(f"Propriétaire inconnu : {proprietaire!r}.")
        nb_souhaits = len(self.utilisateurs[proprietaire].souhaits)
        contre = frozenset(contre)
        if any(not 0 <= i < nb_souhaits for i in contre):
            raise ValueError(f"« contre » doit désigner des souhaits de {proprietaire!r}.")
        if etat is not None and etat not in ETATS:
            raise ValueError(f"etat doit être parmi {ETATS}.")
        caracteristiques = tuple(sorted(dict(caracteristiques).items()))
        o = Objet(id, proprietaire, categorie, titre, contre, contre_strict, sous_categorie, caracteristiques,
                  etat, frozenset(modes), zone, disponible, position)
        self.objets[id] = o
        return o

    def retirer_objet(self, id: str) -> None:
        self.objets.pop(id, None)

    def p_acceptation_de(self, utilisateur: Utilisateur) -> float:
        """Chance qu'il dise oui à une boucle (hors souhait « j'accepte d'office ») : son taux s'il est connu."""
        return self.p_acceptation if utilisateur.acceptation is None else utilisateur.acceptation

    def proba_participant(self, transfert: Transfert) -> float:
        """Probabilité que le receveur accepte la boucle et aille au bout."""
        fiab = self.utilisateurs[transfert.receveur].fiabilite
        return transfert.proba_acceptation * fiab

    @staticmethod
    def boucle_admise(transferts) -> bool:
        """Chaque objet donné respecte sa liste stricte « contre » (le donneur reçoit le transfert précédent)."""
        return all(transferts[k].objet.accepte(transferts[k - 1]) for k in range(len(transferts)))

    def creer_boucle(self, transferts) -> Boucle:
        transferts = tuple(transferts)
        return Boucle(transferts, prod(self.proba_participant(t) for t in transferts))
