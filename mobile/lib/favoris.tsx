import { router } from 'expo-router';
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { Alert } from 'react-native';

import { api, ErreurApi } from './api';
import { useSession } from './session';
import { ecrire, lire } from './stockage';
import { vibrer } from './vibrer';

// Un seul cœur, comme sur Vinted (Ben, 28/10) : il met l'objet en favori ET donne le « J'aime » du Match.
// Un visiteur garde ses cœurs 24 h sur l'appareil ; à la connexion, ils deviennent des favoris et des J'aime.
const CLE = 'troc.favoris';
const DUREE_VISITEUR_MS = 24 * 3600 * 1000;
const MAX_VISITEUR = 50;

export interface FavoriLocal {
  objet_id: number;
  ajoute_le: string;
}

interface Favoris {
  coeurs: Set<number>;
  // Cœurs d'un visiteur, avec leur date (ils expirent au bout de 24 h).
  locaux: FavoriLocal[];
  basculerCoeur: (objetId: number) => Promise<void>;
  recharger: () => Promise<void>;
}

const Contexte = createContext<Favoris | null>(null);

const frais = (liste: FavoriLocal[]) => liste.filter((f) => Date.now() - new Date(f.ajoute_le).getTime() < DUREE_VISITEUR_MS);

type ResultatAvis = { match: { avec: { pseudo: string } } | null };

/** Le J'aime part en même temps que le favori ; il est refusé sur certains objets (le sien, déjà échangé) sans que le favori en pâtisse. */
const aimer = (objetId: number) => api<ResultatAvis>('/match/avis', { corps: { objet_id: objetId, aime: true } }).catch(() => ({ match: null }));

export function FournisseurFavoris({ children }: { children: ReactNode }) {
  const { pret, moi } = useSession();
  const [locaux, setLocaux] = useState<FavoriLocal[]>([]);
  const [coeursCompte, setCoeursCompte] = useState<Set<number>>(new Set());
  const avertiVisiteur = useRef(false);

  const recharger = useCallback(async () => {
    if (!moi) {
      setLocaux(frais(await lire<FavoriLocal[]>(CLE, [])));
      setCoeursCompte(new Set());
      return;
    }
    // Les cœurs du visiteur rejoignent le compte à la connexion, puis l'appareil les oublie.
    const enAttente = frais(await lire<FavoriLocal[]>(CLE, []));
    for (const f of enAttente) {
      await api('/moi/favoris', { corps: { objet_id: f.objet_id } }).catch(() => undefined);
      await aimer(f.objet_id);
    }
    if (enAttente.length) await ecrire(CLE, null);
    setLocaux([]);
    const [favoris, aimes] = await Promise.all([
      api<{ id: number }[]>('/moi/favoris').catch(() => []),
      api<number[]>('/match/avis').catch(() => []),
    ]);
    setCoeursCompte(new Set([...favoris.map((o) => o.id), ...aimes]));
  }, [moi]);

  useEffect(() => {
    if (pret) recharger();
  }, [pret, recharger]);

  const basculerCoeur = useCallback(
    async (objetId: number) => {
      if (!moi) {
        const deja = locaux.some((f) => f.objet_id === objetId);
        if (!deja) vibrer();
        const liste = deja
          ? locaux.filter((f) => f.objet_id !== objetId)
          : [{ objet_id: objetId, ajoute_le: new Date().toISOString() }, ...locaux].slice(0, MAX_VISITEUR);
        setLocaux(liste);
        await ecrire(CLE, liste);
        if (!deja && !avertiVisiteur.current) {
          avertiVisiteur.current = true;
          Alert.alert('Gardé 24 heures', 'Sans compte, vos cœurs restent sur ce téléphone pendant 24 heures. Avec un compte, ils sont gardés et deviennent des « J\'aime » : si le propriétaire aime un de vos objets, c\'est un match.', [
            { text: 'Plus tard', style: 'cancel' },
            { text: 'Créer un compte', onPress: () => router.push('/connexion') },
          ]);
        }
        return;
      }
      const deja = coeursCompte.has(objetId);
      if (!deja) vibrer();
      const suivant = new Set(coeursCompte);
      if (deja) suivant.delete(objetId);
      else suivant.add(objetId);
      setCoeursCompte(suivant);
      try {
        if (deja) {
          // L'un des deux peut manquer (cœur donné sur le site avant le 28/10) : on retire ce qui existe.
          await Promise.all([
            api(`/moi/favoris/${objetId}`, { method: 'DELETE' }).catch(() => undefined),
            api(`/match/avis/${objetId}`, { method: 'DELETE' }).catch(() => undefined),
          ]);
        } else {
          await api('/moi/favoris', { corps: { objet_id: objetId } });
          const r = await aimer(objetId);
          if (r.match) vibrer('succes');
          if (r.match) Alert.alert("C'est un match !", `${r.match.avec.pseudo} aime aussi un de vos objets. Proposez l'échange depuis l'onglet Échanges.`);
        }
      } catch (e) {
        setCoeursCompte(coeursCompte);
        Alert.alert('Favori', e instanceof ErreurApi ? e.message : String(e));
      }
    },
    [moi, locaux, coeursCompte],
  );

  const coeurs = moi ? coeursCompte : new Set(locaux.map((f) => f.objet_id));
  return <Contexte.Provider value={{ coeurs, locaux, basculerCoeur, recharger }}>{children}</Contexte.Provider>;
}

export function useFavoris(): Favoris {
  const f = useContext(Contexte);
  if (!f) throw new Error('useFavoris hors de FournisseurFavoris');
  return f;
}
