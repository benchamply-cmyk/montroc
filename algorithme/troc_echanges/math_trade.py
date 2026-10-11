"""« Math trade » à la TradeMaximizer : trouver le nombre maximal d'échanges
possibles sur tout le marché, sous forme de boucles.

Deux modes :

- ``longueur_max=3`` (ou 2) : mode de lancement recommandé par l'étude.
  On énumère toutes les boucles de 2 et 3 personnes, puis on choisit le
  meilleur ensemble compatible (empaquetage).
- ``longueur_max=None`` : TradeMaximizer « pur », boucles de longueur
  illimitée. Résolu exactement par un flot de coût minimal (comme le vrai
  TradeMaximizer, qui ramène le problème à une affectation) : maximum
  d'objets échangés, puis préférence aux souhaits les mieux classés.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

from . import empaquetage
from .boucles import cle_classement, enumerer_boucles
from .flot import FlotCoutMin
from .graphe import GrapheEchanges
from .modele import Boucle, Contraintes, Marche, Transfert

OBJECTIFS = ("echanges", "esperance")


@dataclass
class Solution:
    boucles: list[Boucle]
    optimal: bool
    duree_s: float
    candidats: int = 0
    stats: dict = field(default_factory=dict)

    @property
    def nb_objets_echanges(self) -> int:
        return sum(b.longueur for b in self.boucles)

    @property
    def participants(self) -> set[str]:
        return {p for b in self.boucles for p in b.participants}

    @property
    def esperance_objets(self) -> float:
        """Nombre d'objets échangés attendu une fois les refus pris en compte."""
        return sum(b.longueur * b.proba_reussite for b in self.boucles)

    def resume(self) -> str:
        longueurs = {}
        for b in self.boucles:
            longueurs[b.longueur] = longueurs.get(b.longueur, 0) + 1
        detail = ", ".join(f"{n} boucle(s) à {k}" for k, n in sorted(longueurs.items())) or "aucune boucle"
        return (f"{self.nb_objets_echanges} objets échangés, {len(self.participants)} participants "
                f"({detail}) ; espérance après refus : {self.esperance_objets:.1f} objets ; "
                f"{'optimal prouvé' if self.optimal else 'meilleure solution trouvée'} en {self.duree_s:.2f} s")


def math_trade(marche: Marche, longueur_max: int | None = 3, objectif: str = "echanges",
               options_par_transfert: int = 2, proba_min: float = 0.0,
               contraintes: Contraintes | None = None,
               taille_exacte: int = 400, limite_noeuds: int = 50_000,
               duree_max_s: float = 10.0) -> Solution:
    """Calcule l'ensemble de boucles qui maximise les échanges.

    - ``objectif="echanges"`` : maximise le nombre d'objets échangés
      (TradeMaximizer), à égalité préfère les boucles les plus sûres ;
    - ``objectif="esperance"`` : maximise le nombre d'objets échangés
      *attendu* (longueur × chance que tous acceptent), ce qui favorise les
      échanges directs et les acceptations automatiques. Mode bornée seulement.
    """
    if objectif not in OBJECTIFS:
        raise ValueError(f"objectif doit être parmi {OBJECTIFS}")
    debut = time.perf_counter()
    graphe = GrapheEchanges(marche, contraintes)
    if longueur_max is None:
        if objectif != "echanges":
            raise ValueError("Le mode sans limite de longueur ne gère que l'objectif 'echanges'.")
        boucles = _trade_maximizer(graphe)
        return Solution(sorted(boucles, key=cle_classement), True, time.perf_counter() - debut)

    candidats = [b for b in enumerer_boucles(graphe, longueur_max, options_par_transfert)
                 if b.proba_reussite >= proba_min]
    eps = 1.0 / (len(candidats) + 1)
    rang_max = max((b.somme_rangs for b in candidats), default=1)
    poids, ressources = [], []
    for b in candidats:
        # départage : boucle plus sûre, puis souhaits mieux classés (toujours < 1 au total)
        departage = eps * (0.5 * b.proba_reussite + 0.5 * (1 - b.somme_rangs / (rang_max + 1)))
        base = b.longueur if objectif == "echanges" else b.longueur * b.proba_reussite
        poids.append(base + (departage if objectif == "echanges" else departage * 1e-3))
        ressources.append([("o", t.objet.id) for t in b.transferts]
                          + [("s",) + t.cle_souhait for t in b.transferts])

    def capacite(r):
        return 1 if r[0] == "o" else graphe.capacite_souhait.get(r[1:], 0)

    choix, optimal = empaquetage.resoudre(poids, ressources, capacite, taille_exacte,
                                           limite_noeuds, duree_max_s)
    boucles = sorted((candidats[i] for i in choix), key=cle_classement)
    return Solution(boucles, optimal, time.perf_counter() - debut, candidats=len(candidats))


def _trade_maximizer(graphe: GrapheEchanges) -> list[Boucle]:
    """Boucles de longueur illimitée, maximum d'objets échangés (exact).

    Réseau : chaque objet b porte une unité. Elle revient à son propriétaire
    (objet non échangé, coût M) ou passe par un souhait d'un autre
    utilisateur (coût = rang du souhait). Chaque utilisateur doit renvoyer
    autant d'unités qu'il a d'objets : il reçoit donc autant qu'il donne.
    """
    transferts = list(graphe.tous_les_transferts())
    if not transferts:
        return []
    objets = {}
    for t in transferts:
        objets[t.objet.id] = t.objet
    users = sorted({o.proprietaire for o in objets.values()} | {t.receveur for t in transferts})
    souhaits = sorted({t.cle_souhait for t in transferts})

    idx = {}
    for nom in [("S",), ("T",)] + [("u", u) for u in users] + [("o", o) for o in objets] + [("s",) + s for s in souhaits]:
        idx[nom] = len(idx)
    S, T = idx[("S",)], idx[("T",)]
    reseau = FlotCoutMin(len(idx))
    rang_max = max(t.rang for t in transferts)
    M = rang_max * len(objets) + 1

    nb_objets = {}
    for o in objets.values():
        reseau.ajouter_arc(S, idx[("o", o.id)], 1, 0)
        reseau.ajouter_arc(idx[("o", o.id)], idx[("u", o.proprietaire)], 1, M)
        nb_objets[o.proprietaire] = nb_objets.get(o.proprietaire, 0) + 1
    for u, n in nb_objets.items():
        reseau.ajouter_arc(idx[("u", u)], T, n, 0)
    for s in souhaits:
        reseau.ajouter_arc(idx[("s",) + s], idx[("u", s[0])], graphe.capacite_souhait[s], 0)
    arc_transfert: dict[int, Transfert] = {}
    for t in transferts:
        e = reseau.ajouter_arc(idx[("o", t.objet.id)], idx[("s",) + t.cle_souhait], 1, t.rang)
        arc_transfert[e] = t

    reseau.resoudre(S, T)
    realises = [t for e, t in arc_transfert.items() if reseau.flot(e) > 0]
    return [graphe.marche.creer_boucle(c) for c in _decomposer_en_cycles(realises)]


def _decomposer_en_cycles(transferts: list[Transfert]) -> list[list[Transfert]]:
    """Chaque utilisateur donne autant qu'il reçoit : on découpe en cycles
    simples (un utilisateur n'apparaît qu'une fois par boucle)."""
    sortants: dict[str, list[Transfert]] = defaultdict(list)
    for t in sorted(transferts, key=lambda t: t.cle, reverse=True):
        sortants[t.donneur].append(t)
    cycles = []
    for depart in sorted(list(sortants)):
        while sortants[depart]:
            chemin: list[Transfert] = []
            noeuds = [depart]          # noeuds[i] = donneur de chemin[i]
            position = {depart: 0}
            u = depart
            while True:
                t = sortants[u].pop()
                chemin.append(t)
                v = t.receveur
                if v not in position:
                    position[v] = len(noeuds)
                    noeuds.append(v)
                    u = v
                    continue
                k = position[v]
                cycles.append(chemin[k:])
                for n in noeuds[k + 1:]:
                    del position[n]
                noeuds, chemin, u = noeuds[:k + 1], chemin[:k], v
                if not chemin:
                    break
    return cycles
