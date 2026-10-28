import { router, useFocusEffect } from 'expo-router';
import { useCallback, useRef } from 'react';
import { FlatList, Pressable, RefreshControl, Text, View } from 'react-native';

import { EtatRequete, s, Vignette } from '../components/ui';
import { aFaire, STATUTS_ECHANGE } from '../lib/echanges';
import { useSession } from '../lib/session';
import { couleurs, rayon } from '../lib/theme';
import type { EchangeLecture } from '../lib/types';
import { useRequete } from '../lib/useRequete';

/** Mes échanges, en cours et passés, les plus récents d'abord (GET /moi/echanges). */
export default function MesEchanges() {
  const { moi } = useSession();
  const echanges = useRequete<EchangeLecture[]>('/moi/echanges');
  const dejaVu = useRef(false);
  const { recharger } = echanges;
  useFocusEffect(
    useCallback(() => {
      if (dejaVu.current) recharger();
      dejaVu.current = true;
    }, [recharger]),
  );

  return (
    <FlatList
      style={s.ecran}
      contentContainerStyle={{ padding: 16, gap: 12 }}
      data={echanges.donnees ?? []}
      keyExtractor={(e) => String(e.id)}
      refreshControl={<RefreshControl refreshing={false} onRefresh={recharger} tintColor={couleurs.accent} />}
      ListHeaderComponent={<EtatRequete {...echanges} />}
      ListEmptyComponent={
        echanges.donnees ? <Text style={s.discret}>Pas encore d'échange. Ils arrivent par le Match ou le Grand Troc du dimanche.</Text> : null
      }
      renderItem={({ item: e }) => {
        const action = moi ? aFaire(e, moi.id) : null;
        const recu = e.transferts.find((t) => t.receveur_id === moi?.id);
        return (
          <Pressable
            onPress={() => router.push(`/echange/${e.id}`)}
            style={({ pressed }) => [{ gap: 8, padding: 12, borderRadius: rayon, borderWidth: 1, borderColor: action ? couleurs.accent : couleurs.trait }, pressed && { opacity: 0.6 }]}
          >
            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <Text style={s.titre}>{e.par_match ? 'Accord du Match' : e.grand_troc_jour ? 'Grand Troc' : 'Échange'} · {e.transferts.length} personnes</Text>
              {action && <Text style={{ color: couleurs.accent, fontWeight: '700' }}>{action}</Text>}
            </View>
            <Text style={[s.discret, { textAlign: 'left' }]}>{STATUTS_ECHANGE[e.statut] ?? e.statut}</Text>
            {recu && <Vignette objet={recu.objet} droite={<Text style={s.discret}>Je reçois</Text>} />}
          </Pressable>
        );
      }}
    />
  );
}
