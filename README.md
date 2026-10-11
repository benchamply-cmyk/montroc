# montroc

L'alternative montroc : échanger des objets **sans prix ni monnaie**. Chacun dit ce qu'il a et ce qui lui serait utile, et Troc trouve l'échange, même en boucle à trois.

Site prévu : [montroc.fr](https://montroc.fr)

## Contenu du dépôt

| Dossier | Contenu |
|---|---|
| [`web/`](web/) | La version web minimaliste : une seule page HTML autonome (accueil, mes listes, échanges proposés, dépôt sécurisé). Maquette interactive, sans serveur ni base de données. |
| [`algorithme/`](algorithme/) | Le moteur d'échanges en Python (bibliothèque standard uniquement) : boucles autour d'un utilisateur, « math trade » à l'échelle d'une ville, gestion des refus. Voir son [README](algorithme/README.md). |

## Voir le site en local

Ouvrir `web/index.html` dans un navigateur, ou :

```
cd web
python3 -m http.server 8000
# puis http://localhost:8000
```

Le dossier `web/` peut être publié tel quel sur n'importe quel hébergement statique (GitHub Pages, Netlify, OVH…) pour montroc.fr.

## Lancer l'algorithme

Python 3.10 ou plus récent, aucune dépendance.

```
cd algorithme
python3 exemple.py                      # démonstration commentée
python3 -m unittest discover -s tests   # 20 tests
python3 benchmark.py 1000 2000 5000     # banc d'essai « ville »
```

## Prochaines étapes

- Relier la page web à l'algorithme (petite API qui appelle `boucles_autour` et `math_trade`).
- Comptes utilisateurs, photos des objets, notifications d'acceptation sous 48 h.
- Brancher le nom de domaine montroc.fr sur l'hébergement choisi.
