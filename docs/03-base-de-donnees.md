# Base de données

PostgreSQL 16, hébergée sur **Neon** en production, dans **Docker** en local. Le schéma est décrit dans [`api/src/montroc_api/models.py`](../api/src/montroc_api/models.py) et son historique dans [`api/alembic/versions/`](../api/alembic/versions/).

## Schéma

```mermaid
erDiagram
    categories ||--o{ objets : "classe"
    categories ||--o{ souhaits : "souhait large"
    utilisateurs ||--o{ objets : "possède"
    utilisateurs ||--o{ souhaits : "exprime"
    objets ||--o{ souhaits : "souhait précis"
    echanges ||--|{ transferts : "2 ou 3 étapes"
    objets ||--o{ transferts : "circule"
    utilisateurs ||--o{ transferts : "donne / reçoit"

    categories { string slug PK  string libelle }
    utilisateurs { int id PK  string email UK  string pseudo UK  string zone  float fiabilite  timestamptz cree_le }
    objets { int id PK  int proprietaire_id FK  string categorie_slug FK  string titre  text description  string statut }
    souhaits { int id PK  int utilisateur_id FK  string categorie_slug FK  int objet_id FK  int rang  int quantite  bool acceptation_auto }
    echanges { int id PK  string statut  float proba_reussite  timestamptz expire_le }
    transferts { int id PK  int echange_id FK  int position  int donneur_id FK  int receveur_id FK  int objet_id FK  string reponse }
```

Aucune colonne de prix ni de monnaie : c'est voulu.

## Ce que la base garantit elle-même

Ces règles sont des **contraintes PostgreSQL** : même un bug dans l'API ne peut pas les violer.

| Règle | Contrainte |
|---|---|
| Un e-mail ne sert qu'une fois, sans tenir compte des majuscules | index unique sur `lower(email)` |
| Un pseudo est unique | `uq_utilisateurs_pseudo` |
| La fiabilité est entre 0 et 1 | `ck_utilisateurs_fiabilite_0_1` |
| Un objet a un titre non vide et une catégorie existante | `ck_objets_titre_non_vide`, clé étrangère |
| Un statut d'objet / d'échange / de réponse est une valeur connue | `ck_objets_statut_objet`, `ck_echanges_statut_echange`, `ck_transferts_reponse` |
| Un souhait vise **soit** une catégorie **soit** un objet précis | `ck_souhaits_categorie_ou_objet` |
| Rang et quantité d'un souhait ≥ 1 | `ck_souhaits_rang_positif`, `ck_souhaits_quantite_positive` |
| Une boucle a au plus 3 étapes, sans se donner à soi-même | `ck_transferts_boucle_max_3`, `ck_transferts_donneur_different_receveur` |
| Un objet n'apparaît qu'une fois par échange | `uq_transferts_echange_objet` |
| Supprimer un compte supprime ses objets, souhaits et échanges liés | `ON DELETE CASCADE` |

Et dans l'API :
- quand une boucle est enregistrée, ses objets sont **verrouillés** (`SELECT … FOR UPDATE`) puis passent en `reserve` : deux échanges simultanés ne peuvent pas réserver le même objet ;
- un refus ou un délai de 48 h dépassé **annule** l'échange et remet les objets en `disponible`.

Les tests (`api/tests/test_base_de_donnees.py`) vérifient chacune de ces contraintes sur une vraie base PostgreSQL.

## Migrations (Alembic)

Toute évolution du schéma passe par une **migration** versionnée dans Git. On ne modifie jamais la base de production à la main.

```
# 1. modifier api/src/montroc_api/models.py
# 2. générer la migration
make migration m="ajoute les photos des objets"
# 3. relire le fichier créé dans api/alembic/versions/ (toujours !)
# 4. l'appliquer en local et lancer les tests
make migrer && make tests
```

- En production, Render exécute `alembic upgrade head` avant chaque démarrage de l'API.
- La CI vérifie que les migrations correspondent aux modèles (`alembic check`) : une PR qui modifie `models.py` sans migration est refusée.
- Revenir en arrière d'une migration : `cd api && alembic downgrade -1`.
- Les noms de contraintes suivent une convention fixe (`ck_<table>_<règle>`, `fk_…`, `uq_…`, `ix_…`), ce qui garde les migrations lisibles.

Migrations existantes :

| Révision | Contenu |
|---|---|
| `0001` | schéma initial |
| `0002` | catégories de base (poussette, siège auto, vélo, livres…) |

## Sauvegardes et restauration

- **Neon** conserve l'historique de la base et permet de **restaurer à un instant passé** (*Restore* / *Branches → Create branch from a point in time*). La durée de cet historique dépend de l'offre (courte sur l'offre gratuite) : la passer à une offre payante au lancement public.
- Sauvegarde manuelle complémentaire, à faire avant toute opération risquée :
  ```
  pg_dump "$DATABASE_URL" --format=custom --file=montroc-$(date +%F).dump
  # restauration : pg_restore --clean --no-owner -d "$DATABASE_URL" montroc-AAAA-MM-JJ.dump
  ```
- Pour tester une migration délicate : créer une branche Neon depuis `main`, pointer une API locale dessus, migrer, vérifier, puis supprimer la branche.

## Se connecter à la base

- **VS Code** : extension SQLTools (recommandée par le projet), connexion « montroc (local) » déjà configurée.
- **Terminal** : `psql postgresql://montroc:montroc@localhost:5432/montroc` (local) ou `psql "$DATABASE_URL"` (Neon).
- **Neon** : onglet *SQL Editor* dans la console.
