/* Business model V2 : localisation des objets et zones d'intérêt (à la Leboncoin : une ville ou « autour de moi »,
   un rayon, ou toute la France par colis), ShortList « Qui aime ? », Troc Premium et encart publicitaire.
   Les villes viennent de la Base Adresse Nationale (api-adresse.data.gouv.fr), sans clé ni pistage ; les positions
   sont arrondies à environ 1 km avant d'être envoyées.
   Chargé après le script principal de index.html et match.js, dont il reprend api(), esc(), toast(), moi… */
const Premium = (() => {
  const BAN = 'https://api-adresse.data.gouv.fr';
  const AVANTAGES = {
    sans_pub: 'Sans publicité', voir_qui_aime: 'Voir qui aime vos objets', retour_arriere: 'Retour arrière dans le Match',
    apercu_du_stock: 'Aperçu du stock du dimanche', avant_premiere: 'Avant-première du Grand Troc à 17 h',
    shortlist: 'En tête des ShortLists', priorite: 'Priorité à égalité au Grand Troc', zones_multiples: "Jusqu'à 3 zones d'intérêt",
    garantie_colis: 'Garantie TrocTroc sur vos colis', famille: '3 proches inclus',
  };
  const arrondi = x => Math.round(x * 100) / 100;
  const euros = x => x == null ? '' : x.toLocaleString(document.documentElement.lang || 'fr', {style: 'currency', currency: 'EUR'});
  let catalogue = null;

  /* Villes : suggestions pendant la frappe, et « Autour de moi » par la position du navigateur. */
  const trouvees = new Map();
  async function villes(q) {
    if (q.trim().length < 3) return [];
    try {
      const r = await fetch(`${BAN}/search/?type=municipality&limit=6&q=${encodeURIComponent(q)}`);
      const d = await r.json();
      return d.features.map(f => ({libelle: `${f.properties.city} (${f.properties.postcode})`, latitude: f.geometry.coordinates[1], longitude: f.geometry.coordinates[0]}));
    } catch { return []; }
  }
  function suggerer(input, liste) {
    let attente;
    input.addEventListener('input', () => {
      clearTimeout(attente);
      attente = setTimeout(async () => {
        const r = await villes(input.value); r.forEach(v => trouvees.set(v.libelle, v));
        liste.innerHTML = r.map(v => `<option value="${esc(v.libelle)}"></option>`).join('');
      }, 250);
    });
  }
  const choisie = libelle => trouvees.get(libelle.trim()) || null;
  function autourDeMoi() {
    return new Promise((ok, ko) => {
      if (!navigator.geolocation) return ko(new Error("Votre navigateur ne donne pas votre position : tapez votre ville."));
      navigator.geolocation.getCurrentPosition(async p => {
        const latitude = arrondi(p.coords.latitude), longitude = arrondi(p.coords.longitude);
        let libelle = 'Autour de moi';
        try {
          const d = await (await fetch(`${BAN}/reverse/?lat=${latitude}&lon=${longitude}`)).json();
          const pr = d.features[0] && d.features[0].properties; if (pr) libelle = `${pr.city} (${pr.postcode})`;
        } catch {}
        const v = {libelle, latitude, longitude}; trouvees.set(libelle, v); ok(v);
      }, () => ko(new Error("Position refusée : tapez votre ville.")), {maximumAge: 6e5, timeout: 1e4});
    });
  }

  // Formulaire « Proposer un objet » : Ajouter une localisation.
  const fObj = $('#f-obj');
  suggerer($('#lieu-obj'), $('#lieux-obj'));
  $('#autour-obj').onclick = async () => {
    try { const v = await autourDeMoi(); fObj.lieu.value = v.libelle; } catch (err) { toast(err.message); }
  };
  function localisation(f) {
    const lieu = f.lieu.value.trim();
    if (!lieu) {
      const z = moi && moi.zones_interet && moi.zones_interet[0];
      return z ? {lieu: z.libelle, latitude: z.latitude, longitude: z.longitude} : {};
    }
    const v = choisie(lieu);
    return v ? {lieu: v.libelle, latitude: v.latitude, longitude: v.longitude} : {lieu};
  }

  /* Mon espace : où je troque. */
  function afficherZones() {
    if (!moi) return;
    const zones = moi.zones_interet || [], max = moi.zones_max || 1;
    $('#zones').innerHTML = `
      <p class="muted" style="font-size:14px;margin:0 0 8px">Les objets de vos zones s'échangent en main propre. Hors de vos zones, seulement par colis, si vous acceptez toute la France.</p>
      ${zones.map((z, i) => `<div class="demande-ligne"><div class="t"><b>${esc(z.libelle)}</b><span>Dans un rayon de ${z.rayon_km} km</span></div>
        <button class="x" type="button" aria-label="Retirer cette zone" data-zone-retirer="${i}">×</button></div>`).join('')
        || '<p class="muted">Aucune zone : TrocTroc se fie à votre ville.</p>'}
      ${zones.length < max ? `<form class="stack" id="f-zone"><div class="lieu-ligne">
          <input class="input" name="ville" list="lieux-zone" placeholder="Ville ou code postal" autocomplete="off" required>
          <button class="btn" type="button" id="autour-zone">Autour de moi</button></div><datalist id="lieux-zone"></datalist>
        <label class="field"><span>Rayon</span><select class="input" name="rayon">${[2, 5, 10, 20, 50].map(r => `<option value="${r}"${r === 10 ? ' selected' : ''}>${r} km</option>`).join('')}</select></label>
        <div class="btns"><button class="btn primary">Ajouter cette zone</button></div></form>`
        : max === 1 ? '<p class="muted" style="font-size:14px">Plusieurs zones (travail, famille…) : avec Premium Plus.</p>' : ''}
      <label class="interrupteur"><input type="checkbox" id="toute-france"${moi.toute_la_france ? ' checked' : ''}> Toute la France, par colis (chacun paie l'envoi de son objet)</label>`;
    const f = $('#f-zone');
    if (f) {
      suggerer(f.ville, $('#lieux-zone'));
      $('#autour-zone').onclick = async () => { try { f.ville.value = (await autourDeMoi()).libelle; } catch (err) { toast(err.message); } };
      f.onsubmit = async e => {
        e.preventDefault();
        const v = choisie(f.ville.value) || (await villes(f.ville.value))[0];
        if (!v) { toast('Ville introuvable : essayez avec le code postal.'); return; }
        await enregistrerZones([...zones, {...v, rayon_km: +f.rayon.value}]);
      };
    }
    $('#toute-france').onchange = async e => {
      try { moi = await api('/moi', {method: 'PATCH', body: {toute_la_france: e.target.checked}}); toast('Enregistré'); } catch (err) { toast(err.message); }
      afficherZones();
    };
  }
  async function enregistrerZones(zones) {
    try { moi = await api('/moi', {method: 'PATCH', body: {zones_interet: zones}}); toast('Zones enregistrées'); }
    catch (err) { toast(err.message); }
    afficherZones();
  }
  $('#zones').addEventListener('click', e => {
    const i = e.target.dataset.zoneRetirer; if (i === undefined) return;
    enregistrerZones(moi.zones_interet.filter((_, j) => j !== +i));
  });

  /* Troc Premium. */
  const lien = (url, achat) => `${url}?client_reference_id=${moi.id}-${achat}&prefilled_email=${encodeURIComponent(moi.email)}`;
  function formuleHtml(f) {
    const prix = f.prix_unique != null ? `${euros(f.prix_unique)} le dimanche` : `${euros(f.prix_mois)} par mois ou ${euros(f.prix_an)} par an`;
    const boutons = Object.entries(f.liens).map(([periode, url]) => `<a class="btn${f.cle === 'plus' ? ' primary' : ''}" href="${esc(lien(url, periode === 'pass' ? 'pass' : `${f.cle}_${periode}`))}" rel="noopener">${periode === 'an' ? "À l'année" : periode === 'mois' ? 'Au mois' : 'Acheter'}</a>`).join('');
    return `<article class="formule${f.cle === 'plus' ? ' conseillee' : ''}"><b>${esc(f.nom)}</b><span class="prix">${prix}</span>
      <ul>${f.avantages.map(a => `<li>${esc(AVANTAGES[a] || a)}</li>`).join('')}${f.super_jaime_par_semaine ? `<li>${f.super_jaime_par_semaine} Super J'aime par semaine</li>` : ''}</ul>
      ${boutons ? `<div class="btns">${boutons}</div>` : ''}</article>`;
  }
  async function afficherPremium() {
    if (!moi) return;
    catalogue ??= await api('/premium').catch(() => null);
    if (!catalogue) return;
    const actuelle = moi.formule && catalogue.formules.find(f => f.cle === moi.formule);
    let html;
    if (actuelle) {
      html = `<p>Vous profitez de <b>Troc Premium ${esc(actuelle.nom)}</b>${moi.premium_jusqu_au ? ` jusqu'au ${new Date(moi.premium_jusqu_au).toLocaleDateString(document.documentElement.lang || 'fr')}` : ''}.</p>
        <ul>${moi.avantages.map(a => `<li>${esc(AVANTAGES[a] || a)}</li>`).join('')}</ul>
        ${moi.avantages.includes('apercu_du_stock') ? '<div class="btns"><button class="btn" type="button" id="apercu-btn">Aperçu du stock du dimanche</button></div><div id="apercu"></div>' : ''}
        ${moi.formule === 'famille' && moi.premium_jusqu_au ? `<form class="stack" id="f-famille"><label class="field"><span>Ajouter un proche (e-mail de son compte TrocTroc)</span>
          <input class="input" type="email" name="email" required></label><div class="btns"><button class="btn">Ajouter</button></div></form>` : ''}
        ${catalogue.portail ? `<div class="btns"><a class="btn" href="${esc(catalogue.portail)}" rel="noopener">Gérer ou résilier mon abonnement</a></div>` : ''}`;
    } else {
      html = `<p>Échanger reste gratuit et illimité. Premium ajoute du confort et vous fait passer en premier quand plusieurs membres veulent le même objet, sans jamais faire perdre un échange à personne.</p>
        ${moi.essai_disponible && catalogue.jours_essai ? `<div class="btns"><button class="acc-btn y" type="button" id="essai-btn">Essayer Premium Plus ${catalogue.jours_essai} jours, gratuitement</button></div>` : ''}
        <div class="formules">${catalogue.formules.map(formuleHtml).join('')}</div>`;
    }
    $('#premium').innerHTML = html;
    afficherPub();
  }
  $('#premium').addEventListener('click', async e => {
    if (e.target.id === 'essai-btn') {
      e.target.disabled = true;
      try { moi = await api('/premium/essai', {method: 'POST'}); toast('Bienvenue dans Troc Premium Plus !'); afficher(); }
      catch (err) { toast(err.message); e.target.disabled = false; }
    }
    if (e.target.id === 'apercu-btn') {
      try {
        const objets = await api('/moi/apercu');
        $('#apercu').innerHTML = objets.length ? `<div class="grille">${objets.map(carteObjet).join('')}</div>` : '<p class="muted">Rien pour vos demandes en ce moment.</p>';
      } catch (err) { toast(err.message); }
    }
  });
  $('#premium').addEventListener('submit', async e => {
    e.preventDefault(); if (e.target.id !== 'f-famille') return;
    try { await api('/premium/famille', {method: 'POST', body: {email: e.target.email.value.trim()}}); toast('Proche ajouté'); e.target.reset(); }
    catch (err) { toast(err.message); }
  });

  // Encart publicitaire local, sans pistage : jamais pour qui a « sans publicité ».
  function afficherPub() {
    const sansPub = moi && (moi.avantages || []).includes('sans_pub');
    $$('[data-pub]').forEach(x => {
      x.hidden = sansPub || !catalogue || !catalogue.publicite_texte;
      if (!x.hidden) x.innerHTML = `<span class="label">Annonce</span> ${catalogue.publicite_lien ? `<a href="${esc(catalogue.publicite_lien)}" rel="noopener sponsored">${esc(catalogue.publicite_texte)}</a>` : esc(catalogue.publicite_texte)}`;
    });
  }

  /* « Qui aime ? » : la ShortList d'un objet convoité, ou tous les intéressés avec Premium. */
  $('#items').addEventListener('click', async e => {
    const id = e.target.dataset.interesses; if (!id) return;
    const bloc = $('#interesses-' + id); if (!bloc.hidden) { bloc.hidden = true; return; }
    try {
      const r = await api(`/moi/objets/${id}/interesses`);
      bloc.innerHTML = r.interesses.length
        ? `<p class="muted" style="font-size:13px">${r.convoite ? `Objet convoité : ${r.nb_jaime} J'aime. ` : ''}Aimez un de leurs objets et c'est un match.</p>` + r.interesses.map(i => `<div class="demande-ligne"><div class="t">
            <b>${i.super_jaime ? '★ ' : ''}${esc(i.membre.pseudo)}${i.membre.zone ? ` <span class="muted" style="font-weight:400">· ${esc(i.membre.zone)}</span>` : ''}</b>
            <span>${i.ses_objets.length ? i.ses_objets.slice(0, 4).map(o => `<a href="#objet-${o.id}">${esc(o.titre)}</a>`).join(', ') : 'Aucun objet proposé'}</span></div></div>`).join('')
        : `<p class="muted" style="font-size:13px">${r.nb_jaime} J'aime. La liste s'ouvre à partir de 5 (objet convoité), ou tout de suite avec Troc Premium.</p>`;
      bloc.hidden = false;
    } catch (err) { toast(err.message); }
  });

  function afficher() { afficherZones(); afficherPremium(); }
  if (moi) afficher(); else api('/premium').then(c => { catalogue = c; afficherPub(); }).catch(() => {});
  return {afficher, localisation};
})();
