/* Le Match : une pile de cartes d'objets qui répondent à mes souhaits, à glisser à droite (« J'aime ») ou à gauche
   (« Non merci »), comme sur une appli de rencontre,
   et mes matchs (un cœur de chaque côté) où je propose l'échange 1 à 1, à tout moment.
   Chargé après le script principal de index.html, dont il reprend api(), esc(), toast(), vignette()… */
(() => {
  let cartes = [], matchs = [], dejaArrive = false;
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
        <span class="muted" style="font-size:14px">${esc(ETATS[o.etat] || '')}${o.etat ? ' · ' : ''}${Detail.nom(o.categorie_slug, o.sous_categorie_slug)}${Detail.caracs(o.categorie_slug, o.caracteristiques) ? ' · ' + Detail.caracs(o.categorie_slug, o.caracteristiques) : ''} · ${esc(p.pseudo)}${p.zone ? ', ' + esc(p.zone) : ''}${p.reputation !== 'nouveau' && reputation(p) ? ' · ' + reputation(p) : ''}</span>
        ${o.description ? `<span style="font-size:14px">${esc(o.description.slice(0, 140))}${o.description.length > 140 ? '…' : ''}</span>` : ''}
        <span class="pourquoi">${pourquoi(c)}</span>
        <a class="voir" href="#objet-${o.id}" data-fiche="${o.id}">Voir la fiche</a>
      </div><span class="sceau oui" aria-hidden="true">J'aime</span><span class="sceau non" aria-hidden="true">Non merci</span></article>`;
  }

  // Deux cartes empilées : celle du dessus se glisse, celle du dessous attend.
  function afficherCarrousel() {
    const n = cartes.length;
    $('#carrousel-compte').textContent = n ? `${n} objet${n > 1 ? 's' : ''} pour vous` : '';
    $('#carrousel').innerHTML = n ? cartes.slice(0, 2).map(carteHtml).reverse().join('')
      : '<p class="empty">Plus rien à vous montrer pour l\'instant. Ajoutez des souhaits ou des objets : la pile se remplit dès qu\'un objet correspond.</p>';
    const cs = $$('#carrousel .carte'); cs.forEach((c, j) => c.classList.toggle('devant', j === cs.length - 1));
    $('#ronds').hidden = $('#match-aide').hidden = !n;
  }

  // Glisser la carte du dessus : au-delà d'un tiers de sa largeur, c'est un choix ; sinon elle revient.
  let glisse = null;
  $('#carrousel').addEventListener('pointerdown', e => {
    const c = e.target.closest('.carte.devant'); if (!c || e.button || e.target.closest('a,button')) return;
    glisse = {c, x: e.clientX, dx: 0, id: e.pointerId}; c.setPointerCapture(e.pointerId); c.classList.add('tenue');
  });
  $('#carrousel').addEventListener('pointermove', e => {
    if (!glisse || e.pointerId !== glisse.id) return;
    glisse.dx = e.clientX - glisse.x;
    glisse.c.style.transform = `translateX(${glisse.dx}px) rotate(${glisse.dx / 18}deg)`;
    glisse.c.style.setProperty('--oui', Math.max(0, Math.min(1, glisse.dx / 100)));
    glisse.c.style.setProperty('--non', Math.max(0, Math.min(1, -glisse.dx / 100)));
  });
  const lacher = e => {
    if (!glisse || e.pointerId !== glisse.id) return;
    const {c, dx} = glisse; glisse = null; c.classList.remove('tenue');
    if (Math.abs(dx) > c.offsetWidth / 3) { avis(dx > 0); return; }
    c.style.transform = ''; c.style.removeProperty('--oui'); c.style.removeProperty('--non');
  };
  $('#carrousel').addEventListener('pointerup', lacher);
  $('#carrousel').addEventListener('pointercancel', lacher);
  $('#m-oui').onclick = () => avis(true);
  $('#m-non').onclick = () => avis(false);
  addEventListener('keydown', e => {
    if ($('#v-match').hidden || e.target.closest('input,textarea,select') || document.querySelector('dialog[open]')) return;
    if (e.key === 'ArrowRight') avis(true);
    if (e.key === 'ArrowLeft') avis(false);
  });

  let enCours = false;
  async function avis(aime) {
    const c = cartes[0], carte = $('#carrousel .carte.devant'); if (!c || !carte || enCours) return;
    enCours = true; const id = c.objet.id;
    try {
      const r = await api('/match/avis', {method: 'POST', body: {objet_id: id, aime}});
      carte.style.transform = `translateX(${aime ? 130 : -130}%) rotate(${aime ? 18 : -18}deg)`; carte.style.opacity = 0;
      await new Promise(ok => setTimeout(ok, calme ? 0 : 340));
      cartes = cartes.filter(x => x.objet.id !== id); afficherCarrousel();
      if (r.match) {
        matchs = [r.match, ...matchs.filter(x => x.avec.id !== r.match.avec.id)]; afficherMatchs();
        fenetre.dataset.avec = r.match.avec.id;
        $('#match-qui').textContent = `${r.match.avec.pseudo} aime aussi un de vos objets. Proposez-lui l'échange quand vous voulez.`;
        fenetre.showModal();
      } else if (aime) toast('Noté ! Si l\'intérêt est réciproque, c\'est un match.');
    } catch (err) { toast(err.message); carte.style.transform = ''; }
    finally { enCours = false; }
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
    mesMatchs = matchs; afficherEspace();
  }

  // Le Match à trois : des boucles possibles tout de suite, où chacun reçoit ce qu'il a demandé ou aimé.
  let boucles = [];
  function boucleHtml(b, i) {
    const nom = (id, pseudo) => id === moi.id ? 'Vous' : esc(pseudo);
    const etapes = b.etapes.map(e => `<li>${e.objet.photo_url ? `<img src="${esc(vignette(e.objet.photo_url, 56))}" alt="">` : ''}
      <span><b>${nom(e.donneur_id, e.donneur_pseudo)}</b> ${e.donneur_id === moi.id ? 'donnez' : 'donne'} « ${esc(e.objet.titre)} » à <b>${e.receveur_id === moi.id ? 'vous' : esc(e.receveur_pseudo)}</b></span></li>`).join('');
    return `<article class="card featured"><span class="tag a">Boucle à trois</span>
      <ol class="etapes-trois">${etapes}</ol>
      <div class="btns"><button class="btn primary" type="button" data-boucle="${i}">Proposer la boucle</button></div></article>`;
  }
  function afficherBoucles() {
    $('#bloc-trois').hidden = !boucles.length;
    $('#boucles-trois').innerHTML = boucles.map(boucleHtml).join('');
  }

  async function chargerMatch() {
    if (!moi) return;
    try {
      [cartes, matchs, boucles] = await Promise.all([api('/match/carrousel?limite=30'), api('/match'), api('/match/boucles').catch(() => []), Detail.charger()]);
      afficherBoucles(); afficherCarrousel(); afficherMatchs();
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
    const v = e.target.closest('[data-voir-echange]');
    if (v) { e.preventDefault(); go('trades'); const c = document.getElementById('echange-' + v.dataset.voirEchange); if (c) c.scrollIntoView(); return; }

    const t = e.target.closest('[data-boucle]');
    if (t) {
      const b = boucles[t.dataset.boucle]; t.disabled = true;
      try {
        await api('/match/boucle', {method: 'POST', body: {objets: b.etapes.map(x => x.objet.id)}});
        toast('Boucle proposée : les deux autres ont 48 h pour dire oui.');
        await Promise.all([chargerMatch(), chargerEchanges()]);
      } catch (err) { toast(err.message); t.disabled = false; }
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
  go = (v, o) => { goAvant(v, o); if (v === 'match' && moi) chargerMatch(); };
  const toutChargerAvant = toutCharger;
  toutCharger = async () => {
    await Promise.all([toutChargerAvant(), chargerMatch()]);
    if (!dejaArrive && location.hash === '#match') { dejaArrive = true; go('match'); }
  };
  document.addEventListener('tt:match', chargerMatch);
  if (moi) chargerMatch();
})();
