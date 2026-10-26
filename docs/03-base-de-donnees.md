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
    grands_trocs ||--o{ echanges : "propose le dimanche"
    echanges ||--|{ transferts : "2 ou 3 étapes"
    objets ||--o{ transferts : "circule"
    utilisateurs ||--o{ transferts : "donne / reçoit"
    utilisateurs ||--o{ sessions : "connecté"
    objets ||--o{ signalements : "visé"
    utilisateurs ||--o{ signalements : "visé / auteur"
    objets ||--o{ objets_contre : "je le donne contre"
    souhaits ||--o{ objets_contre : "accepté en échange"
    utilisateurs ||--o{ avis : "J'aime / Non merci"
    objets ||--o{ avis : "vu dans le carrousel"

    categories { string slug PK  string libelle }
    utilisateurs { int id PK  string email UK  string pseudo UK  string zone  string telephone  float fiabilite  int engagements_tenus  int engagements_manques  timestamptz suspendu_le  timestamptz cree_le }
    objets { int id PK  int proprietaire_id FK  string categorie_slug FK  string titre  text description  string etat  string photo_url  string statut  bool contre_strict  jsonb modes_echange }
    souhaits { int id PK  int utilisateur_id FK  string categorie_slug FK  int objet_id FK  jsonb caracteristiques  jsonb preferences  string etat_min  string mode_recherche  jsonb alternatives  jsonb modes_echange  jsonb zones  int rang  int quantite  bool acceptation_auto }
    grands_trocs { int id PK  date jour UK  int nb_boucles  int nb_objets  int nb_participants  bool optimal  timestamptz repeche_le  int nb_objets_repeches  int nb_objets_remplaces }
    objets_contre { int objet_id PK, FK  int souhait_id PK, FK }
    avis { int utilisateur_id PK, FK  int objet_id PK, FK  bool aime  timestamptz cree_le }
    echanges { int id PK  int grand_troc_id FK  bool par_match  bool remplacement  timestamptz remplacants_cherches_le  string statut  float proba_reussite  timestamptz expire_le  timestamptz rappel_envoye_le }
    transferts { int id PK  int echange_id FK  int position  int donneur_id FK  int receveur_id FK  int objet_id FK  string reponse  timestamptz depose_le  string code_retrait }
    jetons_connexion { int id PK  string email  string empreinte UK  timestamptz expire_le  timestamptz utilise_le }
    sessions { int id PK  int utilisateur_id FK  string empreinte UK  timestamptz expire_le }
    signalements { int id PK  int objet_id FK  int utilisateur_vise_id FK  int auteur_id FK  string motif  text explication  string statut  text decision }
```

Aucune colonne de prix ni de monnaie : c'est voulu.

## Ce que la base garantit elle-même

Ces règles sont des **contraintes PostgreSQL** : même un bug dans l'API ne peut pas les violer.

| Règle | Contrainte |
|---|---|
| Un e-mail ne sert qu'une fois, sans tenir compte des majuscules | index unique sur `lower(email)` |
| Un pseudo est unique | `uq_utilisateurs_pseudo` |
| La fiabilité est entre 0 et 1 | `ck_utilisateurs_fiabilite_0_1` |
| Les compteurs d'engagements tenus et manqués sont positifs | `ck_utilisateurs_engagements_positifs` |
| Un objet a un titre non vide et une catégorie existante | `ck_objets_titre_non_vide`, clé étrangère |
| Un objet n'est proposé (`disponible`) qu'avec une photo et un état | `ck_objets_photo_et_etat_si_disponible` |
| Un lien de connexion ou une session n'est stocké que sous forme d'empreinte, unique | `uq_jetons_connexion_empreinte`, `uq_sessions_empreinte` |
| Un signalement est expliqué (10 caractères au moins) et survit à la suppression de sa cible | `ck_signalements_explication_utile`, `ON DELETE SET NULL` |
| Un statut d'objet / d'échange / de réponse est une valeur connue | `ck_objets_statut_objet`, `ck_echanges_statut_echange`, `ck_transferts_reponse` |
| Un souhait vise **soit** une catégorie **soit** un objet précis | `ck_souhaits_categorie_ou_objet` |
| Rang et quantité d'un souhait ≥ 1 | `ck_souhaits_rang_positif`, `ck_souhaits_quantite_positive` |
| Une boucle a au plus 3 étapes, sans se donner à soi-même | `ck_transferts_boucle_max_3`, `ck_transferts_donneur_different_receveur` |
| Un objet n'apparaît qu'une fois par échange | `uq_transferts_echange_objet` |
| Supprimer un compte supprime ses objets, souhaits et échanges liés | `ON DELETE CASCADE` |

Et dans l'API :
- quand une boucle est enregistrée, ses objets sont **verrouillés** (`SELECT … FOR UPDATE`) puis passent en `reserve` : deux échanges simultanés ne peuvent pas réserver le même objet ;
- un refus, un délai de 48 h dépassé ou des dépôts incomplets à la fin de la semaine (dimanche midi après le Grand Troc) **annulent** l'échange et remettent les objets en `disponible` ;
- un objet retiré par la modération passe en `modere` : son propriétaire ne peut pas le remettre en ligne ;
- la liste « je le donne contre… » d'un objet (`objets_contre`) ne contient que des souhaits de son propriétaire ;
- la fiabilité découle des engagements : `(tenus + 9) / (tenus + manqués + 9)`. Un dépôt compte comme tenu ; ne pas répondre dans les 48 h, ou accepter sans déposer, comme manqué ; un refus ne compte pas. Les autres membres en voient la **réputation** (fiche d'un objet, carte du Match) : « Nouveau membre » tant que rien n'est mené ni manqué, « Membre fiable » à partir de 3 échanges menés au bout avec une fiabilité d'au moins 90 %, « Fiabilité à confirmer » à 75 % ou moins (trois manquements sans échange mené), avec le nombre d'échanges menés au bout.

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
