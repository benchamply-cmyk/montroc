import { useEffect, useRef } from 'react';
import { Animated, Easing, Text, View } from 'react-native';

import { couleurs } from '../lib/theme';

const TAILLE = 220;
const RAYON = 82;
// Comme l'animation de l'accueil du site : vous, Sophie et Loïc, chacun reçoit de l'autre.
const NOEUDS = [
  { nom: 'Vous', angle: -90, objet: '👶' },
  { nom: 'Sophie', angle: 30, objet: '🌱' },
  { nom: 'Loïc', angle: 150, objet: '🚲' },
];

/** La boucle d'échange à trois, avec les objets qui circulent sur l'anneau. */
export function Boucle3() {
  const tour = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const anim = Animated.loop(Animated.timing(tour, { toValue: 1, duration: 9000, easing: Easing.linear, useNativeDriver: true }));
    anim.start();
    return () => anim.stop();
  }, [tour]);
  const rotation = tour.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });
  const position = (angle: number, demi: number) => ({
    left: TAILLE / 2 + RAYON * Math.cos((angle * Math.PI) / 180) - demi,
    top: TAILLE / 2 + RAYON * Math.sin((angle * Math.PI) / 180) - demi,
  });

  return (
    <View
      style={{ width: TAILLE, height: TAILLE, alignSelf: 'center' }}
      accessibilityLabel="Exemple de boucle : vous donnez une poussette à Sophie, Sophie donne un kit de jardinage à Loïc, Loïc vous donne un vélo enfant."
    >
      <View style={{ position: 'absolute', left: TAILLE / 2 - RAYON, top: TAILLE / 2 - RAYON, width: RAYON * 2, height: RAYON * 2, borderRadius: RAYON, borderWidth: 2, borderColor: couleurs.trait, borderStyle: 'dashed' }} />
      <Animated.View style={{ position: 'absolute', width: TAILLE, height: TAILLE, transform: [{ rotate: rotation }] }}>
        {NOEUDS.map((n) => (
          <Text key={n.objet} style={{ position: 'absolute', fontSize: 20, ...position(n.angle + 60, 12) }}>
            {n.objet}
          </Text>
        ))}
      </Animated.View>
      {NOEUDS.map((n) => (
        <View
          key={n.nom}
          style={{
            position: 'absolute',
            width: 64,
            height: 30,
            borderRadius: 15,
            backgroundColor: n.nom === 'Vous' ? couleurs.marque : couleurs.surface,
            borderWidth: 1,
            borderColor: couleurs.trait,
            alignItems: 'center',
            justifyContent: 'center',
            left: TAILLE / 2 + RAYON * Math.cos((n.angle * Math.PI) / 180) - 32,
            top: TAILLE / 2 + RAYON * Math.sin((n.angle * Math.PI) / 180) - 15,
          }}
        >
          <Text style={{ color: n.nom === 'Vous' ? couleurs.accentEncre : couleurs.encre, fontWeight: '700', fontSize: 13 }}>{n.nom}</Text>
        </View>
      ))}
      <View style={{ position: 'absolute', left: 0, right: 0, top: TAILLE / 2 - 26, alignItems: 'center' }}>
        <Text style={{ color: couleurs.encre, fontWeight: '800', fontSize: 16 }}>1 boucle</Text>
        <Text style={{ color: couleurs.discret, fontSize: 12 }}>3 personnes servies</Text>
        <Text style={{ color: couleurs.ok, fontSize: 11, marginTop: 2, textAlign: 'center', maxWidth: 120 }}>Jusqu'à +40 % de chances</Text>
      </View>
    </View>
  );
}
