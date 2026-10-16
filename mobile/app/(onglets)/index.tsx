import { Image } from 'expo-image';
import { Link } from 'expo-router';
import { useState } from 'react';
import { FlatList, Pressable, RefreshControl, Text, View } from 'react-native';

import { Champ, EtatRequete, s } from '../../components/ui';
import { couleurs, ETATS, rayon } from '../../lib/theme';
import type { Objet } from '../../lib/types';
import { useRequete } from '../../lib/useRequete';

/** Le catalogue public : consultable sans compte, comme sur troctroc.fr/#objets. */
export default function Catalogue() {
  const [saisie, setSaisie] = useState('');
  const [q, setQ] = useState('');
  const requete = useRequete<Objet[]>(q ? `/objets?q=${encodeURIComponent(q)}` : '/objets');
  const objets = requete.donnees ?? [];

  return (
    <View style={s.ecran}>
      <FlatList
        data={objets}
        keyExtractor={(o) => String(o.id)}
        numColumns={2}
        columnWrapperStyle={{ gap: 12 }}
        contentContainerStyle={{ padding: 16, gap: 12 }}
        refreshControl={<RefreshControl refreshing={false} onRefresh={requete.recharger} tintColor={couleurs.accent} />}
        ListHeaderComponent={
          <View style={{ gap: 12, marginBottom: 4 }}>
            <Champ
              libelle="Chercher un objet"
              placeholder="vélo, Epiphone, poussette…"
              value={saisie}
              onChangeText={setSaisie}
              onSubmitEditing={() => setQ(saisie.trim())}
              returnKeyType="search"
            />
            <EtatRequete {...requete} />
            {!requete.chargement && !requete.erreur && (
              <Text style={[s.discret, { textAlign: 'left' }]}>
                {objets.length} objet{objets.length > 1 ? 's' : ''} disponible{objets.length > 1 ? 's' : ''}
              </Text>
            )}
          </View>
        }
        renderItem={({ item }) => (
          <Link href={`/objet/${item.id}`} asChild>
            <Pressable style={{ flex: 1, maxWidth: '50%', gap: 6 }}>
              <Image
                source={item.photo_url}
                style={{ aspectRatio: 1, borderRadius: rayon, backgroundColor: couleurs.surface }}
                contentFit="cover"
              />
              <Text style={s.titre} numberOfLines={2}>
                {item.titre}
              </Text>
              {item.etat && <Text style={[s.discret, { textAlign: 'left' }]}>{ETATS[item.etat]}</Text>}
            </Pressable>
          </Link>
        )}
      />
    </View>
  );
}
