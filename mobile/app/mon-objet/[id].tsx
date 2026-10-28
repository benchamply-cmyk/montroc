import { Image } from 'expo-image';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, KeyboardAvoidingView, Platform, ScrollView, Text, View } from 'react-native';

import { Bouton, Champ, EtatRequete, Puces, s, Section, Vignette } from '../../components/ui';
import { api, ErreurApi } from '../../lib/api';
import { couleurs, ETATS, rayon } from '../../lib/theme';
import type { Etat, ListeInteresses, MonObjet } from '../../lib/types';
import { useRequete } from '../../lib/useRequete';

const STATUTS: Record<string, string> = { disponible: 'En ligne', reserve: 'Réservé (échange en cours)', echange: 'Échangé', retire: 'Retiré', modere: 'Retiré par la modération' };

/** Gérer un de mes objets : le modifier, le retirer ou le remettre en ligne, voir qui l'aime. */
export default function GererObjet() {
  const { id } = useLocalSearchParams<{ id: string }>();
  // Pas de GET /moi/objets/{id} : la liste de mes objets est courte.
  const mesObjets = useRequete<MonObjet[]>('/moi/objets');
  const objet = mesObjets.donnees?.find((o) => String(o.id) === id);
  const [titre, setTitre] = useState('');
  const [description, setDescription] = useState('');
  const [etat, setEtat] = useState<Etat | null>(null);
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    if (!objet) return;
    setTitre(objet.titre);
    setDescription(objet.description ?? '');
    setEtat(objet.etat);
  }, [objet]);

  async function modifier(corps: object, succes: string) {
    setEnvoi(true);
    try {
      const maj = await api<MonObjet>(`/moi/objets/${id}`, { method: 'PATCH', corps });
      mesObjets.setDonnees((liste) => liste?.map((o) => (o.id === maj.id ? maj : o)) ?? null);
      Alert.alert(succes);
    } catch (e) {
      Alert.alert('Mon objet', e instanceof ErreurApi ? e.message : String(e));
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <KeyboardAvoidingView style={s.ecran} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 22, paddingBottom: 48 }} keyboardShouldPersistTaps="handled">
        <Stack.Screen options={{ title: objet?.titre ?? 'Mon objet' }} />
        <EtatRequete {...mesObjets} />
        {mesObjets.donnees && !objet && <Text style={s.discret}>Cet objet n'est plus dans votre liste.</Text>}
        {objet && (
          <>
            <View style={{ flexDirection: 'row', gap: 12, alignItems: 'center' }}>
              <Image source={objet.photo_url} style={{ width: 96, height: 96, borderRadius: rayon, backgroundColor: couleurs.surface }} contentFit="cover" />
              <View style={{ flex: 1, gap: 4 }}>
                <Text style={s.titre}>{STATUTS[objet.statut] ?? objet.statut}</Text>
                <Bouton titre="Voir comme les autres" secondaire onPress={() => router.push(`/objet/${objet.id}`)} />
              </View>
            </View>

            {(objet.statut === 'disponible' || objet.statut === 'retire') && (
              <Bouton
                titre={objet.statut === 'disponible' ? 'Retirer du catalogue' : 'Remettre en ligne'}
                secondaire={objet.statut === 'disponible'}
                desactive={envoi}
                onPress={() =>
                  modifier(
                    { statut: objet.statut === 'disponible' ? 'retire' : 'disponible' },
                    objet.statut === 'disponible' ? 'Objet retiré du catalogue.' : 'Objet remis en ligne.',
                  )
                }
              />
            )}

            <Interesses objetId={objet.id} />

            <Section titre="Modifier">
              <Champ libelle="Titre" value={titre} onChangeText={setTitre} maxLength={120} />
              <Puces
                libelle="État"
                options={Object.entries(ETATS).map(([valeur, libelle]) => ({ valeur, libelle }))}
                choisies={etat ? [etat] : []}
                onChange={([e]) => setEtat((e as Etat) ?? null)}
              />
              <Champ
                libelle="Description"
                value={description}
                onChangeText={setDescription}
                maxLength={2000}
                multiline
                style={[s.champ, { minHeight: 90, textAlignVertical: 'top' }]}
              />
              <Bouton
                titre="Enregistrer"
                desactive={envoi || !titre.trim()}
                onPress={() => modifier({ titre: titre.trim(), description: description.trim() || null, ...(etat ? { etat } : {}) }, 'Objet enregistré.')}
              />
            </Section>
          </>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

/** « Qui aime ? » : la ShortList d'un objet convoité (5 J'aime ou plus), ou tous les intéressés avec Troc Premium. */
function Interesses({ objetId }: { objetId: number }) {
  const liste = useRequete<ListeInteresses>(`/moi/objets/${objetId}/interesses`);
  const d = liste.donnees;
  if (!d) return null;
  return (
    <Section titre={`${d.nb_jaime} J'aime${d.convoite ? ' · objet convoité' : ''}`}>
      {d.interesses.length === 0 ? (
        <Text style={[s.discret, { textAlign: 'left' }]}>
          {d.nb_jaime ? "La liste s'ouvre à partir de 5 J'aime (objet convoité), ou tout de suite avec Troc Premium." : "Personne n'a encore aimé cet objet."}
        </Text>
      ) : (
        d.interesses.map((i) => (
          <View key={i.membre.id} style={{ gap: 6 }}>
            <Text style={s.titre}>
              {i.membre.pseudo}
              {i.super_jaime ? ' · Super J’aime' : ''}
              {i.en_tete ? ' · en tête' : ''}
            </Text>
            {i.ses_objets.slice(0, 3).map((o) => (
              <Vignette key={o.id} objet={o} />
            ))}
          </View>
        ))
      )}
    </Section>
  );
}
