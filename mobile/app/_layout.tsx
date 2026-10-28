import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { EcranChargement } from '../components/EcranChargement';
import { PremiereOuverture } from '../components/PremiereOuverture';
import { FournisseurFavoris } from '../lib/favoris';
import { FournisseurSession, useSession } from '../lib/session';
import { couleurs } from '../lib/theme';

/** Logo et nom par-dessus l'app tant que la session n'est pas relue ; dessous, les écrans de première ouverture. */
function Chargement() {
  const { pret } = useSession();
  return (
    <>
      <PremiereOuverture pret={pret} />
      <EcranChargement pret={pret} />
    </>
  );
}

export default function Racine() {
  return (
    <FournisseurSession>
      <FournisseurFavoris>
        <StatusBar style="light" />
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: couleurs.fond },
            headerTintColor: couleurs.encre,
            // Sinon iOS affiche le nom du groupe de routes « (onglets) ».
            headerBackTitle: 'Retour',
            contentStyle: { backgroundColor: couleurs.fond },
          }}
        >
          <Stack.Screen name="(onglets)" options={{ headerShown: false }} />
          <Stack.Screen name="objet/[id]" options={{ title: '' }} />
          <Stack.Screen name="recherche" options={{ title: 'Rechercher' }} />
          <Stack.Screen name="favoris" options={{ title: 'Favoris' }} />
          <Stack.Screen name="mes-objets" options={{ title: 'Mes objets' }} />
          <Stack.Screen name="mon-objet/[id]" options={{ title: 'Mon objet' }} />
          <Stack.Screen name="proposer" options={{ title: 'Proposer un objet', presentation: 'modal' }} />
          <Stack.Screen name="souhaits" options={{ title: 'Mes souhaits' }} />
          <Stack.Screen name="grand-troc" options={{ title: 'Le Grand Troc' }} />
          <Stack.Screen name="echange/[id]" options={{ title: 'Échange' }} />
          <Stack.Screen name="premium" options={{ title: 'Troc Premium' }} />
          <Stack.Screen name="compte" options={{ title: 'Mon compte' }} />
          <Stack.Screen name="infos" options={{ title: 'Aide et infos' }} />
          <Stack.Screen name="signaler" options={{ title: 'Signaler', presentation: 'modal' }} />
          <Stack.Screen name="assistant" options={{ title: 'Assistant TopTroc', presentation: 'modal' }} />
          <Stack.Screen name="connexion" options={{ title: 'Connexion', presentation: 'modal' }} />
        </Stack>
        <Chargement />
      </FournisseurFavoris>
    </FournisseurSession>
  );
}
