/* Le Match : un carrousel d'objets qui répondent à mes souhaits, « J'aime » ou « Non merci » sur chacun,
   et mes matchs (un cœur de chaque côté) où je propose l'échange 1 à 1, à tout moment.
   Chargé après le script principal de index.html, dont il reprend api(), esc(), toast(), vignette()… */
(() => {
  let cartes = [], matchs = [], dejaArrive = false;
  const COEUR = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg>';
  const CROIX = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
  const titres = l => l.map(o => `« ${esc(o.titre)} »`).join(', ');
  const cat = slug => esc(categories[slug] || slug);

  function pourquoi(c) {
    if (c.il_aime.length) return `<strong>${esc(c.proprietaire.pseudo)} aime votre ${titres(c.il_aime.slice(0, 2))}</strong> : un cœur et c'est un match.`;
    const lignes = [];
    if (c.correspond_a_mes_souhaits) lignes.push(c.souhait_categorie ? `Répond à votre demande <strong>${Detail.nom(c.souhait_categorie, c.souhait_sous_categorie)}</strong>.` : 'Vous le cherchiez.');
    if (c.il_cherche.length) lignes.push(`${esc(c.proprietaire.pseudo)} cherche ce que vous avez : ${titres(c.il_cherche.slice(0, 2))}.`);
    if (c.sa_demande) lignes.push(`Sa demande : <q>${esc(c.sa_demande)}</q>`);
    return lignes.join(' ');
  }

  function carteHtml(c, i) {
    const o = c.objet, p = c.proprietaire;
    const tag = c.il_aime.length ? '<span class="tag m">Match immédiat</span>' : c.il_cherche.length && c.correspond_a_mes_souhaits ? '<span class="tag a">Réciproque</span>' : '';
    return `<article class="carte${c.il_aime.length ? ' chaude' : ''}" data-i="${i}" aria-label="${esc(o.titre)}">
      <div class="ph">${o.photo_url ? `<img src="${esc(vignette(o.photo_url, 640))}" alt="" loading="lazy">` : ''}${tag}</div>
      <div class="corps"><b>${esc(o.titre)}</b>
        <span class="muted" style="font-size:14px">${esc(ETATS[o.etat] || '')}${o.etat ? ' · ' : ''}${Detail.nom(o.categorie_slug, o.sous_categorie_slug)}${Detail.caracs(o.categorie_slug, o.caracteristiques) ? ' · ' + Detail.caracs(o.categorie_slug, o.caracteristiques) : ''} · ${esc(p.pseudo)}${p.zone ? ', ' + esc(p.zone) : ''}</span>
        ${o.description ? `<span style="font-size:14px">${esc(o.description.slice(0, 140))}${o.description.length > 140 ? '…' : ''}</span>` : ''}
        <span class="pourquoi">${pourquoi(c)}</span>
        <div class="choix"><button class="non" type="button" data-avis="${o.id}">${CROIX}Non merci</button><button class="oui" type="button" data-avis="${o.id}" data-aime="1">${COEUR}J'aime</button></div>
      </div></article>`;
  }

  function afficherCarrousel() {
    const n = cartes.length;
    $('#carrousel-compte').textContent = n ? `${n} objet${n > 1 ? 's' : ''} pour vous` : '';
    $('#carrousel').innerHTML = n ? cartes.map(carteHtml).join('')
      : '<p class="empty">Plus rien à vous montrer pour l\'instant. Ajoutez des souhaits ou des objets : le carrousel se remplit dès qu\'un objet correspond.</p>';
    $$('[data-defiler]').forEach(b => b.hidden = n < 2);
  }

  function choix(nom, objets, coche) {
    return `<div class="choix-objets">${objets.map((o, j) => `<label><input type="radio" name="${nom}" value="${o.id}"${j === 0 && coche ? ' checked' : ''}>
      ${o.photo_url ? `<img src="${esc(vignette(o.photo_url, 56))}" alt="">` : ''}${esc(o.titre)}</label>`).join('')}</div>`;
  }

  function matchHtml(x, i) {
    const qui = esc(x.avec.pseudo);
    const bas = x.echange_id
      ? `<p class="status">Échange en cours avec ${qui}.</p><a class="btn" href="#echange-${x.echange_id}" data-voir-echange="${x.echange_id}">Voir l'échange</a>`
      : `<div class="stack" style="display:flex;flex-direction:column;gap:10px">
          <span class="label">Vous recevez</span>${choix('recoit-' + i, x.ses_objets, true)}
          <span class="label">Vous donnez</span>${choix('donne-' + i, x.mes_objets, true)}
          <div class="btns"><button class="btn primary" type="button" data-accord="${i}">Proposer l'échange</button></div>
          <p class="muted" style="font-size:13px">${qui} a 48 h pour dire oui, puis chacun dépose dans les 7 jours.</p></div>`;
    return `<article class="card featured" id="match-${x.avec.id}"><span class="tag m">Match</span>
      <b><span class="coeur">♥</span> Vous et ${qui}${x.avec.zone ? ` <span class="muted" style="font-weight:400">· ${esc(x.avec.zone)}</span>` : ''}</b>${bas}</article>`;
  }

  function afficherMatchs() {
    const libres = matchs.filter(x => !x.echange_id).length;
    $('#badge-match').textContent = libres; $('#badge-match').hidden = !libres;
    $('#match-title').textContent = libres ? `${libres} match${libres > 1 ? 's' : ''} à conclure` : 'Ça vous plaît ?';
    $('#matchs').innerHTML = matchs.map(matchHtml).join('')
      || '<p class="empty">Pas encore de match. Un « J\'aime » sur un objet marqué « Match immédiat » en crée un tout de suite.</p>';
  }

  async function chargerMatch() {
    if (!moi) return;
    try {
      [cartes, matchs] = await Promise.all([api('/match/carrousel?limite=30'), api('/match'), Detail.charger()]);
      afficherCarrousel(); afficherMatchs();
    } catch (err) { toast(err.message); }
  }

  // « C'est un match ! » : une fenêtre qui mène droit à l'accord.
  const fenetre = document.createElement('dialog');
  fenetre.className = 'its-a-match';
  fenetre.innerHTML = `<div class="stack" style="display:flex;flex-direction:column;gap:14px;align-items:center">
    <span class="coeur" style="font-size:40px" aria-hidden="true">♥</span><h2>C'est un match !</h2><p class="muted" id="match-qui"></p>
    <div class="btns" style="justify-content:center"><button class="btn primary" type="button" data-fin="accord">Proposer l'échange</button><button class="btn" type="button" data-fin="plus">Continuer</button></div></div>`;
  document.body.append(fenetre);
  fenetre.addEventListener('click', e => {
    const fin = e.target.dataset.fin; if (!fin) return;
    fenetre.close();
    const c = fin === 'accord' && document.getElementById('match-' + fenetre.dataset.avec);
    if (c) c.scrollIntoView({behavior: calme ? 'auto' : 'smooth', block: 'center'});
  });

  $('#v-match').addEventListener('click', async e => {
    const d = e.target.closest('[data-defiler]');
    if (d) { const r = $('#carrousel'), c = r.querySelector('.carte'); r.scrollBy({left: (c ? c.offsetWidth + 14 : 300) * d.dataset.defiler, behavior: calme ? 'auto' : 'smooth'}); return; }

    const v = e.target.closest('[data-voir-echange]');
    if (v) { e.preventDefault(); go('trades'); const c = document.getElementById('echange-' + v.dataset.voirEchange); if (c) c.scrollIntoView(); return; }

    const b = e.target.closest('[data-avis]');
    if (b) {
      const aime = !!b.dataset.aime, carte = b.closest('.carte'), id = +b.dataset.avis;
      carte.querySelectorAll('button').forEach(x => x.disabled = true);
      try {
        const r = await api('/match/avis', {method: 'POST', body: {objet_id: id, aime}});
        carte.classList.add(aime ? 'part-d' : 'part-g');
        await new Promise(ok => setTimeout(ok, calme ? 0 : 340));
        cartes = cartes.filter(c => c.objet.id !== id); afficherCarrousel();
        if (r.match) {
          matchs = [r.match, ...matchs.filter(x => x.avec.id !== r.match.avec.id)]; afficherMatchs();
          fenetre.dataset.avec = r.match.avec.id;
          $('#match-qui').textContent = `${r.match.avec.pseudo} aime aussi un de vos objets. Proposez-lui l'échange quand vous voulez.`;
          fenetre.showModal();
        } else if (aime) toast('Noté ! Si l\'intérêt est réciproque, c\'est un match.');
      } catch (err) { toast(err.message); carte.querySelectorAll('button').forEach(x => x.disabled = false); }
      return;
    }

    const a = e.target.closest('[data-accord]');
    if (a) {
      const i = a.dataset.accord, carte = a.closest('article');
      const recoit = carte.querySelector(`input[name="recoit-${i}"]:checked`), donne = carte.querySelector(`input[name="donne-${i}"]:checked`);
      if (!recoit || !donne) return toast('Choisissez ce que vous donnez et ce que vous recevez.');
      a.disabled = true;
      try {
        await api('/match/accord', {method: 'POST', body: {mon_objet_id: +donne.value, son_objet_id: +recoit.value}});
        toast(`Proposition envoyée à ${matchs[i].avec.pseudo}`);
        await Promise.all([chargerMatch(), chargerEchanges()]);
      } catch (err) { toast(err.message); a.disabled = false; }
    }
  });

  // Branchements sur le script principal : la vue se charge à l'ouverture, avec le reste du compte.
  const goAvant = go;
  go = v => { goAvant(v); if (v === 'match' && moi) chargerMatch(); };
  const toutChargerAvant = toutCharger;
  toutCharger = async () => {
    await Promise.all([toutChargerAvant(), chargerMatch()]);
    if (!dejaArrive && location.hash === '#match') { dejaArrive = true; history.replaceState(null, '', location.pathname); go('match'); }
  };
  if (moi) chargerMatch();
})();
