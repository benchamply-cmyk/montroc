# Comptes, e-mails, photos et modération (étape 1)

Ce que l'étape 1 a ajouté, et ce qu'il faut configurer **de tes mains** pour que le premier troc fonctionne en ligne. Aucun secret n'est dans le dépôt : tout passe par les variables d'environnement de Render et un secret GitHub.

## Ce que fait le site maintenant

1. **Connexion par lien magique** : on saisit son e-mail, on reçoit un lien valable 20 minutes, à usage unique. À la première connexion, on choisit un pseudo et une ville. La session dure 30 jours.
2. **Site branché sur l'API** : mes objets, mes souhaits (par catégorie), mes échanges possibles, accepter / refuser, dépôt.
3. **Photo et état obligatoires** : impossible de publier un objet sans les deux (vérifié par le site, par l'API et par la base).
4. **E-mails aux moments clés** : « Une boucle vous attend », « Plus que 12 h pour répondre », « C'est oui pour tout le monde : à vous de déposer », « Inès a déposé », « Tout est déposé : votre objet vous attend », « Échange annulé ».
5. **Signalement et modération** : un bouton « Signaler » sur les objets des autres, un onglet « Modération » pour les comptes modérateurs, des décisions motivées envoyées par e-mail.

## 1. E-mails : une adresse OVH qui envoie

Les e-mails partent par le serveur SMTP d'OVH (offre Startup, déjà payée).

1. Espace client OVH → **Web Cloud → E-mails → troctroc.fr** : crée l'adresse `bonjour@troctroc.fr` (ou utilise une adresse existante) et choisis un mot de passe long, **différent** de celui du compte OVH.
2. Vérifie qu'elle fonctionne : connecte-toi au webmail OVH avec cette adresse.
3. Recommandé contre les spams : dans **E-mails → troctroc.fr**, active **DKIM** si OVH le propose, et ne touche pas aux lignes **SPF** et **MX** de la zone DNS.

Réglages utilisés par l'API (déjà par défaut) : serveur `ssl0.ovh.net`, port `465` (SSL), identifiant = l'adresse complète.

## 2. Photos : un compte Cloudinary gratuit

1. Crée un compte sur [cloudinary.com](https://cloudinary.com/users/register_free) (offre gratuite : largement assez pour démarrer).
2. Tableau de bord → **Settings → API Keys** (ou la page d'accueil du *Product Environment*) : copie la ligne **API environment variable**, qui ressemble à `cloudinary://123456789:AbCdEf…@nom-du-cloud`.
3. C'est la valeur de `CLOUDINARY_URL` ci-dessous. Elle contient un secret : ne la colle nulle part ailleurs que dans Render.

Les photos sont réduites dans le navigateur (1600 px, ce qui efface aussi la position GPS) puis envoyées directement à Cloudinary, dans le dossier `objets`.

## 3. Variables d'environnement sur Render

Render → service **montroc-api** → **Environment** → *Add Environment Variable*, puis **Save, rebuild and deploy** :

| Variable | Valeur |
|---|---|
| `SMTP_UTILISATEUR` | `bonjour@troctroc.fr` |
| `SMTP_MOT_DE_PASSE` | le mot de passe de cette adresse |
| `EMAIL_EXPEDITEUR` | `Troc <bonjour@troctroc.fr>` (même adresse que ci-dessus) |
| `CLOUDINARY_URL` | la ligne copiée à l'étape 2 |
| `MODERATEURS` | ton e-mail de connexion à Troc, ex. `ben.champly@gmail.com` (plusieurs : séparés par des virgules) |
| `TACHES_SECRET` | une longue chaîne au hasard (ex. 40 caractères générés par ton gestionnaire de mots de passe) |
| `POINT_DE_DEPOT` | le lieu de dépôt, ex. `Ressourcerie La Boucle, 12 rue d'Austerlitz, mar.–sam. 10 h–19 h` |
| `SITE_URL` | `https://troctroc.fr` (déjà la valeur par défaut) |

Au redémarrage, la migration `0003` s'applique toute seule. Les objets déjà publiés sans photo passent en « retiré » : leur propriétaire peut en publier de nouveaux avec photo.

## 4. Tâches planifiées : un secret GitHub

Render gratuit n'a pas de tâches planifiées : c'est GitHub Actions ([`.github/workflows/taches.yml`](../.github/workflows/taches.yml)) qui appelle l'API toutes les heures (rappels « plus que 12 h », échanges expirés) et chaque nuit (math trade sur tout le marché).

1. GitHub → dépôt **montroc** → **Settings → Secrets and variables → Actions → New repository secret**.
2. Nom : `TACHES_SECRET`, valeur : **la même** que dans Render.
3. Pour vérifier : onglet **Actions → Tâches planifiées → Run workflow**. L'étape « Appel » doit afficher `{"rappels_envoyes":0,"echanges_expires":0}`.

## 5. Vérifier le premier troc

1. Sur https://troctroc.fr, saisis ton e-mail : le lien arrive (regarde les spams la première fois et marque-le « pas un spam »).
2. Choisis ton pseudo, publie un objet avec photo, ajoute un souhait.
3. Avec un deuxième compte (une autre adresse), publie l'objet que tu souhaites et souhaite le tien : l'échange apparaît dans « Échanges possibles ».
4. Ton compte modérateur voit l'onglet **Modération**.

## Modération et DSA

Troc héberge des contenus publiés par ses utilisateurs (photos, descriptions) : le règlement européen sur les services numériques (DSA) s'applique. Ce qui est en place :

- **Mécanisme de notification (art. 16)** : n'importe qui peut signaler un objet ou un compte, avec ou sans compte (sans compte, un e-mail est demandé). Un accusé de réception est envoyé, et les modérateurs sont prévenus par e-mail.
- **Exposé des motifs (art. 17)** : chaque décision est rédigée par un modérateur et envoyée à la personne concernée, avec la mesure prise (objet retiré, compte suspendu), la mention qu'une personne (pas un automate) a décidé, et le moyen de contester (répondre à l'e-mail).
- **Information de l'auteur du signalement** : il reçoit la suite donnée.
- **Historique** : les signalements et décisions restent en base, même si l'objet ou le compte est supprimé (utile pour le rapport de transparence).

Reste à faire (hors étape 1, voir la [feuille de route](05-git-et-branches.md#feuille-de-route)) : mentions légales et point de contact (art. 11 et 12, ex. `contact@troctroc.fr`), conditions d'utilisation avec les règles de modération (art. 14), rapport de transparence annuel.
