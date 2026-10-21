# Algorithme d'échanges Troc

Module Python sans dépendance obligatoire (Python 3.10+ ; [OR-Tools](https://developers.google.com/optimization) en option pour le solveur exact, `pip install "./algorithme[exact]"`) qui trouve des échanges **sans prix ni monnaie** : chaque utilisateur publie des objets disponibles et liste ce qui lui serait utile ; l'algorithme cherche des **boucles** où chacun donne un objet et en reçoit un.

```
cd algorithme
python3 exemple.py                      # démonstration commentée
python3 -m unittest discover -s tests   # 26 tests, ~20 s (3 sautés sans OR-Tools)
python3 benchmark.py 1000 2000 5000     # banc d'essai « ville »
```

## Les trois briques

| Brique | Fonction | À quoi ça sert dans l'app |
|---|---|---|
| **Version simple** | `boucles_autour(marche, "Alice")` | Écran « Mes échanges possibles » : les boucles de 2 et 3 personnes qui incluent Alice, classées par chance de réussite. Instantané. |
| **Math trade** (TradeMaximizer) | `math_trade(marche, longueur_max=3)` | Grand Troc du dimanche et repêchage du mardi : le **nombre maximal d'objets échangés** sur toute la ville, chaque objet ne partant qu'une fois. |
| **Robustesse** | `remplacants(...)`, `replanifier(...)` | Quand quelqu'un refuse ou ne répond pas en 48 h : on garde les boucles acceptées et on cherche aussitôt un remplaçant pour les autres. |

## Modèle

```python
from troc_echanges import Marche, Souhait, math_trade

m = Marche(p_acceptation=0.7, p_auto=0.95)
m.ajouter_utilisateur("Alice", [Souhait(categorie="siege-auto", acceptation_auto=True)], zone="Marseille")
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
- une **référence** libre (`ref`, le numéro du souhait en base pour l'API), reprise par chaque transfert qui le sert (`Transfert.souhait_ref`) : l'API compte ainsi ce qu'un souhait a déjà reçu et le passe au moteur dans `Contraintes.souhaits_consommes`.

Un objet peut porter une liste **« je le donne contre… »** (`contre`, des indices de souhaits de son propriétaire), comme les listes par objet de BoardGameGeek (« ce jeu contre A ou B ») :
- `contre_strict=True` : l'objet ne part que si son propriétaire reçoit, dans la même boucle, un de ces souhaits ;
- `contre_strict=False` : simple préférence ; à défaut, l'objet part contre n'importe lequel de ses souhaits, comme sans liste.

```python
m.ajouter_utilisateur("Alice", [Souhait(categorie="siege-auto"), Souhait(categorie="livres")])
m.ajouter_objet("p1", "Alice", "poussette", contre={0}, contre_strict=True)   # seulement contre un siège auto
```

Un utilisateur a une **zone** (les échanges restent dans la même ville si `meme_zone=True`), une **fiabilité** (0 à 1, à relier à la réputation) qui entre dans l'estimation de réussite, et une **priorité** d'équité (1 par défaut, voir plus bas).

### Les dix règles du matching

Celles du document « Catégories et caractéristiques » (section 13), telles que le moteur les applique :

1. **Intercatégories** : seul compte ce que chacun demande ; une boucle peut mêler poussette, perceuse et livre.
2. **Critères obligatoires** : `Souhait.criteres` (paires clé, valeur : taille, marque, modèle…). Un objet de la catégorie du souhait doit indiquer cette valeur (sans tenir compte des majuscules ni des espaces) ; un objet qui ne l'indique pas est écarté. `etat_min` fixe l'état minimum (`ETATS` : correct, bon, très bon, comme neuf, neuf).
3. **Recherche flexible** : `Souhait.alternatives`, d'autres (catégorie, sous-catégorie ou None) acceptées, et `mode` : `"precise"` (l'objet demandé seulement), `"flexible"` (défaut : aussi les alternatives), `"ouverte"` (tout objet de la catégorie du souhait et de celles des alternatives). Les critères ne jugent que les objets de la catégorie du souhait. `Souhait.preferences` : critères **préférentiels**, qui n'écartent rien mais améliorent la qualité.
4. **Boucles de 2, 3, 4 personnes ou plus** (`longueur_max` jusqu'à 6). Au-delà de 3, la longueur baisse si l'énumération dépasse `BUDGET_CYCLES` chemins, puis si le solveur exact manquerait de mémoire, jusqu'à 3. `sol.stats["longueur_max"]` dit celle retenue.
5. **Optimisation** : d'abord le nombre d'objets échangés, puis l'équité, puis la qualité (`Boucle.qualite` : objet visé plutôt qu'alternative, critères préférentiels, préférences « contre »), puis la sûreté.
6. **Exclusivité** : un objet part au plus une fois, un souhait ne reçoit pas plus que sa quantité.
7. **Logistique** : `Objet.modes` et `Souhait.modes` (main propre, point relais ; vide : tous) doivent avoir un mode commun ; le lieu de l'objet (`Objet.zone`, sinon la zone de son propriétaire) doit être dans `Souhait.zones`, ou à défaut dans la zone du receveur.
8. **Disponibilité** : un objet `disponible=False` (réservé, échangé) n'entre pas dans le graphe.
9. **Validation** : le moteur ne fait que proposer ; l'API demande l'accord de chaque participant (sauf « acceptation automatique » cochée d'avance) avant tout dépôt.
10. **Équité** : à nombre d'objets égal, on sert le plus de personnes, chacune comptée avec sa `priorite`. L'API la calcule ainsi, règle publique : 1 + (3 − objets reçus ces 4 dernières semaines), au moins 1.

La chance de réussite d'une boucle est le produit des acceptations de chaque participant : 49 % pour un échange à 2, 34 % pour une boucle à 3 avec 70 % d'acceptation, comme dans l'étude.

## Le math trade, en détail

Comme TradeMaximizer sur BoardGameGeek, on cherche le **maximum d'échanges simultanés**, sous forme de boucles, avec deux modes :

1. **`longueur_max=3` (ou 4, 5, 6 ; le Grand Troc demande 4)**, boucles de 2 à `longueur_max` personnes, avec deux moteurs (`moteur=`) :
   - **`"exact"`** (`solveur_exact.py`, CP-SAT d'OR-Tools) : on énumère les cycles de *personnes* et le solveur choisit les objets, sans en écarter aucun. Objectifs dans l'ordre : le plus d'objets échangés, puis le plus de **personnes différentes servies** (comme `USERS-TRADING` de TradeMaximizer), pondérées par leur priorité d'équité, puis la meilleure qualité, puis les boucles les plus sûres et les souhaits les mieux classés. `sol.optimal` dit si le nombre d'objets est prouvé maximal.
   - **`"heuristique"`** : on énumère les boucles d'objets (au plus `options_par_transfert` objets par couple de personnes), puis on choisit le meilleur ensemble compatible par groupes indépendants : recherche exacte jusqu'à 400 boucles candidates, glouton et amélioration locale au-delà. Elle n'annonce un optimal (`sol.optimal`) que si l'énumération n'a rien écarté : aucun couple de personnes avec plus de `options_par_transfert` objets possibles, aucun objet qui remplit plusieurs souhaits de son receveur (`sol.stats["enumeration_complete"]`).
   - **`"auto"`** (défaut) : l'exact si OR-Tools est installé et si le marché reste sous `solveur_exact.MAX_COPIES_AUTO` (6 000 copies de cycles, environ 2 400 personnes sur le banc d'essai, pour rester sous les 512 Mo de Render gratuit) ; l'heuristique sinon, ou si l'exact ne trouve rien dans le temps imparti (`duree_max_s`, 10 s par défaut).
2. **`longueur_max=None` (TradeMaximizer pur)**. Boucles de longueur illimitée, résolu **exactement** par un flot de coût minimal, comme le vrai TradeMaximizer : maximum d'objets échangés, puis préférence aux souhaits les mieux classés. Utile pour comparer et mesurer ce qu'on perd en limitant à 3 (les boucles obtenues sont souvent très longues, donc irréalistes au lancement).

Deux objectifs pour le mode borné :
- `objectif="echanges"` (défaut) : maximum d'objets échangés, puis les départages ci-dessus ;
- `objectif="esperance"` : maximum d'objets échangés **attendus** une fois les refus pris en compte (longueur × chance de réussite). Favorise les échanges directs et les acceptations automatiques. Les deux moteurs le gèrent ; le moteur exact le prouve optimal (une variable par combinaison de chances d'une boucle, tout reste linéaire). C'est l'objectif du Grand Troc (`OBJECTIF_GRAND_TROC` côté API, `echanges` pour revenir à l'ancien).

Autres réglages : `proba_min` (écarter les boucles trop risquées), `options_par_transfert` (combien d'objets différents essayer entre deux mêmes personnes, 2 par défaut).

**Boucles à 4** (même banc d'essai, `benchmark.ville`, budget 30 s) : à 500 personnes, 176 objets échangés contre 110 avec des boucles de 3 (+60 %), en 3,5 s ; dès 1 000 personnes, le solveur exact dépasserait sa limite de mémoire avec des boucles de 4, le moteur revient donc à 3 (698 objets, 2,2 s).

## Gestion des refus

```python
boucle = sol.boucles[0]
autres = sol.boucles[1:]                         # déjà acceptées : on n'y touche pas
remplacants(m, boucle, "Bruno", autres)          # pour chaque autre participant : ses meilleures boucles de secours
replanifier(m, autres, [(boucle, "Bruno")])      # nouvelle passe de math trade sur ce qui reste libre
```

Seul le transfert que Bruno a refusé est interdit ; Bruno reste disponible pour d'autres boucles, et ses partenaires sont libérés.

## Vérifications faites

- **Optimalité contrôlée par force brute** : sur 40 petits marchés aléatoires, le math trade borné (2 et 3) trouve exactement l'optimum ; sur 30 autres, avec 3 objets par personne et des listes « contre » strictes ou de préférence, le moteur exact aussi ; sur plus de 50 marchés, le mode illimité aussi.
- Cas où l'heuristique se trompe en se disant optimale (deux personnes qui ont chacune 3 objets voulus par l'autre) : elle trouve 4 objets, le moteur exact 6.
- Un objet qui remplit plusieurs souhaits de son receveur (par exemple un siège auto, alternative d'un souhait « poussette » et souhait à part entière) figure une fois par souhait dans `GrapheEchanges.variantes` : le moteur exact et le mode illimité choisissent le souhait à combler. Contrôlé par force brute sur 30 marchés aléatoires à souhaits qui se recouvrent (et plus de 50 en mode illimité).
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

**Moteur exact contre heuristique** (même banc d'essai, budget 30 s, 2 fils) :

| Utilisateurs | Heuristique | Exact | Personnes servies (heur. / exact) |
|---|---|---|---|
| 500 | 110 objets, 2,2 s | 110 objets, **prouvé**, 0,1 s | 95 / 98 |
| 1 000 | 366 objets, 0,1 s | **372**, **prouvé**, 1,6 s | 297 / 303 |
| 2 000 | 1 195 objets, 1,2 s | **1 221**, 26 s, 220 Mo | 881 / 898 |
| 3 000 | 2 356 objets, 11 s | **2 401**, 26 s, 380 Mo | 1 645 / 1 656 (« auto » garde l'heuristique : mémoire) |
| 5 000 | 5 330 objets, 35 s | 5 163 (moins bien, 1 Go de mémoire) | « auto » garde l'heuristique |

## Limites connues

- À 10 000 utilisateurs, l'heuristique prend environ une minute en Python pur, dont la majeure partie pour énumérer les 400 000 boucles candidates ; le moteur exact n'est pas utilisé à cette taille (mémoire). Il faudra alors découper par quartier ou passer à une formulation plus compacte (PICEF).
- Au-delà de 400 boucles candidates par groupe, l'optimum n'est pas prouvé (la solution reste bonne : sur un marché dense de 600 personnes, 1 680 objets échangés en 10 s contre une borne de 1 760 en longueur illimitée).
- Un objet s'échange contre un seul objet. Les offres « plusieurs objets contre un » (offres libres) relèvent d'un autre mécanisme.
- Les listes « contre » choisissent parmi les souhaits de l'utilisateur ; elles ne créent pas de souhait nouveau. Le mode illimité les ignore.

## Fichiers

- `troc_echanges/modele.py` : objets, souhaits, utilisateurs, boucles, contraintes
- `troc_echanges/graphe.py` : graphe « qui peut donner à qui »
- `troc_echanges/boucles.py` : version simple, boucles de 2 et 3 autour d'un utilisateur
- `troc_echanges/math_trade.py` : maximum d'échanges (borné et illimité)
- `troc_echanges/solveur_exact.py` : math trade borné exact (CP-SAT d'OR-Tools)
- `troc_echanges/empaquetage.py` : choix du meilleur ensemble de boucles compatibles
- `troc_echanges/flot.py` : flot de coût minimal (mode illimité)
- `troc_echanges/robustesse.py` : refus, remplaçants, replanification
- `exemple.py`, `benchmark.py`, `tests/test_troc.py`
