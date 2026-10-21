# Journal des versions

Toutes les évolutions de TrocTroc, version par version. Chaque version correspond à une étiquette Git (`v0.4.1`…) posée sur `main`.

Numérotation `vMAJEUR.MINEUR.CORRECTIF` :
- **MINEUR** monte à chaque lot de nouvelles fonctionnalités ;
- **CORRECTIF** monte pour une correction ou un petit ajustement ;
- **MAJEUR** passera à `1` au lancement public à Marseille. Avant, on reste en `0.x` (bêta).

La règle complète est dans [docs/05-git-et-branches.md](docs/05-git-et-branches.md).

## [À venir]

Ce qui est fusionné dans `main` depuis la dernière version vient ici, puis passe sous un numéro quand on étiquette.

- Site : moins de couleurs. Le jaune devient la seule couleur de marque (le violet passe en blanc cassé), catégories en pictos d'un seul trait au lieu d'émojis sur pastilles colorées, tuiles et halos de l'accueil neutres.

## [0.4.1] – 2026-10-17

- Traçabilité : ce journal des versions, le numéro de version dans le pied de page du site, et la règle de nommage des branches et des versions.

## [0.4.0] – 2026-10-17 · L'application mobile

- Application mobile TrocTroc (Expo / React Native) (#30).
- Mobile : proposer un objet, mes souhaits et accord après un match (#31).

## [0.3.0] – 2026-10-17 · Le Match et les catégories

- Le Match : carrousel « J'aime / Non merci » et accords 1 à 1 à tout moment (#20).
- Mon espace : connexion par mot de passe sous le bouton (#22), pop-up de connexion.
- « Je propose » / « Je demande » : sous-catégories, caractéristiques et description libre (#24).
- Les 10 catégories de TrocTroc et leurs 107 sous-catégories (#25).
- Matching : les dix règles du document « Catégories et caractéristiques » (#26).
- Accueil plus visuel inspiré de Vinted, titre d'onglet et favicon (#27).
- Mon espace, Proposer, fiche objet, Match en swipe et barre d'onglets pour tous (#28).
- Navigation : retour arrière avec Précédent ou le trackpad, Mon espace sur `#monespace` (#29).

## [0.2.0] – 2026-10-16 · TrocTroc, la recherche et le Grand Troc

- Nouveau nom TrocTroc : thème sombre, accueil animé, logo et textes revus (#12).
- Ville pilote : Aix-Marseille remplace Lyon (#13).
- Recherche libre sans compte, et le pluriel trouve le singulier (#14, #15).
- « Votre annonce ne part pas ? Troquez-la. » : recopier une annonce Vinted ou Leboncoin (#16).
- Grand Troc du dimanche : un math trade par semaine, prévenu par e-mail et SMS (#17).
- Math trade exact (OR-Tools), « je le donne contre… », fiabilité et repêchage du mardi (#18).
- Menu du site, pied de page et pages Pros, Collectivités, FAQ et légales (#19).

## [0.1.0] – 2026-10-14 · Le site réel

- Étape 1 : connexion par lien magique, site branché sur l'API, photos, e-mails, dépôts et signalements (#10).
- Envoi des e-mails par l'API de Brevo (#11).
- Avant : mise en place du dépôt, domaine troctroc.fr et documentation d'hébergement (#1 à #9).

[À venir]: https://github.com/benchamply-cmyk/montroc/compare/v0.4.1...main
[0.4.1]: https://github.com/benchamply-cmyk/montroc/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/benchamply-cmyk/montroc/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/benchamply-cmyk/montroc/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/benchamply-cmyk/montroc/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/benchamply-cmyk/montroc/releases/tag/v0.1.0
