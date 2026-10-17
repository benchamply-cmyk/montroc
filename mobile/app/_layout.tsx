import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { FournisseurSession } from '../lib/session';
import { couleurs } from '../lib/theme';

export default function Racine() {
  return (
    <FournisseurSession>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: couleurs.fond },
          headerTintColor: couleurs.encre,
          contentStyle: { backgroundColor: couleurs.fond },
        }}
      >
        <Stack.Screen name="(onglets)" options={{ headerShown: false }} />
        <Stack.Screen name="objet/[id]" options={{ title: '' }} />
        <Stack.Screen name="connexion" options={{ title: 'Connexion', presentation: 'modal' }} />
      </Stack>
    </FournisseurSession>
  );
}
