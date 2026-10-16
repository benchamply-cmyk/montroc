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

En minuscules, mots séparés par des tirets, sans accents.

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

## Fonctionnalités et interrupteurs

Une nouvelle fonctionnalité se développe sur sa branche `feature/…`, avec son propre interrupteur (*feature flag*) **éteint par défaut**. Elle peut ainsi être fusionnée dans `main` et partir en ligne sans que personne ne la voie, puis être allumée (ou éteinte) depuis l'onglet Modération, sans redéployer. Le détail et le pas-à-pas : [07-fonctionnalites.md](07-fonctionnalites.md).

## Messages de commit

Une phrase à l'impératif qui dit ce que fait le commit, en français : « Ajoute… », « Corrige… », « Documente… ». Le détail (pourquoi) va dans le corps du message si besoin.

## Versions

Quand une étape importante est en ligne, on marque `main` avec une étiquette : `git tag -a v0.1.0 -m "Première mise en ligne" && git push --tags`, puis *Releases → Draft a new release* sur GitHub.

## Feuille de route

Les prochaines branches, dans l'ordre conseillé :

| Branche | Contenu |
|---|---|
| ~~Étape 1~~ (fait) | connexion par lien magique, site branché sur l'API, photos (Cloudinary) et état obligatoires, e-mails aux moments clés, tâches planifiées, signalements et modération : voir [06-comptes-e-mails-photos.md](06-comptes-e-mails-photos.md) |
| `feature/reputation` | la fiabilité d'un utilisateur évolue selon les échanges menés au bout (et baisse sans réponse) |
| `feature/points-de-depot` | plusieurs lieux de dépôt choisis selon la ville, au lieu d'un seul lieu configuré |
| `feature/pages-legales` | mentions légales, CGU, règles de modération et rapport de transparence annuel (DSA) |
