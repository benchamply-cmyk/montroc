# TopTroc — application mobile

App iOS et Android (Expo / React Native) branchée sur la même API que le site : `https://api.toptroc.com`.

| Onglet | Contenu | Routes de l'API |
|---|---|---|
| Objets | Catalogue public et recherche, fiche objet | `GET /objets`, `GET /objets/{id}` |
| Match | Cartes à glisser : « J'aime » / « Non merci » | `GET /match/carrousel`, `POST /match/avis` |
| Mon espace | Prochain Grand Troc, mes matchs, mes objets, déconnexion | `GET /grand-troc`, `GET /match`, `GET /moi/objets` |
| Connexion | Mot de passe, ou lien magique collé dans l'app, inscription | `POST /auth/connexion`, `/auth/lien`, `/auth/verifier` |

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
- Notifications push pour le Grand Troc du dimanche.
