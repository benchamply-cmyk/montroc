import type { EchangeLecture } from './types';

export const STATUTS_ECHANGE: Record<string, string> = {
  propose: 'En attente des réponses',
  accepte: 'Accepté : remise des objets',
  annule: 'Annulé',
  termine: 'Terminé',
};

/** Ce que j'ai à faire dans un échange, pour le signaler dans la liste ; null si rien. */
export function aFaire(e: EchangeLecture, moiId: number): string | null {
  const recu = e.transferts.find((t) => t.receveur_id === moiId);
  const donne = e.transferts.find((t) => t.donneur_id === moiId);
  if (e.statut === 'propose' && recu?.reponse === 'en_attente') return 'Répondre';
  if (e.statut !== 'propose' && e.statut !== 'accepte') return null;
  if (recu?.mode === 'colis' && !recu.adresse_livraison && !recu.depose_le) return 'Donner mon adresse';
  if (e.statut === 'accepte' && donne && !donne.depose_le) return 'Remettre mon objet';
  return null;
}
