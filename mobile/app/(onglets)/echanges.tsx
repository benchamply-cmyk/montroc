import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';

import { BandeauGrandTroc } from '../../components/BandeauGrandTroc';
import { MonMatch } from '../../components/MonMatch';
import { Bouton, EtatRequete, s, Vignette } from '../../components/ui';
import { aFaire, STATUTS_ECHANGE } from '../../lib/echanges';
import { useSession } from '../../lib/session';
import { couleurs, rayon } from '../../lib/theme';
import type { EchangeLecture, MatchLecture } from '../../lib/types';
import { useRequete } from '../../lib/useRequete';

type Segment = 'a_faire' | 'matchs' | 'en_cours' | 'termines';

/** La boîte de réception de l'app : ce que j'ai à faire, mes matchs, mes échanges en cours et passés, et le Grand Troc. */
export default function Echanges() {
  const { pret, moi } = useSession();
  if (pret && !moi)
    return (
      <ScrollView style={s.ecran} contentContainerStyle={{ padding: 16, gap: 16 }}>
        <BandeauGrandTroc />
        <View style={[s.centre, { paddingTop: 32 }]}>
          <Ionicons name="swap-horizontal" size={40} color={couleurs.discret} />
          <Text style={[s.texte, { textAlign: 'center' }]}>Vos matchs, les propositions à accepter et les remises d'objets arrivent ici.</Text>
          <Bouton titre="Se connecter" onPress={() => router.push('/connexion')} />
        </View>
      </ScrollView>
    );
  return <BoiteEchanges />;
}

function BoiteEchanges() {
  const { moi } = useSession();
  const echanges = useRequete<EchangeLecture[]>('/moi/echanges');
  const matchs = useRequete<MatchLecture[]>('/match');
  const [segment, setSegment] = useState<Segment | null>(null);

  const dejaVu = useRef(false);
  const { recharger: rechargerEchanges } = echanges;
  const { recharger: rechargerMatchs } = matchs;
  const recharger = useCallback(() => {
    rechargerEchanges();
    rechargerMatchs();
  }, [rechargerEchanges, rechargerMatchs]);
  useFocusEffect(
    useCallback(() => {
      if (dejaVu.current) recharger();
      dejaVu.current = true;
    }, [recharger]),
  );

  const liste = echanges.donnees ?? [];
  const aFaireListe = moi ? liste.filter((e) => aFaire(e, moi.id)) : [];
  const enCours = liste.filter((e) => (e.statut === 'propose' || e.statut === 'accepte') && !aFaireListe.includes(e));
  const termines = liste.filter((e) => e.statut === 'termine' || e.statut === 'annule');
  const matchsLibres = (matchs.donnees ?? []).filter((m) => !m.echange_id);
  // Par défaut : ce qui attend une action, sinon les matchs à conclure, sinon les échanges en cours.
  const actif: Segment = segment ?? (aFaireListe.length ? 'a_faire' : matchsLibres.length ? 'matchs' : 'en_cours');

  const segments: [Segment, string, number][] = [
    ['a_faire', 'À faire', aFaireListe.length],
    ['matchs', 'Matchs', matchsLibres.length],
    ['en_cours', 'En cours', enCours.length],
    ['termines', 'Terminés', 0],
  ];

  return (
    <View style={s.ecran}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ flexGrow: 0 }} contentContainerStyle={{ gap: 8, padding: 16, paddingBottom: 8 }}>
        {segments.map(([cle, libelle, nb]) => {
          const choisi = actif === cle;
          return (
            <Pressable
              key={cle}
              accessibilityRole="tab"
              accessibilityState={{ selected: choisi }}
              onPress={() => setSegment(cle)}
              style={[s.puce, { flexDirection: 'row', gap: 6, alignItems: 'center' }, choisi && s.puceActive]}
            >
              <Text style={[s.puceTexte, choisi && { color: couleurs.accentEncre, fontWeight: '700' }]}>{libelle}</Text>
              {nb > 0 && (
                <View style={{ backgroundColor: cle === 'a_faire' ? couleurs.danger : couleurs.trait, borderRadius: 999, minWidth: 20, paddingHorizontal: 6, alignItems: 'center' }}>
                  <Text style={{ color: cle === 'a_faire' ? couleurs.fond : couleurs.encre, fontSize: 12, fontWeight: '700' }}>{nb}</Text>
                </View>
              )}
            </Pressable>
          );
        })}
      </ScrollView>
      <ScrollView
        contentContainerStyle={{ padding: 16, paddingTop: 8, gap: 12, paddingBottom: 48 }}
        refreshControl={<RefreshControl refreshing={false} onRefresh={recharger} tintColor={couleurs.accent} />}
      >
        <BandeauGrandTroc />
        <EtatRequete {...echanges} />
        {actif === 'a_faire' &&
          (aFaireListe.length ? aFaireListe.map((e) => <LigneEchange key={e.id} echange={e} />) : echanges.donnees && <Vide texte="Rien à faire pour l'instant." />)}
        {actif === 'matchs' && (
          <>
            <EtatRequete {...matchs} />
            {matchs.donnees && !matchsLibres.length && <Vide texte="Pas de match à conclure. Donnez des cœurs dans l'onglet Match." action="Aller au Match" onPress={() => router.push('/match')} />}
            {matchsLibres.map((m) => <MonMatch key={m.avec.id} match={m} onConclu={recharger} />)}
          </>
        )}
        {actif === 'en_cours' &&
          (enCours.length ? enCours.map((e) => <LigneEchange key={e.id} echange={e} />) : echanges.donnees && <Vide texte="Aucun échange en cours. Ils arrivent par le Match ou le Grand Troc du dimanche." />)}
        {actif === 'termines' &&
          (termines.length ? termines.map((e) => <LigneEchange key={e.id} echange={e} />) : echanges.donnees && <Vide texte="Vos échanges terminés s'afficheront ici." />)}
      </ScrollView>
    </View>
  );
}

/** Un échange : son type, la prochaine action à faire et l'objet que je reçois. */
function LigneEchange({ echange: e }: { echange: EchangeLecture }) {
  const { moi } = useSession();
  const action = moi ? aFaire(e, moi.id) : null;
  const recu = e.transferts.find((t) => t.receveur_id === moi?.id);
  return (
    <Pressable
      onPress={() => router.push(`/echange/${e.id}`)}
      style={({ pressed }) => [{ gap: 8, padding: 12, borderRadius: rayon, borderWidth: 1, borderColor: action ? couleurs.accent : couleurs.trait }, pressed && { opacity: 0.6 }]}
    >
      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
        <Text style={s.titre}>{e.par_match ? 'Accord du Match' : e.grand_troc_jour ? 'Grand Troc' : 'Échange'} · {e.transferts.length} personnes</Text>
        {action && <Text style={{ color: couleurs.accent, fontWeight: '700' }}>{action}</Text>}
      </View>
      <Text style={[s.discret, { textAlign: 'left' }]}>{STATUTS_ECHANGE[e.statut] ?? e.statut}</Text>
      {recu && <Vignette objet={recu.objet} droite={<Text style={s.discret}>Je reçois</Text>} />}
    </Pressable>
  );
}

function Vide({ texte, action, onPress }: { texte: string; action?: string; onPress?: () => void }) {
  return (
    <View style={[s.centre, { paddingTop: 24 }]}>
      <Text style={s.discret}>{texte}</Text>
      {action && onPress && <Bouton titre={action} secondaire onPress={onPress} />}
    </View>
  );
}
