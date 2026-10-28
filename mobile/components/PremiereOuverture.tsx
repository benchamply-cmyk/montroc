import { Ionicons } from '@expo/vector-icons';
import { useEffect, useRef, useState, type ComponentProps } from 'react';
import { ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ecrire, lire } from '../lib/stockage';
import { couleurs } from '../lib/theme';
import { Bouton, s } from './ui';

const CLE = 'troc.bienvenue';

const PAGES: { icone: ComponentProps<typeof Ionicons>['name']; couleur: string; titre: string; texte: string }[] = [
  {
    icone: 'camera',
    couleur: couleurs.marque,
    titre: 'Je propose',
    texte: "Une photo, un titre : l'objet qui dort chez vous est en ligne. Pas de prix, pas de monnaie.",
  },
  {
    icone: 'heart',
    couleur: couleurs.danger,
    titre: 'Je demande',
    texte: "Mettez un cœur à ce qui vous serait utile. Si son propriétaire aime un de vos objets, c'est un match.",
  },
  {
    icone: 'sync',
    couleur: couleurs.accent,
    titre: 'Ça matche ou ça boucle',
    texte: 'Pas de match direct ? Chaque dimanche à 18 h, le Grand Troc propose des boucles à trois : chacun donne, chacun reçoit.',
  },
];

/** Les 3 écrans de la première ouverture, à faire défiler ; ensuite l'accueil, sans compte. Une seule fois par appareil. */
export function PremiereOuverture({ pret }: { pret: boolean }) {
  const [visible, setVisible] = useState(false);
  const [page, setPage] = useState(0);
  const defilement = useRef<ScrollView>(null);
  // Largeur mesurée sur l'écran lui-même (dans l'aperçu web, la fenêtre est plus large que le téléphone).
  const { width: fenetre } = useWindowDimensions();
  const [largeur, setLargeur] = useState(fenetre);
  const [hauteur, setHauteur] = useState<number | undefined>(undefined);
  const marges = useSafeAreaInsets();

  useEffect(() => {
    if (pret) lire<boolean>(CLE, false).then((vue) => setVisible(!vue));
  }, [pret]);

  if (!visible) return null;
  const terminer = () => {
    setVisible(false);
    ecrire(CLE, true);
  };
  const suivante = () => (page < PAGES.length - 1 ? defilement.current?.scrollTo({ x: (page + 1) * largeur, animated: true }) : terminer());

  return (
    <View
      onLayout={(e) => setLargeur(e.nativeEvent.layout.width)}
      style={[StyleSheet.absoluteFill, { backgroundColor: couleurs.fond, zIndex: 5, paddingTop: marges.top, paddingBottom: Math.max(marges.bottom, 16) }]}
    >
      <ScrollView
        ref={defilement}
        onLayout={(e) => setHauteur(e.nativeEvent.layout.height)}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        scrollEventThrottle={16}
        onScroll={(e) => setPage(Math.round(e.nativeEvent.contentOffset.x / largeur))}
      >
        {PAGES.map((p) => (
          <View key={p.titre} style={{ width: largeur, height: hauteur, padding: 32, justifyContent: 'center', alignItems: 'center', gap: 20 }}>
            <View style={{ width: 120, height: 120, borderRadius: 60, backgroundColor: couleurs.surface, alignItems: 'center', justifyContent: 'center' }}>
              <Ionicons name={p.icone} size={56} color={p.couleur} />
            </View>
            <Text style={[s.grandTitre, { fontSize: 28, textAlign: 'center' }]}>{p.titre}</Text>
            <Text style={[s.texte, { fontSize: 17, lineHeight: 24, textAlign: 'center', color: couleurs.discret }]}>{p.texte}</Text>
          </View>
        ))}
      </ScrollView>
      <View style={{ paddingHorizontal: 24, gap: 16 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 8 }}>
          {PAGES.map((p, i) => (
            <View key={p.titre} style={{ width: i === page ? 22 : 8, height: 8, borderRadius: 4, backgroundColor: i === page ? couleurs.accent : couleurs.trait }} />
          ))}
        </View>
        <Bouton titre={page < PAGES.length - 1 ? 'Suivant' : 'Découvrir les objets'} onPress={suivante} />
        {page < PAGES.length - 1 && <Bouton titre="Passer" secondaire onPress={terminer} />}
      </View>
    </View>
  );
}
