/* Mode visiteur : tout le site sans compte, et des raisons douces d'en créer un.
   - Favoris (bouton cœur) : gardés 24 h dans le navigateur d'un visiteur, avec une fenêtre qui le dit ; pour un membre,
     le cœur pose un « J'aime » (GET /match/favoris), gardé tant que l'objet est proposé.
   - Historique des dernières recherches, sur l'appareil.
   - Suivi par e-mail ou SMS, sans compte (POST /suivis) : nouveaux objets pour ses recherches et rappel avant que
     ses favoris s'effacent. Rien ne part avant le clic sur le lien de confirmation.
   - Proposer un objet sans compte : le compte n'est demandé qu'à la dernière étape (« Publier ») ; l'annonce attend
     dans le navigateur et part dès l'inscription ou la connexion.
   Chargé après le script principal de index.html, dont il reprend api(), esc(), toast(), moi, go(), carteObjet()… */
const Visiteur = (() => {
  const DUREE = 24 * 36e5, FAVORIS_MAX = 50, RECHERCHES_MAX = 10, AVERTIR_TOUS_LES = 24 * 36e5;
  const lire = (cle, defaut) => { try { return JSON.parse(store.get(cle)) ?? defaut; } catch { return defaut; } };
  const ecrire = (cle, valeur) => store.set(cle, valeur == null ? null : JSON.stringify(valeur));
  const COEUR = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg>';
  let favorisMembre = new Map(); // objet_id → objet, pour un membre
  let attente = null; // annonce en attente (photo comprise) si le navigateur n'a pas pu tout garder

  // --- Favoris ---------------------------------------------------------------------------------------------------
  function favorisLocaux() {
    const tous = lire('troc.favoris', []), vivants = tous.filter(f => Date.now() - new Date(f.ajoute_le) < DUREE);
    if (vivants.length !== tous.length) ecrire('troc.favoris', vivants);
    return vivants;
  }
  const est = id => moi ? favorisMembre.has(id) : favorisLocaux().some(f => f.objet_id === id);
  const nombre = () => moi ? favorisMembre.size : favorisLocaux().length;
  const resteMs = f => DUREE - (Date.now() - new Date(f.ajoute_le));

  function coeur(o) {
    if (moi && o.proprietaire_id === moi.id) return '';
    const oui = est(o.id);
    return `<button class="coeur${oui ? ' oui' : ''}" type="button" data-coeur="${o.id}" aria-pressed="${oui}" aria-label="${oui ? 'Retirer des favoris' : 'Ajouter aux favoris'}" title="${oui ? 'Retirer des favoris' : 'Ajouter aux favoris'}">${COEUR}</button>`;
  }
  const objetsVus = new Map(); // ce que les cartes affichées ont montré, pour garder titre et photo dans les favoris
  function retenir(o) { if (o && o.id) objetsVus.set(o.id, o); }

  async function basculer(id) {
    const o = objetsVus.get(id) || await api('/objets/' + id).catch(() => null);
    const ajout = !est(id);
    if (moi) {
      try {
        if (ajout) {
          const r = await api('/match/avis', {method: 'POST', body: {objet_id: id, aime: true}});
          favorisMembre.set(id, o);
          toast(r.match ? `C'est un match avec ${r.match.avec.pseudo} ! Concluez-le dans Match.` : 'Ajouté à vos favoris');
          document.dispatchEvent(new Event('tt:match'));
        } else { await api('/match/avis/' + id, {method: 'DELETE'}); favorisMembre.delete(id); toast('Retiré de vos favoris'); }
      } catch (err) { toast(err.message); return; }
    } else {
      let liste = favorisLocaux().filter(f => f.objet_id !== id);
      if (ajout) {
        if (liste.length >= FAVORIS_MAX) liste = liste.slice(1);
        liste.push({objet_id: id, ajoute_le: new Date().toISOString(), titre: o?.titre || '', photo_url: o?.photo_url || null, categorie_slug: o?.categorie_slug || '', etat: o?.etat || null, proprietaire_id: o?.proprietaire_id});
      }
      ecrire('troc.favoris', liste);
      if (ajout) avertir(); else toast('Retiré de vos favoris');
      synchroniser();
    }
    rafraichir();
  }

  // Les cœurs affichés suivent l'état, le compteur de l'en-tête aussi.
  function rafraichir() {
    $$('[data-coeur]').forEach(b => {
      const oui = est(+b.dataset.coeur);
      b.classList.toggle('oui', oui); b.setAttribute('aria-pressed', oui);
      const texte = oui ? 'Retirer des favoris' : 'Ajouter aux favoris';
      if (b.classList.contains('coeur')) { b.setAttribute('aria-label', texte); b.title = texte; }
      else b.querySelector('span').textContent = oui ? 'Dans vos favoris' : 'Ajouter aux favoris';
    });
    TT.favoris(nombre());
    // La page Favoris suit (compte à rebours compris), sauf pendant une saisie dans le formulaire de suivi.
    if (vueActuelle === 'favoris' && !$('#favoris-contenu')?.contains(document.activeElement)) afficher();
  }
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-coeur]');
    if (b) { e.preventDefault(); e.stopPropagation(); basculer(+b.dataset.coeur); }
  }, true);

  /* La fenêtre des 24 h : au premier favori, puis au plus une fois par jour. Elle dit l'heure où ils s'effacent
     et propose les deux façons de les garder : le compte (pour toujours) ou un e-mail / SMS de rappel. */
  function avertir() {
    if (Date.now() - (lire('troc.favoris-averti', 0)) < AVERTIR_TOUS_LES) { toast('Ajouté à vos favoris, gardés 24 h'); return; }
    ecrire('troc.favoris-averti', Date.now());
    const fin = new Date(Date.now() + DUREE).toLocaleString('fr-FR', {weekday: 'long', hour: 'numeric', minute: '2-digit'});
    const d = fenetre('d-favoris', `<span class="sablier" aria-hidden="true">⏳</span>
      <h2>Vos favoris s'effacent dans 24 h</h2>
      <p>Sans compte, ils restent sur cet appareil jusqu'à <b>${esc(fin)}</b>, puis disparaissent.</p>
      <p class="muted">Avec un compte gratuit, ils sont gardés pour toujours, sur tous vos appareils, et TopTroc cherche l'échange qui vous les apporte.</p>
      <div class="btns colonne"><button class="acc-btn y" type="button" data-creer-compte>Créer mon compte gratuit</button>
        <button class="acc-btn g" type="button" data-vers-suivi>Me prévenir par e-mail ou SMS</button>
        <button class="linkbtn" type="button" value="non" data-fermer>Plus tard</button></div>`);
    d.showModal();
  }
  function fenetre(id, html) {
    let d = document.getElementById(id);
    if (!d) { d = document.createElement('dialog'); d.id = id; d.className = 'visiteur'; document.body.append(d); }
    d.innerHTML = `<form method="dialog" class="stack">${html}</form>`;
    return d;
  }
  document.addEventListener('click', e => {
    const d = e.target.closest('dialog.visiteur'); if (!d) return;
    if (e.target.closest('[data-fermer]')) { d.close(); return; }
    if (e.target.closest('[data-creer-compte]')) { d.close(); versCompteCree(); }
    if (e.target.closest('[data-deja-compte]')) { d.close(); scrollTo({top: 0}); TT.ouvrirConnexion(true); }
    if (e.target.closest('[data-vers-suivi]')) { d.close(); go('favoris'); setTimeout(() => $('#suivi-contact')?.focus(), 50); }
  });
  function versCompteCree() { scrollTo({top: 0}); TT.ouvrirConnexion(true, undefined, true); }

  // --- Historique des recherches ---------------------------------------------------------------------------------
  const recherches = () => lire('troc.recherches', []);
  function noter(q, categorie) {
    q = (q || '').trim(); categorie = categorie || null;
    if (!q && !categorie) return;
    const liste = recherches().filter(r => !(r.q.toLowerCase() === q.toLowerCase() && (r.categorie || null) === categorie));
    liste.unshift({q, categorie, le: new Date().toISOString()});
    ecrire('troc.recherches', liste.slice(0, RECHERCHES_MAX));
    synchroniser(); afficherHistorique();
  }
  const libelleRecherche = r => r.q ? `« ${r.q} »${r.categorie ? ' · ' + (categories[r.categorie] || r.categorie) : ''}` : (categories[r.categorie] || r.categorie);
  function puces(liste) {
    return liste.map((r, i) => `<button type="button" class="puce" data-recherche="${i}">${esc(libelleRecherche(r))}</button>`).join('');
  }
  function afficherHistorique() {
    const zone = $('#search-historique'); if (!zone) return;
    const liste = recherches().slice(0, 5);
    zone.hidden = !liste.length;
    zone.innerHTML = liste.length ? `<span class="muted">Vos recherches récentes</span>${puces(liste)}` : '';
  }
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-recherche]'); if (!b) return;
    const r = recherches()[+b.dataset.recherche]; if (r) chercher(r.q, r.categorie || '');
  });

  // --- Suivi par e-mail ou SMS, sans compte ----------------------------------------------------------------------
  const suivi = () => lire('troc.suivi', null); // {jeton, contact, confirme} ou {demande: contact}
  const listes = () => ({
    recherches: recherches().map(r => ({q: r.q, categorie: r.categorie || null})),
    favoris: favorisLocaux().map(f => ({objet_id: f.objet_id, ajoute_le: f.ajoute_le})),
  });
  let minuteur;
  function synchroniser() {
    const s = suivi(); if (!s || !s.jeton || moi) return;
    clearTimeout(minuteur);
    minuteur = setTimeout(() => api('/suivis/' + encodeURIComponent(s.jeton), {method: 'PUT', body: listes()}).catch(err => {
      if (/plus valable/.test(err.message)) ecrire('troc.suivi', null);
    }), 1500);
  }
  async function demanderSuivi(contact) {
    const email = contact.includes('@');
    await api('/suivis', {method: 'POST', body: {...(email ? {email: contact} : {telephone: contact}), ...listes()}});
    ecrire('troc.suivi', {demande: contact});
  }
  async function confirmerSuivi(jeton) {
    try {
      const s = await api('/suivis/' + encodeURIComponent(jeton) + '/confirmer', {method: 'POST'});
      ecrire('troc.suivi', {jeton, contact: s.email || s.telephone, confirme: true});
      synchroniser(); go('favoris', {remplacer: true});
      toast('Suivi activé : vous serez prévenu des nouveautés et avant que vos favoris s\'effacent.');
    } catch (err) { go('favoris', {remplacer: true}); toast(err.message); }
  }
  async function arreterSuivi(lien) {
    const s = suivi();
    try {
      if (lien) await api('/suivis/arret/' + encodeURIComponent(lien), {method: 'POST'});
      else if (s && s.jeton) await api('/suivis/' + encodeURIComponent(s.jeton), {method: 'DELETE'});
      ecrire('troc.suivi', null); toast('Suivi arrêté : nous ne vous écrirons plus.');
    } catch (err) { toast(err.message); }
    go('favoris', {remplacer: true});
  }

  // --- Page « Favoris » ------------------------------------------------------------------------------------------
  const duree = ms => { const min = Math.max(1, Math.ceil(ms / 6e4)), h = Math.floor(min / 60), m = min % 60; return h ? `${h} h ${String(m).padStart(2, '0')}` : `${m} min`; };
  function carteFavori(f) {
    const o = {id: f.objet_id, titre: f.titre, photo_url: f.photo_url, categorie_slug: f.categorie_slug, etat: f.etat, proprietaire_id: f.proprietaire_id};
    retenir(o);
    const reste = resteMs(f);
    return carteObjet(o).replace('<div class="ph">', `<div class="ph"><span class="expire${reste < 6 * 36e5 ? ' bientot' : ''}" title="s'efface dans ${duree(reste)}"><span aria-hidden="true">⏳</span> ${duree(reste)}</span>`);
  }
  function blocSuivi() {
    const s = suivi();
    if (s && s.confirme) return `<div class="card stack suivi-actif"><b>Suivi activé</b>
      <span class="muted">Nous écrivons à <b>${esc(s.contact)}</b> quand un objet arrive pour vos recherches, et avant que vos favoris s'effacent. Au plus un message par jour.</span>
      <button class="linkbtn" type="button" data-arreter-suivi>Arrêter le suivi et effacer mes données</button></div>`;
    return `<form class="card stack" id="f-suivi">
      <b>Être prévenu, sans compte</b>
      <span class="muted">Un nouvel objet pour vos recherches, un favori qui va s'effacer : laissez un e-mail ou un portable, nous vous prévenons. Au plus un message par jour, arrêt en un clic.</span>
      ${s && s.demande ? `<p class="status">Lien de confirmation envoyé à ${esc(s.demande)} : ouvrez-le pour activer le suivi.</p>` : ''}
      <div class="lieu-ligne"><input class="input" id="suivi-contact" name="contact" required maxlength="254" autocomplete="email" placeholder="E-mail ou 06 12 34 56 78" aria-label="E-mail ou téléphone">
        <button class="acc-btn y" type="submit">Me prévenir</button></div>
      <span class="muted petit">Vos recherches et vos favoris sont envoyés à TopTroc pour ces alertes seulement, puis effacés après 6 mois sans visite. <a href="/confidentialite/">Confidentialité</a></span>
    </form>`;
  }
  async function afficher() {
    const zone = $('#favoris-contenu'); if (!zone) return;
    let cartes, entete;
    if (moi) {
      try { favorisMembre = new Map((await api('/match/favoris')).map(o => [o.id, o])); TT.favoris(favorisMembre.size); } catch (err) { toast(err.message); }
      const liste = [...favorisMembre.values()]; liste.forEach(retenir);
      cartes = liste.map(carteObjet).join('');
      entete = `<p class="muted">Vos favoris restent tant que l'objet est proposé. Ils comptent comme des « J'aime » : si son propriétaire aime un de vos objets, c'est un match.</p>`;
    } else {
      const liste = favorisLocaux().sort((a, b) => resteMs(a) - resteMs(b));
      cartes = liste.map(carteFavori).join('');
      entete = `<div class="avertissement-24h" role="note"><span class="sablier" aria-hidden="true">⏳</span><div>
        <b>${liste.length ? `Vos favoris s'effacent 24 h après leur ajout : le prochain dans ${duree(resteMs(liste[0]))}.` : 'Sans compte, vos favoris sont gardés 24 h sur cet appareil.'}</b>
        <span>Créez votre compte gratuit pour les garder pour toujours et recevoir les propositions d'échange.</span></div>
        <button class="acc-btn y" type="button" data-creer-compte-page>Garder mes favoris</button></div>`;
    }
    const historique = recherches();
    zone.innerHTML = entete
      + (cartes ? `<div class="results">${cartes}</div>` : `<p class="empty">Aucun favori pour l'instant. Touchez le cœur d'un objet pour le retrouver ici. <a href="/#objets">Voir les objets</a></p>`)
      + `<section class="favoris-historique"><div class="list-head"><h3>Vos recherches récentes</h3>${historique.length ? '<button class="linkbtn" type="button" data-effacer-historique>Effacer l\'historique</button>' : ''}</div>
        ${historique.length ? `<div class="puces-recherches">${puces(historique)}</div>` : '<p class="muted">Vos recherches apparaîtront ici, sur cet appareil seulement.</p>'}</section>`
      + (moi ? '' : blocSuivi());
  }
  document.addEventListener('click', e => {
    if (e.target.closest('[data-creer-compte-page]')) versCompteCree();
    if (e.target.closest('[data-effacer-historique]')) { ecrire('troc.recherches', []); synchroniser(); afficher(); afficherHistorique(); }
    if (e.target.closest('[data-arreter-suivi]')) arreterSuivi();
  });
  document.addEventListener('submit', async e => {
    if (e.target.id !== 'f-suivi') return;
    e.preventDefault();
    const b = e.target.querySelector('button[type=submit]'), contact = e.target.contact.value.trim();
    if (contact.includes('@') && !/^\S+@\S+\.\S+$/.test(contact)) { toast('Vérifiez l\'e-mail.'); return; }
    b.disabled = true;
    try { await demanderSuivi(contact); toast('Regardez vos messages : un lien de confirmation vient de partir.'); afficher(); }
    catch (err) { toast(err.message); } finally { b.disabled = false; }
  });

  // --- Proposer un objet sans compte : le compte à la dernière étape -----------------------------------------------
  const lu = blob => new Promise((ok, ko) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = ko; r.readAsDataURL(blob); });
  async function garderAnnonce(f) {
    const fichier = f.photo.files[0];
    const annonce = {
      titre: f.titre.value, categorie_slug: f.categorie_slug.value, sous_categorie_slug: f.sous_categorie_slug.value,
      caracteristiques: Detail.valeurs(f), etat: f.etat.value, lieu: f.lieu.value, latitude: f.latitude.value, longitude: f.longitude.value,
      modes: Detail.modes(f), format_colis: f.format_colis.value, description: f.description.value, annonce_origine: f.annonce_origine.value,
      photo: fichier ? await lu(await reduire(fichier)) : null, le: new Date().toISOString(),
    };
    attente = annonce;
    try { localStorage.setItem('troc.brouillon', JSON.stringify(annonce)); }
    catch { try { localStorage.setItem('troc.brouillon', JSON.stringify({...annonce, photo: null})); } catch { /* gardée dans cet onglet seulement */ } }
    return annonce;
  }
  function derniereEtape(annonce) {
    fenetre('d-publier', `<span class="label">Dernière étape</span>
      <h2>Votre annonce est prête</h2>
      <p>« <b>${esc(annonce.titre)}</b> » sera publiée dès que vous aurez votre compte TopTroc. C'est gratuit, et c'est lui qui vous prévient quand quelqu'un veut l'échanger.</p>
      <ol class="etapes-compte"><li>Indiquez votre e-mail : un lien vous arrive.</li><li>Choisissez votre pseudo et un mot de passe.</li><li>Votre annonce part toute seule.</li></ol>
      <div class="btns colonne"><button class="acc-btn y" type="button" data-creer-compte>Créer mon compte et publier</button>
        <button class="acc-btn g" type="button" data-deja-compte>J'ai déjà un compte</button>
        <button class="linkbtn" type="button" data-fermer>Revenir à l'annonce</button></div>
      <p class="muted petit">Votre annonce attend sur cet appareil. Ouvrez le lien reçu dans ce même navigateur.</p>`).showModal();
  }
  async function publierSansCompte(f) {
    const b = f.querySelector('button[type=submit]'); b.disabled = true;
    try { derniereEtape(await garderAnnonce(f)); } finally { b.disabled = false; }
  }
  // Après l'inscription ou la connexion : on remplit le formulaire avec l'annonce gardée, puis on publie.
  async function reprendre() {
    let a = attente; if (!a) try { a = JSON.parse(localStorage.getItem('troc.brouillon')); } catch { a = null; }
    if (!a || !moi) return false;
    attente = null; store.set('troc.brouillon', null);
    go('proposer'); await Detail.charger().catch(() => {});
    const f = $('#f-obj');
    f.titre.value = a.titre || '';
    const cat = f.querySelector(`input[name=categorie_slug][value="${CSS.escape(a.categorie_slug || '')}"]`); if (cat) cat.checked = true;
    Detail.remplir(f, false); f.sous_categorie_slug.value = a.sous_categorie_slug || ''; Detail.remplirCaracs(f, false);
    f.querySelectorAll('[data-carac]').forEach(x => { if (a.caracteristiques?.[x.dataset.carac]) x.value = a.caracteristiques[x.dataset.carac]; });
    const etat = f.querySelector(`input[name=etat][value="${CSS.escape(a.etat || '')}"]`); if (etat) etat.checked = true;
    f.lieu.value = a.lieu || ''; f.latitude.value = a.latitude || ''; f.longitude.value = a.longitude || '';
    f.querySelectorAll('input[name=mode]').forEach(x => { x.checked = (a.modes || []).includes(x.value); });
    f.format_colis.value = a.format_colis || ''; f.description.value = a.description || ''; f.annonce_origine.value = a.annonce_origine || '';
    if (a.photo) {
      try {
        const blob = await (await fetch(a.photo)).blob(), t = new DataTransfer();
        t.items.add(new File([blob], 'photo.jpg', {type: blob.type || 'image/jpeg'})); f.photo.files = t.files;
        f.photo.dispatchEvent(new Event('change'));
      } catch { /* navigateur sans DataTransfer : la personne reprend sa photo */ }
    }
    if (f.checkValidity()) { toast('Votre compte est prêt : publication de votre annonce…'); f.requestSubmit(); }
    else { f.reportValidity(); toast(f.photo.files.length ? 'Vérifiez l\'annonce, puis publiez.' : 'Ajoutez à nouveau la photo, puis publiez.'); }
    return true;
  }

  // --- Après la connexion : les favoris du visiteur deviennent des « J'aime » du compte -------------------------------
  async function apresConnexion() {
    const locaux = favorisLocaux();
    if (locaux.length) {
      const resultats = await Promise.allSettled(locaux.map(f => api('/match/avis', {method: 'POST', body: {objet_id: f.objet_id, aime: true}})));
      ecrire('troc.favoris', []);
      const gardes = resultats.filter(r => r.status === 'fulfilled').length;
      if (gardes) toast(gardes === 1 ? 'Votre favori est gardé dans votre compte' : `Vos ${gardes} favoris sont gardés dans votre compte`);
    }
    try { favorisMembre = new Map((await api('/match/favoris')).map(o => [o.id, o])); } catch { /* le compteur attendra */ }
    rafraichir();
    return reprendre();
  }

  // Au démarrage : liens de confirmation et d'arrêt du suivi, compteur de l'en-tête.
  function demarrer(h) {
    if (h.startsWith('#suivi=')) { history.replaceState(null, '', location.pathname + '#favoris'); confirmerSuivi(decodeURIComponent(h.slice(7))); return true; }
    if (h.startsWith('#suivi-arret=')) { history.replaceState(null, '', location.pathname + '#favoris'); arreterSuivi(decodeURIComponent(h.slice(13))); return true; }
    return false;
  }
  addEventListener('storage', e => { if (['troc.favoris', 'troc.recherches'].includes(e.key)) rafraichir(); });
  setInterval(() => { if (!moi) rafraichir(); }, 60e3); // les favoris de 24 h s'effacent pendant la visite aussi
  afficherHistorique();

  return {coeur, retenir, est, basculer, noter, afficher, afficherHistorique, publierSansCompte, apresConnexion, reprendre, demarrer, rafraichir};
})();
