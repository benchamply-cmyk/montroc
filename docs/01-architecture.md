# Architecture

montroc est découpé en quatre briques indépendantes, chacune hébergée là où elle est la plus simple à faire tourner.

```mermaid
flowchart LR
    U[Navigateur] -->|https://troctroc.fr| N[Netlify<br/>site statique web/]
    U -->|https://api.troctroc.fr| R[Render<br/>API Python FastAPI]
    R -->|SQL chiffré TLS| P[(Neon<br/>PostgreSQL 16)]
    R -. importe .-> M[Moteur troc_echanges<br/>algorithme/]
    D[OVH<br/>nom de domaine + DNS] -. pointe vers .-> N
    D -. pointe vers .-> R
```

| Brique | Dossier | Hébergement | Rôle |
|---|---|---|---|
| Site | `web/` | **Netlify** (gratuit) | Pages HTML/CSS/JS servies telles quelles. Déploiement automatique à chaque fusion dans `main`, aperçu automatique sur chaque pull request. |
| API | `api/` | **Render** (gratuit au départ, Frankfurt) | Python 3.12 + FastAPI. Reçoit les requêtes du site, lit/écrit la base, appelle le moteur. Documentation interactive sur `/docs`. |
| Moteur | `algorithme/` | (dans l'API) | Bibliothèque Python pure qui trouve les boucles d'échange (2 ou 3 personnes) et le « math trade ». Aucune dépendance, testable seule. |
| Base | `api/alembic/` (schéma) | **Neon** (PostgreSQL managé, Frankfurt) | Données : utilisateurs, objets, souhaits, échanges. Sauvegardes et restauration gérées par Neon. |
| Domaine et e-mails | — | **OVH** (offre Startup) | `troctroc.fr` (et l'alias `troctroc.cloud`, redirigé vers troctroc.fr), les zones DNS et les adresses e-mail `@troctroc.fr`. |

## Pourquoi ce découpage

- **Netlify n'exécute pas de serveur Python ni de base de données** : il sert des fichiers. L'API et la base vivent donc ailleurs.
- **L'offre OVH Startup sert pour les e-mails et le domaine**, pas pour le site : l'hébergement mutualisé ne fait pas tourner d'API Python (il est fait pour PHP), et Netlify sert le site avec déploiement automatique et aperçus de PR.
- **PostgreSQL managé (Neon)** plutôt qu'une base qu'on administre soi-même : sauvegardes, mises à jour et chiffrement sont pris en charge ; la base respecte des contraintes fortes (voir [Base de données](03-base-de-donnees.md)).
- **Tout est en Europe (Frankfurt)** : latence faible depuis la France, données dans l'UE (RGPD).
- Chaque brique peut être remplacée sans toucher aux autres (ex. passer l'API sur un VPS OVH plus tard : seule l'URL `api.troctroc.fr` change de cible).

## Organisation du code de l'API

```
api/
├── pyproject.toml            dépendances et réglages (ruff, pytest)
├── alembic.ini, alembic/     migrations de la base (historique du schéma)
├── src/montroc_api/
│   ├── main.py               création de l'application, CORS, route /sante
│   ├── config.py             réglages lus dans les variables d'environnement
│   ├── db.py                 connexion à PostgreSQL
│   ├── models.py             tables et contraintes (SQLAlchemy)
│   ├── schemas.py            formats JSON d'entrée/sortie (Pydantic)
│   ├── services.py           logique métier : base ⇄ moteur d'échanges
│   └── routers/              une route par ressource
│       ├── catalogue.py      /categories
│       ├── utilisateurs.py   /utilisateurs, leurs objets, souhaits, boucles possibles
│       ├── objets.py         /objets, /souhaits
│       └── echanges.py       /echanges (proposer, répondre, terminer, math trade)
└── tests/                    tests sur une vraie base PostgreSQL
```

Le chemin d'une requête : **route** (`routers/`) → valide le JSON (`schemas.py`) → appelle le **service** (`services.py`) → qui lit les **modèles** (`models.py`) et appelle le **moteur** (`troc_echanges`) → la route renvoie le JSON.

## Cycle de vie d'un échange

```mermaid
stateDiagram-v2
    [*] --> propose: boucle enregistrée,<br/>objets « reserve »
    propose --> accepte: tous les receveurs acceptent<br/>(ou acceptation automatique)
    propose --> annule: un refus ou 48 h dépassées<br/>objets libérés
    accepte --> termine: objets remis<br/>objets « echange »
```

## Ce qui n'est pas encore fait

Voir la feuille de route dans [Git, branches et pull requests](05-git-et-branches.md#feuille-de-route) : authentification, branchement du site sur l'API, photos, notifications, passe nocturne du math trade.
