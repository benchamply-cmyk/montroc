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

## Messages de commit

Une phrase à l'impératif qui dit ce que fait le commit, en français : « Ajoute… », « Corrige… », « Documente… ». Le détail (pourquoi) va dans le corps du message si besoin.

## Versions

Quand une étape importante est en ligne, on marque `main` avec une étiquette : `git tag -a v0.1.0 -m "Première mise en ligne" && git push --tags`, puis *Releases → Draft a new release* sur GitHub.

## Feuille de route

Les prochaines branches, dans l'ordre conseillé :

| Branche | Contenu |
|---|---|
| `feature/authentification` | comptes avec connexion par lien magique (e-mail), jetons de session ; l'API ne fait plus confiance à un `utilisateur_id` envoyé par le client |
| `feature/site-branche-sur-api` | le site `web/` lit et écrit dans l'API au lieu de la maquette en mémoire |
| `feature/photos-objets` | photos des objets (stockage objet, ex. Cloudflare R2 ou OVH Object Storage) |
| `feature/notifications` | e-mails « nouvel échange proposé », rappel avant les 48 h |
| `feature/math-trade-nocturne` | tâche planifiée (Render Cron Job) qui lance `POST /echanges/math-trade` chaque nuit et expire les échanges sans réponse |
| `feature/reputation` | la fiabilité d'un utilisateur évolue selon les échanges menés au bout |
