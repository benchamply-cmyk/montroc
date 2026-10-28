import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';

import { BandeauGrandTroc } from '../../components/BandeauGrandTroc';
import { CarteObjet } from '../../components/CarteObjet';
import { Bouton, s } from '../../components/ui';
import { api } from '../../lib/api';
import { useSession } from '../../lib/session';
import { couleurs, rayon } from '../../lib/theme';
import type { CarteMatch, Categorie, Objet } from '../../lib/types';
import { useRequete } from '../../lib/useRequete';

const PAGE = 30;

/**
 * L'accueil, sur le modèle de Vinted : la barre de recherche en haut, les catégories, « Pour vous »
 * (les objets qui répondent à mes souhaits) puis les nouveautés en grille, sans fin.
 */
export default function Accueil() {
  const { moi } = useSession();
  const categories = useRequete<Categorie[]>('/categories');
  const pourVous = useRequete<CarteMatch[]>(moi ? '/match/carrousel?limite=12' : null);
  const [objets, setObjets] = useState<Objet[]>([]);
  const [fin, setFin] = useState(false);
  const [chargement, setChargement] = useState(false);
  const demande = useRef(0);

  const charger = useCallback(async (depuis: number) => {
    const numero = ++demande.current;
    setChargement(true);
    try {
      const page = await api<Objet[]>(`/objets?limite=${PAGE}&decalage=${depuis}`);
      if (numero !== demande.current) return;
      setObjets((avant) => (depuis === 0 ? page : [...avant, ...page]));
      setFin(page.length < PAGE);
    } catch {
      // Hors ligne ou serveur endormi : le fil reste tel quel, on réessaiera en tirant vers le bas.
    } finally {
      if (numero === demande.current) setChargement(false);
    }
  }, []);

  useEffect(() => {
    charger(0);
  }, [charger]);

  // Au retour sur l'accueil, « Pour vous » a pu changer (cœurs donnés ailleurs). Le premier affichage charge déjà.
  const dejaVu = useRef(false);
  const { recharger: rechargerPourVous } = pourVous;
  useFocusEffect(
    useCallback(() => {
      if (dejaVu.current) rechargerPourVous();
      dejaVu.current = true;
    }, [rechargerPourVous]),
  );

  const chercher = (params: { categorie?: string } = {}) => router.push({ pathname: '/recherche', params });
  const suggestions = (pourVous.donnees ?? []).map((c) => c.objet);

  return (
    <View style={s.ecran}>
      <Pressable
        accessibilityRole="search"
        accessibilityLabel="Chercher un objet"
        onPress={() => chercher()}
        style={({ pressed }) => [
          { flexDirection: 'row', alignItems: 'center', gap: 10, marginHorizontal: 12, marginBottom: 8, paddingHorizontal: 14, height: 44, borderRadius: 12, backgroundColor: couleurs.surface },
          pressed && { opacity: 0.7 },
        ]}
      >
        <Ionicons name="search" size={18} color={couleurs.discret} />
        <Text style={{ color: couleurs.discret, fontSize: 16 }}>Chercher un objet</Text>
      </Pressable>
      <FlatList
        data={objets}
        keyExtractor={(o) => String(o.id)}
        numColumns={3}
        columnWrapperStyle={{ gap: 8 }}
        contentContainerStyle={{ padding: 12, paddingTop: 4, gap: 14, paddingBottom: 32 }}
        refreshControl={
          <RefreshControl
            refreshing={false}
            onRefresh={() => {
              charger(0);
              rechargerPourVous();
            }}
            tintColor={couleurs.accent}
          />
        }
        onEndReachedThreshold={0.6}
        onEndReached={() => !fin && !chargement && objets.length > 0 && charger(objets.length)}
        ListHeaderComponent={
          <View style={{ gap: 16, marginBottom: 2 }}>
            {categories.donnees && (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }} style={{ marginHorizontal: -12 }}>
                <View style={{ width: 4 }} />
                {categories.donnees.map((c) => (
                  <Pressable key={c.slug} style={s.puce} onPress={() => chercher({ categorie: c.slug })}>
                    <Text style={s.puceTexte}>{c.libelle}</Text>
                  </Pressable>
                ))}
                <View style={{ width: 4 }} />
              </ScrollView>
            )}

            {!moi && <Bienvenue />}

            <BandeauGrandTroc />

            {suggestions.length > 0 && (
              <View style={{ gap: 10 }}>
                <TitreBloc titre="Pour vous" action="Matcher" onPress={() => router.push('/match')} />
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
                  {suggestions.map((o) => (
                    <CarteObjet key={o.id} objet={o} style={{ flexGrow: 0, flexShrink: 0, flexBasis: 116, width: 116, maxWidth: 116 }} />
                  ))}
                </ScrollView>
              </View>
            )}

            <TitreBloc titre="Nouveautés" action="Filtrer" onPress={() => chercher()} />
          </View>
        }
        ListEmptyComponent={
          chargement ? null : (
            <View style={s.centre}>
              <Text style={s.discret}>Les premiers objets arrivent bientôt.</Text>
              <Bouton titre="Proposer le premier" onPress={() => router.push('/proposer')} />
            </View>
          )
        }
        ListFooterComponent={chargement ? <ActivityIndicator color={couleurs.accent} style={{ padding: 16 }} /> : null}
        renderItem={({ item }) => <CarteObjet objet={item} />}
      />
    </View>
  );
}

/** Pour un visiteur : la promesse du site en deux lignes et les deux gestes de base. */
function Bienvenue() {
  return (
    <View style={{ padding: 16, gap: 8, borderRadius: rayon, backgroundColor: couleurs.surface }}>
      <Text style={[s.etiquette, { color: couleurs.marque }]}>Pas de prix. Pas de monnaie.</Text>
      <Text style={[s.grandTitre, { fontSize: 22 }]}>Le troc se réinvente.</Text>
      <Text style={[s.texte, { color: couleurs.discret }]}>
        Proposez ce qui dort chez vous, mettez un cœur à ce qui vous serait utile. Un cœur de chaque côté et c'est échangé, sinon une boucle à
        trois le dimanche.
      </Text>
      <View style={{ flexDirection: 'row', gap: 10, marginTop: 4 }}>
        <View style={{ flex: 1 }}>
          <Bouton titre="Créer un compte" onPress={() => router.push('/connexion')} />
        </View>
        <View style={{ flex: 1 }}>
          <Bouton titre="Comment ça marche" secondaire onPress={() => router.push('/infos')} />
        </View>
      </View>
    </View>
  );
}

function TitreBloc({ titre, action, onPress }: { titre: string; action: string; onPress: () => void }) {
  return (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' }}>
      <Text style={[s.titre, { fontSize: 18 }]}>{titre}</Text>
      <Pressable onPress={onPress} hitSlop={10}>
        <Text style={{ color: couleurs.accent, fontWeight: '600' }}>{action}</Text>
      </Pressable>
    </View>
  );
}
