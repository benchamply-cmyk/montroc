import Constants from 'expo-constants';

export const API: string = Constants.expoConfig?.extra?.api ?? 'https://api.troctroc.fr';

// Render gratuit peut mettre près d'une minute à se réveiller : on attend jusque-là avant d'abandonner.
const DELAI_MAX_MS = 70_000;

export class ErreurApi extends Error {
  constructor(public statut: number, message: string) {
    super(message);
  }
}

let jetonCourant: string | null = null;
export function definirJeton(jeton: string | null) {
  jetonCourant = jeton;
}

/** FastAPI renvoie {detail: "…"} ou {detail: [{msg}, …]} pour les erreurs de validation. */
function messageErreur(corps: any, statut: number): string {
  const detail = corps?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return `Erreur ${statut}`;
}

export async function api<T>(chemin: string, options: { method?: string; corps?: unknown } = {}): Promise<T> {
  const controleur = new AbortController();
  const minuterie = setTimeout(() => controleur.abort(), DELAI_MAX_MS);
  try {
    const reponse = await fetch(API + chemin, {
      method: options.method ?? (options.corps ? 'POST' : 'GET'),
      headers: {
        Accept: 'application/json',
        ...(options.corps ? { 'Content-Type': 'application/json' } : {}),
        ...(jetonCourant ? { Authorization: `Bearer ${jetonCourant}` } : {}),
      },
      body: options.corps ? JSON.stringify(options.corps) : undefined,
      signal: controleur.signal,
    });
    if (reponse.status === 204) return undefined as T;
    const corps = await reponse.json().catch(() => null);
    if (!reponse.ok) throw new ErreurApi(reponse.status, messageErreur(corps, reponse.status));
    return corps as T;
  } catch (e) {
    if (e instanceof ErreurApi) throw e;
    throw new ErreurApi(0, 'Le serveur ne répond pas. Vérifiez votre connexion et réessayez.');
  } finally {
    clearTimeout(minuterie);
  }
}
