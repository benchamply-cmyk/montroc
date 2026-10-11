"""Flot de coût minimal (primal-dual : Dijkstra + flot bloquant), sans dépendance.

Utilisé par le mode « TradeMaximizer » sans limite de longueur de boucle.
"""
from __future__ import annotations

import heapq
from collections import deque


class FlotCoutMin:
    def __init__(self, n: int):
        self.n = n
        self.g: list[list[int]] = [[] for _ in range(n)]
        # arcs stockés à plat : to, cap, cost ; l'arc inverse de e est e ^ 1
        self.to: list[int] = []
        self.cap: list[int] = []
        self.cost: list[int] = []

    def ajouter_arc(self, u: int, v: int, cap: int, cost: int) -> int:
        e = len(self.to)
        self.to += [v, u]
        self.cap += [cap, 0]
        self.cost += [cost, -cost]
        self.g[u].append(e)
        self.g[v].append(e + 1)
        return e

    def flot(self, e: int) -> int:
        return self.cap[e ^ 1]

    def resoudre(self, s: int, t: int) -> tuple[int, int]:
        """Flot maximal de coût minimal de s à t. Coûts résiduels initiaux >= 0
        exigés. Renvoie (flot, coût)."""
        n, g, to, cap, cost = self.n, self.g, self.to, self.cap, self.cost
        pot = [0] * n
        INF = float("inf")
        total_flot = total_cout = 0
        while True:
            # Dijkstra sur les coûts réduits
            dist = [INF] * n
            dist[s] = 0
            tas = [(0, s)]
            while tas:
                d, u = heapq.heappop(tas)
                if d > dist[u]:
                    continue
                for e in g[u]:
                    if cap[e] > 0:
                        v = to[e]
                        nd = d + cost[e] + pot[u] - pot[v]
                        if nd < dist[v]:
                            dist[v] = nd
                            heapq.heappush(tas, (nd, v))
            if dist[t] == INF:
                break
            for v in range(n):
                if dist[v] < INF:
                    pot[v] += dist[v]
            # Flot bloquant (Dinic) sur les arcs de coût réduit nul
            while True:
                niveau = [-1] * n
                niveau[s] = 0
                file = deque([s])
                while file:
                    u = file.popleft()
                    for e in g[u]:
                        v = to[e]
                        if cap[e] > 0 and niveau[v] < 0 and cost[e] + pot[u] - pot[v] == 0:
                            niveau[v] = niveau[u] + 1
                            file.append(v)
                if niveau[t] < 0:
                    break
                it = [0] * n
                while True:
                    pousse = self._augmenter(s, t, niveau, it, pot)
                    if not pousse:
                        break
                    total_flot += pousse
                    total_cout += pousse * (pot[t] - pot[s])
        return total_flot, total_cout

    def _augmenter(self, s, t, niveau, it, pot):
        """Trouve un chemin admissible (DFS itératif) et pousse son goulot."""
        g, to, cap, cost = self.g, self.to, self.cap, self.cost
        chemin = []  # arcs
        u = s
        while u != t:
            avance = False
            while it[u] < len(g[u]):
                e = g[u][it[u]]
                v = to[e]
                if cap[e] > 0 and niveau[v] == niveau[u] + 1 and cost[e] + pot[u] - pot[v] == 0:
                    chemin.append(e)
                    u = v
                    avance = True
                    break
                it[u] += 1
            if not avance:
                if u == s:
                    return 0
                niveau[u] = -1  # impasse
                e = chemin.pop()
                u = to[e ^ 1]
                it[u] += 1
        goulot = min(cap[e] for e in chemin)
        for e in chemin:
            cap[e] -= goulot
            cap[e ^ 1] += goulot
        return goulot
