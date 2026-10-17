import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text, View } from 'react-native';

import { caracteristiquesPropres, Detail, DETAIL_VIDE, type ValeurDetail } from '../components/Detail';
import { Bouton, Champ, EtatRequete, Puces, s } from '../components/ui';
import { api, ErreurApi } from '../lib/api';
import { choisirPhoto, envoyerPhoto, type Source } from '../lib/photo';
import { couleurs, ETATS, MODES_ECHANGE, rayon } from '../lib/theme';
import type { CategorieDetaillee, Etat } from '../lib/types';
import { useRequete } from '../lib/useRequete';

export default function Proposer() {
  const categories = useRequete<CategorieDetaillee[]>('/categories');
  const [photo, setPhoto] = useState<string | null>(null);
  const [titre, setTitre] = useState('');
  const [detail, setDetail] = useState<ValeurDetail>(DETAIL_VIDE);
  const [etat, setEtat] = useState<Etat | null>(null);
  const [description, setDescription] = useState('');
  // Aucun mode coché : l'API comprend « tous acceptés ».
  const [modes, setModes] = useState<string[]>([]);
  const [envoi, setEnvoi] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const manque = !photo ? 'une photo' : !titre.trim() ? 'un titre' : !detail.categorie ? 'une catégorie' : !etat ? "l'état" : null;

  async function prendre(source: Source) {
    setErreur(null);
    try {
      const uri = await choisirPhoto(source);
      if (uri) setPhoto(uri);
    } catch (e) {
      setErreur(e instanceof ErreurApi ? e.message : String(e));
    }
  }

  async function publier() {
    if (manque || !photo) return;
    setErreur(null);
    try {
      setEnvoi('Envoi de la photo…');
      const photoEnvoyee = await envoyerPhoto(photo);
      setEnvoi('Publication…');
      await api('/moi/objets', {
        corps: {
          titre: titre.trim(),
          categorie_slug: detail.categorie,
          sous_categorie_slug: detail.sousCategorie,
          caracteristiques: caracteristiquesPropres(categories.donnees ?? [], detail),
          etat,
          description: description.trim() || null,
          modes_echange: modes,
          ...photoEnvoyee,
        },
      });
      router.back();
    } catch (e) {
      setErreur(e instanceof ErreurApi ? e.message : String(e));
    } finally {
      setEnvoi(null);
    }
  }

  return (
    <KeyboardAvoidingView style={s.ecran} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 20, paddingBottom: 48 }} keyboardShouldPersistTaps="handled">
        <View style={{ gap: 10 }}>
          {photo ? (
            <Image source={photo} style={{ width: '100%', aspectRatio: 1, borderRadius: rayon }} contentFit="cover" />
          ) : (
            <View style={{ aspectRatio: 2, borderRadius: rayon, borderWidth: 1, borderStyle: 'dashed', borderColor: couleurs.trait, justifyContent: 'center' }}>
              <Text style={s.discret}>Une photo nette de l'objet, en entier.</Text>
            </View>
          )}
          <View style={{ flexDirection: 'row', gap: 10 }}>
            <View style={{ flex: 1 }}>
              <Bouton titre="Prendre une photo" secondaire onPress={() => prendre('appareil')} />
            </View>
            <View style={{ flex: 1 }}>
              <Bouton titre="Galerie" secondaire onPress={() => prendre('galerie')} />
            </View>
          </View>
        </View>

        <Champ libelle="Titre" value={titre} onChangeText={setTitre} maxLength={120} placeholder="Poussette canne Yoyo" />

        <EtatRequete {...categories} />
        {categories.donnees && <Detail categories={categories.donnees} valeur={detail} onChange={setDetail} />}

        <Puces
          libelle="État"
          options={Object.entries(ETATS).map(([valeur, libelle]) => ({ valeur, libelle }))}
          choisies={etat ? [etat] : []}
          onChange={([e]) => setEtat((e as Etat) ?? null)}
        />

        <Champ
          libelle="Description (facultatif)"
          value={description}
          onChangeText={setDescription}
          maxLength={2000}
          multiline
          style={[s.champ, { minHeight: 90, textAlignVertical: 'top' }]}
        />

        <Puces
          libelle="Modes d'échange (tous si aucun)"
          options={Object.entries(MODES_ECHANGE).map(([valeur, libelle]) => ({ valeur, libelle }))}
          choisies={modes}
          onChange={setModes}
          multiple
        />

        {erreur && <Text style={s.erreur}>{erreur}</Text>}
        <Bouton titre={envoi ?? 'Publier'} desactive={!!envoi || !!manque} onPress={publier} />
        {manque && <Text style={s.discret}>Il manque {manque}.</Text>}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
