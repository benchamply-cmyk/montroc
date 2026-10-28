import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import type { ComponentProps } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';

import { Bouton, s } from '../../components/ui';
import { useSession } from '../../lib/session';
import { couleurs, rayon, REPUTATIONS } from '../../lib/theme';

type NomIcone = ComponentProps<typeof Ionicons>['name'];

/** Profil, sur le modèle de Vinted : qui je suis, puis une liste courte. Tout le reste a son onglet. */
export default function Profil() {
  const { pret, moi, fermer } = useSession();
  const connecte = pret && moi !== null;

  return (
    <ScrollView style={s.ecran} contentContainerStyle={{ padding: 16, gap: 20, paddingBottom: 48 }}>
      {connecte ? (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
          <View style={{ width: 56, height: 56, borderRadius: 28, backgroundColor: couleurs.accent, alignItems: 'center', justifyContent: 'center' }}>
            <Text style={{ color: couleurs.accentEncre, fontSize: 24, fontWeight: '800' }}>{moi.pseudo.slice(0, 1).toUpperCase()}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={s.grandTitre} numberOfLines={1}>{moi.pseudo}</Text>
            <Text style={[s.discret, { textAlign: 'left' }]}>
              {[moi.reputation && (REPUTATIONS[moi.reputation] ?? moi.reputation), moi.zone ?? 'Zone non renseignée', moi.formule && 'Troc Premium']
                .filter(Boolean)
                .join(' · ')}
            </Text>
          </View>
        </View>
      ) : (
        <View style={{ gap: 12 }}>
          <Text style={s.texte}>Connectez-vous pour proposer vos objets, dire ce qui vous serait utile et matcher.</Text>
          <Bouton titre="Se connecter ou créer un compte" onPress={() => router.push('/connexion')} />
        </View>
      )}

      <View style={{ backgroundColor: couleurs.surface, borderRadius: rayon, overflow: 'hidden' }}>
        {connecte && <Ligne icone="cube-outline" titre="Mes objets" onPress={() => router.push('/mes-objets')} />}
        {connecte && <Ligne icone="sparkles-outline" titre="Mes souhaits" onPress={() => router.push('/souhaits')} />}
        <Ligne icone="heart-outline" titre="Favoris" detail={connecte ? undefined : 'Gardés 24 h sans compte'} onPress={() => router.push('/favoris')} />
        {connecte && (
          <Ligne icone="star-outline" titre="Troc Premium" detail={moi.formule ? 'Ma formule' : 'Essai gratuit'} couleur={couleurs.marque} onPress={() => router.push('/premium')} />
        )}
        {connecte && <Ligne icone="settings-outline" titre="Mon compte" onPress={() => router.push('/compte')} />}
        <Ligne icone="help-circle-outline" titre="Aide et infos" detail="FAQ, assistant, pages légales" onPress={() => router.push('/infos')} dernier />
      </View>

      {connecte && <Bouton titre="Se déconnecter" secondaire onPress={fermer} />}
    </ScrollView>
  );
}

function Ligne(p: { icone: NomIcone; titre: string; detail?: string; onPress: () => void; couleur?: string; dernier?: boolean }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={p.onPress}
      style={({ pressed }) => [
        { flexDirection: 'row', alignItems: 'center', gap: 14, paddingHorizontal: 16, minHeight: 52 },
        !p.dernier && { borderBottomWidth: 1, borderBottomColor: couleurs.trait },
        pressed && { opacity: 0.6 },
      ]}
    >
      <Ionicons name={p.icone} size={22} color={p.couleur ?? couleurs.encre} />
      <Text style={[s.titre, { flex: 1 }]}>{p.titre}</Text>
      {p.detail && <Text style={s.discret}>{p.detail}</Text>}
      <Ionicons name="chevron-forward" size={18} color={couleurs.discret} />
    </Pressable>
  );
}
