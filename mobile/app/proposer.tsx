import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text, View } from 'react-native';

import { caracteristiquesPropres, Detail, DETAIL_VIDE, type ValeurDetail } from '../components/Detail';
import { Bouton, Champ, EtatRequete, Puces, s } from '../components/ui';
import { lireAnnonce } from '../lib/annonce';
import { api, ErreurApi } from '../lib/api';
import { choisirPhoto, envoyerPhoto, type Source } from '../lib/photo';
import { useSession } from '../lib/session';
import { couleurs, ETATS, FORMATS_COLIS, MODES_ECHANGE, rayon } from '../lib/theme';
import type { CategorieDetaillee, Etat } from '../lib/types';
import { useRequete } from '../lib/useRequete';
import { chercherVilles, type Ville } from '../lib/villes';
import { vibrer } from '../lib/vibrer';

/** Proposer un objet. Comme sur le site (#77), un visiteur remplit tout ; le compte n'est demandé qu'à la publication. */
export default function Proposer() {
  const { moi } = useSession();
  const categories = useRequete<CategorieDetaillee[]>('/categories');
  const [photo, setPhoto] = useState<string | null>(null);
  const [titre, setTitre] = useState('');
  const [detail, setDetail] = useState<ValeurDetail>(DETAIL_VIDE);
  const [etat, setEtat] = useState<Etat | null>(null);
  const [description, setDescription] = useState('');
  // Aucun mode coché : l'API comprend « tous acceptés ».
  const [modes, setModes] = useState<string[]>([]);
  const [formatColis, setFormatColis] = useState<string | null>(null);
  const [annonce, setAnnonce] = useState('');
  const [origine, setOrigine] = useState<string | null>(null);
  const [lieu, setLieu] = useState('');
  const [ville, setVille] = useState<Ville | null>(null);
  const [villes, setVilles] = useState<Ville[]>([]);
  // Le visiteur est parti se connecter : on publie dès son retour.
  const publierApresConnexion = useRef(false);
  const [envoi, setEnvoi] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const manque = !photo
    ? 'une photo'
    : !titre.trim()
      ? 'un titre'
      : !detail.categorie
        ? 'une catégorie'
        : !etat
          ? "l'état"
          : modes.includes('colis') && !formatColis
            ? 'le format du colis'
            : null;

  useEffect(() => {
    if (ville && ville.libelle === lieu) return;
    const minuterie = setTimeout(() => chercherVilles(lieu).then(setVilles), 400);
    return () => clearTimeout(minuterie);
  }, [lieu, ville]);

  useEffect(() => {
    if (moi && publierApresConnexion.current) {
      publierApresConnexion.current = false;
      publier();
    }
    // publier lit l'état du formulaire au moment du retour de la connexion.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [moi]);

  /** « Votre annonce ne part pas ? Troquez-la. » : on devine le titre et la catégorie depuis l'adresse seulement. */
  function importer(texte: string) {
    setAnnonce(texte);
    const a = lireAnnonce(texte);
    setOrigine(a?.lien ?? null);
    if (!a) return;
    if (a.titre && !titre.trim()) setTitre(a.titre);
    if (a.categorie && !detail.categorie && categories.donnees?.some((c) => c.slug === a.categorie))
      setDetail({ ...DETAIL_VIDE, categorie: a.categorie });
  }

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
    if (!moi) {
      publierApresConnexion.current = true;
      router.push('/connexion');
      return;
    }
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
          format_colis: modes.includes('colis') ? formatColis : null,
          annonce_origine: origine,
          ...(lieu.trim() ? { lieu: lieu.trim() } : {}),
          ...(ville && ville.libelle === lieu.trim() ? { latitude: ville.latitude, longitude: ville.longitude } : {}),
          ...photoEnvoyee,
        },
      });
      vibrer('succes');
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
        <View style={{ gap: 6 }}>
          <Champ
            libelle="Votre annonce Vinted ou Leboncoin ne part pas ? Collez son lien (facultatif)"
            value={annonce}
            onChangeText={importer}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            placeholder="https://www.vinted.fr/items/…"
          />
          {annonce.trim() !== '' && (
            <Text style={[s.discret, { textAlign: 'left', color: origine ? couleurs.ok : couleurs.danger }]}>
              {origine
                ? 'Annonce reconnue : vérifiez le titre et la catégorie, puis reprenez votre photo. Aucun prix ici.'
                : "Ce n'est pas un lien d'annonce Vinted ou Leboncoin."}
            </Text>
          )}
        </View>

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
        {modes.includes('colis') && (
          <Puces
            libelle="Format du colis"
            options={Object.entries(FORMATS_COLIS).map(([valeur, libelle]) => ({ valeur, libelle }))}
            choisies={formatColis ? [formatColis] : []}
            onChange={([f]) => setFormatColis(f ?? null)}
          />
        )}

        <View style={{ gap: 6 }}>
          <Champ
            libelle="Où se trouve l'objet ? (facultatif)"
            value={lieu}
            onChangeText={(t) => {
              setLieu(t);
              setVille(null);
            }}
            placeholder="Marseille"
            maxLength={120}
          />
          {!ville &&
            villes.map((v) => (
              <Bouton
                key={v.libelle}
                titre={v.libelle}
                secondaire
                onPress={() => {
                  setVille(v);
                  setLieu(v.libelle);
                  setVilles([]);
                }}
              />
            ))}
        </View>

        {erreur && <Text style={s.erreur}>{erreur}</Text>}
        <Bouton titre={envoi ?? (moi ? 'Publier' : 'Créer mon compte et publier')} desactive={!!envoi || !!manque} onPress={publier} />
        {manque && <Text style={s.discret}>Il manque {manque}.</Text>}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
