import * as SecureStore from 'expo-secure-store';

// Petites listes gardées sur l'appareil (favoris visiteur, recherches, suivi), comme le localStorage du site.
// SecureStore conseille de rester sous 2 Ko par valeur : les listes sont courtes et bornées par l'appelant.

export async function lire<T>(cle: string, defaut: T): Promise<T> {
  try {
    const brut = await SecureStore.getItemAsync(cle);
    return brut ? (JSON.parse(brut) as T) : defaut;
  } catch {
    return defaut;
  }
}

export async function ecrire(cle: string, valeur: unknown): Promise<void> {
  try {
    if (valeur === null) await SecureStore.deleteItemAsync(cle);
    else await SecureStore.setItemAsync(cle, JSON.stringify(valeur));
  } catch {
    // Trousseau indisponible : la liste reste en mémoire pour cette fois.
  }
}

// Comme le site (troc.recherches) : les dernières recherches, pour y revenir et pour les alertes sans compte.
export const CLE_RECHERCHES = 'troc.recherches';
export interface Recherche {
  q: string;
  categorie: string | null;
}

// Le jeton du suivi par e-mail ou SMS d'un visiteur (troc.suivi sur le site).
export const CLE_SUIVI = 'troc.suivi';
