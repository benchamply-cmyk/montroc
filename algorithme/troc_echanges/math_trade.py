"""« Math trade » à la TradeMaximizer : trouver le nombre maximal d'échanges
possibles sur tout le marché, sous forme de boucles.

Deux modes :

- ``longueur_max=3`` (ou 2, 4, 5…) : mode borné. On énumère les boucles de
  2 à ``longueur_max`` personnes, puis on choisit le meilleur ensemble
  compatible (solveur exact ou empaquetage). Au-delà de 3, la longueur est
  réduite si l'énumération dépasse ``BUDGET_CYCLES`` (« si cela reste
  calculable ») ; ``Solution.stats["longueur_max"]`` dit celle retenue.
- ``longueur_max=None`` : TradeMaximizer « pur », boucles de longueur
  illimitée. Résolu exactement par un flot de coût minimal (comme le vrai
  TradeMaximizer, qui ramène le problème à une affectation) : maximum
  d'objets échangés, puis préférence aux souhaits les mieux classés.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

from . import empaquetage, solveur_exact
from .boucles import cle_classement, enumerer_boucles, longueur_calculable
from .flot import FlotCoutMin
from .graphe import GrapheEchanges
from .modele import Boucle, Contraintes, Marche, Transfert

OBJECTIFS = ("echanges", "esperance")
MOTEURS = ("auto", "exact", "heuristique")
# Chemins explorés au plus pour vérifier qu'une longueur de boucle au-delà de 3 reste calculable (~1 s).
BUDGET_CYCLES = 1_000_000


@dataclass
class Solution:
    boucles: list[Boucle]
    optimal: bool
    duree_s: float
    candidats: int = 0
    stats: dict = field(default_factory=dict)
    moteur: str = "heuristique"

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
               duree_max_s: float = 10.0, moteur: str = "auto",
               budget_cycles: int = BUDGET_CYCLES) -> Solution:
    """Calcule l'ensemble de boucles qui maximise les échanges.

    - ``objectif="echanges"`` : maximise le nombre d'objets échangés
      (TradeMaximizer), à égalité sert le plus de personnes différentes
      (pondérées par ``Utilisateur.priorite``, l'équité), puis la meilleure
      qualité (``Boucle.qualite``), puis les boucles les plus sûres ;
    - ``objectif="esperance"`` : maximise le nombre d'objets échangés
      *attendu* (longueur × chance que tous acceptent), ce qui favorise les
      échanges directs et les acceptations automatiques. Mode bornée seulement.

    ``moteur`` (mode borné, objectif « echanges », sans ``proba_min``) :
    ``"exact"`` utilise le solveur CP-SAT d'OR-Tools (``solveur_exact``),
    ``"heuristique"`` l'empaquetage de boucles énumérées, ``"auto"`` le solveur
    exact s'il est installé et si le marché n'est pas trop grand
    (``solveur_exact.MAX_COPIES_AUTO``), l'heuristique sinon ou s'il ne trouve
    rien à temps.
    """
    if objectif not in OBJECTIFS:
        raise ValueError(f"objectif doit être parmi {OBJECTIFS}")
    if moteur not in MOTEURS:
        raise ValueError(f"moteur doit être parmi {MOTEURS}")
    debut = time.perf_counter()
    graphe = GrapheEchanges(marche, contraintes)
    if longueur_max is None:
        if objectif != "echanges":
            raise ValueError("Le mode sans limite de longueur ne gère que l'objectif 'echanges'.")
        boucles = _trade_maximizer(graphe)
        return Solution(sorted(boucles, key=cle_classement), True, time.perf_counter() - debut)

    stats = {}
    if longueur_max > 3:
        longueur_max = longueur_calculable(graphe, longueur_max, budget_cycles)
        stats["longueur_max"] = longueur_max
    exact_possible = objectif == "echanges" and proba_min == 0
    if moteur == "exact" and not (exact_possible and solveur_exact.disponible()):
        raise ValueError("Le moteur exact demande OR-Tools, l'objectif 'echanges' et proba_min=0.")
    if moteur != "heuristique" and exact_possible:
        limite = solveur_exact.MAX_COPIES_AUTO if moteur == "auto" else None
        # Trop grand pour la mémoire avec des boucles longues : on raccourcit (jusqu'à 3) avant de passer à
        # l'heuristique, qui fait moins bien que le solveur exact sur des boucles plus courtes (banc d'essai).
        for longueur in range(longueur_max, min(longueur_max, 3) - 1, -1):
            try:
                resultat = solveur_exact.resoudre(graphe, longueur, duree_max_s - (time.perf_counter() - debut),
                                                  max_copies=limite)
            except solveur_exact.TropGrand:
                continue
            longueur_max = longueur
            if resultat is not None:
                boucles, optimal, stats_exact = resultat
                stats["longueur_max"] = longueur
                return Solution(sorted(boucles, key=cle_classement), optimal, time.perf_counter() - debut,
                                stats=stats | stats_exact, moteur="exact")
            break
        else:
            longueur_max = longueur
        stats["longueur_max"] = longueur_max
        # Pas d'OR-Tools, trop grand, ou aucune solution trouvée à temps : l'heuristique prend le relais.
        duree_max_s = max(1.0, duree_max_s - (time.perf_counter() - debut))

    candidats = [b for b in enumerer_boucles(graphe, longueur_max, options_par_transfert)
                 if b.proba_reussite >= proba_min]
    eps = 1.0 / (len(candidats) + 1)
    rang_max = max((b.somme_rangs for b in candidats), default=1)
    qualite_max = max((b.qualite for b in candidats), default=0) + 1
    priorite = {u.id: u.priorite for u in marche.utilisateurs.values()}
    priorite_max = max(priorite.values(), default=1)
    poids, ressources = [], []
    for b in candidats:
        # départage (toujours < 1) : équité (priorité moyenne des participants), boucle plus sûre,
        # souhaits mieux classés, qualité
        equite = sum(priorite[p] for p in b.participants) / (b.longueur * priorite_max)
        departage = eps * (0.3 * equite + 0.3 * b.proba_reussite + 0.2 * (1 - b.somme_rangs / (rang_max + 1))
                           + 0.2 * b.qualite / qualite_max)
        base = b.longueur if objectif == "echanges" else b.longueur * b.proba_reussite
        poids.append(base + (departage if objectif == "echanges" else departage * 1e-3))
        ressources.append([("o", t.objet.id) for t in b.transferts]
                          + [("s",) + t.cle_souhait for t in b.transferts])

    def capacite(r):
        return 1 if r[0] == "o" else graphe.capacite_souhait.get(r[1:], 0)

    choix, optimal = empaquetage.resoudre(poids, ressources, capacite, taille_exacte,
                                           limite_noeuds, duree_max_s)
    boucles = sorted((candidats[i] for i in choix), key=cle_classement)
    return Solution(boucles, optimal, time.perf_counter() - debut, candidats=len(candidats), stats=stats)


def _trade_maximizer(graphe: GrapheEchanges) -> list[Boucle]:
    """Boucles de longueur illimitée, maximum d'objets échangés (exact).

    Réseau : chaque objet b porte une unité. Elle revient à son propriétaire
    (objet non échangé, coût M) ou passe par un souhait d'un autre
    utilisateur (coût = rang du souhait). Chaque utilisateur doit renvoyer
    autant d'unités qu'il a d'objets : il reçoit donc autant qu'il donne.
    Les listes « contre » des objets sont ignorées ici (mode de comparaison).
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
