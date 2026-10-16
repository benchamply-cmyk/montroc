"""Modèle de données du troc : utilisateurs, objets, souhaits, transferts, boucles.

Aucune notion de prix ni de monnaie : un utilisateur publie des objets
disponibles et liste des souhaits (une catégorie, ou un objet précis).
Un échange est une boucle de transferts où chacun donne un objet et en reçoit un.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import prod


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
    - ``rang`` : 1 = souhait préféré (sert à départager, comme les listes
      ordonnées de TradeMaximizer) ;
    - ``quantite`` : nombre d'objets que l'utilisateur veut recevoir pour ce
      souhait (évite de recevoir trois poussettes) ;
    - ``acceptation_auto`` : case « j'accepte automatiquement un échange
      contre cet objet » (engagement préalable, section 2 de l'étude) ;
    - ``sous_categorie`` : seulement les objets de cette sous-catégorie ;
    - ``criteres`` : paires (clé, valeur), par exemple (« taille », « 4 ans ») :
      un objet qui donne une autre valeur pour la clé ne convient pas, un objet
      qui ne la précise pas convient encore.
    """
    categorie: str | None = None
    objet_id: str | None = None
    rang: int = 1
    quantite: int = 1
    acceptation_auto: bool = False
    sous_categorie: str | None = None
    criteres: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if (self.categorie is None) == (self.objet_id is None):
            raise ValueError("Un souhait porte soit sur une catégorie, soit sur un objet précis.")
        if self.rang < 1 or self.quantite < 1:
            raise ValueError("rang et quantite doivent être >= 1.")
        if self.sous_categorie is not None and self.categorie is None:
            raise ValueError("Une sous-catégorie précise un souhait de catégorie.")

    def correspond(self, objet: Objet) -> bool:
        if self.objet_id is not None:
            return objet.id == self.objet_id
        if objet.categorie != self.categorie:
            return False
        if self.sous_categorie is not None and objet.sous_categorie != self.sous_categorie:
            return False
        siennes = dict(objet.caracteristiques)
        return all(siennes.get(cle, valeur) == valeur for cle, valeur in self.criteres)


@dataclass
class Utilisateur:
    id: str
    souhaits: list[Souhait] = field(default_factory=list)
    zone: str | None = None
    # Probabilité qu'il aille au bout (dépôt de l'objet) : sert à estimer la
    # réussite d'une boucle. Peut être alimentée par la réputation.
    fiabilite: float = 1.0


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

    def ajouter_utilisateur(self, id: str, souhaits=(), zone=None, fiabilite=1.0) -> Utilisateur:
        if id in self.utilisateurs:
            raise ValueError(f"Utilisateur {id!r} déjà présent.")
        u = Utilisateur(id, list(souhaits), zone, fiabilite)
        self.utilisateurs[id] = u
        return u

    def ajouter_objet(self, id: str, proprietaire: str, categorie: str, titre: str = "",
                      contre=(), contre_strict: bool = False, sous_categorie: str | None = None,
                      caracteristiques=()) -> Objet:
        if id in self.objets:
            raise ValueError(f"Objet {id!r} déjà présent.")
        if proprietaire not in self.utilisateurs:
            raise ValueError(f"Propriétaire inconnu : {proprietaire!r}.")
        nb_souhaits = len(self.utilisateurs[proprietaire].souhaits)
        contre = frozenset(contre)
        if any(not 0 <= i < nb_souhaits for i in contre):
            raise ValueError(f"« contre » doit désigner des souhaits de {proprietaire!r}.")
        caracteristiques = tuple(sorted(dict(caracteristiques).items()))
        o = Objet(id, proprietaire, categorie, titre, contre, contre_strict, sous_categorie, caracteristiques)
        self.objets[id] = o
        return o

    def retirer_objet(self, id: str) -> None:
        self.objets.pop(id, None)

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
