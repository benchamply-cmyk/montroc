# Mise en ligne de montroc.fr, étape par étape

Ordre conseillé : **domaine → base → API → site → DNS → vérifications**. Chaque étape se fait sur ton compte, de tes mains ; rien n'est payant à part le domaine.

Coche au fur et à mesure :

- [ ] 1. Domaine montroc.fr acheté chez OVH (sans hébergement)
- [ ] 2. Base PostgreSQL créée sur Neon
- [ ] 3. API déployée sur Render
- [ ] 4. Site déployé sur Netlify
- [ ] 5. DNS OVH pointés vers Netlify et Render
- [ ] 6. HTTPS actif et vérifications faites
- [ ] 7. Branche `main` protégée sur GitHub

---

## 1. Acheter le domaine chez OVH (sans hébergement)

1. Dans le panier OVH, sur l'écran **« Liez un hébergement web à votre nom de domaine »**, clique **« Ignorer cette étape »** en haut à droite (ou supprime l'hébergement *Startup* avec la corbeille dans « Votre sélection »).
   *Pourquoi :* le site est hébergé par Netlify et l'API par Render. L'hébergement mutualisé OVH ne servirait à rien (et il ne sait pas faire tourner Python).
2. Garde **DNSSEC** (inclus, gratuit).
3. Durée : 1 an suffit pour démarrer ; 3 ans évite d'oublier un renouvellement. Active le **renouvellement automatique** dans tous les cas.
4. Paie, puis attends l'e-mail « domaine activé » (quelques minutes à quelques heures pour un `.fr`).
5. Vérifie dans **Web Cloud → Noms de domaine → montroc.fr** que le domaine apparaît, avec l'onglet **Zone DNS**.

> Les adresses e-mail `@montroc.fr` ne sont pas incluses sans hébergement. Si tu en veux une plus tard : offre « MX Plan » OVH, ou redirection e-mail gratuite (onglet *E-mails* du domaine).

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
6. **Settings → Custom Domains → Add** : `api.montroc.fr`. Render affiche la cible CNAME à mettre chez OVH (`montroc-api.onrender.com`). Garde l'onglet ouvert pour l'étape 5.

> Offre gratuite Render : l'API s'endort après un moment sans visite et met quelques dizaines de secondes à se réveiller. Pour un vrai lancement public, passer à l'offre *Starter* (payante) supprime la mise en veille.

## 4. Déployer le site sur Netlify

1. Sur **https://app.netlify.com** : **Add new site → Import an existing project → GitHub**, choisis `benchamply-cmyk/montroc`.
2. Netlify lit [`netlify.toml`](../netlify.toml) : dossier publié `web`, pas de commande de build. Branche de production : **`main`**. Clique **Deploy**.
3. Vérifie l'adresse provisoire `https://<nom>.netlify.app`.
4. **Site configuration → Domain management → Add a domain** : `montroc.fr`. Netlify propose aussi `www.montroc.fr` : accepte.
5. Netlify propose d'utiliser **Netlify DNS** : refuse (« Set up DNS externally » / garder OVH). Note les valeurs qu'il affiche :
   - pour `montroc.fr` : un enregistrement **A** vers l'adresse du load balancer Netlify (actuellement `75.2.60.5`, vérifie la valeur affichée) ;
   - pour `www` : un **CNAME** vers `<nom>.netlify.app`.

## 5. Configurer la zone DNS chez OVH

Dans **Web Cloud → Noms de domaine → montroc.fr → Zone DNS** :

1. **Supprime** les entrées par défaut qui pointent vers OVH pour le domaine nu et `www` : les lignes de type **A** (et **AAAA** s'il y en a) sur `montroc.fr.` et sur `www.montroc.fr.`, et un éventuel CNAME sur `www`. Ne touche pas aux lignes **NS**, **MX**, **SPF/TXT**.
2. **Ajouter une entrée** :

| Type | Sous-domaine | Cible | Pour |
|---|---|---|---|
| A | *(vide)* | `75.2.60.5` (valeur Netlify) | montroc.fr → Netlify |
| CNAME | `www` | `<nom>.netlify.app.` | www.montroc.fr → Netlify |
| CNAME | `api` | `montroc-api.onrender.com.` | api.montroc.fr → Render |

3. Attends la propagation (de quelques minutes à quelques heures). Pour vérifier depuis un terminal :
   ```
   dig +short montroc.fr
   dig +short www.montroc.fr
   dig +short api.montroc.fr
   ```

## 6. HTTPS et vérifications

1. Netlify : **Domain management → HTTPS → Verify DNS configuration**, puis **Provision certificate** (Let's Encrypt, gratuit, renouvelé tout seul).
2. Render : le domaine `api.montroc.fr` passe en **Verified** et le certificat est émis automatiquement.
3. Vérifie :
   - `https://montroc.fr` affiche le site ;
   - `https://www.montroc.fr` redirige vers `https://montroc.fr` ;
   - `https://api.montroc.fr/sante` répond `ok` ;
   - `https://api.montroc.fr/docs` affiche la documentation de l'API.

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
| OVH | domaine montroc.fr, zone DNS | identifiants OVH (activer la double authentification) |
| Neon | base PostgreSQL (`main`, `dev`) | chaîne de connexion `DATABASE_URL` |
| Render | API `montroc-api` → `api.montroc.fr` | aucun en plus (DATABASE_URL y est stockée) |
| Netlify | site → `montroc.fr` | aucun |
| GitHub | code, CI, pull requests | — |

Active la **double authentification** sur les cinq comptes.
