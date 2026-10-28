import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useRef, useState } from 'react';
import { Animated, PanResponder, Text, useWindowDimensions, View } from 'react-native';

import { Bouton, EtatRequete, s } from '../../components/ui';
import { api, ErreurApi } from '../../lib/api';
import { decisionGlisse } from '../../lib/glisse';
import { useFavoris } from '../../lib/favoris';
import { useSession } from '../../lib/session';
import { vibrer } from '../../lib/vibrer';
import { couleurs, ETATS, rayon } from '../../lib/theme';
import type { CarteMatch, MatchLecture, Objet } from '../../lib/types';
import { useRequete } from '../../lib/useRequete';

type Cartes = Omit<ReturnType<typeof useRequete<CarteMatch[]>>, 'setDonnees'>;

export default function Match() {
  const { pret, moi } = useSession();
  if (!pret) return <View style={s.ecran} />;
  // Un visiteur voit les cartes lui aussi ; son premier cœur lui propose de créer un compte (Ben, 28/10).
  return moi ? <Paquet /> : <PaquetVisiteur />;
}

/** Les nouveautés du catalogue, présentées comme des cartes du Match (le carrousel personnalisé demande un compte). */
function PaquetVisiteur() {
  const objets = useRequete<Objet[]>('/objets?limite=20');
  const cartes = objets.donnees?.map(
    (objet): CarteMatch => ({
      objet,
      proprietaire: { id: objet.proprietaire_id, pseudo: '', zone: objet.lieu ?? null, fiabilite: 0 },
      souhait_categorie: null,
      souhait_sous_categorie: null,
      correspond_a_mes_souhaits: false,
      sa_demande: null,
      il_aime: [],
      il_cherche: [],
    }),
  );
  return <Paquet visiteur={{ ...objets, donnees: cartes ?? null }} />;
}

function Paquet({ visiteur }: { visiteur?: Cartes }) {
  const { moi, rafraichir } = useSession();
  const { basculerCoeur } = useFavoris();
  const { width: largeur } = useWindowDimensions();
  const carrousel = useRequete<CarteMatch[]>(visiteur ? null : '/match/carrousel?limite=20');
  const requete: Cartes = visiteur ?? carrousel;
  const [index, setIndex] = useState(0);
  const [nouveauMatch, setNouveauMatch] = useState<MatchLecture | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const position = useRef(new Animated.ValueXY()).current;

  const cartes = requete.donnees ?? [];
  const carte = cartes[index];

  async function envoyerAvis(aime: boolean, superJaime = false) {
    const objetId = cartes[index]?.objet.id;
    setIndex((i) => i + 1);
    position.setValue({ x: 0, y: 0 });
    if (objetId === undefined) return;
    // Visiteur : le cœur est gardé 24 h sur le téléphone, rien n'est envoyé pour « Non merci ».
    if (visiteur) {
      if (aime) basculerCoeur(objetId);
      return;
    }
    try {
      const r = await api<{ match: MatchLecture | null }>('/match/avis', { corps: { objet_id: objetId, aime, super_jaime: superJaime } });
      if (superJaime) rafraichir();
      if (r.match) {
        vibrer('succes');
        setNouveauMatch(r.match);
      }
    } catch (e) {
      setErreur(e instanceof ErreurApi ? e.message : String(e));
    }
  }

  /** Retour arrière (Troc Premium) : annule le dernier « Non merci » et remet la carte. */
  async function revenir() {
    const precedente = cartes[index - 1];
    if (!precedente) return;
    try {
      await api(`/match/avis/${precedente.objet.id}`, { method: 'DELETE' });
      setIndex((i) => i - 1);
    } catch (e) {
      setErreur(e instanceof ErreurApi ? e.message : String(e));
    }
  }

  function lancer(decision: 'aime' | 'passe', superJaime = false) {
    if (decision === 'aime') vibrer();
    Animated.timing(position, {
      toValue: { x: (decision === 'aime' ? 1 : -1) * largeur * 1.5, y: 0 },
      duration: 220,
      // Le geste pilote `position` côté JS : toutes ses animations doivent rester côté JS.
      useNativeDriver: false,
    }).start(() => envoyerAvis(decision === 'aime', superJaime));
  }

  // Recréé à chaque rendu pour voir l'index courant ; le geste en cours n'en souffre pas.
  const geste = PanResponder.create({
    onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dx) > 8,
    onPanResponderMove: Animated.event([null, { dx: position.x, dy: position.y }], { useNativeDriver: false }),
    onPanResponderRelease: (_, g) => {
      const decision = decisionGlisse(g.dx, g.vx, largeur);
      if (decision) lancer(decision);
      else Animated.spring(position, { toValue: { x: 0, y: 0 }, useNativeDriver: false }).start();
    },
  });

  const rotation = position.x.interpolate({ inputRange: [-largeur, 0, largeur], outputRange: ['-12deg', '0deg', '12deg'] });
  const opaciteAime = position.x.interpolate({ inputRange: [0, largeur / 4], outputRange: [0, 1], extrapolate: 'clamp' });
  const opacitePasse = position.x.interpolate({ inputRange: [-largeur / 4, 0], outputRange: [1, 0], extrapolate: 'clamp' });

  if (nouveauMatch)
    return (
      <View style={[s.ecran, s.centre, { justifyContent: 'center' }]}>
        <Text style={[s.grandTitre, { color: couleurs.ok }]}>C'est un match !</Text>
        <Text style={s.texte}>
          {nouveauMatch.avec.pseudo} aime aussi un de vos objets. Retrouvez-le dans l'onglet Échanges pour proposer l'échange.
        </Text>
        <Bouton titre="Proposer l'échange" onPress={() => { setNouveauMatch(null); router.push('/echanges'); }} />
        <Bouton titre="Continuer à matcher" secondaire onPress={() => setNouveauMatch(null)} />
      </View>
    );

  return (
    <View style={[s.ecran, { padding: 16 }]}>
      <EtatRequete {...requete} />
      {erreur && <Text style={s.erreur}>{erreur}</Text>}
      {requete.donnees && !carte && (
        <View style={s.centre}>
          <Text style={s.texte}>Vous avez tout vu pour l'instant.</Text>
          <Bouton titre="Recharger" secondaire onPress={() => { setIndex(0); requete.recharger(); }} />
        </View>
      )}
      {carte && (
        <>
          <Animated.View
            {...geste.panHandlers}
            style={{
              flex: 1,
              backgroundColor: couleurs.surface,
              borderRadius: rayon,
              overflow: 'hidden',
              transform: [...position.getTranslateTransform(), { rotate: rotation }],
            }}
          >
            <Image source={carte.objet.photo_url} style={{ flex: 1 }} contentFit="cover" />
            <View style={{ padding: 16, gap: 4 }}>
              <Text style={s.grandTitre} numberOfLines={2}>{carte.objet.titre}</Text>
              <Text style={[s.discret, { textAlign: 'left' }]}>
                {[carte.objet.etat && ETATS[carte.objet.etat], carte.proprietaire.pseudo, carte.proprietaire.zone].filter(Boolean).join(' · ')}
                {carte.distance_km != null ? ` · ${Math.round(carte.distance_km)} km` : ''}
                {carte.par_colis ? ' · par colis' : ''}
              </Text>
              {carte.sa_demande && <Text style={[s.discret, { textAlign: 'left' }]} numberOfLines={2}>Sa demande : {carte.sa_demande}</Text>}
              {carte.il_aime.length > 0 && (
                <Text style={[s.texte, { color: couleurs.ok }]}>Il aime déjà « {carte.il_aime[0].titre} » : match direct !</Text>
              )}
              {carte.il_aime.length === 0 && carte.il_cherche.length > 0 && (
                <Text style={[s.texte, { color: couleurs.marque }]}>Votre « {carte.il_cherche[0].titre} » l'intéresserait</Text>
              )}
            </View>
            <Animated.Text style={[tampon, { left: 20, color: couleurs.ok, borderColor: couleurs.ok, opacity: opaciteAime }]}>J'AIME</Animated.Text>
            <Animated.Text style={[tampon, { right: 20, color: couleurs.danger, borderColor: couleurs.danger, opacity: opacitePasse }]}>NON MERCI</Animated.Text>
          </Animated.View>
          <View style={{ flexDirection: 'row', gap: 12, paddingTop: 16 }}>
            <View style={{ flex: 1 }}><Bouton titre="Non merci" secondaire onPress={() => lancer('passe')} /></View>
            <View style={{ flex: 1 }}><Bouton titre="J'aime" onPress={() => lancer('aime')} /></View>
          </View>
          <View style={{ flexDirection: 'row', gap: 12, paddingTop: 10 }}>
            {(moi?.avantages ?? []).includes('retour_arriere') && index > 0 && (
              <View style={{ flex: 1 }}><Bouton titre="↶ Retour" secondaire onPress={revenir} /></View>
            )}
            {(moi?.super_jaime_restants ?? 0) > 0 && (
              <View style={{ flex: 1 }}>
                <Bouton titre={`★ Super J'aime (${moi?.super_jaime_restants})`} secondaire onPress={() => lancer('aime', true)} />
              </View>
            )}
          </View>
        </>
      )}
    </View>
  );
}

const tampon = {
  position: 'absolute' as const,
  top: 24,
  fontSize: 22,
  fontWeight: '900' as const,
  borderWidth: 3,
  borderRadius: 8,
  paddingHorizontal: 10,
  paddingVertical: 4,
};
