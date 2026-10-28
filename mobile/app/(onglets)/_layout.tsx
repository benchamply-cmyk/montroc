import { router, Tabs } from 'expo-router';
import { Pressable, Text } from 'react-native';

import { couleurs } from '../../lib/theme';

const icone = (symbole: string) => ({ color }: { color: string }) => <Text style={{ color, fontSize: 20 }}>{symbole}</Text>;

/** La bulle d'aide du site, en haut à droite de chaque onglet. */
function BoutonAssistant() {
  return (
    <Pressable accessibilityLabel="Poser une question à l'assistant" hitSlop={10} onPress={() => router.push('/assistant')} style={{ paddingHorizontal: 16 }}>
      <Text style={{ color: couleurs.accent, fontSize: 20 }}>💬</Text>
    </Pressable>
  );
}

export default function Onglets() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: couleurs.fond },
        headerTintColor: couleurs.encre,
        headerRight: () => <BoutonAssistant />,
        tabBarStyle: { backgroundColor: couleurs.surface, borderTopColor: couleurs.trait },
        tabBarActiveTintColor: couleurs.accent,
        tabBarInactiveTintColor: couleurs.discret,
        sceneStyle: { backgroundColor: couleurs.fond },
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Accueil', headerTitle: 'TopTroc', tabBarIcon: icone('⌂') }} />
      <Tabs.Screen name="objets" options={{ title: 'Objets', tabBarIcon: icone('▦') }} />
      <Tabs.Screen name="match" options={{ title: 'Match', tabBarIcon: icone('♥') }} />
      <Tabs.Screen name="favoris" options={{ title: 'Favoris', tabBarIcon: icone('★') }} />
      <Tabs.Screen name="moi" options={{ title: 'Mon espace', tabBarIcon: icone('●') }} />
    </Tabs>
  );
}
