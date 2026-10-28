import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, KeyboardAvoidingView, Platform, ScrollView, Text } from 'react-native';

import { Bouton, Champ, Puces, s } from '../components/ui';
import { api, ErreurApi } from '../lib/api';
import { useSession } from '../lib/session';
import type { MotifSignalement } from '../lib/types';

// Mêmes motifs que l'API (signalements.MOTIFS).
const MOTIFS: Record<MotifSignalement, string> = {
  illegal: 'Contenu ou objet illicite',
  dangereux: 'Produit dangereux ou rappelé',
  contrefacon: 'Contrefaçon',
  arnaque: 'Arnaque ou tromperie',
  inapproprie: 'Photo ou texte inapproprié',
  autre: 'Autre motif',
};

/** Signaler un objet ou un compte (DSA, art. 16) : ouvert à tous, avec ou sans compte. */
export default function Signaler() {
  const { objet, utilisateur } = useLocalSearchParams<{ objet?: string; utilisateur?: string }>();
  const { moi } = useSession();
  const [motif, setMotif] = useState<MotifSignalement | null>(null);
  const [explication, setExplication] = useState('');
  const [email, setEmail] = useState('');
  const [envoi, setEnvoi] = useState(false);

  const pret = motif && explication.trim().length >= 10 && (moi || email.includes('@'));

  async function envoyer() {
    if (!pret) return;
    setEnvoi(true);
    try {
      const r = await api<{ id: number }>('/signalements', {
        corps: {
          objet_id: objet ? Number(objet) : null,
          utilisateur_id: utilisateur ? Number(utilisateur) : null,
          motif,
          explication: explication.trim(),
          email_contact: moi ? null : email.trim(),
        },
      });
      Alert.alert('Signalement reçu', `Signalement n° ${r.id} : une personne va l'examiner et vous serez informé de la décision.`);
      router.back();
    } catch (e) {
      Alert.alert('Signalement', e instanceof ErreurApi ? e.message : String(e));
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <KeyboardAvoidingView style={s.ecran} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 18, paddingBottom: 48 }} keyboardShouldPersistTaps="handled">
        <Text style={s.texte}>{objet ? 'Que reprochez-vous à cet objet ?' : 'Que reprochez-vous à ce membre ?'}</Text>
        <Puces
          options={Object.entries(MOTIFS).map(([valeur, libelle]) => ({ valeur, libelle }))}
          choisies={motif ? [motif] : []}
          onChange={([m]) => setMotif((m as MotifSignalement) ?? null)}
        />
        <Champ
          libelle="Expliquez (10 caractères au moins)"
          value={explication}
          onChangeText={setExplication}
          multiline
          maxLength={2000}
          style={[s.champ, { minHeight: 100, textAlignVertical: 'top' }]}
        />
        {!moi && <Champ libelle="Votre e-mail, pour vous informer de la suite" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />}
        <Bouton titre={envoi ? 'Envoi…' : 'Envoyer le signalement'} desactive={envoi || !pret} onPress={envoyer} />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
