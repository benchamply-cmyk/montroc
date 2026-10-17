import * as SecureStore from 'expo-secure-store';
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

import { api, definirJeton, ErreurApi } from './api';
import type { Moi, ResultatConnexion } from './types';

// Le jeton de session (30 jours) va dans le trousseau de l'appareil, pas dans un stockage en clair.
const CLE = 'troctroc.jeton';

interface Session {
  pret: boolean;
  moi: Moi | null;
  ouvrir: (resultat: ResultatConnexion) => Promise<void>;
  fermer: () => Promise<void>;
  rafraichir: () => Promise<void>;
}

const Contexte = createContext<Session | null>(null);

export function FournisseurSession({ children }: { children: ReactNode }) {
  const [pret, setPret] = useState(false);
  const [moi, setMoi] = useState<Moi | null>(null);

  const oublier = useCallback(async () => {
    definirJeton(null);
    setMoi(null);
    await SecureStore.deleteItemAsync(CLE);
  }, []);

  const rafraichir = useCallback(async () => {
    try {
      setMoi(await api<Moi>('/moi'));
    } catch (e) {
      // 401 : session expirée ; 403 : compte suspendu. Hors ligne, on garde la session.
      if (e instanceof ErreurApi && (e.statut === 401 || e.statut === 403)) await oublier();
    }
  }, [oublier]);

  useEffect(() => {
    (async () => {
      const jeton = await SecureStore.getItemAsync(CLE);
      if (jeton) {
        definirJeton(jeton);
        await rafraichir();
      }
      setPret(true);
    })();
  }, [rafraichir]);

  const ouvrir = useCallback(async (resultat: ResultatConnexion) => {
    if (!resultat.jeton || !resultat.utilisateur) return;
    definirJeton(resultat.jeton);
    await SecureStore.setItemAsync(CLE, resultat.jeton);
    setMoi(resultat.utilisateur);
  }, []);

  const fermer = useCallback(async () => {
    // Ferme les sessions côté serveur (tous les appareils), puis localement même hors ligne.
    await api('/auth/deconnexion', { method: 'POST' }).catch(() => undefined);
    await oublier();
  }, [oublier]);

  return <Contexte.Provider value={{ pret, moi, ouvrir, fermer, rafraichir }}>{children}</Contexte.Provider>;
}

export function useSession(): Session {
  const s = useContext(Contexte);
  if (!s) throw new Error('useSession hors de FournisseurSession');
  return s;
}
