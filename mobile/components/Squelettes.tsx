import { useEffect, useRef } from 'react';
import { Animated, View } from 'react-native';

import { couleurs } from '../lib/theme';

/** Des cartes grises qui pulsent pendant le chargement (ou le réveil du serveur), à la place d'un rond qui tourne. */
export function GrilleSquelettes({ nombre = 9 }: { nombre?: number }) {
  const opacite = useRef(new Animated.Value(0.4)).current;
  useEffect(() => {
    const anim = Animated.loop(
      Animated.sequence([
        Animated.timing(opacite, { toValue: 1, duration: 700, useNativeDriver: true }),
        Animated.timing(opacite, { toValue: 0.4, duration: 700, useNativeDriver: true }),
      ]),
    );
    anim.start();
    return () => anim.stop();
  }, [opacite]);
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }} accessibilityLabel="Chargement">
      {Array.from({ length: nombre }, (_, i) => (
        <Animated.View key={i} style={{ width: '31.5%', gap: 6, opacity: opacite }}>
          <View style={{ aspectRatio: 4 / 5, borderRadius: 10, backgroundColor: couleurs.surface }} />
          <View style={{ height: 10, width: '85%', borderRadius: 5, backgroundColor: couleurs.surface }} />
          <View style={{ height: 8, width: '55%', borderRadius: 4, backgroundColor: couleurs.surface }} />
        </Animated.View>
      ))}
    </View>
  );
}
