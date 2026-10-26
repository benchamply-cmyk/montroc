# Configuration du projet

> Page de référence de la configuration de montroc. Source : dossier `docs/` du dépôt GitHub `benchamply-cmyk/montroc`, qui fait foi en cas d'écart.
> Pour la coller dans Confluence : *Insérer → Markdown* (ou `/markdown`), puis coller ce fichier.

## En une phrase

troctroc.fr permet d'échanger des objets **sans prix ni monnaie** : chacun publie ce qu'il a et ce qui lui serait utile, et le moteur trouve des boucles d'échange de 2 ou 3 personnes.

## Architecture

| Brique | Technologie | Hébergeur | Adresse |
|---|---|---|---|
| Site | HTML/CSS/JS statique (`web/`) | Netlify | https://troctroc.fr |
| API | Python 3.12, FastAPI (`api/`) | Render, Frankfurt | https://api.troctroc.fr (doc : `/docs`) |
| Moteur d'échanges | Python pur (`algorithme/`) | dans l'API | — |
| Base de données | PostgreSQL 16 | Neon, Frankfurt | privée (chaîne de connexion secrète) |
| Domaine, DNS, e-mails | troctroc.fr, 10 adresses @troctroc.fr | OVH (offre Startup) | — |
| Code, CI | Git, GitHub Actions | GitHub | https://github.com/benchamply-cmyk/montroc |

Choix clés :
- Offre OVH Startup prise pour les e-mails et le domaine offert ; le site est servi par Netlify et l'API par Render (le mutualisé OVH ne fait pas tourner Python).
- Base PostgreSQL managée : sauvegardes et restauration gérées, règles métier garanties par des contraintes en base.
- Tout en Europe (RGPD, latence).

## Comptes

| Service | Usage | Offre | Double authentification |
|---|---|---|---|
| OVH | domaine, zone DNS, e-mails | Startup | ☐ |
| Neon | projet `troctroc` (branches `main`, `dev`) | gratuite au départ | ☐ |
| Render | service `montroc-api` | gratuite au départ (Starter au lancement public) | ☐ |
| Netlify | site troctroc.fr | gratuite | ☐ |
| GitHub | dépôt, CI, pull requests | gratuite | ☐ |

## Zone DNS (OVH)

Zone **troctroc.fr** :

| Type | Sous-domaine | Cible |
|---|---|---|
| A | (vide) | adresse Netlify (`75.2.60.5`, à vérifier dans Netlify) |
| CNAME | www | `troctroc.netlify.app.` |
| CNAME | api | `montroc-api-csko.onrender.com.` |

Ne jamais supprimer les entrées MX/SPF/DKIM (e-mails OVH). DNSSEC activé. Certificats HTTPS : Let's Encrypt, émis et renouvelés automatiquement par Netlify et Render.

## Variables d'environnement de l'API

| Variable | Production (Render) | Local (`api/.env`) |
|---|---|---|
| `DATABASE_URL` | chaîne Neon, branche `main` (secrète) | `postgresql+psycopg://montroc:montroc@localhost:5432/montroc` |
| `CORS_ORIGINS` | `https://troctroc.fr,https://www.troctroc.fr` | `http://localhost:8000,…` |
| `ENVIRONNEMENT` | `production` | `local` |
| `TEST_DATABASE_URL` | — | base `montroc_test` (vidée par les tests) |

Les secrets ne sont jamais dans Git (`.env` est ignoré ; modèle : `.env.example`).

## Déploiement

- Fusionner une pull request `preprod → prod` **met en ligne** : Netlify redéploie le site, Render redéploie l'API (seulement si `api/` ou `algorithme/` ont changé).
- Au démarrage, l'API applique les migrations de base (`alembic upgrade head`).
- Chaque pull request reçoit un aperçu Netlify et passe la CI : tests du moteur, style, cohérence migrations/modèles, tests de l'API sur PostgreSQL.
- `prod` est protégée : pull request et CI verte obligatoires.

## Base de données

Tables : `categories`, `utilisateurs`, `objets`, `souhaits`, `echanges`, `transferts`. Aucune notion de prix.

Garanties en base : e-mail et pseudo uniques, souhait = catégorie **ou** objet précis, statuts limités à des valeurs connues, boucles de 3 étapes maximum, objet unique par échange, suppressions en cascade. Les objets d'un échange sont verrouillés puis réservés : jamais deux échanges sur le même objet.

Évolutions : uniquement par migration Alembic versionnée (`make migration m="…"`). Sauvegardes : historique Neon + `pg_dump` manuel avant opération risquée.

## Poste de développement

VS Code + Python 3.12 + Docker Desktop. Démarrage :

```
git clone https://github.com/benchamply-cmyk/montroc.git && cd montroc && code .
make installer && cp .env.example api/.env && make base && make api
```

API locale : http://localhost:8001/docs — Site local : `make site` puis http://localhost:8000 — Tests : `make tests`.

## Organisation Git

`prod` = production (ex-`main`), `preprod` = pré-production. Une branche par sujet : `feature/…`, `fix/…`, `docs/…`, `chore/…`, `db/…`. Fusion par pull request vers `preprod` (*Squash and merge*), CI verte obligatoire. Étiquettes de version `vX.Y.Z` aux étapes importantes.

## État d'avancement

| Étape | État |
|---|---|
| Moteur d'échanges (boucles 2-3, math trade, gestion des refus) | ✅ fait, testé |
| Maquette du site | ✅ fait |
| API + schéma de base + migrations + tests | ✅ fait |
| CI GitHub, configuration Netlify et Render, VS Code | ✅ fait |
| Domaine OVH, Neon, Render, Netlify, DNS | ☐ à faire (guide : `docs/02-mise-en-ligne.md`) |
| Authentification | ☐ `feature/authentification` |
| Site branché sur l'API | ☐ `feature/site-branche-sur-api` |
| Photos, notifications, math trade nocturne, réputation | ☐ branches dédiées |

## Liens

- Dépôt : https://github.com/benchamply-cmyk/montroc
- Guide de mise en ligne pas à pas : `docs/02-mise-en-ligne.md`
- Base de données : `docs/03-base-de-donnees.md`
- Développement local : `docs/04-developpement-local.md`
- Git et branches : `docs/05-git-et-branches.md`
