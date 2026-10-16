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
    velos: 'sport', equipements_velos: 'sport', ameublement: 'maison', electromenager: 'electromenager',
    decoration: 'maison', linge_de_maison: 'maison', jeux_jouets: 'enfant', equipement_bebe: 'enfant',
    vetements_bebe: 'enfant', livres: 'culture', cd_musique: 'culture', dvd_films: 'culture', bricolage: 'bricolage',
    jardinage: 'bricolage', sports_hobbies: 'sport', informatique: 'high-tech', image_son: 'high-tech',
    consoles_jeux_video: 'high-tech', consoles: 'high-tech', jeux_video: 'high-tech',
    telephones_objets_connectes: 'high-tech', telephonie: 'high-tech', vetements: 'mode', chaussures: 'mode',
    accessoires_bagagerie: 'mode', montres_bijoux: 'mode', equipement_auto: 'auto-moto', equipement_moto: 'auto-moto',
    instruments_de_musique: 'divers', collection: 'divers', antiquites: 'divers', loisirs_creatifs: 'divers',
  };

  // Mots du titre vers nos catégories : le premier qui correspond l'emporte (les plus précis d'abord).
  const VETEMENT = 'body|pyjama|robe|jupe|pantalon|jean|short|manteau|blouson|parka|pull|gilet|sweat|t ?shirt|tee ?shirt|chaussures|baskets|bottes';
  const ENFANT = 'enfant|enfants|bebe|fille|garcon|junior|\\d+ ?(ans|mois)';
  const MOTS = [
    [/\bpoussettes?\b|\bpoussette canne\b/, 'enfant'],
    [/\bsiege ?auto\b|\brehausseur\b|\bcosy\b/, 'enfant'],
    [/\blit (bebe|parapluie|pliant|evolutif)\b|\bberceau\b|\bcododo\b/, 'enfant'],
    [/\bjeux? de societe\b|\bpuzzle\b|\bmonopoly\b|\bdixit\b|\bscrabble\b/, 'culture'],
    [/\bvelos?\b|\bdraisienne\b|\bvtt\b|\bbmx\b/, 'sport'],
    [new RegExp(`\\b(${VETEMENT})\\b.*\\b(${ENFANT})\\b|\\b(${ENFANT})\\b.*\\b(${VETEMENT})\\b`), 'enfant'],
    [/\blego\b|\bduplo\b|\bplaymobil\b|\bjouets?\b|\bpeluche\b|\bpoupee\b|\bdinette\b/, 'enfant'],
    [/\blivres?\b|\broman\b|\bbd\b|\bmanga\b|\bencyclopedie\b/, 'culture'],
    [/\bperceuse\b|\bvisseuse\b|\bscie\b|\bponceuse\b|\btondeuse\b|\boutils?\b|\bcaisse a outils\b|\bechelle\b/, 'bricolage'],
    [/\baspirateur\b|\bmicro ?ondes?\b|\bcafetiere\b|\bbouilloire\b|\bfour\b|\bfrigo\b|\brefrigerateur\b|\blave ?(linge|vaisselle)\b|\bmixeur\b|\bgrille ?pain\b|\brobot (cuisine|patissier)\b/, 'electromenager'],
    [/\bconsole\b|\bswitch\b|\bplaystation\b|\bps[345]\b|\bxbox\b|\btele(vision)?\b|\btv\b|\bordinateur\b|\bpc\b|\btablette\b|\bipad\b|\btelephone\b|\biphone\b|\benceinte\b|\bcasque\b|\bappareil photo\b/, 'high-tech'],
    [/\braquettes?\b|\bski\b|\btente\b|\bballon\b|\btrottinette\b|\broller\b|\bskate\b|\bhalteres\b|\byoga\b|\bcamping\b|\bping ?pong\b/, 'sport'],
    [/\bcanape\b|\bchaises?\b|\btable\b|\barmoire\b|\bcommode\b|\betagere\b|\bbureau\b|\bbuffet\b|\bfauteuil\b|\bmatelas\b/, 'maison'],
    [/\blampe\b|\bmiroir\b|\bcadre\b|\bvase\b|\btapis\b|\brideaux?\b|\bcoussins?\b|\bbougeoir\b|\bsuspension\b/, 'maison'],
    [/\bvinyles?\b|\bcd\b|\bdvd\b|\bblu ?ray\b/, 'culture'],
    [/\bpneus?\b|\bjantes?\b|\bautoradio\b|\bporte ?velo\b|\bbarres de toit\b/, 'auto-moto'],
    [/\bguitare\b|\bpiano\b|\bviolon\b|\bukulele\b|\bbatterie electronique\b|\bdeguisement\b/, 'divers'],
    [new RegExp(`\\b(${VETEMENT}|sac a main|bijoux?|montre)\\b`), 'mode'],
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
