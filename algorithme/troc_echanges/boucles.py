"""Version simple : chercher les boucles (2, 3, 4 personnes ou plus) autour d'un utilisateur."""
from __future__ import annotations

from itertools import product

from .graphe import GrapheEchanges
from .modele import Boucle, Contraintes, Marche


def options_du_cycle(graphe: GrapheEchanges, cycle_users, variantes: bool = False) -> list[list]:
    """Pour chaque étape k du cycle, les transferts possibles de ``cycle_users[k]`` vers le suivant
    (avec ``variantes``, un objet au titre de chacun des souhaits qu'il remplit, voir ``GrapheEchanges``)."""
    n = len(cycle_users)
    source = graphe.variantes if variantes else graphe.transferts
    return [source[(cycle_users[k], cycle_users[(k + 1) % n])] for k in range(n)]


def _combinaisons(graphe: GrapheEchanges, cycle_users, options: int, variantes: bool = False):
    """Toutes les façons de réaliser un cycle d'utilisateurs avec des objets
    concrets, en gardant les ``options`` meilleurs objets par transfert.
    Les combinaisons qui violent une liste stricte « contre » sont écartées."""
    listes = [o[:options] for o in options_du_cycle(graphe, cycle_users, variantes)]
    for choix in product(*listes):
        if graphe.marche.boucle_admise(choix):
            yield graphe.marche.creer_boucle(choix)


# Au-delà, les boucles deviennent trop fragiles (un refus fait tout tomber) et trop longues à énumérer.
LONGUEUR_MAX_ABSOLUE = 6


class TropDeCycles(Exception):
    """Le budget d'exploration de ``cycles_utilisateurs`` est épuisé."""


def cycles_utilisateurs(graphe: GrapheEchanges, longueur_max: int = 3, autour: str | None = None,
                        budget: int | None = None):
    """Les cycles de 2 à ``longueur_max`` personnes du graphe, sans choisir les
    objets. Avec ``autour``, seulement ceux qui contiennent cet utilisateur (en
    premier) ; sinon tous, chacun une seule fois (il commence par la personne
    la plus ancienne du marché).

    ``budget`` : nombre de chemins explorés au plus ; au-delà, ``TropDeCycles``.
    """
    if not 2 <= longueur_max <= LONGUEUR_MAX_ABSOLUE:
        raise ValueError(f"longueur_max doit valoir de 2 à {LONGUEUR_MAX_ABSOLUE}.")
    succ = graphe.succ
    ordre = {u: i for i, u in enumerate(graphe.marche.utilisateurs)}
    departs = [autour] if autour is not None else list(ordre)
    restant = [budget]

    def prolonger(chemin, dans_chemin):
        u, dernier = chemin[0], chemin[-1]
        for v in succ.get(dernier, ()):
            if v in dans_chemin or (autour is None and ordre[v] < ordre[u]):
                continue
            if restant[0] is not None:
                restant[0] -= 1
                if restant[0] < 0:
                    raise TropDeCycles
            chemin.append(v)
            if u in succ.get(v, ()):
                yield tuple(chemin)
            if len(chemin) < longueur_max:
                dans_chemin.add(v)
                yield from prolonger(chemin, dans_chemin)
                dans_chemin.discard(v)
            chemin.pop()

    for u in departs:
        yield from prolonger([u], {u})


def longueur_calculable(graphe: GrapheEchanges, voulue: int, budget: int) -> int:
    """La plus grande longueur de boucle, jusqu'à ``voulue``, dont l'énumération tient dans ``budget``
    chemins explorés ; jamais moins de 3 (ni de ``voulue``), la longueur du lancement."""
    plancher = min(voulue, 3)
    for k in range(voulue, plancher, -1):
        try:
            for _ in cycles_utilisateurs(graphe, k, budget=budget):
                pass
            return k
        except TropDeCycles:
            continue
    return plancher


def enumerer_boucles(graphe: GrapheEchanges, longueur_max: int = 3, options_par_transfert: int = 2,
                     autour: str | None = None, variantes: bool = False):
    """Énumère les boucles de longueur 2 à ``longueur_max``.

    Avec ``autour``, seulement celles qui contiennent cet utilisateur ; sinon
    toutes, chacune une seule fois. Avec ``variantes``, un objet y figure au
    titre de chacun des souhaits du receveur qu'il remplit.
    """
    for cycle in cycles_utilisateurs(graphe, longueur_max, autour):
        yield from _combinaisons(graphe, cycle, options_par_transfert, variantes)


def cle_classement(b: Boucle):
    """Plus sûre d'abord, puis plus courte, puis souhaits les mieux classés, puis
    meilleure qualité (objets visés, critères préférentiels, préférences « contre »)."""
    return (-b.proba_reussite, b.longueur, b.somme_rangs, -b.qualite, b.objets)


def boucles_autour(marche: Marche, utilisateur: str, longueur_max: int = 3, limite: int | None = 10,
                   options_par_transfert: int = 3, contraintes: Contraintes | None = None) -> list[Boucle]:
    """Les meilleures boucles (2 à ``longueur_max`` personnes) qui incluent ``utilisateur``,
    classées par chance de réussite. C'est ce que l'app propose à quelqu'un
    qui ouvre « Mes échanges possibles »."""
    if utilisateur not in marche.utilisateurs:
        raise KeyError(f"Utilisateur inconnu : {utilisateur!r}")
    graphe = GrapheEchanges(marche, contraintes)
    boucles = sorted(enumerer_boucles(graphe, longueur_max, options_par_transfert, autour=utilisateur),
                     key=cle_classement)
    return boucles if limite is None else boucles[:limite]
