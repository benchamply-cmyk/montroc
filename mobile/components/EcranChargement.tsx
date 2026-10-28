import { useEffect, useRef, useState } from 'react';
import { Animated, Easing, StyleSheet, Text } from 'react-native';

import { couleurs } from '../lib/theme';
import { MarqueLogo, NomTopTroc } from './Logo';

const DUREE_MIN = 1400;

/**
 * Écran de chargement : prend le relais de l'écran de démarrage natif (même logo, même fond),
 * fait tourner le logo comme au survol sur le site, puis s'efface quand la session est prête.
 */
export function EcranChargement({ pret }: { pret: boolean }) {
  const [visible, setVisible] = useState(true);
  const [delaiPasse, setDelaiPasse] = useState(false);
  const tour = useRef(new Animated.Value(0)).current;
  const apparition = useRef(new Animated.Value(0)).current;
  const opacite = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.timing(apparition, { toValue: 1, duration: 500, delay: 150, useNativeDriver: true }).start();
    Animated.timing(tour, { toValue: 1, duration: 900, delay: 300, easing: Easing.bezier(0.6, 0, 0.2, 1), useNativeDriver: true }).start();
    const t = setTimeout(() => setDelaiPasse(true), DUREE_MIN);
    return () => clearTimeout(t);
  }, [apparition, tour]);

  useEffect(() => {
    if (!pret || !delaiPasse) return;
    Animated.timing(opacite, { toValue: 0, duration: 350, useNativeDriver: true }).start(() => setVisible(false));
  }, [pret, delaiPasse, opacite]);

  if (!visible) return null;
  const rotation = tour.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '180deg'] });
  const montee = apparition.interpolate({ inputRange: [0, 1], outputRange: [12, 0] });
  return (
    <Animated.View style={[StyleSheet.absoluteFill, styles.fond, { opacity: opacite }]} pointerEvents="none">
      <Animated.View style={{ transform: [{ rotate: rotation }] }}>
        <MarqueLogo taille={120} />
      </Animated.View>
      <Animated.View style={{ alignItems: 'center', gap: 8, opacity: apparition, transform: [{ translateY: montee }] }}>
        <NomTopTroc taille={30} />
        <Text style={styles.devise}>Pas de prix. Pas de monnaie.</Text>
      </Animated.View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  fond: { backgroundColor: couleurs.fond, alignItems: 'center', justifyContent: 'center', gap: 20, zIndex: 10 },
  devise: { color: couleurs.discret, fontSize: 15 },
});
