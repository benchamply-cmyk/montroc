# montroc

L'alternative montroc : échanger des objets **sans prix ni monnaie**. Chacun dit ce qu'il a et ce qui lui serait utile, et montroc trouve l'échange, même en boucle à trois.

Site prévu : [troctroc.fr](https://troctroc.fr)

## Contenu du dépôt

| Dossier | Contenu |
|---|---|
| [`web/`](web/) | Le site : une page HTML autonome (maquette interactive), publiée par Netlify sur troctroc.fr. |
| [`algorithme/`](algorithme/) | Le moteur d'échanges en Python pur : boucles autour d'un utilisateur, « math trade » à l'échelle d'une ville, gestion des refus. Voir son [README](algorithme/README.md). |
| [`api/`](api/) | L'API FastAPI (Python 3.12) et le schéma PostgreSQL avec ses migrations Alembic. Déployée sur Render (api.troctroc.fr). |
| [`docs/`](docs/) | **La documentation du projet** : architecture, mise en ligne pas à pas, base de données, VS Code, Git. |

## Démarrer

```
make installer             # environnement Python (.venv) : moteur + API
cp .env.example api/.env
make base                  # PostgreSQL local (Docker)
make api                   # API sur http://localhost:8001/docs
make site                  # site sur http://localhost:8000
make tests                 # tous les tests
```

Détails et équivalents VS Code : [docs/04-developpement-local.md](docs/04-developpement-local.md).

## Mettre en ligne

Domaine chez OVH, site sur Netlify, API sur Render, base sur Neon : suivre [docs/02-mise-en-ligne.md](docs/02-mise-en-ligne.md).

## Contribuer

Une branche par fonctionnalité, PR vers `preprod`, puis livraison `preprod → prod` avec la CI verte : [docs/05-git-et-branches.md](docs/05-git-et-branches.md).
