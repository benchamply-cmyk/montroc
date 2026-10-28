import { useEffect, useRef, type ReactNode } from 'react';
import { Animated, BackHandler, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { couleurs } from '../lib/theme';
import { Bouton, s } from './ui';

/**
 * Une feuille qui monte du bas de l'écran (filtres, choix), fermée en touchant le fond.
 * Dessinée dans l'écran plutôt que dans une Modal : elle reste dans le cadre du téléphone de l'aperçu web.
 */
export function FeuilleBas(p: { visible: boolean; titre: string; onFermer: () => void; action?: string; children: ReactNode }) {
  const marges = useSafeAreaInsets();
  const montee = useRef(new Animated.Value(0)).current;
  const { visible, onFermer } = p;

  useEffect(() => {
    if (!visible) return;
    montee.setValue(0);
    Animated.timing(montee, { toValue: 1, duration: 220, useNativeDriver: true }).start();
    // Le bouton retour d'Android ferme la feuille au lieu de quitter l'écran.
    const abonnement = BackHandler.addEventListener('hardwareBackPress', () => {
      onFermer();
      return true;
    });
    return () => abonnement.remove();
  }, [visible, montee, onFermer]);

  if (!visible) return null;
  const decalage = montee.interpolate({ inputRange: [0, 1], outputRange: [400, 0] });
  return (
    <View style={[StyleSheet.absoluteFill, { zIndex: 20, justifyContent: 'flex-end' }]}>
      <Animated.View style={[StyleSheet.absoluteFill, { backgroundColor: 'rgba(0,0,0,0.55)', opacity: montee }]}>
        <Pressable accessibilityLabel="Fermer" style={{ flex: 1 }} onPress={onFermer} />
      </Animated.View>
      <Animated.View
        accessibilityViewIsModal
        style={{
          transform: [{ translateY: decalage }],
          backgroundColor: couleurs.surface,
          borderTopLeftRadius: 20,
          borderTopRightRadius: 20,
          paddingHorizontal: 16,
          paddingTop: 8,
          paddingBottom: Math.max(marges.bottom, 16),
          maxHeight: '80%',
          gap: 12,
        }}
      >
        <View style={{ alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: couleurs.trait }} />
        <Text style={[s.titre, { fontSize: 18 }]}>{p.titre}</Text>
        <ScrollView style={{ flexGrow: 0 }} contentContainerStyle={{ gap: 14, paddingBottom: 4 }}>
          {p.children}
        </ScrollView>
        <Bouton titre={p.action ?? 'Valider'} onPress={onFermer} />
      </Animated.View>
    </View>
  );
}
