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
    """Un objet disponible à l'échange."""
    id: str
    proprietaire: str
    categorie: str
    titre: str = ""


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
      contre cet objet » (engagement préalable, section 2 de l'étude).
    """
    categorie: str | None = None
    objet_id: str | None = None
    rang: int = 1
    quantite: int = 1
    acceptation_auto: bool = False

    def __post_init__(self):
        if (self.categorie is None) == (self.objet_id is None):
            raise ValueError("Un souhait porte soit sur une catégorie, soit sur un objet précis.")
        if self.rang < 1 or self.quantite < 1:
            raise ValueError("rang et quantite doivent être >= 1.")

    def correspond(self, objet: Objet) -> bool:
        if self.objet_id is not None:
            return objet.id == self.objet_id
        return objet.categorie == self.categorie


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

    def ajouter_objet(self, id: str, proprietaire: str, categorie: str, titre: str = "") -> Objet:
        if id in self.objets:
            raise ValueError(f"Objet {id!r} déjà présent.")
        if proprietaire not in self.utilisateurs:
            raise ValueError(f"Propriétaire inconnu : {proprietaire!r}.")
        o = Objet(id, proprietaire, categorie, titre)
        self.objets[id] = o
        return o

    def retirer_objet(self, id: str) -> None:
        self.objets.pop(id, None)

    def proba_participant(self, transfert: Transfert) -> float:
        """Probabilité que le receveur accepte la boucle et aille au bout."""
        fiab = self.utilisateurs[transfert.receveur].fiabilite
        return transfert.proba_acceptation * fiab

    def creer_boucle(self, transferts) -> Boucle:
        transferts = tuple(transferts)
        return Boucle(transferts, prod(self.proba_participant(t) for t in transferts))
