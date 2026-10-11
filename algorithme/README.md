# Algorithme d'échanges Troc

Module Python sans dépendance (Python 3.10+, bibliothèque standard uniquement) qui trouve des échanges **sans prix ni monnaie** : chaque utilisateur publie des objets disponibles et liste ce qui lui serait utile ; l'algorithme cherche des **boucles** où chacun donne un objet et en reçoit un.

```
cd algorithme
python3 exemple.py                      # démonstration commentée
python3 -m unittest discover -s tests   # 20 tests, ~13 s
python3 benchmark.py 1000 2000 5000     # banc d'essai « ville »
```

## Les trois briques

| Brique | Fonction | À quoi ça sert dans l'app |
|---|---|---|
| **Version simple** | `boucles_autour(marche, "Alice")` | Écran « Mes échanges possibles » : les boucles de 2 et 3 personnes qui incluent Alice, classées par chance de réussite. Instantané. |
| **Math trade** (TradeMaximizer) | `math_trade(marche, longueur_max=3)` | Passe globale (par ex. chaque nuit) : le **nombre maximal d'objets échangés** sur toute la ville, chaque objet ne partant qu'une fois. |
| **Robustesse** | `remplacants(...)`, `replanifier(...)` | Quand quelqu'un refuse ou ne répond pas en 48 h : on garde les boucles acceptées et on cherche aussitôt un remplaçant pour les autres. |

## Modèle

```python
from troc_echanges import Marche, Souhait, math_trade

m = Marche(p_acceptation=0.7, p_auto=0.95)
m.ajouter_utilisateur("Alice", [Souhait(categorie="siege-auto", acceptation_auto=True)], zone="Lyon")
m.ajouter_objet("p1", "Alice", "poussette", "Poussette Yoyo")
...
sol = math_trade(m, longueur_max=3)
for b in sol.boucles:
    print(b.decrire())
```

Un `Souhait` porte :
- soit sur une **catégorie** (souhait large, ce que l'étude recommande de pousser), soit sur un **objet précis** (`objet_id`) ;
- un **rang** (1 = préféré), qui départage comme les listes ordonnées de TradeMaximizer ;
- une **quantité** (par défaut 1 : on ne reçoit pas trois poussettes pour un seul souhait) ;
- la case **acceptation automatique** (« j'accepte d'office un échange contre cet objet »), qui fait monter la chance de réussite de 70 % à 95 % par défaut.

Un utilisateur a une **zone** (les échanges restent dans la même ville si `meme_zone=True`) et une **fiabilité** (0 à 1, à relier à la réputation) qui entre dans l'estimation de réussite.

La chance de réussite d'une boucle est le produit des acceptations de chaque participant : 49 % pour un échange à 2, 34 % pour une boucle à 3 avec 70 % d'acceptation, comme dans l'étude.

## Le math trade, en détail

Comme TradeMaximizer sur BoardGameGeek, on cherche le **maximum d'échanges simultanés**, sous forme de boucles, avec deux modes :

1. **`longueur_max=3` (mode de lancement)**. On énumère toutes les boucles de 2 et 3 personnes, puis on choisit le meilleur ensemble compatible (un objet ne part qu'une fois, la quantité de chaque souhait est respectée). Le problème se découpe en groupes indépendants :
   - groupe petit (≤ 400 boucles candidates) : **solution exacte**, prouvée optimale ;
   - groupe grand : algorithme glouton puis amélioration locale, dans un budget de temps (`duree_max_s`, 10 s par défaut). `sol.optimal` dit si l'optimum est prouvé.
2. **`longueur_max=None` (TradeMaximizer pur)**. Boucles de longueur illimitée, résolu **exactement** par un flot de coût minimal, comme le vrai TradeMaximizer : maximum d'objets échangés, puis préférence aux souhaits les mieux classés. Utile pour comparer et mesurer ce qu'on perd en limitant à 3 (les boucles obtenues sont souvent très longues, donc irréalistes au lancement).

Deux objectifs pour le mode borné :
- `objectif="echanges"` (défaut) : maximum d'objets échangés, à égalité la solution la plus sûre ;
- `objectif="esperance"` : maximum d'objets échangés **attendus** une fois les refus pris en compte (longueur × chance de réussite). Favorise les échanges directs et les acceptations automatiques.

Autres réglages : `proba_min` (écarter les boucles trop risquées), `options_par_transfert` (combien d'objets différents essayer entre deux mêmes personnes, 2 par défaut).

## Gestion des refus

```python
boucle = sol.boucles[0]
autres = sol.boucles[1:]                         # déjà acceptées : on n'y touche pas
remplacants(m, boucle, "Bruno", autres)          # pour chaque autre participant : ses meilleures boucles de secours
replanifier(m, autres, [(boucle, "Bruno")])      # nouvelle passe de math trade sur ce qui reste libre
```

Seul le transfert que Bruno a refusé est interdit ; Bruno reste disponible pour d'autres boucles, et ses partenaires sont libérés.

## Vérifications faites

- **Optimalité contrôlée par force brute** : sur 40 petits marchés aléatoires, le math trade borné (2 et 3) trouve exactement l'optimum ; sur plus de 50 marchés, le mode illimité aussi.
- Chaque solution est vérifiée : chaque objet part une fois, il correspond bien à un souhait du receveur, les quantités et la limite de longueur sont respectées, chaque boucle se referme.

**Banc d'essai sur le scénario prudent de l'étude** (`benchmark.py`, une seule exécution, graine fixe) :

| Utilisateurs | Boucle ≤ 3 existe | Échange obtenu dans le math trade | Objets échangés | Temps |
|---|---|---|---|---|
| 500 | 23 % | 19 % | 110 | 2 s |
| 1 000 | 34 % | 30 % | 366 | 0,1 s |
| 2 000 | 50 % | 44 % | 1 194 | 1,5 s |
| 5 000 | 76 % | 67 % | 5 295 | 15 s |
| 10 000 | 89 % | 81 % | 14 760 | 49 s |

La colonne « existe » retrouve les chiffres de la simulation de l'étude (16 / 32 / 51 / 71 / 90 %). La colonne « obtenu » est plus basse parce qu'un objet ne peut partir qu'une fois : c'est le chiffre à retenir pour les prévisions. Il faut encore le multiplier par le taux d'acceptation.

## Limites connues

- À 10 000 utilisateurs, le calcul prend environ une minute en Python pur, dont la majeure partie pour énumérer les 400 000 boucles candidates. C'est très bien pour une passe nocturne ; pour du temps réel à cette échelle, il faudra un solveur d'optimisation (OR-Tools, HiGHS) ou un langage compilé.
- Au-delà de 400 boucles candidates par groupe, l'optimum n'est pas prouvé (la solution reste bonne : sur un marché dense de 600 personnes, 1 680 objets échangés en 10 s contre une borne de 1 760 en longueur illimitée).
- Un objet s'échange contre un seul objet. Les offres « plusieurs objets contre un » (offres libres) relèvent d'un autre mécanisme.
- La table des souhaits par objet précis de TradeMaximizer (« ce jeu-ci contre ces jeux-là seulement ») n'est pas reproduite : les souhaits sont par utilisateur, et n'importe lequel de ses objets peut partir.

## Fichiers

- `troc_echanges/modele.py` : objets, souhaits, utilisateurs, boucles, contraintes
- `troc_echanges/graphe.py` : graphe « qui peut donner à qui »
- `troc_echanges/boucles.py` : version simple, boucles de 2 et 3 autour d'un utilisateur
- `troc_echanges/math_trade.py` : maximum d'échanges (borné et illimité)
- `troc_echanges/empaquetage.py` : choix du meilleur ensemble de boucles compatibles
- `troc_echanges/flot.py` : flot de coût minimal (mode illimité)
- `troc_echanges/robustesse.py` : refus, remplaçants, replanification
- `exemple.py`, `benchmark.py`, `tests/test_troc.py`
