/* « Votre annonce ne part pas ? Troquez-la. »
   On lit seulement le lien collé (son adresse), jamais la page : les conditions d'utilisation de Vinted
   et de Leboncoin interdisent la récupération automatique de leurs annonces. Le titre (Vinted) et la
   catégorie se devinent à partir de l'adresse ; la personne reprend sa photo et choisit l'état. Jamais de prix. */
(function (racine) {
  const SITES = [
    {nom: 'Vinted', hote: /^(www\.)?vinted\.[a-z]{2,3}(\.[a-z]{2})?$/},
    {nom: 'Leboncoin', hote: /^(www\.)?leboncoin\.fr$/},
  ];

  // Rubriques Leboncoin (dans l'adresse de l'annonce) vers nos catégories.
  const RUBRIQUES = {
    velos: 'velo', equipements_velos: 'velo', ameublement: 'meubles', electromenager: 'electromenager',
    decoration: 'deco', jeux_jouets: 'jouets', livres: 'livres', bricolage: 'outillage', jardinage: 'outillage',
    sports_hobbies: 'sport', informatique: 'multimedia', image_son: 'multimedia', consoles_jeux_video: 'multimedia',
    consoles: 'multimedia', jeux_video: 'multimedia', telephones_objets_connectes: 'multimedia', telephonie: 'multimedia',
  };

  // Mots du titre vers nos catégories : le premier qui correspond l'emporte (les plus précis d'abord).
  const VETEMENT = 'body|pyjama|robe|jupe|pantalon|jean|short|manteau|blouson|parka|pull|gilet|sweat|t ?shirt|tee ?shirt|chaussures|baskets|bottes';
  const ENFANT = 'enfant|enfants|bebe|fille|garcon|junior|\\d+ ?(ans|mois)';
  const MOTS = [
    [/\bpoussettes?\b|\bpoussette canne\b/, 'poussette'],
    [/\bsiege ?auto\b|\brehausseur\b|\bcosy\b/, 'siege-auto'],
    [/\blit (bebe|parapluie|pliant|evolutif)\b|\bberceau\b|\bcododo\b/, 'lit-bebe'],
    [/\bjeux? de societe\b|\bpuzzle\b|\bmonopoly\b|\bdixit\b|\bscrabble\b/, 'jeux-de-societe'],
    [/\bvelos?\b|\bdraisienne\b|\bvtt\b|\bbmx\b/, 'velo'],
    [new RegExp(`\\b(${VETEMENT})\\b.*\\b(${ENFANT})\\b|\\b(${ENFANT})\\b.*\\b(${VETEMENT})\\b`), 'vetements-enfant'],
    [/\blego\b|\bduplo\b|\bplaymobil\b|\bjouets?\b|\bpeluche\b|\bpoupee\b|\bdinette\b/, 'jouets'],
    [/\blivres?\b|\broman\b|\bbd\b|\bmanga\b|\bencyclopedie\b/, 'livres'],
    [/\bperceuse\b|\bvisseuse\b|\bscie\b|\bponceuse\b|\btondeuse\b|\boutils?\b|\bcaisse a outils\b|\bechelle\b/, 'outillage'],
    [/\baspirateur\b|\bmicro ?ondes?\b|\bcafetiere\b|\bbouilloire\b|\bfour\b|\bfrigo\b|\brefrigerateur\b|\blave ?(linge|vaisselle)\b|\bmixeur\b|\bgrille ?pain\b|\brobot (cuisine|patissier)\b/, 'electromenager'],
    [/\bconsole\b|\bswitch\b|\bplaystation\b|\bps[345]\b|\bxbox\b|\btele(vision)?\b|\btv\b|\bordinateur\b|\bpc\b|\btablette\b|\bipad\b|\btelephone\b|\biphone\b|\benceinte\b|\bcasque\b|\bappareil photo\b/, 'multimedia'],
    [/\braquettes?\b|\bski\b|\btente\b|\bballon\b|\btrottinette\b|\broller\b|\bskate\b|\bhalteres\b|\byoga\b|\bcamping\b|\bping ?pong\b/, 'sport'],
    [/\bcanape\b|\bchaises?\b|\btable\b|\barmoire\b|\bcommode\b|\betagere\b|\bbureau\b|\bbuffet\b|\bfauteuil\b|\bmatelas\b/, 'meubles'],
    [/\blampe\b|\bmiroir\b|\bcadre\b|\bvase\b|\btapis\b|\brideaux?\b|\bcoussins?\b|\bbougeoir\b|\bsuspension\b/, 'deco'],
  ];

  const sansAccents = t => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

  function categorieDepuisTitre(titre) {
    const t = sansAccents(titre).replace(/[^a-z0-9]+/g, ' ');
    const trouve = MOTS.find(([motif]) => motif.test(t));
    return trouve ? trouve[1] : null;
  }

  // « 4567-robe-zara-fille-8-ans » devient « Robe zara fille 8 ans ».
  function titreDepuisSlug(slug) {
    let t = slug; try { t = decodeURIComponent(slug); } catch { /* adresse mal encodée : on garde le texte brut */ }
    t = t.replace(/^\d+-?/, '').replace(/[-_+]+/g, ' ').replace(/\s+/g, ' ').trim();
    return t ? (t[0].toUpperCase() + t.slice(1)).slice(0, 120) : '';
  }

  /* Lit l'adresse d'une annonce. Renvoie null si ce n'est pas une annonce Vinted ou Leboncoin. */
  function lire(texte) {
    let u;
    try { u = new URL(String(texte || '').trim()); } catch { return null; }
    const hote = u.hostname.toLowerCase(), site = SITES.find(s => s.hote.test(hote));
    if (!site || !['http:', 'https:'].includes(u.protocol) || u.pathname.length < 2) return null;
    const morceaux = u.pathname.split('/').filter(Boolean);
    let titre = '', categorie = null;
    if (site.nom === 'Vinted') {
      const i = morceaux.indexOf('items');
      if (i >= 0 && morceaux[i + 1]) titre = titreDepuisSlug(morceaux[i + 1]);
      if (titre) categorie = categorieDepuisTitre(titre);
    } else {
      // /ad/velos/2712345678 (adresse actuelle) ou /velos/1234567.htm (ancienne).
      const rubrique = morceaux[0] === 'ad' ? morceaux[1] : morceaux[0];
      categorie = RUBRIQUES[rubrique] || null;
    }
    return {site: site.nom, lien: `https://${hote}${u.pathname}`, titre, categorie};
  }

  const AnnonceAilleurs = {lire, categorieDepuisTitre, titreDepuisSlug};
  if (typeof module === 'object' && module.exports) module.exports = AnnonceAilleurs;
  else racine.AnnonceAilleurs = AnnonceAilleurs;
})(this);
