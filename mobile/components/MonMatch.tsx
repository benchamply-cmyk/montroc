import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, Text, View } from 'react-native';

import { api, ErreurApi } from '../lib/api';
import { couleurs, rayon } from '../lib/theme';
import type { EchangeLecture, MatchLecture, ObjetResume } from '../lib/types';
import { Bouton, s, Vignette } from './ui';

/** Un objet à choisir pour l'accord : surligné quand il est choisi. */
function Choix({ objet, choisi, onPress }: { objet: ObjetResume; choisi: boolean; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={{ borderRadius: rayon, borderWidth: 2, borderColor: choisi ? couleurs.accent : 'transparent' }}>
      <Vignette objet={objet} droite={<Text style={{ color: choisi ? couleurs.accent : couleurs.discret, fontSize: 18 }}>{choisi ? '●' : '○'}</Text>} />
    </Pressable>
  );
}

/** Un match : choisir l'objet reçu et l'objet donné, puis proposer l'accord 1 à 1 (l'autre a 48 h pour dire oui). */
export function MonMatch({ match, onConclu }: { match: MatchLecture; onConclu: () => void }) {
  // Un seul objet de chaque côté : il est choisi d'office.
  const [recu, setRecu] = useState(match.ses_objets.length === 1 ? match.ses_objets[0].id : null);
  const [donne, setDonne] = useState(match.mes_objets.length === 1 ? match.mes_objets[0].id : null);
  const [envoi, setEnvoi] = useState(false);

  async function proposer() {
    if (recu === null || donne === null) return;
    setEnvoi(true);
    try {
      await api<EchangeLecture>('/match/accord', { corps: { mon_objet_id: donne, son_objet_id: recu } });
      Alert.alert('Proposition envoyée', `${match.avec.pseudo} a 48 heures pour accepter l'échange.`);
      onConclu();
    } catch (e) {
      Alert.alert('Accord impossible', e instanceof ErreurApi ? e.message : String(e));
    } finally {
      setEnvoi(false);
    }
  }

  if (match.echange_id)
    return (
      <Pressable style={{ gap: 6 }} onPress={() => router.push(`/echange/${match.echange_id}`)}>
        <Text style={s.texte}>Avec {match.avec.pseudo} · accord en cours ›</Text>
        {match.ses_objets.map((o) => <Vignette key={o.id} objet={o} />)}
      </Pressable>
    );

  return (
    <View style={{ gap: 8, padding: 12, borderWidth: 1, borderColor: couleurs.trait, borderRadius: rayon }}>
      <Text style={s.titre}>Avec {match.avec.pseudo}</Text>
      <Text style={[s.discret, { textAlign: 'left' }]}>Je reçois</Text>
      {match.ses_objets.map((o) => <Choix key={o.id} objet={o} choisi={recu === o.id} onPress={() => setRecu(o.id)} />)}
      <Text style={[s.discret, { textAlign: 'left' }]}>Je donne</Text>
      {match.mes_objets.map((o) => <Choix key={o.id} objet={o} choisi={donne === o.id} onPress={() => setDonne(o.id)} />)}
      <Bouton titre={envoi ? 'Envoi…' : "Proposer l'échange"} desactive={envoi || recu === null || donne === null} onPress={proposer} />
    </View>
  );
}
