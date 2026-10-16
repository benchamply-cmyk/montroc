"""Graphe des échanges possibles : un arc v → u existe si v possède un objet
qui correspond à un souhait de u (v peut donner à u)."""
from __future__ import annotations

from collections import defaultdict

from .modele import Contraintes, Marche, Transfert


class GrapheEchanges:
    def __init__(self, marche: Marche, contraintes: Contraintes | None = None):
        self.marche = marche
        self.contraintes = contraintes or Contraintes()
        c = self.contraintes

        # Capacité restante de chaque souhait (quantité - déjà engagé)
        self.capacite_souhait: dict[tuple[str, int], int] = {}
        for u in marche.utilisateurs.values():
            for i, s in enumerate(u.souhaits):
                reste = s.quantite - c.souhaits_consommes.get((u.id, i), 0)
                if reste > 0:
                    self.capacite_souhait[(u.id, i)] = reste

        # Index des objets disponibles
        par_categorie: dict[str, list] = defaultdict(list)
        disponibles = {}
        for o in marche.objets.values():
            if o.id in c.objets_indisponibles or o.proprietaire in c.utilisateurs_exclus:
                continue
            disponibles[o.id] = o
            par_categorie[o.categorie].append(o)

        # transferts[(donneur, receveur)] : options triées, la meilleure d'abord
        self.transferts: dict[tuple[str, str], list[Transfert]] = defaultdict(list)
        for u in marche.utilisateurs.values():
            if u.id in c.utilisateurs_exclus:
                continue
            vus = {}  # un même objet ne compte qu'une fois par receveur (meilleur souhait)
            for i, s in enumerate(u.souhaits):
                if (u.id, i) not in self.capacite_souhait:
                    continue
                if s.objet_id is not None:
                    candidats = [disponibles[s.objet_id]] if s.objet_id in disponibles else []
                else:
                    candidats = [o for o in par_categorie.get(s.categorie, []) if s.correspond(o)]
                for o in candidats:
                    if o.proprietaire == u.id:
                        continue
                    if (o.proprietaire, o.id, u.id) in c.transferts_refuses:
                        continue
                    if marche.meme_zone and not self._meme_zone(o.proprietaire, u.id):
                        continue
                    t = Transfert(
                        donneur=o.proprietaire, receveur=u.id, objet=o, souhait_idx=i,
                        rang=s.rang, auto=s.acceptation_auto,
                        proba_acceptation=marche.p_auto if s.acceptation_auto else marche.p_acceptation,
                    )
                    precedent = vus.get(o.id)
                    if precedent is None or self._ordre(t) < self._ordre(precedent):
                        vus[o.id] = t
            for t in vus.values():
                self.transferts[(t.donneur, t.receveur)].append(t)

        self.succ: dict[str, set[str]] = defaultdict(set)
        for (v, u), options in self.transferts.items():
            options.sort(key=self._ordre)
            self.succ[v].add(u)

    def _meme_zone(self, a: str, b: str) -> bool:
        za = self.marche.utilisateurs[a].zone
        zb = self.marche.utilisateurs[b].zone
        return za is None or zb is None or za == zb

    @staticmethod
    def _ordre(t: Transfert):
        return (not t.auto, t.rang, t.objet.id)

    def tous_les_transferts(self):
        for options in self.transferts.values():
            yield from options
