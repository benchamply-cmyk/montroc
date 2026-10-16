# API montroc

FastAPI + SQLAlchemy 2 + PostgreSQL, migrations Alembic. Elle expose le moteur [`troc_echanges`](../algorithme/) au-dessus de la base.

```
make api        # depuis la racine du dépôt : http://localhost:8001/docs
make tests
```

| Route | Rôle |
|---|---|
| `GET /sante` | l'API et la base répondent |
| `POST /auth/lien`, `POST /auth/verifier`, `POST /auth/deconnexion` | connexion par lien magique (e-mail), session |
| `GET/PATCH/DELETE /moi` | mon profil (dont le portable facultatif pour les SMS), suppression du compte |
| `GET/POST /moi/objets`, `PATCH /moi/objets/{id}`, `GET /moi/photos/signature` | mes objets (photo et état obligatoires) |
| `GET/POST /moi/souhaits`, `DELETE /moi/souhaits/{id}` | ce qui me serait utile |
| `GET /moi/boucles` | « Mes échanges possibles » (boucles de 2 et 3) |
| `GET /moi/echanges` | mes échanges en cours et passés |
| `POST /echanges`, `GET /echanges/{id}` | proposer une de mes boucles (réserve les objets, prévient les autres) |
| `POST /echanges/{id}/reponse` | accepter / refuser (48 h) |
| `POST /echanges/{id}/depot` | j'ai déposé mon objet |
| `GET /categories`, `GET /objets`, `GET /objets/{id}`, `GET /utilisateurs/{id}` | lecture publique, sans compte (`GET /objets?q=vélo enfant` : recherche libre dans le titre, la description et la catégorie) |
| `POST /signalements` | signaler un objet ou un compte (avec ou sans compte) |
| `GET /moderation/signalements`, `POST /moderation/signalements/{id}/decision`, `POST /categories` | modération (comptes listés dans `MODERATEURS`) |
| `GET /match/carrousel` | le Match : objets qui répondent à mes souhaits, ceux qui feraient un match tout de suite d'abord |
| `POST /match/avis` | « J'aime » / « Non merci » sur un objet ; renvoie le match si l'intérêt est réciproque |
| `GET /match`, `POST /match/accord` | mes matchs ; proposer l'échange 1 à 1 à un match, à tout moment (48 h pour répondre, 7 jours pour déposer) |
| `GET /grand-troc` | date du prochain Grand Troc du dimanche et bilan du dernier (public) |
| `POST /taches/horaires`, `POST /taches/grand-troc` | tâches planifiées (en-tête `X-Taches-Secret`) ; `?force=true` lance le Grand Troc tout de suite |

Les routes personnelles demandent l'en-tête `Authorization: Bearer <jeton>`. En local, sans SMTP configuré, les e-mails (dont le lien de connexion) s'affichent dans la console de l'API.

Architecture et schéma : [docs/01-architecture.md](../docs/01-architecture.md), [docs/03-base-de-donnees.md](../docs/03-base-de-donnees.md). Configuration : [docs/06-comptes-e-mails-photos.md](../docs/06-comptes-e-mails-photos.md).
