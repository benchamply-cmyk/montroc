# Git, branches et pull requests

## Principe

- **`prod` = la production** (appelée `main` jusqu'au 26/10/2026). Netlify (site) et Render (API) déploient automatiquement chaque nouveau commit de `prod`.
- **`preprod` = la pré-production** (depuis le 26/10/2026). Toutes les branches partent de `preprod` et y reviennent par une PR. Elle a son site, son API et sa copie de la base (voir [Pré-production](#pré-production)).
- **`prod` ne reçoit que `preprod`**, par une PR `preprod → prod`, quand la campagne de tests de régression est verte et que Ben a validé.
- On ne travaille **jamais directement** sur `prod` ni sur `preprod`.
- Une branche = un sujet. Petite, courte, fusionnée vite (*Squash and merge*), remise à jour avec `preprod` avant la fusion.

```
feature/… fix/… docs/… chore/… mobile/…  ──PR──▶  preprod  ──PR (jeudi)──▶  prod  ──▶  étiquette vX.Y.Z
        ▲                                            │
        └──────── test rouge : on corrige ───────────┘
```

Le contrôle **Règles des branches** (`.github/workflows/regles.yml`) vérifie chaque PR : base `prod` seulement depuis `preprod` ; vers `preprod`, un nom `type/sujet` et un fichier `changelog.d/`.

## Nommer les branches

| Préfixe | Pour | Exemple |
|---|---|---|
| `feature/` | nouvelle fonctionnalité | `feature/authentification` |
| `fix/` | correction de bug | `fix/delai-48h-fuseau` |
| `docs/` | documentation seule | `docs/guide-dns` |
| `chore/` | outillage, dépendances, CI | `chore/maj-fastapi` |
| `db/` | migration de données délicate | `db/fusion-categories` |
| `mobile/` | application mobile (Expo) | `mobile/notifications` |

En minuscules, mots séparés par des tirets, sans accents. Le sujet dit **ce que la branche change**, pour qu'on comprenne l'évolution rien qu'en lisant la liste des branches.

Les fils de discussion Claude reçoivent d'office une branche `claude/project-thread-xxxx`. Pour qu'ils suivent cette règle, les instructions du projet leur demandent de créer leur branche sous la forme `type/sujet`, partie de `preprod`, avec un fichier `changelog.d/`.

## Le cycle d'une fonctionnalité

```
git switch preprod && git pull              # partir de la pré-production
git switch -c feature/photos-objets         # créer la branche
# … coder, make tests …
echo "- Objets : jusqu'à 3 photos par objet." > changelog.d/photos-objets.md   # la ligne du journal
git add -p && git commit -m "Ajoute l'envoi de photos pour les objets"
git push -u origin feature/photos-objets    # publier la branche
```

Puis sur GitHub : **Compare & pull request**, **base : `preprod`**. Le modèle de PR s'affiche ; remplis *Avant / Après / Comment*.

Sur la PR :
1. la **CI** lance les tests du moteur, le style, la vérification des migrations et les tests de l'API sur PostgreSQL ;
2. **Netlify** publie un aperçu du site (*Deploy Preview*) avec son lien ;
3. le contrôle **Règles des branches** vérifie le nom de la branche et le fichier `changelog.d/` ;
4. quand tout est vert et relu : mettre la branche à jour avec `preprod` (*Update branch*), puis **Squash and merge**. La branche est supprimée, la pré-production est déployée.

Chaque semaine (le jeudi), une PR `preprod → prod` livre la production. Pas de livraison du samedi au mardi soir (Grand Troc et 48 h de réponse), sauf correctif urgent passé par `preprod`.

## Messages de commit

Une phrase à l'impératif qui dit ce que fait le commit, en français : « Ajoute… », « Corrige… », « Documente… ». Le détail (pourquoi) va dans le corps du message si besoin.

## Versions

Chaque version est une étiquette Git `vMAJEUR.MINEUR.CORRECTIF` posée sur `prod`, et décrite dans [CHANGELOG.md](../CHANGELOG.md).

| Ce qui change | Chiffre qui monte | Exemple |
|---|---|---|
| un lot de nouvelles fonctionnalités | MINEUR | `v0.4.1` → `v0.5.0` |
| une correction, un petit ajustement | CORRECTIF | `v0.5.0` → `v0.5.1` |
| le lancement public | MAJEUR | `v0.9.3` → `v1.0.0` |

Tant qu'on est en bêta, la version commence par `0.`.

Pour sortir une version :
1. dans chaque PR, ajouter un fichier d'une ligne `changelog.d/<sujet>.md`, jamais de ligne dans `CHANGELOG.md` : deux PR ouvertes ensemble ne se gênent plus (voir [changelog.d/README.md](../changelog.d/README.md)) ;
2. pour préparer la version : *Actions → Versions → Run workflow*, branche `preprod`, numéro `0.6.0` (ou `python3 scripts/version.py 0.6.0` en local). Les lignes rejoignent `CHANGELOG.md`, `VERSION` change en haut de `web/site.js` (pied de page), et une PR `chore/version-0.6.0` part vers `preprod` (une PR ouverte par le robot ne lance pas la CI : la fermer puis la rouvrir) ;
3. à l'arrivée sur `prod` (PR `preprod → prod`), le workflow **Versions** (`.github/workflows/versions.yml`) voit une `VERSION` sans étiquette : il crée l'étiquette `v0.5.0` et la *Release* GitHub avec le texte du journal. Rien à faire à la main.

Les branches fusionnées se suppriment seules si l'option *Settings → General → Automatically delete head branches* est cochée sur GitHub.

## Pré-production

| Brique | Production (`prod`) | Pré-production (`preprod`) |
|---|---|---|
| Site | troctroc.fr (Netlify) | déploiement de branche Netlify : `preprod--troctroc.netlify.app` |
| API | `montroc-api` sur Render (api.troctroc.fr) | `montroc-api-preprod` sur Render (`render.yaml`), `montroc-api-preprod.onrender.com` |
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

Et dans *Settings → General* : *Allow squash merging* seul coché, *Automatically delete head branches* coché. *Settings → Actions → General* : cocher *Allow GitHub Actions to create and approve pull requests* (pour la PR de version).

## Feuille de route

Les prochaines branches, dans l'ordre conseillé :

| Branche | Contenu |
|---|---|
| ~~Étape 1~~ (fait) | connexion par lien magique, site branché sur l'API, photos (Cloudinary) et état obligatoires, e-mails aux moments clés, tâches planifiées, signalements et modération : voir [06-comptes-e-mails-photos.md](06-comptes-e-mails-photos.md) |
| ~~`feature/reputation`~~ (fait) | la fiabilité d'un utilisateur évolue selon les échanges menés au bout (et baisse sans réponse), et les autres membres en voient la réputation |
| `feature/points-de-depot` | plusieurs lieux de dépôt choisis selon la ville, au lieu d'un seul lieu configuré |
| `feature/pages-legales` | mentions légales, CGU, règles de modération et rapport de transparence annuel (DSA) |
