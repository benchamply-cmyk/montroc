import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Pressable, Text, View } from 'react-native';

import { compteARebours } from '../lib/dates';
import { couleurs, rayon } from '../lib/theme';
import type { InfosGrandTroc } from '../lib/types';
import { useRequete } from '../lib/useRequete';
import { s } from './ui';

/** Le bandeau fin du Grand Troc : compte à rebours jusqu'à dimanche 18 h, ouvre le Match à trois et l'aperçu. */
export function BandeauGrandTroc() {
  const grandTroc = useRequete<InfosGrandTroc>('/grand-troc');
  if (!grandTroc.donnees) return null;
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push('/grand-troc')}
      style={({ pressed }) => [
        { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderRadius: rayon, backgroundColor: couleurs.surface, borderLeftWidth: 4, borderLeftColor: couleurs.marque },
        pressed && { opacity: 0.6 },
      ]}
    >
      <Ionicons name="sync" size={20} color={couleurs.marque} />
      <View style={{ flex: 1 }}>
        <Text style={[s.titre, { fontSize: 15 }]}>Grand Troc {compteARebours(new Date(grandTroc.donnees.prochain), Date.now())}</Text>
        <Text style={[s.discret, { textAlign: 'left' }]}>Dimanche 18 h · Match à trois et boucles possibles</Text>
      </View>
      <Ionicons name="chevron-forward" size={18} color={couleurs.discret} />
    </Pressable>
  );
}
