import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, Switch, Text, View } from 'react-native';

import { Bouton, Champ, Puces, s, Section } from '../components/ui';
import { api, ErreurApi } from '../lib/api';
import { useSession } from '../lib/session';
import { couleurs } from '../lib/theme';
import type { Moi, ZoneInteret } from '../lib/types';
import { chercherVilles, type Ville } from '../lib/villes';

/** Mon compte : pseudo, ville, téléphone (SMS du Grand Troc), zones d'intérêt, mot de passe, suppression. */
export default function Compte() {
  const { moi, rafraichir, fermer } = useSession();
  const [pseudo, setPseudo] = useState(moi?.pseudo ?? '');
  const [zone, setZone] = useState(moi?.zone ?? '');
  const [telephone, setTelephone] = useState(moi?.telephone ?? '');
  const [motDePasse, setMotDePasse] = useState('');
  const [envoi, setEnvoi] = useState(false);
  if (!moi) return null;

  async function tenter(action: () => Promise<unknown>, succes: string) {
    setEnvoi(true);
    try {
      await action();
      await rafraichir();
      Alert.alert(succes);
    } catch (e) {
      Alert.alert('Mon compte', e instanceof ErreurApi ? e.message : String(e));
    } finally {
      setEnvoi(false);
    }
  }

  function supprimer() {
    Alert.alert(
      'Supprimer mon compte ?',
      'Vos objets, souhaits et favoris seront effacés, et vos échanges en cours annulés pour les autres. Ce n\'est pas réversible.',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Supprimer',
          style: 'destructive',
          onPress: async () => {
            try {
              await api('/moi', { method: 'DELETE' });
              await fermer();
              router.back();
            } catch (e) {
              Alert.alert('Mon compte', e instanceof ErreurApi ? e.message : String(e));
            }
          },
        },
      ],
    );
  }

  return (
    <KeyboardAvoidingView style={s.ecran} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 24, paddingBottom: 48 }} keyboardShouldPersistTaps="handled">
        <Section titre="Profil">
          <Champ libelle="Pseudo" value={pseudo} onChangeText={setPseudo} maxLength={40} autoCapitalize="none" />
          <Champ libelle="Ville ou quartier" value={zone} onChangeText={setZone} maxLength={80} placeholder="Marseille 6e" />
          <Champ
            libelle="Téléphone mobile (un SMS par Grand Troc, jamais montré aux autres)"
            value={telephone}
            onChangeText={setTelephone}
            keyboardType="phone-pad"
            maxLength={30}
          />
          <Bouton
            titre="Enregistrer"
            desactive={envoi || pseudo.trim().length < 2}
            onPress={() =>
              tenter(
                () => api<Moi>('/moi', { method: 'PATCH', corps: { pseudo: pseudo.trim(), zone: zone.trim() || null, telephone: telephone.trim() || null } }),
                'Profil enregistré.',
              )
            }
          />
        </Section>

        <Zones moi={moi} onChange={(corps) => tenter(() => api<Moi>('/moi', { method: 'PATCH', corps }), "Zones d'intérêt enregistrées.")} />

        <Section titre={moi.a_un_mot_de_passe ? 'Changer de mot de passe' : 'Choisir un mot de passe'}>
          <Champ libelle="Nouveau mot de passe (8 caractères au moins)" value={motDePasse} onChangeText={setMotDePasse} secureTextEntry autoCapitalize="none" />
          <Bouton
            titre="Enregistrer le mot de passe"
            secondaire
            desactive={envoi || motDePasse.length < 8}
            onPress={() => tenter(() => api('/auth/mot-de-passe', { method: 'PUT', corps: { mot_de_passe: motDePasse } }).then(() => setMotDePasse('')), 'Mot de passe enregistré.')}
          />
        </Section>

        <Section titre="Compte">
          <Text style={[s.discret, { textAlign: 'left' }]}>{moi.email}</Text>
          <Bouton titre="Supprimer mon compte" secondaire onPress={supprimer} />
        </Section>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

/** Zones d'intérêt (une, trois avec Troc Premium) et « toute la France » par colis. */
function Zones({ moi, onChange }: { moi: Moi; onChange: (corps: object) => void }) {
  const zones = moi.zones_interet ?? [];
  const max = moi.zones_max ?? 1;
  const touteLaFrance = moi.toute_la_france ?? false;
  const [q, setQ] = useState('');
  const [villes, setVilles] = useState<Ville[]>([]);
  const [rayonKm, setRayonKm] = useState('10');

  useEffect(() => {
    const minuterie = setTimeout(() => chercherVilles(q).then(setVilles), 400);
    return () => clearTimeout(minuterie);
  }, [q]);

  const enregistrer = (liste: ZoneInteret[]) =>
    onChange({ zones_interet: liste.map((z) => ({ libelle: z.libelle, latitude: z.latitude, longitude: z.longitude, rayon_km: z.rayon_km })) });

  return (
    <Section titre="Où troquer en main propre">
      {zones.map((z, i) => (
        <View key={i} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Text style={s.texte}>
            {z.libelle} · {z.rayon_km} km
          </Text>
          <Pressable onPress={() => enregistrer(zones.filter((_, j) => j !== i))} hitSlop={8}>
            <Text style={{ color: couleurs.danger }}>Retirer</Text>
          </Pressable>
        </View>
      ))}
      {zones.length < max ? (
        <>
          <Champ libelle="Ajouter une ville" value={q} onChangeText={setQ} placeholder="Marseille" />
          <Puces
            libelle="Rayon"
            options={['5', '10', '20', '50'].map((v) => ({ valeur: v, libelle: `${v} km` }))}
            choisies={[rayonKm]}
            onChange={([r]) => setRayonKm(r ?? '10')}
          />
          {villes.map((v) => (
            <Bouton
              key={v.libelle}
              titre={`+ ${v.libelle}`}
              secondaire
              onPress={() => {
                setQ('');
                enregistrer([...zones, { ...v, rayon_km: Number(rayonKm) }]);
              }}
            />
          ))}
        </>
      ) : (
        max === 1 && <Text style={[s.discret, { textAlign: 'left' }]}>Plusieurs zones (travail, famille…) : avec Premium Plus.</Text>
      )}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={[s.texte, { flex: 1 }]}>Voir aussi les objets de toute la France (envoi par colis)</Text>
        <Switch value={touteLaFrance} onValueChange={(v) => onChange({ toute_la_france: v })} trackColor={{ true: couleurs.accent }} />
      </View>
    </Section>
  );
}
