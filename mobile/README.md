# TopTroc — application mobile

App iOS et Android (Expo / React Native) branchée sur la même API que le site : `https://api.toptroc.com`.

Navigation sur le modèle de Vinted : 5 onglets (Accueil · Match · Proposer + · Échanges · Profil), une action par onglet.
À la première ouverture, 3 écrans à faire défiler présentent le principe (Je propose, Je demande, Ça matche ou ça boucle). Les filtres s'ouvrent dans des feuilles en bas de l'écran ; sur une fiche, l'action principale reste collée en bas et « Signaler » passe dans le menu « … ».

| Écran | Contenu | Routes de l'API |
|---|---|---|
| Accueil (onglet) | Barre de recherche, catégories, bandeau du Grand Troc, « Pour vous » (membre), nouveautés en grille sans fin | `GET /objets`, `GET /categories`, `GET /match/carrousel` |
| Rechercher | Recherche plein écran, catégories, filtres (sous-catégorie, état, caractéristiques, tri), dernières recherches | `GET /objets`, `GET /categories` |
| Fiche objet | Photo, détail, propriétaire et réputation, cœur, signalement | `GET /objets/{id}`, `GET /utilisateurs/{id}` |
| Match (onglet) | Cartes à glisser : « J'aime » / « Non merci », Super J'aime et retour arrière (Premium) ; sans compte, les nouveautés, et le premier cœur propose de créer un compte | `GET /match/carrousel`, `POST /match/avis`, `DELETE /match/avis/{id}` |
| Proposer (+, onglet central) | S'ouvre par-dessus l'écran en cours (voir plus bas) | — |
| Échanges (onglet, pastille) | Segments À faire, Matchs (proposer l'accord), En cours, Terminés ; bandeau du Grand Troc | `GET /moi/echanges`, `GET /match`, `POST /match/accord` |
| Grand Troc | Compte à rebours, bilan du dernier, Match à trois, mes échanges possibles | `GET /grand-troc`, `GET /match/boucles`, `POST /match/boucle`, `GET /moi/boucles`, `POST /echanges` |
| Profil (onglet) | Mes objets, Mes souhaits, Favoris, Troc Premium, Mon compte, Aide et infos, déconnexion | — |
| Favoris | Le cœur (favori et J'aime du Match à la fois) : dans le compte, ou 24 h sur le téléphone sans compte ; alertes par e-mail ou SMS sans compte | `/moi/favoris`, `/match/avis`, `POST /suivis` |
| Mes objets | Mes objets et leur statut | `GET /moi/objets` |
| Un échange | Répondre (48 h), adresse pour un colis, remise et suivi, codes de retrait | `GET /moi/echanges`, `/echanges/{id}/reponse`, `/adresse`, `/depot` |
| Mon objet | Modifier, retirer ou remettre en ligne, « Qui aime ? » | `PATCH /moi/objets/{id}`, `GET /moi/objets/{id}/interesses` |
| Proposer un objet | Photo, détail, colis, lieu, lien d'annonce Vinted / Leboncoin ; sans compte, la connexion est demandée à la publication | `POST /moi/objets`, `GET /moi/photos/signature` |
| Mes souhaits | Ce qui me serait utile | `/moi/souhaits` |
| Troc Premium | Les 5 formules, essai, famille, aperçu du stock ; paiement par le lien Stripe du site | `GET /premium`, `POST /premium/essai`, `/premium/famille`, `GET /moi/apercu` |
| Mon compte | Pseudo, ville, téléphone, zones d'intérêt, mot de passe, suppression | `PATCH /moi`, `PUT /auth/mot-de-passe`, `DELETE /moi` |
| Assistant (Profil › Aide et infos) | La bulle d'aide du site | `GET /assistant`, `POST /assistant` |
| Signaler | Objet ou compte, avec ou sans compte (DSA) | `POST /signalements` |
| Aide et infos | Concept, comment ça marche, FAQ, CGU, confidentialité, mentions légales : pages du site ouvertes dans le navigateur | — |
| Connexion | Code à 6 chiffres reçu par e-mail ou mot de passe, inscription | `/auth/…` |

Le jeton de session (30 jours) est rangé dans le trousseau de l'appareil (`expo-secure-store`) et envoyé en `Authorization: Bearer …`. Le CORS de l'API ne concerne pas l'app native.

## Démarrer

Il faut Node.js 20 ou plus (https://nodejs.org) et Xcode pour le simulateur iOS.

```
cd mobile
npm install
npx expo install --fix    # aligne les versions sur le SDK Expo installé
npx expo start --ios      # ou : scanner le QR code avec Expo Go sur un téléphone
```

Expo Go doit être de la même version que le SDK du projet (SDK 54). Celui des stores ne fait tourner que le dernier SDK : sur un vrai téléphone, utiliser un build de test (ci-dessous).

Pour viser une autre API sans rien modifier : `API_URL=http://localhost:8001 npx expo start` (API locale, `make api`) ou `API_URL=https://montroc-api-preprod.onrender.com npx expo start`.

## Builds de test (EAS)

Projet Expo : [@bentester/toptroc](https://expo.dev/accounts/bentester/projects/toptroc). Identifiant de l'app : `com.toptroc.app`.

| Profil (`eas.json`) | API | App installée | Pour qui |
|---|---|---|---|
| `preview` | api.toptroc.com (production) | TopTroc, `com.toptroc.app` | testeurs : vrais comptes, vrais e-mails |
| `preprod` | montroc-api-preprod.onrender.com | TopTroc preprod, `com.toptroc.app.preprod` | recette : tous les e-mails partent à `COURRIELS_VERS` |

Les deux apps s'installent côte à côte. `app.config.js` choisit l'API, le nom et l'identifiant d'après `API_URL`.

```
npm i -g eas-cli && eas login                         # une fois
eas build -p android --profile preview                # APK à installer depuis le lien ou le QR code
eas device:create                                     # une fois par iPhone de test (lien à ouvrir sur l'iPhone)
eas build -p ios --profile preview                    # demande le compte Apple Developer au premier build
```

Build de développement (`expo-dev-client`, recharge le code depuis `npx expo start`) : `npx expo prebuild --clean && npx expo run:ios` sur le Mac, ou `eas build --profile development` (simulateur iOS, APK Android). `plugins/with-ios-27.js` le rend compatible Xcode 27 / iOS 27 (UIScene, cible iOS des pods).

Les numéros de build montent tout seuls (`appVersionSource: remote`). Pour le Play Store et l'App Store : profil `production`.

## Prochaines étapes

- Liens universels : ouvrir le lien magique `https://toptroc.com/#connexion=…` directement dans l'app.
- Notifications push pour le Grand Troc du dimanche et les échanges (il faut d'abord enregistrer les jetons d'appareil côté API).
- Troc Premium sur iPhone : l'App Store peut exiger l'achat intégré pour un abonnement numérique ; aujourd'hui l'app ouvre le lien Stripe du site.
