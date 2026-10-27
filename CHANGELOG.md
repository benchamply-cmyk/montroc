# Journal des versions

Toutes les évolutions de TrocTroc, version par version.

Numérotation (décidée par Ben le 26/10/2026) :
* **prod** (la production) : `V5.100`, puis **+100 à chaque livraison** `preprod → prod` (`V5.200`, `V5.300`…). Chaque livraison a son étiquette Git (`V5.200`) et sa section ci-dessous ;
* **preprod** (la pré-production) : `V5.1000`, puis **+1000 à chaque PR fusionnée** dans `preprod` (`V5.2000`, `V5.3000`…), étiquette `preprod-V5.2000` posée automatiquement ;
* le **premier chiffre** monte à la prochaine version stable, quand Ben le décide : prod passe à `V6.100`, puis preprod à `V6.1000` une fois cette version en production.

Avant le 26/10/2026, les versions étaient numérotées `v0.x.y` (sections plus bas). La règle complète est dans [docs/05-git-et-branches.md](docs/05-git-et-branches.md).

## [À venir]

Chaque PR ajoute sa ligne dans un fichier de [changelog.d/](changelog.d/) ; les lignes arrivent ici à la préparation de la livraison (`python3 scripts/version.py livraison`).

## [V6.200] – 2026-10-27 · Design et UX

- Design : fond Acier bleuté avec reliefs et ombres, nouveau logo (deux T emboîtés), titre de l'accueil retravaillé, et une page dédiée pour Le concept, Comment ça marche, Le Grand Troc et Particuliers.

## [V6.100] – 2026-10-26 · TopTroc et business model V2

- Site : le bouton de langue affiche le drapeau et le code FR, EN ou ES ; les deux autres versions apparaissent au survol ou au clic, avec navigation au clavier.
- Site : sélecteur Français / English / Español et versions anglaise et espagnole de toutes les pages, avec la même arborescence et les mêmes fonctionnalités.
- TrocTroc devient TopTroc : nouveau nom sur le site, dans les e-mails, les SMS et l'app, et nouvelle adresse toptroc.com (API api.toptroc.com, contact@toptroc.com) ; troctroc.fr redirige en 301 vers toptroc.com.
- Business model V2 : remise en main propre par défaut, envoi par colis aux frais de l'expéditeur (format jusqu'à 30 kg, numéro de suivi, Garantie TopTroc), localisation de chaque objet et zones d'intérêt réglées par chacun (« Autour de moi », rayon, toute la France), et Troc Premium (Essentiel, Plus, Famille, Pro, Pass Dimanche : essai gratuit, paiement Stripe, avant-première du Grand Troc à 17 h, ShortLists des objets convoités, Super J'aime, retour arrière, priorité seulement pour départager).

## [V5.200] – 2026-10-26

- Dépôt : branche `preprod` entre les branches de travail et `prod`, lignes du journal dans `changelog.d/`, contrôle automatique des règles de branches, réglages de pré-production (e-mails redirigés, SMS coupés).
- Dépôt : la branche de production `main` devient `prod` (workflows CI, règles des branches, versions, render.yaml, documentation, lien du journal en pied de page).
- Pré-production : les e-mails partent de contact@troctroc.fr, l'expéditeur validé chez Brevo (bonjour@ n'y est pas validé, les mails n'arrivaient pas).
- Tâches horaires : l'expiration des échanges suit la même horloge que le Grand Troc ; les tests ne dépendent plus de la date du jour.
- Versions : les étiquettes preprod-V… (rattrapage de V5.1000 et V5.2000 compris) et la préparation des livraisons passent par le jeton VERSIONS_TOKEN ; le jeton par défaut de GitHub Actions est refusé quand les workflows de preprod diffèrent de prod.
- Match à trois : l'onglet Match propose aussi des boucles à trois possibles tout de suite, où chacun reçoit ce qu'il a demandé ou aimé ; dans la pile, à égalité, les objets d'un propriétaire fiable et peu convoités passent devant.
- Versions : nouvelle numérotation, prod en V5.100 (+100 à chaque livraison) et preprod en V5.1000 (+1000 à chaque PR fusionnée), étiquettes posées automatiquement ; les branches se nomment type/sujet-vX.Y ; le pied de page affiche V5.100 (ou la version preprod sur le site de pré-production).
- Grand Troc : une même personne reçoit au plus 3 objets par Grand Troc, repêchage compris ; un gros déposant ne prend plus tout le dimanche (réglage `PLAFOND_ECHANGES_GRAND_TROC`, 0 pour aucun plafond).
- Grand Troc : les « J'aime » d'un membre comptent ensemble comme un seul souhait, classé après ses souhaits déclarés ; dix coups de cœur ne font plus recevoir dix objets le même dimanche (réglage `COUPS_DE_COEUR_PAR_GRAND_TROC`, 1 par défaut).
- Pré-production en place : service Render, branche Neon et déploiement Netlify de `preprod`.
- Grand Troc : après un refus, les partenaires lâchés reçoivent une autre boucle dans l'heure avec les objets libérés, au lieu d'attendre le repêchage du mardi 18 h (migration 0018).
- Réputation : la fiche d'un objet, la carte du Match et Mon espace montrent les échanges menés au bout et une pastille « Nouveau membre », « Membre fiable » ou « Fiabilité à confirmer », tirée de la fiabilité (qui monte à chaque dépôt et baisse sans réponse ou sans dépôt).
- Points de dépôt : un lieu par ville ou quartier (réglage `POINTS_DE_DEPOT`) ; chaque échange prend celui de la zone de la plupart de ses participants, sinon le lieu par défaut `POINT_DE_DEPOT` (#64).

## [V5.100] – 2026-10-26 · Nouvelle numérotation

Version en production le 26/10/2026 (`v0.5.0` et les deux changements ci-dessous), point de départ de la numérotation `V5.x`.

- Site : une seule couleur vive (le jaune) et des pictogrammes au trait ; étapes de l'accueil « Je propose » / « Je demande », textes du Match et du Grand Troc reformulés (#43).
- Accueil : la section « Le concept » est retirée ; le lien du menu mène au haut de l'accueil (#46).
- Connexion : le formulaire « Se connecter ou créer un compte » quitte l'accueil ; tout passe par le bouton « Se connecter » en haut de page, qui gagne un mode « Créer un compte » (e-mail seul, lien magique) (#46).

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

[À venir]: https://github.com/benchamply-cmyk/montroc/compare/V6.200...preprod
[V6.200]: https://github.com/benchamply-cmyk/montroc/compare/V6.100...V6.200
[V6.100]: https://github.com/benchamply-cmyk/montroc/compare/V5.200...V6.100
[V5.200]: https://github.com/benchamply-cmyk/montroc/compare/V5.100...V5.200
[V5.100]: https://github.com/benchamply-cmyk/montroc/compare/v0.5.0...V5.100
[0.5.0]: https://github.com/benchamply-cmyk/montroc/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/benchamply-cmyk/montroc/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/benchamply-cmyk/montroc/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/benchamply-cmyk/montroc/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/benchamply-cmyk/montroc/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/benchamply-cmyk/montroc/releases/tag/v0.1.0
