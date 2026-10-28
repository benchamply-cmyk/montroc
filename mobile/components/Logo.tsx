import { Text, View, type ViewStyle } from 'react-native';

import { couleurs } from '../lib/theme';

// Les deux T emboîtés de web/favicon.svg, en coordonnées 0-32 (après le translate/scale du SVG).
const BLOCS: { x: number; y: number; l: number; h: number; c: string }[] = [
  { x: 5.84, y: 6.62, l: 14.04, h: 3.9, c: couleurs.encre },
  { x: 10.91, y: 10.52, l: 3.9, h: 8.58, c: couleurs.encre },
  { x: 12.08, y: 21.44, l: 14.04, h: 3.9, c: couleurs.marque },
  { x: 17.15, y: 12.86, l: 3.9, h: 8.58, c: couleurs.marque },
];

/** Le logo du site, dessiné en vues (net à toutes les tailles, sans image). */
export function MarqueLogo({ taille = 26, style }: { taille?: number; style?: ViewStyle }) {
  const k = taille / 32;
  return (
    <View style={[{ width: taille, height: taille }, style]}>
      {BLOCS.map((b, i) => (
        <View key={i} style={{ position: 'absolute', left: b.x * k, top: b.y * k, width: b.l * k, height: b.h * k, backgroundColor: b.c }} />
      ))}
    </View>
  );
}

/** Le nom « TopTroc », « Troc » en jaune, comme dans l'en-tête du site. */
export function NomTopTroc({ taille = 17 }: { taille?: number }) {
  return (
    <Text style={{ color: couleurs.encre, fontSize: taille, fontWeight: '800', letterSpacing: taille * 0.06, textTransform: 'uppercase' }}>
      Top<Text style={{ color: couleurs.marque }}>Troc</Text>
    </Text>
  );
}

/** Logo et nom côte à côte : le titre des onglets. */
export function EnTeteLogo() {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }} accessibilityRole="header" accessibilityLabel="TopTroc">
      <MarqueLogo taille={26} />
      <NomTopTroc />
    </View>
  );
}
