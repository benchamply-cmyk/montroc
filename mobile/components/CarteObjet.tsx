import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import { Link } from 'expo-router';
import { Pressable, Text, View, type ViewStyle } from 'react-native';

import { useFavoris } from '../lib/favoris';
import { useSession } from '../lib/session';
import { couleurs, ETATS } from '../lib/theme';
import type { Objet } from '../lib/types';

/** Le cœur, seul symbole « j'aime bien » de l'app : favori et J'aime du Match à la fois. */
export function BoutonCoeur({ objet, grand }: { objet: Pick<Objet, 'id' | 'proprietaire_id'>; grand?: boolean }) {
  const { moi } = useSession();
  const { coeurs, basculerCoeur } = useFavoris();
  // Pas de cœur sur ses propres objets.
  if (moi?.id === objet.proprietaire_id) return null;
  const aime = coeurs.has(objet.id);
  const taille = grand ? 24 : 15;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={aime ? 'Retirer le cœur' : "J'aime, garder en favori"}
      accessibilityState={{ selected: aime }}
      hitSlop={10}
      onPress={() => basculerCoeur(objet.id)}
      style={{ backgroundColor: 'rgba(17,19,24,0.75)', borderRadius: 999, width: taille + 14, height: taille + 14, alignItems: 'center', justifyContent: 'center' }}
    >
      <Ionicons name={aime ? 'heart' : 'heart-outline'} size={taille} color={aime ? couleurs.danger : couleurs.encre} />
    </Pressable>
  );
}

/**
 * Une carte d'objet : photo, cœur, titre, état et lieu. Par défaut, une des trois colonnes d'une grille
 * (cartes resserrées à la demande de Ben, 28/10).
 */
export function CarteObjet({ objet, style }: { objet: Objet; style?: ViewStyle }) {
  return (
    <View style={[{ flex: 1, maxWidth: '33.34%', gap: 4 }, style]}>
      <Link href={`/objet/${objet.id}`} asChild>
        <Pressable style={{ gap: 4 }} accessibilityLabel={objet.titre}>
          <Image source={objet.photo_url} style={{ aspectRatio: 4 / 5, borderRadius: 10, backgroundColor: couleurs.surface }} contentFit="cover" />
          <Text style={{ color: couleurs.encre, fontSize: 13, fontWeight: '600' }} numberOfLines={1}>
            {objet.titre}
          </Text>
          <Text style={{ color: couleurs.discret, fontSize: 12 }} numberOfLines={1}>
            {[objet.etat && ETATS[objet.etat], objet.lieu].filter(Boolean).join(' · ')}
          </Text>
        </Pressable>
      </Link>
      <View style={{ position: 'absolute', top: 6, right: 6 }}>
        <BoutonCoeur objet={objet} />
      </View>
    </View>
  );
}
