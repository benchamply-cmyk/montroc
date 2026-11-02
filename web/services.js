/* Troc & Services : échanger des articles contre le service d'un professionnel certifié (et service contre service).
   Une page publique (#services : les métiers, les pros certifiés), la fiche d'un pro (#pro-12) avec « Proposer des
   articles en échange », la conversation et le contrat (#negociation-7), et dans Mon espace l'onglet « Troc & Services »
   (#mes-services : mes conversations, mon activité pro à faire certifier, mes offres). La modération y certifie les pros.
   Chargé après index.html, match.js, premium.js et visiteur.js, dont il reprend api(), esc(), toast(), go(), moi… */
const Services = (() => {
  const FAMILLES = [
    {nom: 'Déménagement', metiers: ['services-demenagement']},
    {nom: 'Bâtiment', metiers: ['services-maconnerie', 'services-electricite', 'services-plomberie', 'services-peinture']},
    {nom: 'Jardinage', metiers: ['services-jardinage']},
    {nom: 'Transporteur / chauffeur', metiers: ['services-transport']},
  ];
  const STATUTS_PRO = {en_attente: 'En cours de vérification', certifie: 'Pro certifié', refuse: 'À compléter'};
  const STATUTS_NEGO = {ouverte: 'En discussion', accord_propose: 'Accord proposé', conclue: 'Contrat signé', annulee: 'Close'};
  const BADGE = '<span class="ts-badge"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l7 3v6c0 4.5-3 7.6-7 9-4-1.4-7-4.5-7-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/></svg>Pro certifié</span>';
  let metiers = [], pros = [], filtre = '', mesNegos = [], negoActive = null, proActif = null;
  const nomMetier = slug => (metiers.find(m => m.slug === slug) || {}).libelle || slug;
  const date = d => new Date(d).toLocaleDateString(document.documentElement.lang || 'fr', {day: 'numeric', month: 'long', year: 'numeric'});

  /* Styles propres à Troc & Services (mêmes jetons que le reste du site : une seule couleur vive, le jaune). */
  document.head.insertAdjacentHTML('beforeend', `<style>
    .ts-etapes{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:0;padding:0;list-style:none;counter-reset:e}
    .ts-etapes li{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:14px 16px;font-size:15px;counter-increment:e}
    .ts-etapes li::before{content:counter(e);display:inline-grid;place-items:center;width:24px;height:24px;border-radius:50%;background:var(--mark);color:#111318;font-weight:700;font-size:13px;margin-right:8px}
    .ts-familles{display:flex;gap:8px;flex-wrap:wrap}
    .ts-familles button{border:1px solid var(--line);background:var(--surface);color:var(--ink);font:inherit;font-size:14px;font-weight:600;border-radius:999px;padding:8px 14px;cursor:pointer}
    .ts-familles button[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
    .ts-pros{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
    .ts-pro{display:flex;flex-direction:column;gap:8px;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:16px;color:var(--ink);text-decoration:none}
    .ts-pro:hover{border-color:var(--mark)}
    .ts-pro b{font-size:17px}.ts-pro p{margin:0;font-size:14px;color:var(--muted);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
    .ts-badge{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:700;color:var(--mark);border:1px solid var(--mark);border-radius:999px;padding:1px 8px 1px 5px;width:max-content}
    .ts-badge svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:2}
    .ts-meta{display:flex;gap:6px 14px;flex-wrap:wrap;font-size:13px;color:var(--muted)}
    .ts-offres{display:flex;flex-direction:column;gap:10px}
    .ts-offre{display:flex;gap:12px;align-items:center;background:var(--surface-2);border:1px solid var(--line);border-radius:var(--r);padding:10px}
    .ts-offre img{width:64px;height:64px;border-radius:10px;object-fit:cover;flex:none}
    .ts-offre .t{flex:1;min-width:0}.ts-offre .t span{display:block;font-size:13px;color:var(--muted)}
    .ts-choix{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
    .ts-choix label{display:flex;gap:8px;align-items:center;background:var(--surface-2);border:1px solid var(--line);border-radius:12px;padding:8px;font-size:14px;cursor:pointer}
    .ts-choix label:has(input:checked){border-color:var(--mark)}
    .ts-choix img{width:40px;height:40px;border-radius:8px;object-fit:cover}
    .ts-fil{display:flex;flex-direction:column;gap:8px;max-height:420px;overflow-y:auto;padding:4px 2px}
    .ts-msg{max-width:82%;padding:9px 13px;border-radius:16px;font-size:15px;background:var(--surface);border:1px solid var(--line);align-self:flex-start;white-space:pre-wrap}
    .ts-msg.moi{align-self:flex-end;background:var(--ink);color:var(--bg);border-color:var(--ink)}
    .ts-msg.sys{align-self:center;background:none;border:1px dashed var(--line);color:var(--muted);font-size:13px;text-align:center}
    .ts-msg small{display:block;font-size:11px;opacity:.7;margin-top:2px}
    .ts-accord{border:1px solid var(--mark);border-radius:var(--r);padding:14px 16px;display:flex;flex-direction:column;gap:6px;font-size:15px}
    .ts-contrat{white-space:pre-wrap;font-family:var(--mono);font-size:13px;line-height:1.55;background:var(--surface-2);border:1px solid var(--line);border-radius:var(--r);padding:16px;max-height:460px;overflow:auto}
    .ts-ligne{display:flex;justify-content:space-between;gap:10px;align-items:center;padding:12px 0;border-bottom:1px solid var(--line);cursor:pointer}
    .ts-ligne .t{min-width:0}.ts-ligne .t span{display:block;font-size:13px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .ts-point{width:9px;height:9px;border-radius:50%;background:var(--mark);flex:none}
    @media print{body>*:not(.wrap),.wrap>*:not(#v-nego),#v-nego>*:not(#nego-contrat){display:none!important}.ts-contrat{max-height:none;border:0;color:#000;background:#fff}}
  </style>`);

  /* Les vues : la page publique, la fiche d'un pro, une conversation, et l'onglet de Mon espace. */
  $('#v-objet').insertAdjacentHTML('afterend', `
  <section class="view" id="v-services" hidden>
    <div class="hero"><span class="label">Troc & Services</span><h2>Échanger ses articles contre le savoir-faire d'un pro</h2>
      <p class="muted">Engager un professionnel certifié par TopTroc et le payer en articles, définis par contrat. Ou échanger un service contre un autre.</p></div>
    <ol class="ts-etapes">
      <li>Choisir le service recherché</li><li>Proposer des articles en échange</li><li>Négocier dans la conversation</li><li>Signer le contrat généré par TopTroc</li>
    </ol>
    <div class="ts-familles" id="ts-familles" role="group" aria-label="Métiers"></div>
    <div class="ts-pros" id="ts-pros" aria-live="polite"></div>
    <div class="card stack"><span class="label">Vous êtes professionnel ?</span>
      <p style="margin:0">Proposer son activité contre des articles, ou contre le service d'un autre pro. TopTroc vérifie SIRET, assurances et qualifications avant de certifier le profil.</p>
      <div class="btns"><button class="btn primary" type="button" id="ts-devenir">Faire certifier mon activité</button></div></div>
  </section>
  <section class="view" id="v-pro" hidden>
    <button class="retour" type="button" data-go="services"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg>Troc & Services</button>
    <div id="ts-fiche" class="stack"></div>
  </section>
  <section class="view" id="v-mespro" hidden>
    <nav class="onglets" data-espace aria-label="Mon espace"></nav>
    <div class="hero"><span class="label">Troc & Services</span><h2>Mes conversations et mon activité pro</h2></div>
    <div class="card"><span class="label">Conversations</span><div id="ts-negos"></div></div>
    <div id="ts-moi-pro" class="stack"></div>
  </section>
  <section class="view" id="v-nego" hidden>
    <nav class="onglets" data-espace aria-label="Mon espace"></nav>
    <button class="retour" type="button" data-go="mespro"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg>Mes conversations</button>
    <div id="ts-nego" class="stack"></div>
  </section>`);
  $('#reports').insertAdjacentHTML('beforebegin', '<div id="ts-mod" class="stack"></div>');

  async function chargerMetiers() {
    if (!metiers.length) metiers = await api('/services/metiers');
    return metiers;
  }

  /* Page publique : les familles de métiers et les pros certifiés. */
  async function afficher() {
    try { await chargerMetiers(); pros = await api('/services/pros'); }
    catch (err) { $('#ts-pros').innerHTML = `<p class="empty">${esc(err.message)}</p>`; return; }
    $('#ts-familles').innerHTML = [['', 'Tous les métiers'], ...FAMILLES.map(f => [f.nom, f.nom])]
      .map(([v, l]) => `<button type="button" data-famille="${esc(v)}" aria-pressed="${v === filtre}">${esc(l)}</button>`).join('');
    const famille = FAMILLES.find(f => f.nom === filtre);
    const liste = pros.filter(p => !famille || famille.metiers.includes(p.metier));
    $('#ts-pros').innerHTML = liste.map(p => `<a class="ts-pro" href="#pro-${p.id}" data-pro="${p.id}">
        ${BADGE}<b>${esc(p.nom_commercial)}</b><span class="muted" style="font-size:14px">${esc(p.metier_libelle)} · ${esc(p.zone_intervention || 'Zone à préciser')}</span>
        <p>${esc(p.description)}</p>
        <span class="ts-meta"><span>${p.experience_annees} ans d'expérience</span><span>${p.services.length} offre${p.services.length > 1 ? 's' : ''}</span><span>${reputation(p)}</span></span></a>`).join('')
      || '<p class="empty">Pas encore de professionnel certifié pour ce métier. Les premiers arrivent : revenir bientôt, ou faire certifier son activité.</p>';
  }
  $('#ts-familles').onclick = e => { const b = e.target.closest('[data-famille]'); if (b) { filtre = b.dataset.famille; afficher(); } };
  $('#ts-pros').onclick = e => { const a = e.target.closest('[data-pro]'); if (a) { e.preventDefault(); ouvrirPro(+a.dataset.pro); } };
  $('#ts-devenir').onclick = () => moi ? go('mespro') : versCompte();

  /* Fiche d'un pro : la fiche métier, ses offres, et « Proposer des articles en échange ». */
  async function ouvrirPro(id) {
    go('pro', {adresse: '#pro-' + id});
    $('#ts-fiche').innerHTML = '<p class="muted">Chargement…</p>';
    try { await chargerMetiers(); proActif = await api('/services/pros/' + id); }
    catch (err) { $('#ts-fiche').innerHTML = `<p class="empty">${esc(err.message)}</p>`; return; }
    const p = proActif, m = metiers.find(x => x.slug === p.metier) || {exemples: [], justificatifs: []};
    $('#ts-fiche').innerHTML = `
      <div class="card stack">${BADGE}<h2 style="margin:0">${esc(p.nom_commercial)}</h2>
        <span class="ts-meta"><span>${esc(p.metier_libelle)}</span><span>${esc(p.zone_intervention || '')}</span><span>${p.experience_annees} ans d'expérience</span><span>Membre ${esc(p.pseudo)} · ${reputation(p)}</span></span>
        <p style="margin:0;white-space:pre-wrap">${esc(p.description)}</p>
        ${p.qualifications ? `<p class="muted" style="margin:0;font-size:14px">Qualifications : ${esc(p.qualifications)}</p>` : ''}
        <p class="muted" style="margin:0;font-size:13px">Certifié le ${date(p.certifie_le)} : SIRET, assurances et justificatifs vérifiés par TopTroc.</p></div>
      <div class="card stack"><span class="label">Ses offres</span>
        <div class="ts-offres">${p.services.map(o => `<div class="ts-offre">${o.photo_url ? `<img src="${esc(vignette(o.photo_url, 128))}" alt="">` : ''}
          <div class="t"><b>${esc(o.titre)}</b><span>${esc([o.caracteristiques.duree, o.description].filter(Boolean).join(' · '))}</span></div>
          <button class="btn primary" type="button" data-proposer-sur="${o.id}">Proposer des articles</button></div>`).join('') || '<p class="empty">Aucune offre en ligne pour l\'instant.</p>'}</div></div>
      <details class="card"><summary><b>Fiche métier : ${esc(m.libelle || '')}</b></summary>
        <p>${esc(m.description || '')}</p><p class="muted" style="font-size:14px">Exemples : ${esc(m.exemples.join(' · '))}</p>
        <p class="muted" style="font-size:14px">Vérifié avant certification : ${esc(m.justificatifs.join(' · '))}</p></details>
      <form class="card stack" id="ts-f-proposer" hidden>
        <span class="label">Proposer des articles en échange</span><b id="ts-cible"></b>
        <div class="ts-choix" id="ts-choix"></div>
        <label class="field"><span>Message</span><textarea class="input" name="message" required maxlength="2000" placeholder="Décrire le besoin : quoi, où, quand."></textarea></label>
        <div class="btns"><button class="btn primary" type="submit">Envoyer et ouvrir la conversation</button></div></form>`;
  }
  $('#ts-fiche').addEventListener('click', e => {
    const b = e.target.closest('[data-proposer-sur]'); if (!b) return;
    if (!moi) return versCompte();
    const o = proActif.services.find(x => x.id === +b.dataset.proposerSur), f = $('#ts-f-proposer');
    const miens = mesObjets.filter(x => x.statut === 'disponible');
    f.dataset.objet = o.id; f.hidden = false; $('#ts-cible').textContent = `Contre « ${o.titre} »`;
    $('#ts-choix').innerHTML = miens.map(x => `<label><input type="checkbox" name="c" value="${x.id}">${x.photo_url ? `<img src="${esc(vignette(x.photo_url, 80))}" alt="">` : ''}<span>${esc(x.titre)}</span></label>`).join('')
      || '<p class="empty">Proposer d\'abord un objet : il servira de paiement.</p>';
    f.scrollIntoView({behavior: 'smooth', block: 'center'});
  });
  $('#ts-fiche').addEventListener('submit', async e => {
    e.preventDefault(); const f = e.target, ids = [...f.querySelectorAll('[name=c]:checked')].map(x => +x.value);
    if (!ids.length) return toast('Choisir au moins un article à proposer.');
    try { const n = await api('/negociations', {method: 'POST', body: {objet_id: +f.dataset.objet, contreparties: ids, message: f.message.value.trim()}});
      toast('Conversation ouverte'); afficherNego(n); } catch (err) { toast(err.message); }
  });

  /* Une conversation : messages, conditions proposées, contrat. */
  async function ouvrirNegociation(id) {
    if (!moi) return versCompte();
    try { afficherNego(await api('/negociations/' + id)); } catch (err) { toast(err.message); go('mespro'); }
  }
  function afficherNego(n) {
    negoActive = n; go('nego', {adresse: '#negociation-' + n.id});
    const avec = n.initiateur.id === moi.id ? n.destinataire : n.initiateur, jeSuisInitiateur = n.initiateur.id === moi.id;
    const ouverte = ['ouverte', 'accord_propose'].includes(n.statut), c = n.conditions;
    const articles = n.contreparties.map(o => `« ${esc(o.titre)} »`).join(', ');
    const accord = n.statut === 'accord_propose' ? `<div class="ts-accord"><span class="label">Accord proposé par ${esc(n.accord_propose_par_id === moi.id ? 'vous' : avec.pseudo)}</span>
        <b>${esc(c.prestation)}</b><span>Le ${esc(date(c.date_prevue))} · ${esc(c.lieu)}${c.duree ? ' · ' + esc(c.duree) : ''}</span><span>Contre ${articles}</span>
        ${n.accord_propose_par_id === moi.id ? `<span class="muted" style="font-size:14px">En attente de la réponse de ${esc(avec.pseudo)}.</span>`
          : '<div class="btns"><button class="btn primary" type="button" id="ts-accepter">Accepter et signer le contrat</button></div>'}</div>` : '';
    const ct = n.contrat;
    const contrat = ct ? `<div class="card stack" id="nego-contrat"><span class="label">Contrat n° ${esc(ct.numero)} · ${ct.statut === 'realise' ? 'réalisé' : 'en cours'}</span>
        <div class="ts-contrat">${esc(ct.texte)}</div>
        <div class="btns"><button class="btn" type="button" onclick="print()">Imprimer ou enregistrer en PDF</button>
        ${ct.statut === 'en_cours' && !(jeSuisInitiateur ? ct.confirme_initiateur_le : ct.confirme_destinataire_le) ? '<button class="btn primary" type="button" id="ts-confirmer">Confirmer : tout a été fait</button>' : ''}</div>
        ${ct.statut === 'en_cours' && (jeSuisInitiateur ? ct.confirme_initiateur_le : ct.confirme_destinataire_le) ? `<span class="muted" style="font-size:14px">Confirmé de votre côté : en attente de ${esc(avec.pseudo)}.</span>` : ''}</div>` : '';
    $('#ts-nego').innerHTML = `
      <div class="card stack"><span class="label">${esc(STATUTS_NEGO[n.statut])} · avec ${esc(avec.pseudo)}</span>
        <b>« ${esc(n.objet.titre)} » contre ${articles}</b>
        <div class="ts-fil" id="ts-fil">${n.messages.map(x => `<div class="ts-msg ${x.auteur_id == null ? 'sys' : x.auteur_id === moi.id ? 'moi' : ''}">${esc(x.texte)}<small>${x.auteur_id == null ? 'TopTroc' : esc(x.auteur)} · ${new Date(x.cree_le).toLocaleString('fr-FR', {dateStyle: 'short', timeStyle: 'short'})}</small></div>`).join('')}</div>
        ${ouverte ? `<form class="stack" id="ts-f-msg"><textarea class="input" name="texte" required maxlength="2000" rows="2" placeholder="Écrire un message…"></textarea>
          <div class="btns"><button class="btn primary" type="submit">Envoyer</button><button class="btn" type="button" id="ts-ouvrir-accord">Proposer un accord</button><button class="btn" type="button" id="ts-annuler">Mettre fin</button></div></form>` : ''}
      </div>
      ${accord}
      <form class="card stack" id="ts-f-accord" hidden><span class="label">Proposer un accord</span>
        <label class="field"><span>Prestation</span><textarea class="input" name="prestation" required minlength="10" maxlength="2000">${esc(c.prestation || '')}</textarea></label>
        <label class="field"><span>Date prévue</span><input class="input" type="date" name="date_prevue" required value="${esc(c.date_prevue || '')}"></label>
        <label class="field"><span>Lieu</span><input class="input" name="lieu" required maxlength="200" value="${esc(c.lieu || '')}"></label>
        <label class="field"><span>Durée (facultatif)</span><input class="input" name="duree" maxlength="60" value="${esc(c.duree || '')}"></label>
        ${jeSuisInitiateur ? `<fieldset class="field"><legend>Articles donnés en échange</legend><div class="ts-choix">${mesObjets.filter(o => o.statut === 'disponible').map(o => `<label><input type="checkbox" name="c" value="${o.id}"${n.contreparties.some(x => x.id === o.id) ? ' checked' : ''}><span>${esc(o.titre)}</span></label>`).join('')}</div></fieldset>` : ''}
        <div class="btns"><button class="btn primary" type="submit">Proposer ces conditions</button></div></form>
      ${contrat}`;
    const fil = $('#ts-fil'); fil.scrollTop = fil.scrollHeight;
  }
  const agir = async (chemin, body) => { try { afficherNego(await api(chemin, {method: 'POST', body})); } catch (err) { toast(err.message); } };
  $('#ts-nego').addEventListener('click', e => {
    const n = negoActive; if (!n) return;
    if (e.target.id === 'ts-ouvrir-accord') { const f = $('#ts-f-accord'); f.hidden = !f.hidden; f.scrollIntoView({behavior: 'smooth'}); }
    else if (e.target.id === 'ts-accepter') agir(`/negociations/${n.id}/accepter`);
    else if (e.target.id === 'ts-annuler' && confirm('Mettre fin à cette conversation ?')) agir(`/negociations/${n.id}/annuler`);
    else if (e.target.id === 'ts-confirmer') agir(`/contrats/${n.contrat.id}/confirmer`);
  });
  $('#ts-nego').addEventListener('submit', e => {
    e.preventDefault(); const f = e.target, n = negoActive;
    if (f.id === 'ts-f-msg') return agir(`/negociations/${n.id}/messages`, {texte: f.texte.value.trim()});
    const ids = [...f.querySelectorAll('[name=c]:checked')].map(x => +x.value);
    agir(`/negociations/${n.id}/accord`, {prestation: f.prestation.value.trim(), date_prevue: f.date_prevue.value, lieu: f.lieu.value.trim(),
      duree: f.duree.value.trim() || null, contreparties: ids.length ? ids : null});
  });

  /* Mon espace › Troc & Services : conversations, dossier pro et offres. */
  async function afficherMonEspace() {
    if (!moi) return;
    let profils = [];
    try { await chargerMetiers(); [mesNegos, profils] = await Promise.all([api('/moi/negociations'), api('/moi/pro')]); }
    catch (err) { toast(err.message); return; }
    marquerOnglets();
    $$('#v-mespro [data-espace] [aria-current]').forEach(b => b.parentNode.scrollLeft = b.offsetLeft - 40);
    $('#ts-negos').innerHTML = mesNegos.map(n => `<div class="ts-ligne" data-nego="${n.id}"><div class="t"><b>${esc(n.objet_titre)} · ${esc(n.avec.pseudo)}</b><span>${esc(STATUTS_NEGO[n.statut])} · ${esc(n.dernier_message)}</span></div>${n.a_moi_de_repondre ? '<span class="ts-point" title="À vous de répondre"></span>' : ''}</div>`).join('')
      || '<p class="empty">Aucune conversation. Choisir un service dans <a href="/#services">Troc & Services</a> et proposer des articles en échange.</p>';
    const certifies = profils.filter(p => p.statut === 'certifie');
    const options = metiers.map(m => `<option value="${m.slug}">${esc(m.libelle)}</option>`).join('');
    $('#ts-moi-pro').innerHTML = `
      ${profils.map(p => `<div class="card stack"><span class="label">${esc(nomMetier(p.metier))}</span>
        ${p.statut === 'certifie' ? BADGE : `<span class="tag a">${esc(STATUTS_PRO[p.statut])}</span>`}<b>${esc(p.nom_commercial)}</b>
        ${p.motif ? `<p style="margin:0">Motif : ${esc(p.motif)}</p>` : ''}
        ${p.statut === 'en_attente' ? '<p class="muted" style="margin:0;font-size:14px">TopTroc vérifie les justificatifs : réponse par e-mail.</p>' : ''}</div>`).join('')}
      ${certifies.length ? `<form class="card stack" id="ts-f-offre"><span class="label">Publier une offre de service</span>
        <label class="field"><span>Métier</span><select class="input" name="metier">${certifies.map(p => `<option value="${p.metier}">${esc(nomMetier(p.metier))}</option>`).join('')}</select></label>
        <label class="field"><span>Titre</span><input class="input" name="titre" required maxlength="120" placeholder="Ex. Réparer une fuite, tailler une haie"></label>
        <label class="field"><span>Ce qui est compris</span><textarea class="input" name="description" maxlength="2000"></textarea></label>
        <label class="field"><span>Durée</span><select class="input" name="duree"><option value="">—</option>${['1 heure', 'Demi-journée', '1 journée', '2 jours ou plus', 'Forfait'].map(d => `<option>${d}</option>`).join('')}</select></label>
        <label class="field"><span>Photo (une réalisation)</span><input class="input" type="file" name="photo" accept="image/*" required></label>
        <div class="btns"><button class="btn primary" type="submit">Publier l'offre</button></div></form>` : ''}
      <details class="card"${profils.length ? '' : ' open'}><summary><b>Faire certifier une activité pro</b></summary>
        <form class="stack" id="ts-f-pro" style="margin-top:12px">
          <label class="field"><span>Métier</span><select class="input" name="metier" required>${options}</select></label>
          <p class="muted" style="margin:0;font-size:14px" id="ts-pieces"></p>
          <label class="field"><span>Nom commercial</span><input class="input" name="nom_commercial" required minlength="2" maxlength="120"></label>
          <label class="field"><span>SIRET</span><input class="input" name="siret" required inputmode="numeric" placeholder="14 chiffres"></label>
          <label class="field"><span>Fiche métier : l'activité, le savoir-faire</span><textarea class="input" name="description" required minlength="40" maxlength="3000"></textarea></label>
          <label class="field"><span>Années d'expérience</span><input class="input" type="number" name="experience_annees" min="0" max="60" value="0"></label>
          <label class="field"><span>Zone d'intervention</span><input class="input" name="zone_intervention" maxlength="120" placeholder="Ex. Marseille et 20 km autour"></label>
          <label class="field"><span>Assurance (assureur et n° de contrat)</span><input class="input" name="assurance" maxlength="200"></label>
          <label class="field"><span>Qualifications, labels</span><input class="input" name="qualifications" maxlength="300"></label>
          <label class="field"><span>Justificatifs (Kbis ou avis INSEE, attestations : photo ou PDF)</span><input class="input" type="file" name="pieces" accept="image/*,application/pdf" multiple required></label>
          <div class="btns"><button class="btn primary" type="submit">Envoyer pour vérification</button></div></form></details>`;
    const f = $('#ts-f-pro'), pieces = () => { const m = metiers.find(x => x.slug === f.metier.value); $('#ts-pieces').textContent = m ? 'À fournir : ' + m.justificatifs.join(' · ') : ''; };
    f.metier.onchange = pieces; pieces();
  }
  $('#ts-negos').onclick = e => { const l = e.target.closest('[data-nego]'); if (l) ouvrirNegociation(+l.dataset.nego); };
  $('#ts-moi-pro').addEventListener('submit', async e => {
    e.preventDefault(); const f = e.target, b = f.querySelector('button[type=submit]'); b.disabled = true;
    try {
      if (f.id === 'ts-f-pro') {
        const justificatifs = [];
        for (const fichier of [...f.pieces.files].slice(0, 6)) justificatifs.push((await envoyerPhoto(fichier)).photo_url);
        await api('/moi/pro', {method: 'POST', body: {metier: f.metier.value, nom_commercial: f.nom_commercial.value.trim(), siret: f.siret.value,
          description: f.description.value.trim(), experience_annees: +f.experience_annees.value || 0, zone_intervention: f.zone_intervention.value.trim() || null,
          assurance: f.assurance.value.trim() || null, qualifications: f.qualifications.value.trim() || null, justificatifs}});
        toast('Dossier envoyé : TopTroc le vérifie et répond par e-mail.');
      } else {
        const photo = await envoyerPhoto(f.photo.files[0]);
        await api('/moi/objets', {method: 'POST', body: {categorie_slug: 'services', sous_categorie_slug: f.metier.value, titre: f.titre.value.trim(),
          description: f.description.value.trim() || null, caracteristiques: f.duree.value ? {duree: f.duree.value} : {}, ...photo}});
        toast('Offre publiée : elle entre aussi dans le Match et le Grand Troc.');
        if (typeof chargerListes === 'function') chargerListes();
      }
      afficherMonEspace();
    } catch (err) { toast(err.message); } finally { b.disabled = false; }
  });

  /* Modération : les dossiers pro à vérifier, avec leurs justificatifs. */
  async function moderation() {
    let liste; try { await chargerMetiers(); liste = await api('/moderation/pros'); } catch { return; }
    $('#ts-mod').innerHTML = liste.length ? `<div class="list-head"><span class="label">Professionnels à certifier</span></div>` + liste.map(p => `<article class="card stack" data-pro-id="${p.id}">
        <span class="tag a">${esc(nomMetier(p.metier))} · dossier n° ${p.id}</span><b>${esc(p.nom_commercial)} (${esc(p.pseudo)}, ${esc(p.email)})</b>
        <span class="ts-meta"><span>SIRET ${esc(p.siret)}</span><span>${p.experience_annees} ans</span><span>${esc(p.assurance || 'Assurance non indiquée')}</span><span>${esc(p.qualifications || '')}</span></span>
        <p style="margin:0;font-size:15px;white-space:pre-wrap">${esc(p.description)}</p>
        <span>${p.justificatifs.map((u, i) => `<a href="${esc(u)}" target="_blank" rel="noopener">Justificatif ${i + 1}</a>`).join(' · ')}</span>
        <label class="field"><span>Motif (obligatoire pour un refus, envoyé au membre)</span><textarea class="input" name="motif"></textarea></label>
        <div class="btns"><button class="btn primary" data-certifier="1">Certifier</button><button class="btn" data-certifier="0">Refuser</button></div></article>`).join('') : '';
  }
  $('#ts-mod').onclick = async e => {
    const d = e.target.dataset.certifier; if (d === undefined) return; const c = e.target.closest('article');
    try { await api(`/moderation/pros/${c.dataset.proId}/decision`, {method: 'POST', body: {certifier: d === '1', motif: c.querySelector('[name=motif]').value.trim() || null}});
      toast(d === '1' ? 'Professionnel certifié' : 'Refus envoyé'); moderation(); } catch (err) { toast(err.message); }
  };

  return {afficher, ouvrirPro, ouvrirNegociation, afficherMonEspace, moderation,
    aRepondre: () => mesNegos.filter(n => n.a_moi_de_repondre).length || ''};
})();
