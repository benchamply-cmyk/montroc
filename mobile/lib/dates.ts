/** « dans 2 j 5 h », « dans 3 h 12 min », « maintenant ». */
export function compteARebours(cible: Date, maintenant: number) {
  const min = Math.max(0, Math.round((cible.getTime() - maintenant) / 60000));
  if (min === 0) return 'maintenant';
  const j = Math.floor(min / 1440);
  const h = Math.floor((min % 1440) / 60);
  return j ? `dans ${j} j ${h} h` : h ? `dans ${h} h ${min % 60} min` : `dans ${min} min`;
}
