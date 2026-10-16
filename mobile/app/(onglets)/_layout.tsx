import { Tabs } from 'expo-router';
import { Text } from 'react-native';

import { couleurs } from '../../lib/theme';

const icone = (symbole: string) => ({ color }: { color: string }) => <Text style={{ color, fontSize: 20 }}>{symbole}</Text>;

export default function Onglets() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: couleurs.fond },
        headerTintColor: couleurs.encre,
        tabBarStyle: { backgroundColor: couleurs.surface, borderTopColor: couleurs.trait },
        tabBarActiveTintColor: couleurs.accent,
        tabBarInactiveTintColor: couleurs.discret,
        sceneStyle: { backgroundColor: couleurs.fond },
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Objets', tabBarIcon: icone('▦') }} />
      <Tabs.Screen name="match" options={{ title: 'Match', tabBarIcon: icone('♥') }} />
      <Tabs.Screen name="moi" options={{ title: 'Mon espace', tabBarIcon: icone('●') }} />
    </Tabs>
  );
}
