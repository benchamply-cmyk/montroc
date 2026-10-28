import { Image } from 'expo-image';
import { Link } from 'expo-router';
import { Pressable, Text, View } from 'react-native';

import { useFavoris } from '../lib/favoris';
import { useSession } from '../lib/session';
import { couleurs, ETATS, rayon } from '../lib/theme';
import type { Objet } from '../lib/types';
import { s } from './ui';

/** L'étoile (favori, pour tous) et le cœur (« J'aime » du Match, pour les membres), comme sur les cartes du site. */
export function BoutonsFavori({ objet, grand }: { objet: Pick<Objet, 'id' | 'proprietaire_id'>; grand?: boolean }) {
  const { moi } = useSession();
  const { etoiles, coeurs, basculerEtoile, basculerCoeur } = useFavoris();
  // Pas d'étoile ni de cœur sur ses propres objets.
  if (moi?.id === objet.proprietaire_id) return null;
  const taille = grand ? 26 : 18;
  const pastille = { backgroundColor: 'rgba(17,19,24,0.75)', borderRadius: 999, width: taille + 16, height: taille + 16, alignItems: 'center' as const, justifyContent: 'center' as const };
  return (
    <View style={{ flexDirection: 'row', gap: 6 }}>
      <Pressable
        accessibilityLabel={etoiles.has(objet.id) ? 'Retirer des favoris' : 'Ajouter aux favoris'}
        hitSlop={6}
        onPress={() => basculerEtoile(objet.id)}
        style={pastille}
      >
        <Text style={{ fontSize: taille, color: etoiles.has(objet.id) ? couleurs.marque : couleurs.encre }}>{etoiles.has(objet.id) ? '★' : '☆'}</Text>
      </Pressable>
      {moi && (
        <Pressable
          accessibilityLabel={coeurs.has(objet.id) ? "Retirer mon J'aime" : "J'aime"}
          hitSlop={6}
          onPress={() => basculerCoeur(objet.id)}
          style={pastille}
        >
          <Text style={{ fontSize: taille, color: coeurs.has(objet.id) ? couleurs.danger : couleurs.encre }}>{coeurs.has(objet.id) ? '♥' : '♡'}</Text>
        </Pressable>
      )}
    </View>
  );
}

/** Une carte du catalogue : photo, étoile et cœur, titre, état et lieu. */
export function CarteObjet({ objet }: { objet: Objet }) {
  return (
    <View style={{ flex: 1, maxWidth: '50%', gap: 6 }}>
      <Link href={`/objet/${objet.id}`} asChild>
        <Pressable style={{ gap: 6 }}>
          <Image source={objet.photo_url} style={{ aspectRatio: 1, borderRadius: rayon, backgroundColor: couleurs.surface }} contentFit="cover" />
          <Text style={s.titre} numberOfLines={2}>
            {objet.titre}
          </Text>
          <Text style={[s.discret, { textAlign: 'left' }]} numberOfLines={1}>
            {[objet.etat && ETATS[objet.etat], objet.lieu].filter(Boolean).join(' · ')}
          </Text>
        </Pressable>
      </Link>
      <View style={{ position: 'absolute', top: 8, right: 8 }}>
        <BoutonsFavori objet={objet} />
      </View>
    </View>
  );
}
