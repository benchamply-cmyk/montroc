# Mise en ligne de troctroc.fr, étape par étape

Ordre conseillé : **domaine → base → API → site → DNS → vérifications**. Chaque étape se fait sur ton compte, de tes mains ; seul OVH est payant (domaine + offre Startup pour les e-mails).

Coche au fur et à mesure :

- [ ] 1. Domaines troctroc.fr (principal) et troctroc.cloud (alias) + offre Startup chez OVH, adresses e-mail créées
- [ ] 2. Base PostgreSQL créée sur Neon
- [ ] 3. API déployée sur Render
- [ ] 4. Site déployé sur Netlify
- [ ] 5. DNS OVH pointés vers Netlify et Render
- [ ] 6. HTTPS actif et vérifications faites
- [ ] 7. Branche `main` protégée sur GitHub

---

## 1. Acheter le domaine chez OVH (avec l'offre Startup)

Choix retenu : domaine **troctroc.fr + hébergement Startup**, pris pour ses services annexes, pas pour héberger le site :

- **10 adresses e-mail** `@troctroc.fr` (5 Go chacune) : c'est l'intérêt principal (`contact@`, `bonjour@`, `ben@`…) ;
- **domaine offert la première année** ;
- un espace web OVH (100 Go, 15 sites, sauvegardes) qui reste disponible pour d'éventuelles pages annexes, mais **le site troctroc.fr est servi par Netlify** et l'API Python par Render (l'hébergement mutualisé ne fait pas tourner Python).

Étapes :
1. Garde **DNSSEC** (inclus) et active le **renouvellement automatique** du domaine et de l'hébergement.
2. Paie, puis attends l'e-mail « domaine activé » (quelques minutes à quelques heures pour un `.fr`).
3. Dans **Web Cloud → Noms de domaine → troctroc.fr**, vérifie l'onglet **Zone DNS**.
4. Fais les points 1 à 3 aussi pour **troctroc.cloud**, l'alias : il ne sert qu'à rediriger vers troctroc.fr (même site, une seule adresse officielle).
5. Dans **Web Cloud → E-mails** (ou *Hébergements → troctroc.fr → E-mails*), crée tes adresses. Les enregistrements **MX** qui font marcher ces e-mails sont créés par OVH : **ne jamais les supprimer**.

## 2. Créer la base PostgreSQL sur Neon

1. Crée un compte sur **https://neon.tech** (connexion avec GitHub possible).
2. **Create project** :
   - Project name : `montroc`
   - Postgres version : **16**
   - Region : **AWS Europe Central 1 (Frankfurt)**
   - Database name : `montroc`
3. Neon crée une branche de base **`main`** (la production). Dans **Dashboard → Connect**, copie la **connection string** (format `postgresql://utilisateur:motdepasse@ep-xxx.eu-central-1.aws.neon.tech/montroc?sslmode=require`).
   - Garde-la dans ton gestionnaire de mots de passe. **Ne la colle jamais dans le code ni dans GitHub.**
4. Recommandé : **Branches → Create branch** `dev` (copie de `main`), pour essayer des migrations sans risque.

Le schéma (tables, contraintes) n'est pas créé à la main : l'API applique les migrations à chaque démarrage.

## 3. Déployer l'API sur Render

1. Crée un compte sur **https://render.com** avec ton compte GitHub, et autorise l'accès au dépôt `benchamply-cmyk/montroc`.
2. **New → Blueprint**, choisis le dépôt `montroc`. Render lit le fichier [`render.yaml`](../render.yaml) et propose le service **montroc-api** (Frankfurt, offre gratuite).
3. Render demande la valeur de **`DATABASE_URL`** : colle la chaîne de connexion Neon de l'étape 2.
4. **Apply**. Le premier déploiement installe Python, applique les migrations et démarre l'API.
5. Vérifie : ouvre `https://montroc-api.onrender.com/sante` (le nom exact est affiché par Render). Tu dois voir `{"statut":"ok",...}`. La documentation interactive est sur `/docs`.
6. **Settings → Custom Domains → Add** : `api.troctroc.fr`. Render affiche la cible CNAME à mettre chez OVH (`montroc-api.onrender.com`). Garde l'onglet ouvert pour l'étape 5.

> Offre gratuite Render : l'API s'endort après un moment sans visite et met quelques dizaines de secondes à se réveiller. Pour un vrai lancement public, passer à l'offre *Starter* (payante) supprime la mise en veille.

## 4. Déployer le site sur Netlify

1. Sur **https://app.netlify.com** : **Add new project → Import an existing project → GitHub** (Netlify appelle désormais les sites des « projects »), choisis `benchamply-cmyk/montroc`.
2. Netlify lit [`netlify.toml`](../netlify.toml) : dossier publié `web`, pas de commande de build. Branche de production : **`main`**. Clique **Deploy**.
3. Vérifie l'adresse provisoire `https://<nom>.netlify.app`.
4. **Project configuration → Domain management → Add a domain** : `troctroc.fr`. Netlify propose aussi `www.troctroc.fr` : accepte. Vérifie que `troctroc.fr` est marqué **Primary domain**.
5. **Add a domain alias** : `troctroc.cloud`, puis `www.troctroc.cloud`. Les redirections 301 vers `troctroc.fr` sont déjà écrites dans [`netlify.toml`](../netlify.toml).
6. Netlify propose d'utiliser **Netlify DNS** : refuse (« Set up DNS externally » / garder OVH). Note les valeurs qu'il affiche :
   - pour `troctroc.fr` : un enregistrement **A** vers l'adresse du load balancer Netlify (actuellement `75.2.60.5`, vérifie la valeur affichée) ;
   - pour `www` : un **CNAME** vers `<nom>.netlify.app`.

## 5. Configurer la zone DNS chez OVH

Dans **Web Cloud → Noms de domaine → troctroc.fr → Zone DNS** :

1. **Supprime** les entrées par défaut qui pointent vers l'hébergement OVH pour le domaine nu et `www` : les lignes de type **A** (et **AAAA** s'il y en a) sur `troctroc.fr.` et sur `www.troctroc.fr.`, et un éventuel CNAME sur `www`. Ne touche pas aux lignes **NS**, **MX**, **SPF/TXT** (DKIM, autodiscover) : ce sont tes e-mails.
2. **Ajouter une entrée** :

| Type | Sous-domaine | Cible | Pour |
|---|---|---|---|
| A | *(vide)* | `75.2.60.5` (valeur Netlify) | troctroc.fr → Netlify |
| CNAME | `www` | `<nom>.netlify.app.` | www.troctroc.fr → Netlify |
| CNAME | `api` | `montroc-api.onrender.com.` | api.troctroc.fr → Render |

3. Attends la propagation (de quelques minutes à quelques heures). Pour vérifier depuis un terminal :
   ```
   dig +short troctroc.fr
   dig +short www.troctroc.fr
   dig +short api.troctroc.fr
   ```
4. Même chose dans **Noms de domaine → troctroc.cloud → Zone DNS**, avec seulement deux lignes (pas d'`api`, pas d'e-mails nécessaires sur l'alias) :

| Type | Sous-domaine | Cible | Pour |
|---|---|---|---|
| A | *(vide)* | `75.2.60.5` (valeur Netlify) | troctroc.cloud → Netlify → redirigé vers troctroc.fr |
| CNAME | `www` | `<nom>.netlify.app.` | www.troctroc.cloud → Netlify → redirigé vers troctroc.fr |

## 6. HTTPS et vérifications

1. Netlify : **Domain management → HTTPS → Verify DNS configuration**, puis **Provision certificate** (Let's Encrypt, gratuit, renouvelé tout seul).
2. Render : le domaine `api.troctroc.fr` passe en **Verified** et le certificat est émis automatiquement.
3. Vérifie :
   - `https://troctroc.fr` affiche le site ;
   - `https://www.troctroc.fr`, `https://troctroc.cloud` et `https://www.troctroc.cloud` redirigent vers `https://troctroc.fr` ;
   - `https://api.troctroc.fr/sante` répond `ok` ;
   - `https://api.troctroc.fr/docs` affiche la documentation de l'API.

## 7. Protéger la branche `main` sur GitHub

Dans le dépôt : **Settings → Branches → Add branch ruleset** (ou *Add rule*), cible `main` :

- **Require a pull request before merging** ;
- **Require status checks to pass** : coche *Moteur d'échanges* et *API et base de données* (ils apparaissent après la première CI) ;
- **Block force pushes**.

Ainsi, rien n'arrive en production sans pull request et sans tests verts. Comme Netlify et Render déploient `main`, **fusionner une PR = mettre en ligne**.

---

## Récapitulatif des comptes et secrets

| Service | Ce qu'on y trouve | Secret à garder |
|---|---|---|
| OVH | domaines troctroc.fr et troctroc.cloud, zones DNS, e-mails (offre Startup) | identifiants OVH (activer la double authentification) |
| Neon | base PostgreSQL (`main`, `dev`) | chaîne de connexion `DATABASE_URL` |
| Render | API `montroc-api` → `api.troctroc.fr` | aucun en plus (DATABASE_URL y est stockée) |
| Netlify | site → `troctroc.fr` (alias `troctroc.cloud`) | aucun |
| GitHub | code, CI, pull requests | — |

Active la **double authentification** sur les cinq comptes.
