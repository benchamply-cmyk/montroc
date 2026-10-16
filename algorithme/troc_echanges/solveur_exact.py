"""Math trade borné (boucles de 2 à ``longueur_max`` personnes) résolu exactement par programmation par contraintes.

Utilise le solveur CP-SAT de Google OR-Tools (licence Apache 2.0), s'il est
installé ; sinon ``math_trade`` garde l'empaquetage heuristique.

Formulation : on énumère les cycles de *personnes* (pas d'objets). Chaque cycle
peut servir plusieurs fois (« copies », par exemple deux personnes qui
s'échangent deux paires d'objets) ; pour chaque copie active, le solveur choisit
un transfert par étape. Aucun objet n'est écarté d'avance : c'est ce qui manquait
à l'énumération des boucles, limitée à quelques objets par couple de personnes.

Contraintes : chaque objet part au plus une fois, chaque souhait ne reçoit pas
plus que sa quantité, et un objet à liste « contre » stricte ne part que si son
propriétaire reçoit, dans la même boucle, un des souhaits de la liste.

Objectifs, dans l'ordre (chaque étape garde le résultat de la précédente) :
1. le plus d'objets échangés ;
2. équité : le plus de personnes différentes servies (comme la métrique
   USERS-TRADING de TradeMaximizer), chacune comptée avec son poids
   ``Utilisateur.priorite`` (plus fort pour qui a peu reçu récemment) ;
3. la meilleure qualité : objets visés plutôt qu'alternatives, critères
   préférentiels et préférences « contre » respectés (``Boucle.qualite``) ;
4. les boucles les plus sûres, puis les souhaits les mieux classés.
"""
from __future__ import annotations

import math
import time

from .boucles import cycles_utilisateurs, options_du_cycle
from .graphe import GrapheEchanges
from .modele import QUALITE_CONTRE, Boucle

try:
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover - dépend de l'installation
    cp_model = None

# Part du budget de temps de chaque étape (la première, le nombre d'objets, compte le plus).
PARTS_DU_BUDGET = (0.7, 0.1, 0.1, 0.1)
# Au-delà, le mode « auto » de math_trade garde l'heuristique. Banc d'essai : à 2 000 personnes (~3 600 copies),
# CP-SAT fait mieux qu'elle avec ~220 Mo de mémoire ; à 3 000 (~12 500 copies) il monte à ~380 Mo, trop près des
# 512 Mo de Render gratuit ; à 5 000 (~50 000 copies) il trouve moins bien qu'elle en 30 s et dépasse 1 Go.
MAX_COPIES_AUTO = 6_000
# Deux fils : la mémoire grandit avec le nombre de fils (Render gratuit : 512 Mo), le gain au-delà est faible.
FILS = 2


class TropGrand(Exception):
    """Le problème dépasse ``max_copies`` : la mémoire ne suffirait pas."""


def disponible() -> bool:
    return cp_model is not None


def resoudre(graphe: GrapheEchanges, longueur_max: int, duree_max_s: float,
             fils: int = FILS, max_copies: int | None = None) -> tuple[list[Boucle], bool, dict] | None:
    """Renvoie (boucles, nombre d'objets prouvé maximal ?, statistiques), ou None si
    OR-Tools manque ou si aucune solution n'a été trouvée dans le temps imparti.
    Lève ``TropGrand`` si le problème dépasse ``max_copies``."""
    if cp_model is None:
        return None
    debut = time.perf_counter()
    marche = graphe.marche
    cycles = []
    for cycle in cycles_utilisateurs(graphe, longueur_max):
        options = options_du_cycle(graphe, cycle)
        cycles.append((cycle, options, min(len(o) for o in options)))
    if max_copies is not None and sum(q for _, _, q in cycles) > max_copies:
        raise TropGrand
    modele = cp_model.CpModel()

    copies = []          # (cycle, variable « copie active », [[(variable, transfert)] par étape])
    par_objet: dict[str, list] = {}
    par_souhait: dict[tuple[str, int], list] = {}
    par_personne: dict[str, list] = {}
    qualites, couts = [], []
    variables = []       # copies et transferts : la solution d'une étape sert d'indice à la suivante

    for cycle, options, nb_copies in cycles:
        n = len(cycle)
        precedente = None
        for _ in range(nb_copies):
            active = modele.new_bool_var("")
            variables.append(active)
            if precedente is not None:
                modele.add_implication(active, precedente)  # copies dans l'ordre : pas de symétries
            precedente = active
            etapes = []
            for liste in options:
                xs = [(modele.new_bool_var(""), t) for t in liste]
                variables.extend(x for x, _ in xs)
                modele.add(sum(x for x, _ in xs) == active)
                etapes.append(xs)
                for x, t in xs:
                    par_objet.setdefault(t.objet.id, []).append(x)
                    par_souhait.setdefault(t.cle_souhait, []).append(x)
                    couts.append((x, _cout(marche, t)))
                    if t.qualite:
                        qualites.append((x, t.qualite))
            for k in range(n):
                # cycle[k] donne à l'étape k et reçoit à l'étape k - 1.
                for x, t in etapes[k]:
                    if not t.objet.contre:
                        continue
                    recus = [y for y, r in etapes[k - 1] if t.objet.prefere(r)]
                    if t.objet.contre_strict:
                        modele.add(x <= sum(recus))
                    else:
                        bonus = modele.new_bool_var("")
                        modele.add(bonus <= x)
                        modele.add(bonus <= sum(recus))
                        qualites.append((bonus, QUALITE_CONTRE))
            for u in cycle:
                par_personne.setdefault(u, []).append(active)
            copies.append((cycle, active, etapes))

    if not copies:
        return [], True, {"copies": 0}
    for xs in par_objet.values():
        if len(xs) > 1:
            modele.add(sum(xs) <= 1)
    for cle, xs in par_souhait.items():
        if len(xs) > graphe.capacite_souhait[cle]:
            modele.add(sum(xs) <= graphe.capacite_souhait[cle])
    servis = []
    for u, actives in par_personne.items():
        s = modele.new_bool_var("")
        modele.add(s <= sum(actives))
        servis.append((s, marche.utilisateurs[u].priorite))

    objets = sum(len(cycle) * active for cycle, active, _ in copies)
    etapes_objectif = [
        (objets, True),
        (sum(p * s for s, p in servis), True),
        (sum(q * x for x, q in qualites), True),
        (sum(c * x for x, c in couts), False),
    ]

    solveur = cp_model.CpSolver()
    solveur.parameters.num_workers = fils
    solveur.parameters.random_seed = 1
    valeurs = None   # meilleure affectation connue
    optimal = False
    statuts = []
    for i, ((expression, maximiser), part) in enumerate(zip(etapes_objectif, PARTS_DU_BUDGET, strict=True)):
        reste = duree_max_s - (time.perf_counter() - debut)
        if reste <= 0.05:
            break
        if isinstance(expression, int):  # rien à optimiser à cette étape
            continue
        (modele.maximize if maximiser else modele.minimize)(expression)
        modele.clear_hints()
        if valeurs is not None:
            for v, val in zip(variables, valeurs):
                modele.add_hint(v, val)
        # Chaque étape a sa part du budget ; la dernière prend tout le temps restant.
        solveur.parameters.max_time_in_seconds = max(0.05, reste if i == len(etapes_objectif) - 1
                                                     else min(reste, duree_max_s * part))
        statut = solveur.solve(modele)
        statuts.append(solveur.status_name(statut))
        if statut not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break
        if i == 0:
            optimal = statut == cp_model.OPTIMAL
        valeurs = [solveur.value(v) for v in variables]
        atteint = round(solveur.objective_value)
        modele.add(expression >= atteint if maximiser else expression <= atteint)

    if valeurs is None:
        return None
    choisi = {v.index: val for v, val in zip(variables, valeurs)}
    boucles = []
    for _cycle, active, etapes in copies:
        if not choisi[active.index]:
            continue
        transferts = [next(t for x, t in xs if choisi[x.index]) for xs in etapes]
        boucles.append(marche.creer_boucle(transferts))
    stats = {"copies": len(copies), "etapes": statuts, "duree_s": time.perf_counter() - debut}
    return boucles, optimal, stats


def _cout(marche, t) -> int:
    """Coût entier d'un transfert : surtout le risque de refus, puis le rang du souhait."""
    p = max(marche.proba_participant(t), 1e-6)
    return round(-1000 * math.log(p)) * 100 + min(t.rang, 99)
