/* TopTroc Pro : le profil professionnel dans Mon espace (secteur, entreprise, SIRET) et la catégorie réservée
   au secteur, ajoutée aux formulaires « Proposer » et « Je demande ». Le badge « Pro vérifié » vient de la
   modération, après contrôle du SIRET.
   Chargé après le script principal de index.html, dont il reprend api(), esc(), toast(), moi, store… */
const Pro = (() => {
  const SECTEURS = {batiment: 'Artisans du bâtiment', auto_moto: 'Garages auto et moto', alimentaire: 'Commerces alimentaires et restaurants'};
  const PICTO = '<path d="M3 21h18M5 21V8l7-5 7 5v13M9 21v-6h6v6"/>';
  let categoriePro = null;

  /* La catégorie Pro du secteur, en plus des catégories de tous dans les formulaires. */
  async function ajouterCategorie() {
    const slug = moi?.pro?.categorie_slug;
    document.querySelectorAll('[data-categorie-pro]').forEach(x => { if (x.dataset.categoriePro !== slug) x.remove(); });
    if (!slug || !$('#cat-obj').children.length) return;
    if (categoriePro?.slug !== slug) {
      const cats = await api('/categories?pro=true').catch(() => []);
      categoriePro = cats.find(c => c.slug === slug) || null;
    }
    if (!categoriePro) return;
    categories[slug] = categoriePro.libelle;
    if (!$('#cat-obj').querySelector(`[data-categorie-pro="${slug}"]`))
      $('#cat-obj').insertAdjacentHTML('afterbegin', `<label data-categorie-pro="${esc(slug)}"><input type="radio" name="categorie_slug" value="${esc(slug)}" required><span><svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${PICTO}</svg>${esc(categoriePro.libelle)}</span></label>`);
    if (!$('#cat-wish').querySelector(`[data-categorie-pro="${slug}"]`))
      $('#cat-wish').options[0].insertAdjacentHTML('afterend', `<option data-categorie-pro="${esc(slug)}" value="${esc(slug)}">${esc(categoriePro.libelle)}</option>`);
  }

  function formulaire(p) {
    return `<form class="stack" id="f-pro">
      <label class="field"><span>Secteur</span><select class="input" name="secteur" required>
        ${Object.entries(SECTEURS).map(([k, l]) => `<option value="${k}"${p?.secteur === k ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select></label>
      <label class="field"><span>Nom de l'entreprise</span><input class="input" name="raison_sociale" required minlength="2" maxlength="120" value="${esc(p?.raison_sociale || '')}" autocomplete="organization"></label>
      <div class="grid2">
        <label class="field"><span>SIRET (14 chiffres)</span><input class="input" name="siret" required inputmode="numeric" maxlength="20" value="${esc(p?.siret || '')}" placeholder="732 829 320 00074"></label>
        <label class="field"><span>Métier (facultatif)</span><input class="input" name="metier" maxlength="80" value="${esc(p?.metier || '')}" placeholder="Plombier, garage, boulangerie…"></label>
      </div>
      <p class="muted" style="font-size:13px;margin:0">Le SIRET n'est jamais montré aux autres membres : seule l'équipe TopTroc le vérifie. Le nom de l'entreprise et le métier s'affichent sur votre profil.</p>
      <div class="btns"><button class="btn primary" type="submit">${p ? 'Enregistrer' : 'Activer mon profil Pro'}</button>${p ? '<button class="btn" type="button" id="pro-quitter">Repasser en compte particulier</button>' : ''}</div>
    </form>`;
  }

  function afficher() {
    const zone = $('#pro');
    if (!zone || !moi) return;
    const p = moi.pro;
    zone.innerHTML = p
      ? `<p><b>${esc(p.raison_sociale)}</b>${p.metier ? ` · ${esc(p.metier)}` : ''} · ${esc(SECTEURS[p.secteur])}
          <span class="pro-badge${p.verifie ? '' : ' attente'}">${p.verifie ? 'Pro vérifié' : 'SIRET en cours de vérification'}</span></p>
        <p class="muted" style="font-size:14px">Votre catégorie réservée : <a href="#categorie=${esc(p.categorie_slug)}">${esc(categoriePro?.libelle || 'catégorie Pro')}</a>. Seuls les professionnels de votre secteur y publient et y demandent.</p>
        <details><summary class="btn">Modifier mon profil Pro</summary>${formulaire(p)}</details>`
      : `<p>Artisan, garage, commerce alimentaire ou restaurant ? Activer le profil Pro ouvre une catégorie réservée aux professionnels de votre secteur, pour échanger vos surplus entre confrères. <a href="/pro/">En savoir plus</a></p>
        <details${store.get('troc.apres-connexion') === 'pro' ? ' open' : ''}><summary class="btn primary">Activer TopTroc Pro</summary>${formulaire(null)}</details>`;
    ajouterCategorie().then(() => {
      const lien = zone.querySelector('a[href^="#categorie="]');
      if (lien && categoriePro) lien.textContent = categoriePro.libelle;
    });
    if (store.get('troc.apres-connexion') === 'pro') {
      store.set('troc.apres-connexion', null);
      setTimeout(() => $('#c-pro').scrollIntoView({block: 'start', behavior: 'smooth'}), 300);
    }
  }

  $('#pro').addEventListener('submit', async e => {
    if (e.target.id !== 'f-pro') return;
    e.preventDefault();
    const f = e.target, avant = moi.pro;
    try {
      moi = await api('/pro/profil', {method: 'PUT', body: {secteur: f.secteur.value, raison_sociale: f.raison_sociale.value.trim(), siret: f.siret.value, metier: f.metier.value.trim() || null}});
      toast(avant ? 'Profil Pro enregistré' : 'Bienvenue dans TopTroc Pro !');
      afficher();
    } catch (err) { toast(err.message); }
  });
  $('#pro').addEventListener('click', async e => {
    if (!e.target.closest('#pro-quitter')) return;
    try { moi = await api('/pro/profil', {method: 'DELETE'}); toast('Compte particulier'); afficher(); }
    catch (err) { toast(err.message); }
  });

  /* Lien « Créer mon compte Pro » de la page /pro/ : Mon espace, carte TopTroc Pro, après connexion s'il le faut. */
  function ouvrir() {
    store.set('troc.apres-connexion', 'pro');
    if (!moi) return versCompte();
    go('lists');
    afficher();
  }

  return {afficher, ajouterCategorie, ouvrir};
})();
