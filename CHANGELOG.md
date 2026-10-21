# Journal des versions

Toutes les évolutions de TrocTroc, version par version. Chaque version correspond à une étiquette Git (`v0.4.1`…) posée sur `main`.

Numérotation `vMAJEUR.MINEUR.CORRECTIF` :
- **MINEUR** monte à chaque lot de nouvelles fonctionnalités ;
- **CORRECTIF** monte pour une correction ou un petit ajustement ;
- **MAJEUR** passera à `1` au lancement public à Marseille. Avant, on reste en `0.x` (bêta).

La règle complète est dans [docs/05-git-et-branches.md](docs/05-git-et-branches.md).

## [À venir]

Ce qui est fusionné dans `main` depuis la dernière version vient ici, puis passe sous un numéro quand on étiquette.

## [0.5.0] – 2026-10-21 · Le math trade fiabilisé

- Math trade : un souhait comblé ne reçoit plus d'autre objet au repêchage, au Grand Troc suivant ni pendant un accord du Match (chaque transfert garde le souhait qu'il sert) (#33).
- Grand Troc : la base enregistre les boucles de 4 personnes (jusqu'à 6) ; avant, la première boucle de 4 trouvée faisait échouer tout le Grand Troc (#34).
- Math trade : un objet qui remplit plusieurs souhaits du receveur peut combler le second quand le premier est déjà servi ; le moteur exact et le mode illimité ne ratent plus ces échanges (#35).
- Math trade : l'heuristique de secours n'annonce plus un « optimal prouvé » quand elle a écarté des boucles possibles (plus de 2 objets entre deux personnes, ou un objet qui remplit plusieurs souhaits) (#37).
- Grand Troc : deux créneaux de lancement de plus le dimanche (18 h et 19 h UTC) ; en heure d'hiver, un seul tombait après 18 h à Paris (#38).
- Grand Troc : une boucle devenue impossible pendant le calcul (objet réservé entre-temps) est sautée au lieu de faire échouer tout le Grand Troc ; les chiffres enregistrés sont ceux des boucles vraiment proposées (#39).
- Grand Troc : chaque calcul garde sa trace (moteur exact ou heuristique, longueur de boucle retenue, statuts du solveur), le dimanche comme au repêchage du mardi (#40).
- Math trade : la chance qu'un membre dise oui à une boucle est son propre taux de « oui » (lissé vers 70 % tant qu'il a peu répondu), au lieu de 70 % pour tous ; un refus pèse sur les calculs suivants (#41).
- Grand Troc : le moteur exact maximise les objets échangés *attendus* (longueur × chance que tous acceptent) ; une boucle de 4 incertaine cède la place à une boucle de 3 plus sûre qui lui dispute un objet (réglage `OBJECTIF_GRAND_TROC`, `echanges` pour revenir à l'ancien calcul) (#42).
- Site : moins de couleurs, pictogrammes au trait et une seule couleur d'accent (#43).
- Dépôt : la vieille copie du moteur dans `algorithme/build/` (du 13 octobre) n'est plus suivie par Git ; une installation locale ne peut plus la prendre à la place du code actuel (#44).

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
