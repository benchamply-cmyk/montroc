"""Choisir un ensemble de boucles compatibles de poids maximal.

Deux boucles sont incompatibles si elles utilisent le même objet, ou si elles
dépassent la quantité d'un souhait. C'est un problème d'empaquetage
(« set packing »), difficile en théorie, mais il se découpe en composantes
indépendantes (quartiers, catégories) qui restent petites en pratique :

- composante petite : recherche exacte par séparation et évaluation ;
- composante grande, ou budget épuisé : glouton + amélioration locale.
"""
from __future__ import annotations

import sys
import time
from collections import defaultdict


class _UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        p = self.parent.setdefault(x, x)
        while p != self.parent[p]:
            self.parent[p] = self.parent[self.parent[p]]
            p = self.parent[p]
        self.parent[x] = p
        return p

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def _compatible(ressources, usage, capacite):
    return all(usage.get(r, 0) + 1 <= capacite(r) for r in ressources)


def _ajouter(ressources, usage):
    for r in ressources:
        usage[r] = usage.get(r, 0) + 1


def _retirer(ressources, usage):
    for r in ressources:
        usage[r] -= 1


def _glouton(indices, poids, ressources, capacite, degre):
    """Prend d'abord les boucles qui gênent le moins les autres."""
    usage = {}
    choisis = []
    cle = {i: poids[i] / (1 + sum(degre[r] / capacite(r) for r in ressources[i])) for i in indices}
    for i in sorted(indices, key=lambda i: -cle[i]):
        if _compatible(ressources[i], usage, capacite):
            _ajouter(ressources[i], usage)
            choisis.append(i)
    return choisis


def _amelioration_locale(indices, poids, ressources, capacite, par_ressource, choisis,
                         max_passes=10, echeance=None):
    """Recherche locale : on fait entrer une boucle non choisie en retirant
    celles qui la gênent, puis on recomplète autour des ressources libérées.
    On garde le changement s'il améliore le total."""
    selection = set(choisis)
    usage = {}
    tenants = defaultdict(set)
    for i in selection:
        _ajouter(ressources[i], usage)
        for r in ressources[i]:
            tenants[r].add(i)

    def entrer(i):
        selection.add(i)
        _ajouter(ressources[i], usage)
        for r in ressources[i]:
            tenants[r].add(i)

    def sortir(i):
        selection.discard(i)
        _retirer(ressources[i], usage)
        for r in ressources[i]:
            tenants[r].discard(i)

    for _ in range(max_passes):
        progres = False
        for c in indices:
            if c in selection:
                continue
            if echeance is not None and time.perf_counter() > echeance:
                return list(selection)
            genants = set()
            for r in ressources[c]:
                exces = usage.get(r, 0) + 1 - capacite(r)
                if exces > 0:
                    deja = len(genants & tenants[r])
                    for g in sorted(tenants[r] - genants, key=lambda g: poids[g])[:max(0, exces - deja)]:
                        genants.add(g)
            if not genants:
                entrer(c)
                progres = True
                continue
            perte = sum(poids[g] for g in genants)
            liberees = {r for g in genants for r in ressources[g]}
            for g in genants:
                sortir(g)
            entrer(c)
            gain = poids[c] - perte
            ajouts = []
            voisins = {j for r in liberees for j in par_ressource[r]} - selection - genants
            for j in sorted(voisins, key=lambda j: -poids[j]):
                if _compatible(ressources[j], usage, capacite):
                    entrer(j)
                    ajouts.append(j)
                    gain += poids[j]
            if gain > 1e-12:
                progres = True
            else:
                for j in ajouts:
                    sortir(j)
                sortir(c)
                for g in genants:
                    entrer(g)
        if not progres:
            break
    return list(selection)


def _exact(indices, poids, ressources, capacite, incumbent, limite_noeuds):
    """Séparation et évaluation. Renvoie (meilleure sélection, optimal ?)."""
    ordre = sorted(indices, key=lambda i: -poids[i])
    meilleur = [list(incumbent), sum(poids[i] for i in incumbent)]
    noeuds = [0]
    usage = {}
    courant = []

    def borne(k):
        return sum(poids[ordre[j]] for j in range(k, len(ordre))
                   if _compatible(ressources[ordre[j]], usage, capacite))

    def rec(k, valeur):
        noeuds[0] += 1
        if noeuds[0] > limite_noeuds:
            return
        if valeur > meilleur[1] + 1e-12:
            meilleur[0], meilleur[1] = list(courant), valeur
        if k >= len(ordre) or valeur + borne(k) <= meilleur[1] + 1e-12:
            return
        i = ordre[k]
        if _compatible(ressources[i], usage, capacite):
            _ajouter(ressources[i], usage)
            courant.append(i)
            rec(k + 1, valeur + poids[i])
            courant.pop()
            _retirer(ressources[i], usage)
        rec(k + 1, valeur)

    ancienne = sys.getrecursionlimit()
    sys.setrecursionlimit(max(ancienne, 2 * len(ordre) + 1000))
    try:
        rec(0, 0.0)
    finally:
        sys.setrecursionlimit(ancienne)
    return meilleur[0], noeuds[0] <= limite_noeuds


def resoudre(poids, ressources, capacite, taille_exacte=400, limite_noeuds=50_000, duree_max_s=10.0):
    """``poids[i]`` et ``ressources[i]`` décrivent le candidat i ;
    ``capacite(r)`` donne la capacité de la ressource r.

    Renvoie (indices choisis, optimal_prouve).
    """
    echeance = time.perf_counter() + duree_max_s
    uf = _UnionFind()
    par_ressource = defaultdict(list)
    for i, rs in enumerate(ressources):
        uf.find(("c", i))
        for r in rs:
            uf.union(("c", i), ("r", r))
            par_ressource[r].append(i)
    degre = {r: len(v) for r, v in par_ressource.items()}
    composantes = defaultdict(list)
    for i in range(len(ressources)):
        composantes[uf.find(("c", i))].append(i)

    choix, optimal = [], True
    for indices in composantes.values():
        if len(indices) == 1:
            choix.extend(indices)
            continue
        sel = _glouton(indices, poids, ressources, capacite, degre)
        sel = _amelioration_locale(indices, poids, ressources, capacite, par_ressource, sel,
                                   echeance=echeance)
        if len(indices) <= taille_exacte:
            sel, prouve = _exact(indices, poids, ressources, capacite, sel, limite_noeuds)
            optimal &= prouve
        else:
            optimal = False
        choix.extend(sel)
    return choix, optimal
