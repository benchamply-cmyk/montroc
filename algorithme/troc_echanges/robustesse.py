"""Rendre les boucles robustes aux refus (section 2 de l'étude).

Une boucle ne se réalise que si tout le monde dit oui. Quand quelqu'un
refuse ou ne répond pas dans les 48 h, on garde les boucles déjà acceptées
et on cherche aussitôt des remplacements pour les autres participants.
"""
from __future__ import annotations

from .boucles import boucles_autour
from .math_trade import Solution, math_trade
from .modele import Boucle, Contraintes, Marche


def proba_tous_acceptent(p: float, longueur: int) -> float:
    """Avec 70 % d'acceptation : 49 % pour 2, 34 % pour 3, 24 % pour 4."""
    return p ** longueur


def contraintes_apres_refus(boucles_maintenues: list[Boucle],
                            refus: list[tuple[Boucle, str]],
                            base: Contraintes | None = None) -> Contraintes:
    """Construit les contraintes d'une nouvelle recherche :
    - les objets et souhaits des boucles maintenues sont réservés ;
    - pour chaque refus (boucle, utilisateur qui refuse), seul le transfert
      que cet utilisateur devait recevoir est interdit. Il reste disponible
      pour d'autres boucles, et les autres participants sont libérés.
    """
    c = Contraintes(
        objets_indisponibles=set(base.objets_indisponibles) if base else set(),
        souhaits_consommes=dict(base.souhaits_consommes) if base else {},
        transferts_refuses=set(base.transferts_refuses) if base else set(),
        utilisateurs_exclus=set(base.utilisateurs_exclus) if base else set(),
    )
    for b in boucles_maintenues:
        c.engager(b)
    for boucle, refusant in refus:
        recus = [t for t in boucle.transferts if t.receveur == refusant]
        if not recus:
            raise ValueError(f"{refusant!r} ne participe pas à cette boucle.")
        for t in recus:
            c.transferts_refuses.add(t.cle)
    return c


def replanifier(marche: Marche, boucles_maintenues: list[Boucle], refus: list[tuple[Boucle, str]],
                longueur_max: int = 3, contraintes: Contraintes | None = None, **options) -> Solution:
    """Nouvelle passe de math trade sur ce qui n'est pas engagé, après refus."""
    c = contraintes_apres_refus(boucles_maintenues, refus, contraintes)
    return math_trade(marche, longueur_max=longueur_max, contraintes=c, **options)


def remplacants(marche: Marche, boucle: Boucle, refusant: str, boucles_maintenues: list[Boucle] = (),
                limite: int = 3, contraintes: Contraintes | None = None) -> dict[str, list[Boucle]]:
    """Pour chaque participant lâché par ``refusant``, les meilleures boucles
    de remplacement immédiates (version « autour d'un utilisateur »)."""
    c = contraintes_apres_refus(list(boucles_maintenues), [(boucle, refusant)], contraintes)
    return {p: boucles_autour(marche, p, limite=limite, contraintes=c)
            for p in boucle.participants if p != refusant}
