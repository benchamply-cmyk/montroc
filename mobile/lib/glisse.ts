export type Decision = 'aime' | 'passe' | null;

/**
 * Au moment où le doigt quitte la carte du Match : « J'aime », « Non merci », ou la carte revient au centre (null).
 *
 * @param dx       déplacement horizontal depuis le début du geste, en points (positif = vers la droite)
 * @param vx       vitesse horizontale au lâcher, en points par milliseconde (positif = vers la droite)
 * @param largeur  largeur de l'écran, en points
 */
export function decisionGlisse(dx: number, vx: number, largeur: number): Decision {
  // Un geste qui repart en sens inverse au lâcher est une hésitation : la carte revient.
  if (dx !== 0 && vx !== 0 && Math.sign(dx) !== Math.sign(vx) && Math.abs(vx) > 0.2) return null;
  // « J'aime » peut créer un match et une proposition d'échange : il demande un geste plus franc.
  const seuil = dx > 0 ? 0.35 : 0.25;
  const loin = Math.abs(dx) > largeur * seuil;
  const vif = Math.abs(vx) > 0.6 && Math.abs(dx) > largeur * 0.1;
  if (!loin && !vif) return null;
  return dx > 0 ? 'aime' : 'passe';
}
