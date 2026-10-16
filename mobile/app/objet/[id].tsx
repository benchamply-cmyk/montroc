import { Image } from 'expo-image';
import { Stack, useLocalSearchParams } from 'expo-router';
import { ScrollView, Text, View } from 'react-native';

import { EtatRequete, s } from '../../components/ui';
import { couleurs, ETATS, rayon } from '../../lib/theme';
import type { Objet } from '../../lib/types';
import { useRequete } from '../../lib/useRequete';

export default function FicheObjet() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const requete = useRequete<Objet>(`/objets/${id}`);
  const objet = requete.donnees;

  return (
    <ScrollView style={s.ecran} contentContainerStyle={{ padding: 16, gap: 14 }}>
      <Stack.Screen options={{ title: objet?.titre ?? '' }} />
      <EtatRequete {...requete} />
      {objet && (
        <>
          <Image
            source={objet.photo_url}
            style={{ aspectRatio: 1, borderRadius: rayon, backgroundColor: couleurs.surface }}
            contentFit="cover"
          />
          <Text style={s.grandTitre}>{objet.titre}</Text>
          {objet.etat && <Text style={[s.discret, { textAlign: 'left' }]}>{ETATS[objet.etat]}</Text>}
          {objet.description && <Text style={s.texte}>{objet.description}</Text>}
          {Object.entries(objet.caracteristiques).map(([cle, valeur]) => (
            <View key={cle} style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <Text style={s.discret}>{cle.replace(/_/g, ' ')}</Text>
              <Text style={s.texte}>{valeur}</Text>
            </View>
          ))}
          <Text style={[s.discret, { textAlign: 'left' }]}>
            Pas de prix : cet objet s'échange contre ce qui est utile à son propriétaire, directement ou en boucle au
            Grand Troc du dimanche.
          </Text>
        </>
      )}
    </ScrollView>
  );
}
