"""Algorithme d'échanges de Troc : boucles d'échanges sans prix ni monnaie.

- ``boucles_autour`` : version simple, boucles de 2, 3 personnes ou plus autour d'un utilisateur ;
- ``math_trade`` : maximum d'échanges sur tout le marché, façon TradeMaximizer
  (solveur exact CP-SAT si OR-Tools est installé) ;
- ``replanifier`` / ``remplacants`` : relancer après un refus.
"""
from . import solveur_exact
from .boucles import boucles_autour, enumerer_boucles
from .graphe import GrapheEchanges
from .math_trade import Solution, math_trade
from .modele import ETATS, MODES_RECHERCHE, Boucle, Contraintes, Marche, Objet, Souhait, Transfert, Utilisateur
from .robustesse import contraintes_apres_refus, proba_tous_acceptent, remplacants, replanifier

__all__ = [
    "ETATS", "MODES_RECHERCHE", "Boucle", "Contraintes", "GrapheEchanges", "Marche", "Objet", "Solution", "Souhait",
    "Transfert", "Utilisateur", "boucles_autour", "contraintes_apres_refus", "enumerer_boucles",
    "math_trade", "proba_tous_acceptent", "remplacants", "replanifier", "solveur_exact",
]
