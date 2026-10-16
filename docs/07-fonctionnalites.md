# Feature Flag engine : allumer et éteindre une fonctionnalité

Chaque grande fonctionnalité de TrocTroc (le Match, le Grand Troc du dimanche, l'import d'annonce…) a un **interrupteur**. On l'allume ou on l'éteint **à tout moment, pour tout le monde, sans toucher au code ni redéployer**.

Deux outils, deux rôles :

| Outil | Sert à | Exemple |
|---|---|---|
| **L'interrupteur** (feature flag) | décider si une fonctionnalité est visible en production | « J'éteins le Match ce week-end, je le rallume lundi » |
| **La branche** `feature/…` | travailler sur le code d'une fonctionnalité sans gêner le reste | « Je fais évoluer le Match sur `feature/match-v2` » |

Une branche ne sert pas à allumer ou éteindre : seul `main` est en ligne. C'est l'interrupteur qui décide de ce que voient les visiteurs, et la branche qui isole le travail en cours.

## Allumer ou éteindre (sans code)

1. Se connecter sur troctroc.fr avec un compte de modération (listé dans `MODERATEURS` sur Render).
2. Onglet **Modération**, bloc **Fonctionnalités du site**.
3. Cocher ou décocher. C'est immédiat : la page suivante de chaque visiteur suit le nouvel état.

Le bloc montre aussi qui a changé quoi, et quand.

Ce qui se passe quand une fonctionnalité est éteinte :

| Clé | Éteinte, cela donne |
|---|---|
| `match` | l'onglet Match, la carte de l'accueil et la ligne de « Comment ça marche » disparaissent ; les routes `/match…` répondent 404. Les « J'aime » déjà donnés restent en base (et comptent au Grand Troc). |
| `grand_troc` | les cartes du Grand Troc et le lien du menu disparaissent ; la tâche du dimanche et le repêchage du mardi ne lancent plus rien. Les échanges déjà proposés suivent leur cours. |
| `import_annonce` | le bloc « Votre annonce ne part pas ? » de l'accueil et le champ « Déjà en vente sur Vinted ou Leboncoin ? » disparaissent. |

Sans action de la modération, chaque fonctionnalité garde son **état par défaut** écrit dans le code.

## Comment c'est construit

- **API** : le catalogue est dans [`api/src/montroc_api/fonctionnalites.py`](../api/src/montroc_api/fonctionnalites.py) (clé, nom, description, état par défaut). L'état choisi est gardé dans la table `fonctionnalites`.
  - `GET /fonctionnalites` (public) : `{"match": true, "grand_troc": true, …}`
  - `GET /moderation/fonctionnalites`, `PUT /moderation/fonctionnalites/{cle}` (modération) : lister, allumer ou éteindre.
  - Une route se protège avec `dependencies=[exiger("match")]` (voir `routers/matchs.py`) ; dans le code, `fonctionnalites.est_active(session, "grand_troc")`.
- **Site** : [`web/site.js`](../web/site.js) lit `GET /fonctionnalites` sur toutes les pages. Tout élément marqué `data-fonctionnalite="match"` est masqué quand `match` est éteinte. En JavaScript : `await TTF.pret` puis `TTF.actif('match')`. Si l'API ne répond pas, tout reste affiché (l'API refuse de toute façon les routes d'une fonctionnalité éteinte).

## Isoler le code d'une fonctionnalité

Pour pouvoir travailler sur une fonctionnalité sans toucher au reste, son code vit dans ses propres fichiers, branchés au reste en quelques points seulement. Le Match est le modèle :

| Où | Fichier propre au Match | Point de branchement |
|---|---|---|
| Règles métier | `api/src/montroc_api/matchs.py` | – |
| Routes | `api/src/montroc_api/routers/matchs.py` | une ligne dans `main.py`, protégée par `exiger("match")` |
| Tests | `api/tests/test_match.py` | – |
| Site | `web/match.js` | une balise `<script>` dans `index.html`, le bloc `#v-match`, les éléments `data-fonctionnalite="match"` |
| Base | migration `0008_match` | – |

## Ajouter une nouvelle fonctionnalité, pas à pas

1. **Brancher** : `git switch main && git pull && git switch -c feature/ma-fonction`.
2. **Déclarer l'interrupteur** dans `CATALOGUE` (`fonctionnalites.py`), avec `par_defaut=False` : la fonctionnalité pourra arriver en ligne éteinte.
3. **Isoler** : un module métier, un routeur avec `dependencies=[exiger("ma_fonction")]`, un fichier de tests, un script `web/ma-fonction.js`, et `data-fonctionnalite="ma_fonction"` sur ce qui s'affiche.
4. **Tester** : `make tests`, plus un test « éteinte → 404 » comme dans `api/tests/test_fonctionnalites.py`.
5. **Pull request** vers `main`, CI verte, fusion. Elle part en production **éteinte** : personne ne la voit.
6. **Essayer en production** quand on veut, en l'allumant depuis Modération ; l'éteindre si quelque chose cloche.
7. **Faire évoluer** : nouvelle branche (`feature/ma-fonction-v2`), même cycle. La version en ligne reste intacte jusqu'à la fusion.

Quand une fonctionnalité est adoptée pour de bon et ne sera plus jamais éteinte, on peut retirer son interrupteur (une petite PR `chore/retire-interrupteur-…`) pour garder le code simple.
