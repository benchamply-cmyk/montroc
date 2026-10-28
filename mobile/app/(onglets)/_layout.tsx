import { Ionicons } from '@expo/vector-icons';
import { router, Tabs, usePathname } from 'expo-router';
import { useEffect, useState, type ComponentProps } from 'react';
import { View } from 'react-native';

import { EnTeteLogo } from '../../components/Logo';
import { api } from '../../lib/api';
import { aFaire } from '../../lib/echanges';
import { useSession } from '../../lib/session';
import { couleurs } from '../../lib/theme';
import type { EchangeLecture } from '../../lib/types';

type NomIcone = ComponentProps<typeof Ionicons>['name'];

/** Icône pleine pour l'onglet actif, en contour pour les autres. */
const icone =
  (nom: string) =>
  ({ color, focused, size }: { color: string; focused: boolean; size: number }) => (
    <Ionicons name={(focused ? nom : `${nom}-outline`) as NomIcone} size={size} color={color} />
  );

/** Le bouton Proposer, mis en avant au centre de la barre comme « Vendre » sur Vinted. */
function IconeProposer() {
  return (
    <View style={{ backgroundColor: couleurs.marque, borderRadius: 12, width: 44, height: 32, alignItems: 'center', justifyContent: 'center' }}>
      <Ionicons name="add" size={26} color={couleurs.accentEncre} />
    </View>
  );
}

/** Le nombre d'échanges qui attendent une action de ma part, pour la pastille de l'onglet Échanges. */
function useNbAFaire() {
  const { moi } = useSession();
  const chemin = usePathname();
  const [nb, setNb] = useState(0);
  useEffect(() => {
    if (!moi) return setNb(0);
    api<EchangeLecture[]>('/moi/echanges')
      .then((liste) => setNb(liste.filter((e) => aFaire(e, moi.id)).length))
      .catch(() => undefined);
    // Relu à chaque changement d'écran : une réponse donnée ailleurs fait baisser la pastille.
  }, [moi, chemin]);
  return nb;
}

// 5 onglets sur le modèle de Vinted (validé par Ben le 28/10) : une action par onglet, Proposer au centre.
export default function Onglets() {
  const nbAFaire = useNbAFaire();
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: couleurs.fond },
        headerTintColor: couleurs.encre,
        headerShadowVisible: false,
        // Le logo et le nom du site en en-tête de chaque onglet, le nom de l'onglet reste en bas.
        headerTitle: () => <EnTeteLogo />,
        headerTitleAlign: 'left',
        tabBarStyle: { backgroundColor: couleurs.surface, borderTopColor: couleurs.trait },
        tabBarActiveTintColor: couleurs.accent,
        tabBarInactiveTintColor: couleurs.discret,
        sceneStyle: { backgroundColor: couleurs.fond },
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Accueil', tabBarIcon: icone('home') }} />
      <Tabs.Screen name="match" options={{ title: 'Match', tabBarIcon: icone('heart') }} />
      <Tabs.Screen
        name="publier"
        options={{ title: 'Proposer', tabBarIcon: () => <IconeProposer />, tabBarActiveTintColor: couleurs.discret }}
        listeners={{
          // Pas d'écran derrière l'onglet : Proposer s'ouvre par-dessus, on revient où l'on était.
          tabPress: (e) => {
            e.preventDefault();
            router.push('/proposer');
          },
        }}
      />
      <Tabs.Screen
        name="echanges"
        options={{
          title: 'Échanges',
          tabBarIcon: icone('swap-horizontal'),
          tabBarBadge: nbAFaire || undefined,
          tabBarBadgeStyle: { backgroundColor: couleurs.danger, color: couleurs.fond, fontWeight: '700' },
        }}
      />
      <Tabs.Screen name="profil" options={{ title: 'Profil', tabBarIcon: icone('person') }} />
    </Tabs>
  );
}
