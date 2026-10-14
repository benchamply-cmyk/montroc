"""Version simple : chercher les boucles de 2 et 3 autour d'un utilisateur."""
from __future__ import annotations

from itertools import product

from .graphe import GrapheEchanges
from .modele import Boucle, Contraintes, Marche


def options_du_cycle(graphe: GrapheEchanges, cycle_users) -> list[list]:
    """Pour chaque étape k du cycle, les transferts possibles de ``cycle_users[k]`` vers le suivant."""
    n = len(cycle_users)
    return [graphe.transferts[(cycle_users[k], cycle_users[(k + 1) % n])] for k in range(n)]


def _combinaisons(graphe: GrapheEchanges, cycle_users, options: int):
    """Toutes les façons de réaliser un cycle d'utilisateurs avec des objets
    concrets, en gardant les ``options`` meilleurs objets par transfert.
    Les combinaisons qui violent une liste stricte « contre » sont écartées."""
    listes = [o[:options] for o in options_du_cycle(graphe, cycle_users)]
    for choix in product(*listes):
        if graphe.marche.boucle_admise(choix):
            yield graphe.marche.creer_boucle(choix)


def cycles_utilisateurs(graphe: GrapheEchanges, longueur_max: int = 3, autour: str | None = None):
    """Les cycles de 2 à ``longueur_max`` (2 ou 3) personnes du graphe, sans
    choisir les objets. Avec ``autour``, seulement ceux qui contiennent cet
    utilisateur (en premier) ; sinon tous, chacun une seule fois."""
    if longueur_max not in (2, 3):
        raise ValueError("longueur_max doit valoir 2 ou 3 (boucles limitées à 3 au lancement).")
    succ = graphe.succ
    utilisateurs = list(graphe.marche.utilisateurs)
    ordre = {u: i for i, u in enumerate(utilisateurs)}
    departs = [autour] if autour is not None else utilisateurs

    for u in departs:
        for v in succ.get(u, ()):
            if autour is None and ordre[v] < ordre[u]:
                continue
            if u in succ.get(v, ()):
                yield (u, v)
            if longueur_max < 3:
                continue
            for w in succ.get(v, ()):
                if w == u or (autour is None and ordre[w] < ordre[u]):
                    continue
                if u in succ.get(w, ()):
                    yield (u, v, w)


def enumerer_boucles(graphe: GrapheEchanges, longueur_max: int = 3, options_par_transfert: int = 2,
                     autour: str | None = None):
    """Énumère les boucles de longueur 2 à ``longueur_max`` (2 ou 3).

    Avec ``autour``, seulement celles qui contiennent cet utilisateur ; sinon
    toutes, chacune une seule fois.
    """
    for cycle in cycles_utilisateurs(graphe, longueur_max, autour):
        yield from _combinaisons(graphe, cycle, options_par_transfert)


def cle_classement(b: Boucle):
    """Plus sûre d'abord, puis plus courte, puis souhaits les mieux classés, puis
    préférences « contre » respectées."""
    return (-b.proba_reussite, b.longueur, b.somme_rangs, -b.preferences_respectees, b.objets)


def boucles_autour(marche: Marche, utilisateur: str, longueur_max: int = 3, limite: int | None = 10,
                   options_par_transfert: int = 3, contraintes: Contraintes | None = None) -> list[Boucle]:
    """Les meilleures boucles (2 et 3 personnes) qui incluent ``utilisateur``,
    classées par chance de réussite. C'est ce que l'app propose à quelqu'un
    qui ouvre « Mes échanges possibles »."""
    if utilisateur not in marche.utilisateurs:
        raise KeyError(f"Utilisateur inconnu : {utilisateur!r}")
    graphe = GrapheEchanges(marche, contraintes)
    boucles = sorted(enumerer_boucles(graphe, longueur_max, options_par_transfert, autour=utilisateur),
                     key=cle_classement)
    return boucles if limite is None else boucles[:limite]
