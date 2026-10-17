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
};
