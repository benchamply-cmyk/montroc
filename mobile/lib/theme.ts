// Mêmes couleurs que web/site.css : thème sombre unique.
export const couleurs = {
  fond: '#111318',
  surface: '#1A1D24',
  encre: '#F2F3F6',
  discret: '#A3A9B6',
  trait: '#2C303A',
  accent: '#8B97FF',
  accentEncre: '#111318',
  marque: '#E6C23A',
  ok: '#5FD39A',
  okFond: '#16301F',
  danger: '#FF7A6E',
};

export const rayon = 14;

export const ETATS: Record<string, string> = {
  neuf: 'Neuf',
  comme_neuf: 'Comme neuf',
  tres_bon: 'Très bon état',
  bon: 'Bon état',
  correct: 'État correct',
};

// Mêmes clés que nomenclature.MODES_ECHANGE côté API.
export const MODES_ECHANGE: Record<string, string> = {
  main_propre: 'Main propre',
  point_relais: 'Point relais',
  colis: "Colis (frais d'envoi à ma charge)",
};

// Mêmes clés que nomenclature.FORMATS_COLIS côté API.
export const FORMATS_COLIS: Record<string, string> = {
  petit: "Petit colis (jusqu'à 1 kg)",
  moyen: "Colis moyen (jusqu'à 5 kg)",
  grand: "Grand colis (jusqu'à 30 kg)",
};

// Les pages publiques du site (concept, FAQ, pages légales…) s'ouvrent dans le navigateur.
export const SITE = 'https://toptroc.com';

// Mêmes libellés que web/premium.js.
export const AVANTAGES: Record<string, string> = {
  sans_pub: 'Sans publicité',
  voir_qui_aime: 'Voir qui aime vos objets',
  retour_arriere: 'Retour arrière dans le Match',
  apercu_du_stock: 'Aperçu du stock du dimanche',
  avant_premiere: 'Avant-première du Grand Troc à 17 h',
  shortlist: 'En tête des ShortLists',
  priorite: 'Priorité à égalité au Grand Troc',
  zones_multiples: "Jusqu'à 3 zones d'intérêt",
  garantie_colis: 'Garantie TopTroc sur vos colis',
  famille: '3 proches inclus',
};

export const REPUTATIONS: Record<string, string> = {
  nouveau: 'Nouveau membre',
  membre: 'Membre',
  fiable: 'Membre fiable',
  a_confirmer: 'À confirmer',
};
