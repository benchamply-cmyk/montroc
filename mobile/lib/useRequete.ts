import { useCallback, useEffect, useRef, useState } from 'react';

import { api, ErreurApi } from './api';

// Au-delà de ce délai, on prévient que le serveur se réveille (Render gratuit) au lieu d'un simple sablier.
const REVEIL_MS = 4_000;

export function useRequete<T>(chemin: string | null) {
  const [donnees, setDonnees] = useState<T | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(false);
  const [reveil, setReveil] = useState(false);
  const actif = useRef(true);

  const charger = useCallback(async () => {
    if (!chemin) return;
    setChargement(true);
    setErreur(null);
    const minuterie = setTimeout(() => actif.current && setReveil(true), REVEIL_MS);
    try {
      const r = await api<T>(chemin);
      if (actif.current) setDonnees(r);
    } catch (e) {
      if (actif.current) setErreur(e instanceof ErreurApi ? e.message : String(e));
    } finally {
      clearTimeout(minuterie);
      if (actif.current) {
        setChargement(false);
        setReveil(false);
      }
    }
  }, [chemin]);

  useEffect(() => {
    actif.current = true;
    charger();
    return () => {
      actif.current = false;
    };
  }, [charger]);

  return { donnees, erreur, chargement, reveil, recharger: charger, setDonnees };
}
