import { useState } from 'react';
import { Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from 'react-native';

import { caracteristiquesPropres, Detail, DETAIL_VIDE, type ValeurDetail } from '../components/Detail';
import { Bouton, Champ, EtatRequete, Puces, s } from '../components/ui';
import { api, ErreurApi } from '../lib/api';
import { couleurs, ETATS, MODES_ECHANGE, rayon } from '../lib/theme';
import type { CategorieDetaillee, Etat, Souhait } from '../lib/types';
import { useRequete } from '../lib/useRequete';

/** « Puériculture › Poussettes » et « Taille : 4 ans · Marque : Petit Bateau ». */
function decrire(souhait: Souhait, categories: CategorieDetaillee[]) {
  const cat = categories.find((c) => c.slug === souhait.categorie_slug);
  const sous = cat?.sous_categories.find((c) => c.slug === souhait.sous_categorie_slug);
  const nom = souhait.objet_id ? 'Un objet précis' : [cat?.libelle ?? souhait.categorie_slug, sous?.libelle].filter(Boolean).join(' › ');
  const libelle = (cle: string) => cat?.caracteristiques.find((c) => c.cle === cle)?.libelle ?? cle;
  const details = [
    ...Object.entries(souhait.caracteristiques).map(([k, v]) => `${libelle(k)} : ${v}`),
    ...Object.entries(souhait.preferences).map(([k, v]) => `${libelle(k)} : ${v} de préférence`),
    souhait.etat_min && `${ETATS[souhait.etat_min]} au moins`,
  ].filter(Boolean);
  return { nom, details: details.join(' · ') };
}

export default function MesSouhaits() {
  const souhaits = useRequete<Souhait[]>('/moi/souhaits');
  const categories = useRequete<CategorieDetaillee[]>('/categories');
  const [ajout, setAjout] = useState(false);

  function supprimer(souhait: Souhait, nom: string) {
    Alert.alert('Supprimer ce souhait ?', nom, [
      { text: 'Annuler', style: 'cancel' },
      {
        text: 'Supprimer',
        style: 'destructive',
        onPress: async () => {
          try {
            await api(`/moi/souhaits/${souhait.id}`, { method: 'DELETE' });
            souhaits.setDonnees((liste) => liste?.filter((x) => x.id !== souhait.id) ?? null);
          } catch (e) {
            Alert.alert('Suppression impossible', e instanceof ErreurApi ? e.message : String(e));
          }
        },
      },
    ]);
  }

  return (
    <KeyboardAvoidingView style={s.ecran} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 48 }} keyboardShouldPersistTaps="handled">
        <Text style={s.texte}>Dites ce qui vous serait utile : le Match et le Grand Troc vous proposent les objets qui y répondent.</Text>
        <EtatRequete {...souhaits} />
        {souhaits.donnees?.length === 0 && !ajout && <Text style={s.discret}>Aucun souhait pour l'instant.</Text>}
        {souhaits.donnees?.map((souhait) => {
          const { nom, details } = decrire(souhait, categories.donnees ?? []);
          return (
            <View key={souhait.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, backgroundColor: couleurs.surface, borderRadius: rayon }}>
              <View style={{ flex: 1, gap: 2 }}>
                <Text style={s.titre}>{nom}</Text>
                {!!details && <Text style={[s.discret, { textAlign: 'left' }]}>{details}</Text>}
                {souhait.precisions && <Text style={[s.discret, { textAlign: 'left', fontStyle: 'italic' }]}>« {souhait.precisions} »</Text>}
              </View>
              <Pressable onPress={() => supprimer(souhait, nom)} hitSlop={10} accessibilityLabel={`Supprimer le souhait ${nom}`}>
                <Text style={{ color: couleurs.danger, fontSize: 20 }}>✕</Text>
              </Pressable>
            </View>
          );
        })}

        {ajout && categories.donnees ? (
          <NouveauSouhait
            categories={categories.donnees}
            onAjoute={(souhait) => {
              souhaits.setDonnees((liste) => [...(liste ?? []), souhait]);
              setAjout(false);
            }}
            onAnnule={() => setAjout(false)}
          />
        ) : (
          <>
            <EtatRequete {...categories} />
            <Bouton titre="Ajouter un souhait" desactive={!categories.donnees} onPress={() => setAjout(true)} />
          </>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function NouveauSouhait(p: { categories: CategorieDetaillee[]; onAjoute: (s: Souhait) => void; onAnnule: () => void }) {
  const [detail, setDetail] = useState<ValeurDetail>(DETAIL_VIDE);
  const [etatMin, setEtatMin] = useState<Etat | null>(null);
  const [precisions, setPrecisions] = useState('');
  const [modes, setModes] = useState<string[]>([]);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function enregistrer() {
    setErreur(null);
    setEnvoi(true);
    try {
      const souhait = await api<Souhait>('/moi/souhaits', {
        corps: {
          categorie_slug: detail.categorie,
          sous_categorie_slug: detail.sousCategorie,
          // Les caractéristiques choisies sont des critères obligatoires, comme par défaut sur le site.
          caracteristiques: caracteristiquesPropres(p.categories, detail),
          etat_min: etatMin,
          precisions: precisions.trim() || null,
          modes_echange: modes,
        },
      });
      p.onAjoute(souhait);
    } catch (e) {
      setErreur(e instanceof ErreurApi ? e.message : String(e));
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <View style={{ gap: 16, padding: 14, borderWidth: 1, borderColor: couleurs.trait, borderRadius: rayon }}>
      <Text style={s.titre}>Nouveau souhait</Text>
      <Detail categories={p.categories} valeur={detail} onChange={setDetail} demande />
      <Puces
        libelle="État minimum (facultatif)"
        options={Object.entries(ETATS).map(([valeur, libelle]) => ({ valeur, libelle }))}
        choisies={etatMin ? [etatMin] : []}
        onChange={([e]) => setEtatMin((e as Etat) ?? null)}
        facultatif
      />
      <Champ libelle="Précisions (facultatif)" value={precisions} onChangeText={setPrecisions} maxLength={500} placeholder="Pour une enfant de 4 ans" />
      <Puces
        libelle="Modes d'échange (tous si aucun)"
        options={Object.entries(MODES_ECHANGE).map(([valeur, libelle]) => ({ valeur, libelle }))}
        choisies={modes}
        onChange={setModes}
        multiple
      />
      {erreur && <Text style={s.erreur}>{erreur}</Text>}
      <Bouton titre={envoi ? 'Enregistrement…' : 'Enregistrer'} desactive={envoi || !detail.categorie} onPress={enregistrer} />
      <Bouton titre="Annuler" secondaire onPress={p.onAnnule} />
    </View>
  );
}
