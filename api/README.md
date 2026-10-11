# API montroc

FastAPI + SQLAlchemy 2 + PostgreSQL, migrations Alembic. Elle expose le moteur [`troc_echanges`](../algorithme/) au-dessus de la base.

```
make api        # depuis la racine du dépôt : http://localhost:8001/docs
make tests
```

| Route | Rôle |
|---|---|
| `GET /sante` | l'API et la base répondent |
| `GET/POST /categories` | catégories d'objets |
| `POST /utilisateurs`, `GET/DELETE /utilisateurs/{id}` | comptes |
| `POST/GET /utilisateurs/{id}/objets`, `GET /objets`, `PATCH /objets/{id}` | objets disponibles |
| `POST/GET /utilisateurs/{id}/souhaits`, `DELETE /souhaits/{id}` | ce qui serait utile |
| `GET /utilisateurs/{id}/boucles` | « Mes échanges possibles » (boucles de 2 et 3) |
| `POST /echanges` | enregistrer une boucle suggérée (réserve les objets) |
| `POST /echanges/{id}/transferts/{t}/reponse` | accepter / refuser (48 h) |
| `POST /echanges/{id}/terminer` | objets remis |
| `POST /echanges/math-trade` | passe globale : maximum d'échanges sur tout le marché |

Architecture et schéma : [docs/01-architecture.md](../docs/01-architecture.md), [docs/03-base-de-donnees.md](../docs/03-base-de-donnees.md).

> Pas encore d'authentification : `utilisateur_id` est transmis par le client. À ne pas ouvrir au public avant la branche `feature/authentification`.
