"""Graphe des échanges possibles : un arc v → u existe si v possède un objet
qui correspond à un souhait de u (v peut donner à u).

Un objet n'y entre que s'il est disponible, et un transfert que si la
logistique suit : un mode d'échange commun (``Souhait.correspond``) et le lieu
de l'objet dans une zone acceptée par le receveur."""
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
            if not o.disponible or o.id in c.objets_indisponibles or o.proprietaire in c.utilisateurs_exclus:
                continue
            disponibles[o.id] = o
            par_categorie[o.categorie].append(o)

        # transferts[(donneur, receveur)] : options triées, la meilleure d'abord, un objet une seule fois (au
        # titre du meilleur souhait du receveur) : pour énumérer des boucles d'objets sans doublons.
        self.transferts: dict[tuple[str, str], list[Transfert]] = defaultdict(list)
        # variantes[(donneur, receveur)] : en plus, l'objet au titre de chaque autre souhait du receveur qu'il
        # remplit. Si le meilleur souhait est déjà servi, l'objet peut encore en combler un autre : les moteurs
        # exacts (CP-SAT, flot) choisissent parmi les variantes pour ne rater aucun échange.
        self.variantes: dict[tuple[str, str], list[Transfert]] = defaultdict(list)
        for u in marche.utilisateurs.values():
            if u.id in c.utilisateurs_exclus:
                continue
            vus = {}  # un même objet ne compte qu'une fois par receveur (meilleur souhait)
            for i, s in enumerate(u.souhaits):
                if (u.id, i) not in self.capacite_souhait:
                    continue
                if s.objet_id is not None:
                    candidats = [disponibles[s.objet_id]] if s.objet_id in disponibles else []
                elif s.objets:
                    candidats = [disponibles[x] for x in sorted(s.objets) if x in disponibles]
                else:
                    candidats = [o for cat in sorted(s.categories_visees())
                                 for o in par_categorie.get(cat, []) if s.correspond(o)]
                for o in candidats:
                    if o.proprietaire == u.id:
                        continue
                    if (o.proprietaire, o.id, u.id) in c.transferts_refuses:
                        continue
                    if not self._zone_acceptee(o, s, u.id):
                        continue
                    t = Transfert(
                        donneur=o.proprietaire, receveur=u.id, objet=o, souhait_idx=i,
                        rang=s.rang, auto=s.acceptation_auto,
                        proba_acceptation=marche.p_auto if s.acceptation_auto else marche.p_acceptation_de(u),
                        qualite=s.qualite(o), souhait_ref=s.ref,
                    )
                    self.variantes[(t.donneur, t.receveur)].append(t)
                    precedent = vus.get(o.id)
                    if precedent is None or self._ordre(t) < self._ordre(precedent):
                        vus[o.id] = t
            for t in vus.values():
                self.transferts[(t.donneur, t.receveur)].append(t)

        self.succ: dict[str, set[str]] = defaultdict(set)
        for (v, u), options in self.transferts.items():
            options.sort(key=self._ordre)
            self.succ[v].add(u)
        for options in self.variantes.values():
            options.sort(key=self._ordre)

    def _zone_acceptee(self, objet, souhait, receveur: str) -> bool:
        """L'objet peut-il parvenir au receveur ? S'il a choisi des zones d'intérêt (ou toute la France) : l'objet
        dans une de ses zones, sinon par colis si le souhait et l'objet l'acceptent (``Utilisateur.acces``).
        Sinon, par noms de zones : le lieu de l'objet (le sien, sinon la zone de son propriétaire) dans une zone
        acceptée ; lieu inconnu : accepté ; sans zones précisées sur le souhait, même zone que le receveur
        (si ``Marche.meme_zone``)."""
        u = self.marche.utilisateurs[receveur]
        if u.zones_geographiques and not souhait.zones:
            acces = u.acces(objet)
            if acces == "loin":
                return souhait.accepte_le_colis() and objet.accepte_le_colis()
            return acces is not None
        zone = objet.zone or self.marche.utilisateurs[objet.proprietaire].zone
        if zone is None:
            return True
        if souhait.zones:
            return zone in souhait.zones
        za = self.marche.utilisateurs[receveur].zone
        return not self.marche.meme_zone or za is None or za == zone

    @staticmethod
    def _ordre(t: Transfert):
        return (not t.auto, t.rang, -t.qualite, t.objet.id)

    def tous_les_transferts(self, variantes: bool = False):
        """Tous les transferts ; avec ``variantes``, un objet au titre de chacun des souhaits qu'il remplit."""
        for options in (self.variantes if variantes else self.transferts).values():
            yield from options
