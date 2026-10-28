import { router, useFocusEffect } from 'expo-router';
import { useCallback, useRef } from 'react';
import { FlatList, Pressable, RefreshControl, Text, View } from 'react-native';

import { Bouton, EtatRequete, s, Vignette } from '../components/ui';
import { couleurs } from '../lib/theme';
import type { ObjetResume } from '../lib/types';
import { useRequete } from '../lib/useRequete';

const STATUTS: Record<string, string> = { disponible: 'En ligne', reserve: 'Réservé', echange: 'Échangé', retire: 'Retiré', modere: 'Modéré' };

/** Mes objets proposés, avec leur statut ; chacun ouvre sa fiche de gestion. */
export default function MesObjets() {
  const objets = useRequete<(ObjetResume & { statut: string })[]>('/moi/objets');
  // Au retour de « Proposer » ou d'une fiche : la liste a pu changer. Le premier affichage charge déjà.
  const dejaVu = useRef(false);
  const { recharger } = objets;
  useFocusEffect(
    useCallback(() => {
      if (dejaVu.current) recharger();
      dejaVu.current = true;
    }, [recharger]),
  );

  return (
    <FlatList
      style={s.ecran}
      contentContainerStyle={{ padding: 16, gap: 10, paddingBottom: 48 }}
      data={objets.donnees ?? []}
      keyExtractor={(o) => String(o.id)}
      refreshControl={<RefreshControl refreshing={false} onRefresh={recharger} tintColor={couleurs.accent} />}
      ListHeaderComponent={<EtatRequete {...objets} />}
      ListEmptyComponent={
        objets.donnees ? (
          <View style={s.centre}>
            <Text style={s.discret}>Aucun objet proposé pour l'instant.</Text>
            <Bouton titre="Proposer mon premier objet" onPress={() => router.push('/proposer')} />
          </View>
        ) : null
      }
      renderItem={({ item: o }) => (
        <Pressable onPress={() => router.push(`/mon-objet/${o.id}`)} style={({ pressed }) => pressed && { opacity: 0.6 }}>
          <Vignette objet={o} droite={<Text style={s.discret}>{STATUTS[o.statut] ?? o.statut}</Text>} />
        </Pressable>
      )}
    />
  );
}
