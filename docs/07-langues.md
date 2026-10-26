# Langues du site

Le français reste à la racine. Les versions anglaise et espagnole suivent les mêmes chemins, préfixés par `/english/` et `/espanol/` (ex. `/english/faq/`, `/espanol/pros/`). Le menu permet de changer de langue en gardant la page, les paramètres et l'ancre en cours. La session reste partagée sur le même domaine. Les ancres et identifiants métier restent identiques.

## Modifier le contenu

Les fichiers de référence restent `web/index.html`, `web/*/index.html`, `web/site.js` et `web/match.js`. Les traductions sont dans `web/i18n/messages.json` : chaque texte français a une entrée `en` et `es`. Elles sont intégrées aux pages et littéraux JavaScript au build, sans service tiers, sans traduction à la volée et sans observer le DOM.

```sh
npm ci
npm test
npm run build
python3 -m http.server 8000 --directory web
```

Netlify exécute `npm run build` avant de publier `web/`. Les dossiers générés `web/english/` et `web/espanol/` ne se modifient pas à la main et ne sont pas versionnés. Les assets visuels restent communs aux trois versions. Acorn analyse le JavaScript pour ne traduire que les chaînes, jamais les identifiants, expressions ou commentaires. Les pages ont leurs balises `lang`, `canonical` et `hreflang` réciproques.

Les libellés de catégories, sous-catégories et caractéristiques de l'API sont traduits à l'affichage. Les valeurs des options de formulaire restent celles attendues par l'API, même si leur texte est traduit. Les titres, descriptions et précisions saisis par les membres restent leurs textes originaux : aucune traduction automatique ne remplace leurs annonces. Le texte des e-mails et SMS envoyés par l'API reste en français. Le lien de connexion conserve cependant la langue demandée par le site (`langue` : `fr`, `en` ou `es`, français par défaut), pour terminer l'inscription dans cette langue.

Les dates sont affichées dans la langue choisie, toujours dans le fuseau `Europe/Paris` pour le Grand Troc. Les pluriels sont regroupés dans `web/langue.js`. Les erreurs API connues sont traduites ; les erreurs inattendues ont un message de secours dans la langue choisie.

Les contrôles testent la couverture des textes statiques et du catalogue, la génération, les liens et les paramètres, les scripts générés et le maintien des valeurs métier. Avant une fusion, vérifier également le menu sur ordinateur et mobile, les pages internes et les parcours de connexion et d'échange en pré-production.
