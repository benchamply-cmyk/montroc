# Git, branches et pull requests

## Principe

- **`prod` = la production** (appelée `main` jusqu'au 26/10/2026). Netlify (site) et Render (API) déploient automatiquement chaque nouveau commit de `prod`.
- **`preprod` = la pré-production** (depuis le 26/10/2026). Toutes les branches partent de `preprod` et y reviennent par une PR. Elle a son site, son API et sa copie de la base (voir [Pré-production](#pré-production)).
- **`prod` ne reçoit que `preprod`**, par une PR `preprod → prod`, quand la campagne de tests de régression est verte et que Ben a validé.
- On ne travaille **jamais directement** sur `prod` ni sur `preprod`.
- Une branche = un sujet. Petite, courte, fusionnée vite (*Squash and merge*), remise à jour avec `preprod` avant la fusion.

```
feature/…-v5.2000 fix/…-v5.3000 …  ──PR──▶  preprod (V5.2000…)  ──PR (jeudi)──▶  prod (V5.200…)
        ▲                                            │
        └──────── test rouge : on corrige ───────────┘
```

Le contrôle **Règles des branches** (`.github/workflows/regles.yml`) vérifie chaque PR : base `prod` seulement depuis `preprod` ; vers `preprod`, un nom `type/sujet-vX.Y` et un fichier `changelog.d/` ; vers `prod`, un numéro de livraison préparé (voir [Versions](#versions)).

## Nommer les branches

Forme : **`type/sujet-vX.Y`**, où `vX.Y` est la version que prendra `preprod` à la fusion (la prochaine : dernière version de preprod + 1000).

| Préfixe | Pour | Exemple |
|---|---|---|
| `feature/` | nouvelle fonctionnalité | `feature/authentification-v5.2000` |
| `fix/` | correction de bug | `fix/delai-48h-fuseau-v5.2000` |
| `docs/` | documentation seule | `docs/guide-dns-v5.2000` |
| `chore/` | outillage, dépendances, CI | `chore/maj-fastapi-v5.2000` |
| `db/` | migration de données délicate | `db/fusion-categories-v5.2000` |
| `mobile/` | application mobile (Expo) | `mobile/notifications-v5.2000` |

En minuscules, mots séparés par des tirets, sans accents. Le sujet dit **ce que la branche change**, pour qu'on comprenne l'évolution rien qu'en lisant la liste des branches.

Pour connaître le nom à donner : `python3 scripts/version.py branche feature photos` répond `feature/photos-v5.2000` (d'après les étiquettes du dépôt). Si deux branches partent en même temps avec le même numéro, la seconde fusionnée prendra en réalité le numéro suivant : le contrôle le signale par un simple avertissement, rien à renommer (le nom d'une branche ne change plus une fois la PR ouverte).

Les fils de discussion Claude reçoivent d'office une branche `claude/project-thread-xxxx`. Pour qu'ils suivent cette règle, les instructions du projet leur demandent de créer leur branche sous la forme `type/sujet-vX.Y`, partie de `preprod`, avec un fichier `changelog.d/`.

## Le cycle d'une fonctionnalité

```
git switch preprod && git pull              # partir de la pré-production
python3 scripts/version.py branche feature photos-objets   # → feature/photos-objets-v5.2000
git switch -c feature/photos-objets-v5.2000 # créer la branche
# … coder, make tests …
echo "- Objets : jusqu'à 3 photos par objet." > changelog.d/photos-objets.md   # la ligne du journal
git add -p && git commit -m "Ajoute l'envoi de photos pour les objets"
git push -u origin feature/photos-objets-v5.2000   # publier la branche
```

Puis sur GitHub : **Compare & pull request**, **base : `preprod`**. Le modèle de PR s'affiche ; remplis *Avant / Après / Comment*.

Sur la PR :
1. la **CI** lance les tests du moteur, le style, la vérification des migrations et les tests de l'API sur PostgreSQL ;
2. **Netlify** publie un aperçu du site (*Deploy Preview*) avec son lien ;
3. le contrôle **Règles des branches** vérifie le nom de la branche et le fichier `changelog.d/` ;
4. quand tout est vert et relu : mettre la branche à jour avec `preprod` (*Update branch*), puis **Squash and merge**. La branche est supprimée, la pré-production est déployée et le workflow **Versions** lui donne son numéro (étiquette `preprod-V5.2000`).

Chaque semaine (le jeudi), une PR `preprod → prod` livre la production. Pas de livraison du samedi au mardi soir (Grand Troc et 48 h de réponse), sauf correctif urgent passé par `preprod`.

## Messages de commit

Une phrase à l'impératif qui dit ce que fait le commit, en français : « Ajoute… », « Corrige… », « Documente… ». Le détail (pourquoi) va dans le corps du message si besoin.

## Versions

Règle décidée par Ben le 26/10/2026. Les étiquettes Git font foi ; elles sont posées par le workflow **Versions** (`.github/workflows/versions.yml`), jamais à la main.

| | Production (`prod`) | Pré-production (`preprod`) |
|---|---|---|
| Version au 26/10/2026 | `V5.100` | `V5.1000` |
| Monte de | **+100 à chaque livraison** `preprod → prod` | **+1000 à chaque PR fusionnée** dans `preprod` |
| Suite | `V5.200`, `V5.300`, `V5.400`… | `V5.2000`, `V5.3000`, `V5.4000`… |
| Étiquette Git | `V5.200` (+ *Release* GitHub avec le journal) | `preprod-V5.2000` |
| Affichée dans le pied de page | `VERSION` en haut de `web/site.js` | dernière étiquette `preprod-V…` (lue sur GitHub par le site preprod) |
| Version majeure | `V6.100` à la prochaine version stable, **quand Ben le décide** | `V6.1000` une fois `V6.100` en production |

### Ce qui se passe tout seul

- **PR fusionnée dans `preprod`** : le workflow **Versions** pose l'étiquette `preprod-V…` suivante sur le commit. Le pied de page du site preprod l'affiche.
- **Livraison fusionnée dans `prod`** : le workflow **Versions** crée l'étiquette `V…` et la *Release* GitHub avec la section du journal.
- **Contrôle Règles des branches** : il refuse une branche sans `-vX.Y`, une PR qui change `VERSION` à la main, et une PR `preprod → prod` dont le numéro de livraison n'est pas préparé.

### Livrer la production (chaque jeudi)

1. *Actions → Versions → Run workflow*, branche `preprod` (cocher *majeure* seulement quand Ben décide de passer à `V6.100`). Le robot calcule le numéro (`V5.200`), range les lignes de `changelog.d/` dans `CHANGELOG.md`, met `VERSION` à `5.200` dans `web/site.js` et ouvre la PR `chore/version-5.200` vers `preprod` (une PR ouverte par le robot ne lance pas la CI : la fermer puis la rouvrir). En local : `python3 scripts/version.py livraison`.
2. Fusionner cette PR dans `preprod` (preprod prend elle aussi son numéro +1000).
3. Ouvrir la PR `preprod → prod`, la fusionner une fois les tests verts : `V5.200` est en production, étiquetée.

Les lignes du journal : dans chaque PR, un fichier d'une ligne `changelog.d/<sujet>.md`, jamais de ligne dans `CHANGELOG.md` (voir [changelog.d/README.md](../changelog.d/README.md)). Les versions d'avant le 26/10/2026 restent étiquetées `v0.1.0` … `v0.5.0`.

Les branches fusionnées se suppriment seules si l'option *Settings → General → Automatically delete head branches* est cochée sur GitHub.

## Pré-production

| Brique | Production (`prod`) | Pré-production (`preprod`) |
|---|---|---|
| Site | toptroc.com (Netlify) | déploiement de branche Netlify : `preprod--troctroc.netlify.app` |
| API | `montroc-api` sur Render (api.toptroc.com) | `montroc-api-preprod` sur Render (`render.yaml`), `montroc-api-preprod.onrender.com` |
| Base | Neon, branche principale | branche Neon `preprod`, copie de la production |
| E-mails, SMS | Brevo | tous les e-mails à `COURRIELS_VERS` (le vrai destinataire en tête du sujet), `SMS_ACTIFS=false` |
| Grand Troc | dimanche 18 h, tâche planifiée | à la main : *Actions → Tâches planifiées → Run workflow*, environnement `preprod` |

Le site choisit son API d'après son adresse : une adresse qui commence par `preprod--` ou `preprod.` appelle `montroc-api-preprod.onrender.com` (`web/site.js` et `web/index.html`). Si Render donne une autre adresse au service, la changer à ces deux endroits et dans `taches.yml`.

### Mise en place (une fois, par Ben)

Faite le 26/10/2026. Le service Render `montroc-api-preprod` a été créé directement (sans passer par le Blueprint). Netlify exige la connexion à l'équipe pour tout ce qui n'est pas la production : `preprod--troctroc.netlify.app` n'est visible que connecté à Netlify. Le premier déploiement du site preprod part au premier commit arrivé sur `preprod` après l'activation.

1. **Neon** : *Branches → Create branch* `preprod` depuis la branche principale ; copier sa chaîne de connexion.
2. **Render** : *Blueprints* → synchroniser ce dépôt (le service `montroc-api-preprod` apparaît), puis renseigner `DATABASE_URL` (branche Neon `preprod`), `COURRIELS_VERS`, `BREVO_API_KEY`, `CLOUDINARY_URL`, `MODERATEURS`, `TACHES_SECRET`.
3. **GitHub** : secret `TACHES_SECRET_PREPROD` (*Settings → Secrets and variables → Actions*), même valeur que `TACHES_SECRET` du service preprod.
4. **Netlify** : *Site configuration → Build & deploy → Branches and deploy contexts → Branch deploys* : ajouter `preprod`.

### Protection des branches (Settings → Branches → Add rule, une règle par branche)

| Réglage | `prod` | `preprod` |
|---|---|---|
| Require a pull request before merging | oui | oui |
| Require approvals | non | 1 (voir la note) |
| Require status checks to pass | Moteur d'échanges, API et base de données, Application mobile, Règles des branches | les mêmes |
| Require branches to be up to date before merging | oui | oui |
| Allow force pushes, Allow deletions | non | non |

Note sur la relecture : GitHub n'accepte pas qu'on approuve sa propre PR. Tant que Ben est seul sur le dépôt, laisser *Require approvals* à 1 sur `preprod` mais cocher *Allow specified actors to bypass* pour Ben (ou ne pas cocher *Do not allow bypassing*) : il fusionne après avoir relu les PR ouvertes par Claude.

### Jeton du workflow Versions (une fois, par Ben)

Le jeton fourni d'office à GitHub Actions ne peut pas poser d'étiquette ni pousser de branche sur un commit de `preprod` dont les fichiers `.github/workflows/` diffèrent de `prod` (erreur 403 « Resource not accessible by integration »). Le workflow **Versions** utilise donc un jeton personnel :

1. GitHub → photo de profil → *Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token* ; nom `versions-troctroc`, expiration 1 an, *Only select repositories* : `montroc` ;
2. *Repository permissions* : **Contents : Read and write**, **Workflows : Read and write**, **Pull requests : Read and write** ;
3. copier le jeton, puis dans le dépôt : *Settings → Secrets and variables → Actions → New repository secret*, nom **`VERSIONS_TOKEN`**.

Bonus : la PR « Livraison » ouverte avec ce jeton lance la CI d'elle-même. Penser à renouveler le jeton à son expiration (le job « Version de preprod » échoue alors avec un message qui le dit).

Et dans *Settings → General* : *Allow squash merging* seul coché, *Automatically delete head branches* coché. *Settings → Actions → General* : cocher *Allow GitHub Actions to create and approve pull requests* (pour la PR de version).

## Feuille de route

Les prochaines branches, dans l'ordre conseillé :

| Branche | Contenu |
|---|---|
| ~~Étape 1~~ (fait) | connexion par lien magique, site branché sur l'API, photos (Cloudinary) et état obligatoires, e-mails aux moments clés, tâches planifiées, signalements et modération : voir [06-comptes-e-mails-photos.md](06-comptes-e-mails-photos.md) |
| ~~`feature/reputation`~~ (fait) | la fiabilité d'un utilisateur évolue selon les échanges menés au bout (et baisse sans réponse), et les autres membres en voient la réputation |
| ~~`feature/points-de-depot`~~ (fait) | plusieurs lieux de dépôt choisis selon la ville, au lieu d'un seul lieu configuré |
| `feature/pages-legales` | mentions légales, CGU, règles de modération et rapport de transparence annuel (DSA) |
