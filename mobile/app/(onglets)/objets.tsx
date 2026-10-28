import { useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';

import { CarteObjet } from '../../components/CarteObjet';
import { Bouton, Champ, EtatRequete, Puces, s } from '../../components/ui';
import { api, ErreurApi } from '../../lib/api';
import { CLE_RECHERCHES, ecrire, lire, type Recherche } from '../../lib/stockage';
import { couleurs, ETATS } from '../../lib/theme';
import type { CategorieDetaillee, Objet } from '../../lib/types';
import { useRequete } from '../../lib/useRequete';

const PAGE = 40;

interface Filtres {
  q: string;
  categorie: string | null;
  sousCategorie: string | null;
  etats: string[];
  // clé → valeurs acceptées (taille M ou L…).
  caracteristiques: Record<string, string[]>;
  tri: 'recent' | 'ancien';
}

const AUCUN: Filtres = { q: '', categorie: null, sousCategorie: null, etats: [], caracteristiques: {}, tri: 'recent' };

/** Même requête que la page d'une catégorie du site (#83) : l'API filtre et pagine. */
function chemin(f: Filtres, decalage: number) {
  const p: string[] = [`limite=${PAGE}`, `decalage=${decalage}`, `tri=${f.tri}`];
  if (f.q) p.push(`q=${encodeURIComponent(f.q)}`);
  if (f.categorie) p.push(`categorie=${encodeURIComponent(f.categorie)}`);
  if (f.categorie && f.sousCategorie) p.push(`sous_categorie=${encodeURIComponent(f.sousCategorie)}`);
  f.etats.forEach((e) => p.push(`etat=${e}`));
  if (f.categorie)
    Object.entries(f.caracteristiques).forEach(([cle, valeurs]) =>
      valeurs.forEach((v) => p.push(`caracteristique=${encodeURIComponent(`${cle}:${v}`)}`)),
    );
  return `/objets?${p.join('&')}`;
}

/** Le catalogue public : consultable sans compte, comme sur toptroc.com/#objets. */
export default function Catalogue() {
  const categories = useRequete<CategorieDetaillee[]>('/categories');
  const [saisie, setSaisie] = useState('');
  const [filtres, setFiltres] = useState<Filtres>(AUCUN);
  const [panneau, setPanneau] = useState(false);
  const [objets, setObjets] = useState<Objet[]>([]);
  const [fin, setFin] = useState(false);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [recherches, setRecherches] = useState<Recherche[]>([]);
  const demande = useRef(0);
  // L'accueil ouvre le catalogue sur une recherche ou une catégorie.
  const params = useLocalSearchParams<{ q?: string; categorie?: string }>();
  useEffect(() => {
    if (params.q === undefined && params.categorie === undefined) return;
    const q = params.q ?? '';
    setSaisie(q);
    setFiltres({ ...AUCUN, q, categorie: params.categorie || null });
  }, [params.q, params.categorie]);

  useEffect(() => {
    lire<Recherche[]>(CLE_RECHERCHES, []).then(setRecherches);
  }, []);

  const charger = useCallback(
    async (depuis: number) => {
      const numero = ++demande.current;
      setChargement(true);
      setErreur(null);
      try {
        const page = await api<Objet[]>(chemin(filtres, depuis));
        // Une réponse arrivée après un changement de filtre est ignorée.
        if (numero !== demande.current) return;
        setObjets((avant) => (depuis === 0 ? page : [...avant, ...page]));
        setFin(page.length < PAGE);
      } catch (e) {
        if (numero === demande.current) setErreur(e instanceof ErreurApi ? e.message : String(e));
      } finally {
        if (numero === demande.current) setChargement(false);
      }
    },
    [filtres],
  );

  useEffect(() => {
    charger(0);
  }, [charger]);

  const categorie = categories.donnees?.find((c) => c.slug === filtres.categorie);
  const caracteristiques = (categorie?.caracteristiques ?? []).filter(
    (c) => c.options && (!c.pour || (filtres.sousCategorie !== null && c.pour.includes(filtres.sousCategorie))),
  );
  const nbFiltres = filtres.etats.length + (filtres.sousCategorie ? 1 : 0) + Object.values(filtres.caracteristiques).flat().length + (filtres.tri === 'ancien' ? 1 : 0);

  async function chercher(q: string, cat: string | null = filtres.categorie) {
    setSaisie(q);
    setFiltres((f) => ({ ...f, q, categorie: cat, sousCategorie: cat === f.categorie ? f.sousCategorie : null, caracteristiques: cat === f.categorie ? f.caracteristiques : {} }));
    if (!q && !cat) return;
    const liste = [{ q, categorie: cat }, ...recherches.filter((r) => r.q !== q || r.categorie !== cat)].slice(0, 10);
    setRecherches(liste);
    await ecrire(CLE_RECHERCHES, liste);
  }

  const libelleCategorie = (slug: string | null) => categories.donnees?.find((c) => c.slug === slug)?.libelle;

  return (
    <View style={s.ecran}>
      <FlatList
        data={objets}
        keyExtractor={(o) => String(o.id)}
        numColumns={2}
        columnWrapperStyle={{ gap: 12 }}
        contentContainerStyle={{ padding: 16, gap: 12 }}
        refreshControl={<RefreshControl refreshing={false} onRefresh={() => charger(0)} tintColor={couleurs.accent} />}
        onEndReachedThreshold={0.5}
        onEndReached={() => !fin && !chargement && objets.length > 0 && charger(objets.length)}
        ListHeaderComponent={
          <View style={{ gap: 12, marginBottom: 4 }}>
            <Champ
              libelle="Chercher un objet"
              placeholder="vélo, Epiphone, poussette…"
              value={saisie}
              onChangeText={setSaisie}
              onSubmitEditing={() => chercher(saisie.trim())}
              returnKeyType="search"
            />
            {!filtres.q && !saisie && recherches.length > 0 && (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
                {recherches.map((r) => (
                  <Pressable key={`${r.q}|${r.categorie}`} style={s.puce} onPress={() => chercher(r.q, r.categorie)}>
                    <Text style={s.puceTexte}>↺ {[r.q, libelleCategorie(r.categorie)].filter(Boolean).join(' · ')}</Text>
                  </Pressable>
                ))}
              </ScrollView>
            )}
            {categories.donnees && (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
                {[{ slug: null as string | null, libelle: 'Tout' }, ...categories.donnees].map((c) => {
                  const active = filtres.categorie === c.slug;
                  return (
                    <Pressable key={c.slug ?? 'tout'} style={[s.puce, active && s.puceActive]} onPress={() => chercher(filtres.q, c.slug)}>
                      <Text style={[s.puceTexte, active && { color: couleurs.accentEncre }]}>{c.libelle}</Text>
                    </Pressable>
                  );
                })}
              </ScrollView>
            )}
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text style={[s.discret, { textAlign: 'left' }]}>
                {chargement && objets.length === 0 ? '' : `${objets.length}${fin ? '' : '+'} objet${objets.length > 1 ? 's' : ''}`}
              </Text>
              <Pressable onPress={() => setPanneau((p) => !p)} hitSlop={8}>
                <Text style={{ color: couleurs.accent, fontWeight: '600' }}>Filtres{nbFiltres ? ` (${nbFiltres})` : ''} {panneau ? '▲' : '▼'}</Text>
              </Pressable>
            </View>
            {panneau && (
              <View style={{ gap: 14, padding: 12, borderWidth: 1, borderColor: couleurs.trait, borderRadius: 14 }}>
                {categorie && categorie.sous_categories.length > 0 && (
                  <Puces
                    libelle="Sous-catégorie"
                    options={categorie.sous_categories.map((c) => ({ valeur: c.slug, libelle: c.libelle }))}
                    choisies={filtres.sousCategorie ? [filtres.sousCategorie] : []}
                    onChange={([c]) => setFiltres((f) => ({ ...f, sousCategorie: c ?? null, caracteristiques: {} }))}
                    facultatif
                  />
                )}
                <Puces
                  libelle="État"
                  options={Object.entries(ETATS).map(([valeur, libelle]) => ({ valeur, libelle }))}
                  choisies={filtres.etats}
                  onChange={(etats) => setFiltres((f) => ({ ...f, etats }))}
                  multiple
                />
                {caracteristiques.map((c) => (
                  <Puces
                    key={c.cle}
                    libelle={c.libelle}
                    options={(c.options ?? []).map((o) => ({ valeur: o, libelle: o }))}
                    choisies={filtres.caracteristiques[c.cle] ?? []}
                    onChange={(v) => setFiltres((f) => ({ ...f, caracteristiques: { ...f.caracteristiques, [c.cle]: v } }))}
                    multiple
                  />
                ))}
                {!categorie && <Text style={[s.discret, { textAlign: 'left' }]}>Choisissez une catégorie pour filtrer par taille, marque, pointure…</Text>}
                <Puces
                  libelle="Trier"
                  options={[
                    { valeur: 'recent', libelle: 'Plus récents' },
                    { valeur: 'ancien', libelle: 'Plus anciens' },
                  ]}
                  choisies={[filtres.tri]}
                  onChange={([t]) => setFiltres((f) => ({ ...f, tri: (t as Filtres['tri']) ?? 'recent' }))}
                />
                {nbFiltres > 0 && (
                  <Bouton titre="Effacer les filtres" secondaire onPress={() => setFiltres((f) => ({ ...AUCUN, q: f.q, categorie: f.categorie }))} />
                )}
              </View>
            )}
            {erreur && <EtatRequete chargement={false} reveil={false} erreur={erreur} recharger={() => charger(0)} />}
          </View>
        }
        ListEmptyComponent={
          chargement ? null : !erreur ? <Text style={s.discret}>Aucun objet ne correspond pour l'instant. Essayez d'élargir la recherche.</Text> : null
        }
        ListFooterComponent={chargement ? <ActivityIndicator color={couleurs.accent} style={{ padding: 16 }} /> : null}
        renderItem={({ item }) => <CarteObjet objet={item} />}
      />
    </View>
  );
}
