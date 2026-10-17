import * as ImagePicker from 'expo-image-picker';

import { api, ErreurApi } from './api';
import type { PhotoSignature } from './types';

export type Source = 'appareil' | 'galerie';

/** Prend ou choisit une photo ; null si la personne annule. Lève une ErreurApi lisible si l'accès est refusé. */
export async function choisirPhoto(source: Source): Promise<string | null> {
  // La galerie passe par le sélecteur du système, qui ne demande pas l'accès à toute la photothèque.
  if (source === 'appareil' && !(await ImagePicker.requestCameraPermissionsAsync()).granted)
    throw new ErreurApi(0, "Autorisez l'appareil photo dans les réglages.");
  const options: ImagePicker.ImagePickerOptions = {
    mediaTypes: ['images'],
    allowsEditing: true,
    aspect: [1, 1],
    // Comme le site, qui réduit la photo avant l'envoi : assez net pour le catalogue, léger en 4G.
    quality: 0.6,
  };
  try {
    const r = source === 'appareil' ? await ImagePicker.launchCameraAsync(options) : await ImagePicker.launchImageLibraryAsync(options);
    return r.canceled ? null : r.assets[0].uri;
  } catch {
    // Le simulateur iOS n'a pas d'appareil photo.
    throw new ErreurApi(0, "L'appareil photo n'est pas disponible : choisissez une photo de la galerie.");
  }
}

/** Envoie la photo directement à Cloudinary, avec la signature donnée par l'API (comme le site). */
export async function envoyerPhoto(uri: string): Promise<{ photo_url: string; photo_id: string }> {
  const sig = await api<PhotoSignature>('/moi/photos/signature');
  const corps = new FormData();
  // React Native lit le fichier local à partir de {uri, name, type}.
  corps.append('file', { uri, name: 'photo.jpg', type: 'image/jpeg' } as unknown as Blob);
  corps.append('api_key', sig.api_key);
  corps.append('timestamp', String(sig.timestamp));
  corps.append('folder', sig.folder);
  corps.append('signature', sig.signature);
  const reponse = await fetch(sig.url_envoi, { method: 'POST', body: corps }).catch(() => null);
  if (!reponse?.ok) throw new ErreurApi(reponse?.status ?? 0, "La photo n'a pas pu être envoyée.");
  const d = await reponse.json();
  return { photo_url: d.secure_url, photo_id: d.public_id };
}
