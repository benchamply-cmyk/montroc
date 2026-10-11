# Développer en local avec VS Code

## Prérequis (une seule fois)

| Outil | Pour | Installation (macOS) |
|---|---|---|
| Git | récupérer le code | `xcode-select --install` |
| Python 3.12 ou plus | API et moteur | https://www.python.org/downloads/ ou `brew install python@3.12` |
| Docker Desktop | base PostgreSQL locale | https://www.docker.com/products/docker-desktop/ |
| VS Code | éditeur | https://code.visualstudio.com/ |

> Sans Docker : crée une branche `dev` sur Neon et mets sa chaîne de connexion dans `api/.env` (`DATABASE_URL=...`). Les tests, eux, ont besoin d'une base qu'ils peuvent vider : utilise une deuxième branche Neon `test` dans `TEST_DATABASE_URL`.

## Récupérer et installer le projet

```
git clone https://github.com/benchamply-cmyk/montroc.git
cd montroc
code .                 # ouvre VS Code dans le dossier
```

VS Code propose d'installer les **extensions recommandées** (Python, Ruff, SQLTools, Docker, GitLens, Mermaid) : accepte.

Puis, dans le terminal de VS Code (`Ctrl+ù` / `⌃\``) :

```
make installer         # crée .venv et installe le moteur + l'API
cp .env.example api/.env
make base              # démarre PostgreSQL dans Docker
make api               # applique les migrations et lance l'API
```

- API : http://localhost:8001 — documentation interactive : **http://localhost:8001/docs** (on peut y essayer chaque route).
- Site : `make site` puis http://localhost:8000.

Si VS Code demande quel interpréteur Python utiliser : choisis `.venv` (`⌘⇧P` → *Python: Select Interpreter*).

## Se repérer dans le projet

```
montroc/
├── web/                  le site (HTML/CSS/JS) publié par Netlify
├── algorithme/           le moteur d'échanges, Python pur
│   ├── troc_echanges/    modele.py (données), graphe.py, boucles.py, math_trade.py, robustesse.py
│   ├── exemple.py        démonstration commentée : le meilleur point de départ
│   └── tests/
├── api/                  l'API FastAPI (voir docs/01-architecture.md)
├── docs/                 cette documentation
├── .vscode/              réglages, lancements et tâches VS Code partagés
├── .github/              CI et modèle de pull request
├── Makefile              raccourcis (make installer, make api, make tests…)
├── docker-compose.yml    PostgreSQL local
├── netlify.toml          configuration du site en ligne
└── render.yaml           configuration de l'API en ligne
```

Ordre de lecture conseillé pour comprendre : `algorithme/exemple.py` → `algorithme/troc_echanges/modele.py` → `api/src/montroc_api/models.py` → `api/src/montroc_api/services.py` → `api/src/montroc_api/routers/`.

## Lancer, déboguer, tester depuis VS Code

**Exécuter et déboguer** (`⌘⇧D`), configurations prêtes :

| Configuration | Ce qu'elle fait |
|---|---|
| API montroc (débogage) | lance l'API ; un point d'arrêt (clic dans la marge) s'arrête quand une requête passe par là |
| Moteur : exemple commenté | exécute `algorithme/exemple.py` pas à pas |
| Moteur : banc d'essai | mesure le math trade sur 1 000 utilisateurs fictifs |
| Tests API : fichier ouvert | lance les tests du fichier affiché |

**Tests** : onglet *Testing* (fiole), ou `⌘⇧P` → *Tasks: Run Test Task*, ou `make tests`.

**Tâches** (`⌘⇧P` → *Tasks: Run Task*) : installer, démarrer la base, migrer, lancer l'API, servir le site, tests, style.

**Style** : Ruff formate le code à chaque sauvegarde. `make lint` vérifie comme la CI.

**Base** : panneau SQLTools → connexion « montroc (local) » pour voir les tables et lancer des requêtes.

## Commandes utiles

| Commande | Effet |
|---|---|
| `make installer` | (ré)installe l'environnement Python |
| `make base` | démarre PostgreSQL (Docker) |
| `make migrer` | applique les migrations |
| `make migration m="..."` | crée une migration après modification de `models.py` |
| `make api` | lance l'API avec rechargement automatique |
| `make site` | sert le site statique |
| `make tests` | tests du moteur et de l'API |
| `make lint` / `make format` | vérifie / corrige le style |
| `docker compose down` | arrête la base (les données sont conservées) |
| `docker compose down -v` | arrête et **efface** la base locale |
