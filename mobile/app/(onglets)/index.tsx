import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Linking, Pressable, RefreshControl, ScrollView, Text, TextInput, View } from 'react-native';

import { Boucle3 } from '../../components/Boucle3';
import { CarteObjet } from '../../components/CarteObjet';
import { Bouton, s } from '../../components/ui';
import { compteARebours } from '../../lib/dates';
import { aFaire } from '../../lib/echanges';
import { useSession } from '../../lib/session';
import { couleurs, rayon, SITE } from '../../lib/theme';
import type { Categorie, EchangeLecture, InfosGrandTroc, Objet } from '../../lib/types';
import { useRequete } from '../../lib/useRequete';

/** L'accueil du site (#88), resserré pour un téléphone : chercher, proposer, voir ce qui attend un troc, le Match et le Grand Troc. */
export default function Accueil() {
  const { moi } = useSession();
  const categories = useRequete<Categorie[]>('/categories');
  const objets = useRequete<Objet[]>('/objets?limite=10');
  const grandTroc = useRequete<InfosGrandTroc>('/grand-troc');
  const echanges = useRequete<EchangeLecture[]>(moi ? '/moi/echanges' : null);
  const [saisie, setSaisie] = useState('');
  const [maintenant, setMaintenant] = useState(Date.now());

  useEffect(() => {
    const minuterie = setInterval(() => setMaintenant(Date.now()), 30_000);
    return () => clearInterval(minuterie);
  }, []);

  // Au retour sur l'accueil, le fil et les échanges ont pu changer. Le premier affichage charge déjà.
  const dejaVu = useRef(false);
  const { recharger: rechargerObjets } = objets;
  const { recharger: rechargerEchanges } = echanges;
  useFocusEffect(
    useCallback(() => {
      if (dejaVu.current) {
        rechargerObjets();
        rechargerEchanges();
      }
      dejaVu.current = true;
    }, [rechargerObjets, rechargerEchanges]),
  );

  const voirObjets = (params: { q?: string; categorie?: string } = {}) => router.push({ pathname: '/objets', params });
  const nbAFaire = moi ? (echanges.donnees ?? []).filter((e) => aFaire(e, moi.id)).length : 0;
  const prochain = grandTroc.donnees ? new Date(grandTroc.donnees.prochain) : null;
  const dernier = grandTroc.donnees?.dernier;

  return (
    <ScrollView
      style={s.ecran}
      contentContainerStyle={{ paddingVertical: 20, gap: 28, paddingBottom: 48 }}
      keyboardShouldPersistTaps="handled"
      refreshControl={<RefreshControl refreshing={false} onRefresh={() => { rechargerObjets(); grandTroc.recharger(); rechargerEchanges(); }} tintColor={couleurs.accent} />}
    >
      <View style={{ paddingHorizontal: 16, gap: 12 }}>
        <Text style={[s.etiquette, { color: couleurs.marque }]}>Pas de prix. Pas de monnaie.</Text>
        <Text style={[s.grandTitre, { fontSize: 28, lineHeight: 33 }]}>Le troc se réinvente.</Text>
        <Text style={[s.texte, { color: couleurs.discret }]}>La boucle d'échange augmente vos chances : tout le monde y gagne.</Text>
        <View style={[s.champ, { flexDirection: 'row', alignItems: 'center', paddingVertical: 4, paddingRight: 4 }]}>
          <TextInput
            style={{ flex: 1, color: couleurs.encre, fontSize: 16, paddingVertical: 10 }}
            placeholder="Vélo, poussette, perceuse…"
            placeholderTextColor={couleurs.discret}
            value={saisie}
            onChangeText={setSaisie}
            onSubmitEditing={() => voirObjets({ q: saisie.trim() })}
            returnKeyType="search"
            maxLength={100}
          />
          <Pressable accessibilityLabel="Chercher" onPress={() => voirObjets({ q: saisie.trim() })} style={{ backgroundColor: couleurs.accent, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 10 }}>
            <Text style={{ color: couleurs.accentEncre, fontWeight: '700' }}>Chercher</Text>
          </Pressable>
        </View>
      </View>

      {categories.donnees && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingHorizontal: 16 }}>
          {categories.donnees.map((c) => (
            <Pressable key={c.slug} style={s.puce} onPress={() => voirObjets({ categorie: c.slug })}>
              <Text style={s.puceTexte}>{c.libelle}</Text>
            </Pressable>
          ))}
        </ScrollView>
      )}

      <View style={{ paddingHorizontal: 16, flexDirection: 'row', gap: 10 }}>
        <View style={{ flex: 1 }}>
          <Pressable onPress={() => router.push('/proposer')} style={({ pressed }) => [s.bouton, { backgroundColor: couleurs.marque }, pressed && { opacity: 0.6 }]}>
            <Text style={s.boutonTexte}>Proposer un objet</Text>
          </Pressable>
        </View>
        <View style={{ flex: 1 }}>
          <Bouton titre="Voir les objets" secondaire onPress={() => voirObjets()} />
        </View>
      </View>

      {moi && (
        <View style={{ paddingHorizontal: 16, flexDirection: 'row', gap: 10 }}>
          <Raccourci titre={nbAFaire ? `Mes échanges · ${nbAFaire}` : 'Mes échanges'} accent={nbAFaire > 0} onPress={() => router.push('/echanges')} />
          <Raccourci titre="Mes souhaits" onPress={() => router.push('/souhaits')} />
        </View>
      )}

      <Boucle3 />

      <View style={{ gap: 12 }}>
        <TitreBloc titre="En attente d'un troc" action="Tout voir" onPress={() => voirObjets()} />
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 12, paddingHorizontal: 16 }}>
          {(objets.donnees ?? []).map((o) => (
            <CarteObjet key={o.id} objet={o} style={{ flex: 0, width: 150, maxWidth: 150 }} />
          ))}
          {objets.donnees?.length === 0 && <Text style={s.discret}>Les premiers objets arrivent bientôt.</Text>}
        </ScrollView>
      </View>

      <View style={{ gap: 12, paddingHorizontal: 16 }}>
        <TitreBloc titre="Comment ça marche" action="En savoir plus" onPress={() => Linking.openURL(`${SITE}/comment-ca-marche/`)} marge={0} />
        <View style={{ flexDirection: 'row', gap: 10 }}>
          <Etape icone="📷" titre="Je propose" detail="Mes objets" onPress={() => router.push('/proposer')} />
          <Etape icone="★" titre="Je demande" detail="Mes souhaits" onPress={() => router.push(moi ? '/souhaits' : '/connexion')} />
        </View>
      </View>

      <Tuile etiquette="Le Match, à tout moment" couleur={couleurs.danger} titre="Un cœur de chaque côté, et c'est échangé.">
        <Bouton titre={moi ? 'Voir les objets pour moi' : 'Créer mon compte'} onPress={() => router.push(moi ? '/match' : '/connexion')} />
      </Tuile>

      <Tuile etiquette="Le Grand Troc du dimanche" couleur={couleurs.marque} titre="Pas de match ? On a une solution.">
        <Text style={[s.texte, { color: couleurs.discret }]}>Des boucles à trois. 48 h pour dire oui.</Text>
        {prochain && (
          <Text style={[s.titre, { color: couleurs.marque }]}>
            Prochain : {compteARebours(prochain, maintenant)} · dimanche 18 h
          </Text>
        )}
        {dernier && (
          <Text style={[s.discret, { textAlign: 'left' }]}>
            Dimanche dernier : {dernier.nb_objets} objets échangés entre {dernier.nb_participants} membres.
          </Text>
        )}
        <Bouton titre="Je participe" secondaire onPress={() => router.push('/grand-troc')} />
      </Tuile>

      <Tuile etiquette="Pour les particuliers" couleur={couleurs.accent} titre="Simplicité.">
        {['Publier', 'Choisir', 'Provoquer un Match', 'Propositions chaque dimanche'].map((t) => (
          <Text key={t} style={s.texte}>✓ {t}</Text>
        ))}
        <Pressable onPress={() => router.push('/proposer')}>
          <Text style={[s.texte, { color: couleurs.discret }]}>
            Déjà sur Vinted ou Leboncoin ? <Text style={{ color: couleurs.accent }}>Troquer son annonce</Text>
          </Text>
        </Pressable>
        <Text style={[s.texte, { color: couleurs.discret }]}>
          Entreprise ou collectivité ?{' '}
          <Text style={{ color: couleurs.accent }} onPress={() => Linking.openURL(`${SITE}/pros/`)}>Professionnels</Text>
          {' · '}
          <Text style={{ color: couleurs.accent }} onPress={() => Linking.openURL(`${SITE}/collectivites/`)}>Collectivités</Text>
        </Text>
      </Tuile>
    </ScrollView>
  );
}

function TitreBloc({ titre, action, onPress, marge = 16 }: { titre: string; action: string; onPress: () => void; marge?: number }) {
  return (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', paddingHorizontal: marge }}>
      <Text style={[s.titre, { fontSize: 18 }]}>{titre}</Text>
      <Pressable onPress={onPress} hitSlop={8}>
        <Text style={{ color: couleurs.accent, fontWeight: '600' }}>{action}</Text>
      </Pressable>
    </View>
  );
}

function Raccourci({ titre, onPress, accent }: { titre: string; onPress: () => void; accent?: boolean }) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [{ flex: 1, padding: 14, borderRadius: rayon, backgroundColor: couleurs.surface, borderWidth: 1, borderColor: accent ? couleurs.accent : couleurs.trait }, pressed && { opacity: 0.6 }]}
    >
      <Text style={[s.titre, accent && { color: couleurs.accent }]}>{titre} ›</Text>
    </Pressable>
  );
}

function Etape({ icone, titre, detail, onPress }: { icone: string; titre: string; detail: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderRadius: rayon, backgroundColor: couleurs.surface }, pressed && { opacity: 0.6 }]}>
      <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: couleurs.fond, alignItems: 'center', justifyContent: 'center' }}>
        <Text style={{ fontSize: 18, color: couleurs.marque }}>{icone}</Text>
      </View>
      <View>
        <Text style={s.titre}>{titre}</Text>
        <Text style={[s.discret, { textAlign: 'left' }]}>{detail}</Text>
      </View>
    </Pressable>
  );
}

function Tuile({ etiquette, titre, couleur, children }: { etiquette: string; titre: string; couleur: string; children: React.ReactNode }) {
  return (
    <View style={{ marginHorizontal: 16, padding: 18, gap: 10, borderRadius: rayon + 4, backgroundColor: couleurs.surface, borderLeftWidth: 4, borderLeftColor: couleur }}>
      <Text style={[s.etiquette, { color: couleur }]}>{etiquette}</Text>
      <Text style={[s.grandTitre, { fontSize: 21, lineHeight: 26 }]}>{titre}</Text>
      {children}
    </View>
  );
}
