/* Espace réservé (offre « Espace salariés » et « Résidences ») : une entreprise ou un bailleur ouvre un espace,
   ses membres le rejoignent par le lien /#espace=<nom-court> avec leur adresse e-mail professionnelle, puis
   réservent s'ils le veulent leurs objets à leurs collègues (remise sur place). La modération crée les espaces.
   Chargé après le script principal de index.html, dont il reprend api(), esc(), toast(), store, moi, go()… */
const Espace = (() => {
  const ATTENTE = 'troc.espace';

  /* Lien d'invitation : sans compte, on le garde le temps de la connexion ; avec un compte, on rejoint. */
  async function demarrer(h) {
    if (!h.startsWith('#espace=')) return false;
    let slug = h.slice(8); try { slug = decodeURIComponent(slug); } catch {}
    history.replaceState(null, '', location.pathname);
    store.set(ATTENTE, slug);
    if (moi) { await rejoindre(); return true; }
    try {
      const e = await api('/espaces/' + encodeURIComponent(slug));
      toast(`Espace ${e.nom} : connectez-vous avec votre adresse e-mail professionnelle pour le rejoindre.`);
    } catch (err) { store.set(ATTENTE, null); toast(err.message); return false; }
    go('home'); TT.ouvrirConnexion();
    return true;
  }

  async function rejoindre() {
    const slug = store.get(ATTENTE); if (!slug || !moi) return;
    store.set(ATTENTE, null);
    try {
      moi = await api('/espaces/' + encodeURIComponent(slug) + '/rejoindre', {method: 'POST'});
      afficherSession(); toast(`Bienvenue dans l'espace ${moi.espace.nom} : vous pouvez réserver vos objets à vos collègues.`);
      go('lists');
    } catch (err) { toast(err.message); }
  }

  async function quitter() {
    if (!confirm('Quitter cet espace ? Vos objets réservés aux collègues redeviendront visibles de tous.')) return;
    try { moi = await api('/moi/espace', {method: 'DELETE'}); afficherSession(); toast('Vous avez quitté l\'espace.'); }
    catch (err) { toast(err.message); }
  }

  /* Mon espace : la carte « Mon entreprise » ; Proposer : la case « Réservé à mes collègues ». */
  function afficher() {
    const e = moi && moi.espace, carte = document.getElementById('c-espace'), cas = document.getElementById('reserve-obj');
    if (carte) {
      carte.hidden = !e;
      if (e) {
        document.getElementById('espace-txt').innerHTML = `<p><b>${esc(e.nom)}</b></p>
          <p class="muted" style="font-size:14px">Vos objets cochés « Réservé à mes collègues » ne sont vus que des membres de l'espace et se remettent sur place${e.lieu_de_remise ? ' : ' + esc(e.lieu_de_remise) : ''}.</p>
          <div class="btns"><button class="btn" type="button" data-espace-collegues>Voir les objets des collègues</button><button class="btn" type="button" data-espace-quitter>Quitter l'espace</button></div>`;
      }
    }
    if (cas) { cas.hidden = !e; if (e) cas.querySelector('[data-espace-nom]').textContent = e.nom; else cas.querySelector('input').checked = false; }
    if (moi) rejoindre();
  }

  async function collegues() {
    go('search', {adresse: '#objets'});
    document.getElementById('search-title').textContent = moi.espace.nom;
    document.getElementById('search-count').textContent = '';
    document.getElementById('search-plus').hidden = true;
    const zone = document.getElementById('results');
    try {
      const objets = await api('/objets?espace=true');
      zone.innerHTML = objets.length ? objets.map(carteObjet).join('')
        : '<p class="empty">Aucun objet réservé pour l\'instant. Soyez le premier à en proposer un à vos collègues.</p>';
    } catch (err) { toast(err.message); }
  }

  document.addEventListener('click', e => {
    if (e.target.closest('[data-espace-quitter]')) quitter();
    else if (e.target.closest('[data-espace-collegues]')) collegues();
  });

  /* Modération : créer, ouvrir ou fermer les espaces vendus aux clients. */
  async function moderation() {
    const bloc = document.getElementById('mod-espaces'); if (!bloc) return;
    let liste; try { liste = await api('/moderation/espaces'); } catch (err) { bloc.innerHTML = `<p class="err">${esc(err.message)}</p>`; return; }
    const lien = s => location.origin + location.pathname + '#espace=' + encodeURIComponent(s);
    bloc.querySelector('[data-liste]').innerHTML = liste.length ? liste.map(e => `<div class="item" style="border:0;padding:0"><div class="t">
        <b>${esc(e.nom)}</b>${e.actif ? '' : ' <span class="tag">Fermé</span>'}
        <span>${e.domaines.map(d => '@' + esc(d)).join(', ')} · ${e.membres} membre(s) · ${e.objets_en_ligne} objet(s) en ligne${e.lieu_de_remise ? ' · ' + esc(e.lieu_de_remise) : ''}</span>
        <span class="muted" style="font-size:13px;display:block;word-break:break-all">Lien d'invitation : ${esc(lien(e.slug))}</span></div>
        <button class="btn" type="button" data-basculer="${e.id}">${e.actif ? 'Fermer' : 'Rouvrir'}</button></div>`).join('')
      : '<p class="muted">Aucun espace pour l\'instant.</p>';
    bloc.querySelectorAll('[data-basculer]').forEach(b => b.onclick = async () => {
      const e = liste.find(x => x.id === +b.dataset.basculer);
      try { await api('/moderation/espaces/' + e.id, {method: 'PUT', body: {slug: e.slug, nom: e.nom, domaines: e.domaines, lieu_de_remise: e.lieu_de_remise, formule: e.formule, actif: !e.actif}}); moderation(); }
      catch (err) { toast(err.message); }
    });
  }
  const f = document.getElementById('f-espace');
  if (f) f.onsubmit = async ev => {
    ev.preventDefault();
    try {
      await api('/moderation/espaces', {method: 'POST', body: {slug: f.slug.value.trim(), nom: f.nom.value.trim(),
        domaines: f.domaines.value.split(/[,\s;]+/).filter(Boolean), lieu_de_remise: f.lieu_de_remise.value.trim() || null, formule: f.formule.value || null}});
      f.reset(); toast('Espace créé : envoyez son lien d\'invitation au client.'); moderation();
    } catch (err) { toast(err.message); }
  };

  return {demarrer, afficher, moderation};
})();
if (moi) Espace.afficher();
