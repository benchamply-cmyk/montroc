"""Banc d'essai à l'échelle d'une ville, sur le « scénario prudent » de l'étude
(section 5) : 20 000 types d'objets (loi de popularité), 5 objets et 5
souhaits par personne, 20 % de chances d'accepter un objet de la bonne catégorie.

Mesure, pour chaque taille de ville :
- la part d'utilisateurs pour qui une boucle de 3 au plus *existe*
  (ce que mesurait la simulation de l'étude) ;
- la part qui obtient réellement un échange dans le math trade, où chaque
  objet ne part qu'une fois (toujours plus basse) ;
- le temps de calcul.

Lancer : python3 benchmark.py [tailles...]   (ex. python3 benchmark.py 500 1000 2000)
"""
import random
import sys
import time

from troc_echanges import GrapheEchanges, Marche, Souhait, enumerer_boucles, math_trade


def ville(n, types=20000, s=0.8, objets=5, souhaits=5, p=0.2, seed=1):
    rnd = random.Random(seed)
    poids = [1 / (k + 1) ** s for k in range(types)]
    m = Marche(meme_zone=False)
    detient, veut = [], []
    for u in range(n):
        detient.append(set(rnd.choices(range(types), poids, k=objets)))
        veut.append(set(rnd.choices(range(types), poids, k=souhaits)))
    par_type = {}
    for u in range(n):
        for k, c in enumerate(detient[u]):
            par_type.setdefault(c, []).append(f"o{u}_{k}")
    for u in range(n):
        # « J'accepte cet objet précis » avec probabilité p (état, taille, goût)
        ws = [Souhait(objet_id=o) for c in veut[u] for o in par_type.get(c, ())
              if not o.startswith(f"o{u}_") and rnd.random() < p]
        m.ajouter_utilisateur(f"u{u}", ws)
    for u in range(n):
        for k, c in enumerate(detient[u]):
            m.ajouter_objet(f"o{u}_{k}", f"u{u}", f"t{c}")
    return m


def main(tailles):
    print(f"{'utilisateurs':>12} | {'boucle ≤3 existe':>16} | {'échange obtenu':>14} | "
          f"{'objets échangés':>15} | {'boucles candidates':>18} | {'temps':>7}")
    for n in tailles:
        m = ville(n)
        g = GrapheEchanges(m)
        existe = {p for b in enumerer_boucles(g, 3, options_par_transfert=1) for p in b.participants}
        t = time.perf_counter()
        sol = math_trade(m, longueur_max=3)
        duree = time.perf_counter() - t
        print(f"{n:>12} | {len(existe) / n:>16.0%} | {len(sol.participants) / n:>14.0%} | "
              f"{sol.nb_objets_echanges:>15} | {sol.candidats:>18} | {duree:>6.1f}s")


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]] or [500, 1000, 2000, 5000])
