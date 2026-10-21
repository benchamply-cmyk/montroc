# Git, branches et pull requests

## Principe

- **`main` = la production.** Netlify (site) et Render (API) déploient automatiquement chaque nouveau commit de `main`.
- On ne travaille **jamais directement sur `main`** : chaque fonctionnalité a sa branche, et arrive dans `main` par une **pull request** (PR) relue, avec la CI verte.
- Une branche = un sujet. Petite, courte, fusionnée vite.

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

Les fils de discussion Claude reçoivent d'office une branche `claude/project-thread-xxxx`. Pour qu'ils suivent cette règle, les instructions du projet leur demandent de créer leur branche sous la forme `type/sujet`.

## Le cycle d'une fonctionnalité

```
git switch main && git pull                 # partir de la dernière version
git switch -c feature/photos-objets         # créer la branche
# … coder, make tests …
git add -p && git commit -m "Ajoute l'envoi de photos pour les objets"
git push -u origin feature/photos-objets    # publier la branche
```

Puis sur GitHub : **Compare & pull request**. Le modèle de PR s'affiche ; remplis *Avant / Après / Comment*.

Sur la PR :
1. la **CI** lance les tests du moteur, le style, la vérification des migrations et les tests de l'API sur PostgreSQL ;
2. **Netlify** publie un aperçu du site (*Deploy Preview*) avec son lien ;
3. quand tout est vert et relu : **Squash and merge**. La branche est supprimée, `main` est déployée.

## Messages de commit

Une phrase à l'impératif qui dit ce que fait le commit, en français : « Ajoute… », « Corrige… », « Documente… ». Le détail (pourquoi) va dans le corps du message si besoin.

## Versions

Chaque version est une étiquette Git `vMAJEUR.MINEUR.CORRECTIF` posée sur `main`, et décrite dans [CHANGELOG.md](../CHANGELOG.md).

| Ce qui change | Chiffre qui monte | Exemple |
|---|---|---|
| un lot de nouvelles fonctionnalités | MINEUR | `v0.4.1` → `v0.5.0` |
| une correction, un petit ajustement | CORRECTIF | `v0.5.0` → `v0.5.1` |
| le lancement public | MAJEUR | `v0.9.3` → `v1.0.0` |

Tant qu'on est en bêta, la version commence par `0.`.

Pour sortir une version :
1. dans la PR, ajouter une ligne sous « À venir » dans `CHANGELOG.md` ;
2. au moment d'étiqueter, renommer « À venir » en `[0.5.0] – date`, et changer `VERSION` en haut de `web/site.js` (elle s'affiche dans le pied de page) ;
3. à la fusion, le workflow **Versions** (`.github/workflows/versions.yml`) voit une `VERSION` sans étiquette : il crée l'étiquette `v0.5.0` et la *Release* GitHub avec le texte du journal. Rien à faire à la main.

Les branches fusionnées se suppriment seules si l'option *Settings → General → Automatically delete head branches* est cochée sur GitHub.

## Feuille de route

Les prochaines branches, dans l'ordre conseillé :

| Branche | Contenu |
|---|---|
| ~~Étape 1~~ (fait) | connexion par lien magique, site branché sur l'API, photos (Cloudinary) et état obligatoires, e-mails aux moments clés, tâches planifiées, signalements et modération : voir [06-comptes-e-mails-photos.md](06-comptes-e-mails-photos.md) |
| ~~`feature/reputation`~~ (fait) | la fiabilité d'un utilisateur évolue selon les échanges menés au bout (et baisse sans réponse), et les autres membres en voient la réputation |
| `feature/points-de-depot` | plusieurs lieux de dépôt choisis selon la ville, au lieu d'un seul lieu configuré |
| `feature/pages-legales` | mentions légales, CGU, règles de modération et rapport de transparence annuel (DSA) |
