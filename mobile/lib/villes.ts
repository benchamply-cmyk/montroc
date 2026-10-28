// Suggestions de villes par la Base Adresse Nationale, comme web/premium.js (villes()).
const BAN = 'https://api-adresse.data.gouv.fr';

export interface Ville {
  libelle: string;
  latitude: number;
  longitude: number;
}

// 0,01° ≈ 1 km : on n'envoie jamais une position précise (domicile), comme l'API.
const arrondi = (x: number) => Math.round(x * 100) / 100;

export async function chercherVilles(q: string): Promise<Ville[]> {
  if (q.trim().length < 3) return [];
  try {
    const r = await fetch(`${BAN}/search/?type=municipality&limit=5&q=${encodeURIComponent(q.trim())}`);
    const d = await r.json();
    return (d.features ?? []).map((f: any) => ({
      libelle: `${f.properties.city} (${f.properties.postcode})`,
      latitude: arrondi(f.geometry.coordinates[1]),
      longitude: arrondi(f.geometry.coordinates[0]),
    }));
  } catch {
    return [];
  }
}
