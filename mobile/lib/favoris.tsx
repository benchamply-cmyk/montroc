import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { Alert } from 'react-native';

import { api, ErreurApi } from './api';
import { useSession } from './session';
import { ecrire, lire } from './stockage';

// Comme le site (#77) : l'étoile met en favori (24 h sur l'appareil pour un visiteur, dans le compte pour un membre),
// le cœur est le « J'aime » du Match, réservé aux membres. Deux choses distinctes.
const CLE = 'troc.favoris';
const DUREE_VISITEUR_MS = 24 * 3600 * 1000;
const MAX_VISITEUR = 50;

export interface FavoriLocal {
  objet_id: number;
  ajoute_le: string;
}

interface Favoris {
  etoiles: Set<number>;
  coeurs: Set<number>;
  // Favoris d'un visiteur, avec leur date (ils expirent au bout de 24 h).
  locaux: FavoriLocal[];
  basculerEtoile: (objetId: number) => Promise<void>;
  basculerCoeur: (objetId: number) => Promise<void>;
  recharger: () => Promise<void>;
}

const Contexte = createContext<Favoris | null>(null);

const frais = (liste: FavoriLocal[]) => liste.filter((f) => Date.now() - new Date(f.ajoute_le).getTime() < DUREE_VISITEUR_MS);

export function FournisseurFavoris({ children }: { children: ReactNode }) {
  const { pret, moi } = useSession();
  const [locaux, setLocaux] = useState<FavoriLocal[]>([]);
  const [etoilesCompte, setEtoilesCompte] = useState<Set<number>>(new Set());
  const [coeurs, setCoeurs] = useState<Set<number>>(new Set());
  const avertiVisiteur = useRef(false);

  const recharger = useCallback(async () => {
    if (!moi) {
      setLocaux(frais(await lire<FavoriLocal[]>(CLE, [])));
      setCoeurs(new Set());
      return;
    }
    // Les favoris du visiteur rejoignent le compte à la connexion, puis l'appareil les oublie.
    const enAttente = frais(await lire<FavoriLocal[]>(CLE, []));
    for (const f of enAttente) await api('/moi/favoris', { corps: { objet_id: f.objet_id } }).catch(() => undefined);
    if (enAttente.length) await ecrire(CLE, null);
    setLocaux([]);
    const [favoris, aimes] = await Promise.all([
      api<{ id: number }[]>('/moi/favoris').catch(() => []),
      api<number[]>('/match/avis').catch(() => []),
    ]);
    setEtoilesCompte(new Set(favoris.map((o) => o.id)));
    setCoeurs(new Set(aimes));
  }, [moi]);

  useEffect(() => {
    if (pret) recharger();
  }, [pret, recharger]);

  const basculerEtoile = useCallback(
    async (objetId: number) => {
      if (!moi) {
        const deja = locaux.some((f) => f.objet_id === objetId);
        const liste = deja
          ? locaux.filter((f) => f.objet_id !== objetId)
          : [{ objet_id: objetId, ajoute_le: new Date().toISOString() }, ...locaux].slice(0, MAX_VISITEUR);
        setLocaux(liste);
        await ecrire(CLE, liste);
        if (!deja && !avertiVisiteur.current) {
          avertiVisiteur.current = true;
          Alert.alert('Favori gardé 24 heures', 'Sans compte, vos favoris restent sur ce téléphone pendant 24 heures. Créez un compte pour les garder.');
        }
        return;
      }
      const deja = etoilesCompte.has(objetId);
      const suivant = new Set(etoilesCompte);
      if (deja) suivant.delete(objetId);
      else suivant.add(objetId);
      setEtoilesCompte(suivant);
      try {
        if (deja) await api(`/moi/favoris/${objetId}`, { method: 'DELETE' });
        else await api('/moi/favoris', { corps: { objet_id: objetId } });
      } catch (e) {
        setEtoilesCompte(etoilesCompte);
        Alert.alert('Favori', e instanceof ErreurApi ? e.message : String(e));
      }
    },
    [moi, locaux, etoilesCompte],
  );

  const basculerCoeur = useCallback(
    async (objetId: number) => {
      if (!moi) return;
      const deja = coeurs.has(objetId);
      const suivant = new Set(coeurs);
      if (deja) suivant.delete(objetId);
      else suivant.add(objetId);
      setCoeurs(suivant);
      try {
        if (deja) await api(`/match/avis/${objetId}`, { method: 'DELETE' });
        else {
          const r = await api<{ match: { avec: { pseudo: string } } | null }>('/match/avis', { corps: { objet_id: objetId, aime: true } });
          if (r.match) Alert.alert("C'est un match !", `${r.match.avec.pseudo} aime aussi un de vos objets. Proposez l'échange depuis Mon espace.`);
        }
      } catch (e) {
        setCoeurs(coeurs);
        Alert.alert("J'aime", e instanceof ErreurApi ? e.message : String(e));
      }
    },
    [moi, coeurs],
  );

  const etoiles = moi ? etoilesCompte : new Set(locaux.map((f) => f.objet_id));
  return (
    <Contexte.Provider value={{ etoiles, coeurs, locaux, basculerEtoile, basculerCoeur, recharger }}>{children}</Contexte.Provider>
  );
}

export function useFavoris(): Favoris {
  const f = useContext(Contexte);
  if (!f) throw new Error('useFavoris hors de FournisseurFavoris');
  return f;
}
