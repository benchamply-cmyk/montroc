# TrocTroc — application mobile

App iOS et Android (Expo / React Native) branchée sur la même API que le site : `https://api.troctroc.fr`.

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

Pour viser une API locale (`make api`), remplacer `extra.api` dans `app.json` par `http://localhost:8001`.

## Prochaines étapes

- Proposer un objet depuis l'app (photo avec l'appareil, envoi signé Cloudinary via `GET /moi/photos/signature`).
- Souhaits (« Je demande ») et accord 1 à 1 depuis un match (`POST /match/accord`).
- Liens universels : ouvrir le lien magique `https://troctroc.fr/#connexion=…` directement dans l'app.
- Notifications push pour le Grand Troc du dimanche.
