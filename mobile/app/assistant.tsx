import { useRef, useState } from 'react';
import { ActivityIndicator, FlatList, KeyboardAvoidingView, Platform, Text, TextInput, View } from 'react-native';

import { Bouton, s } from '../components/ui';
import { api, ErreurApi } from '../lib/api';
import { couleurs, rayon } from '../lib/theme';
import { useRequete } from '../lib/useRequete';

interface Message {
  role: 'user' | 'assistant';
  contenu: string;
}

const ACCUEIL = "Bonjour ! Je réponds à vos questions sur TopTroc : le Match, le Grand Troc du dimanche, proposer un objet, Troc Premium…";
// L'API accepte 20 messages au plus : on garde la fin de la conversation.
const MAX_MESSAGES = 19;

/** La bulle d'aide du site (#82) : questions sur TopTroc, sans compte. Rien n'est gardé côté serveur. */
export default function Assistant() {
  const etat = useRequete<{ actif: boolean }>('/assistant');
  const [messages, setMessages] = useState<Message[]>([]);
  const [saisie, setSaisie] = useState('');
  const [attente, setAttente] = useState(false);
  const liste = useRef<FlatList<Message>>(null);

  async function envoyer() {
    const question = saisie.trim();
    if (!question || attente) return;
    const suite: Message[] = [...messages, { role: 'user', contenu: question.slice(0, 1000) }];
    setMessages(suite);
    setSaisie('');
    setAttente(true);
    try {
      let envoyes = suite.slice(-MAX_MESSAGES);
      // La conversation envoyée doit commencer par une question.
      while (envoyes[0]?.role !== 'user') envoyes = envoyes.slice(1);
      const r = await api<{ reponse: string }>('/assistant', { corps: { messages: envoyes, langue: 'fr', page: '/app' } });
      setMessages([...suite, { role: 'assistant', contenu: r.reponse }]);
    } catch (e) {
      setMessages([...suite, { role: 'assistant', contenu: e instanceof ErreurApi ? e.message : String(e) }]);
    } finally {
      setAttente(false);
    }
  }

  if (etat.donnees && !etat.donnees.actif)
    return (
      <View style={[s.ecran, s.centre]}>
        <Text style={s.texte}>L'assistant n'est pas disponible pour l'instant. La FAQ répond aux questions courantes.</Text>
      </View>
    );

  return (
    <KeyboardAvoidingView style={s.ecran} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
      <FlatList
        ref={liste}
        data={[{ role: 'assistant', contenu: ACCUEIL } as Message, ...messages]}
        keyExtractor={(_, i) => String(i)}
        contentContainerStyle={{ padding: 16, gap: 10 }}
        onContentSizeChange={() => liste.current?.scrollToEnd({ animated: true })}
        renderItem={({ item }) => (
          <View
            style={{
              alignSelf: item.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '85%',
              backgroundColor: item.role === 'user' ? couleurs.accent : couleurs.surface,
              borderRadius: rayon,
              padding: 12,
            }}
          >
            <Text style={[s.texte, item.role === 'user' && { color: couleurs.accentEncre }]}>{item.contenu}</Text>
          </View>
        )}
        ListFooterComponent={attente ? <ActivityIndicator color={couleurs.accent} style={{ alignSelf: 'flex-start', padding: 8 }} /> : null}
      />
      <View style={{ flexDirection: 'row', gap: 8, padding: 12, borderTopWidth: 1, borderTopColor: couleurs.trait }}>
        <TextInput
          style={[s.champ, { flex: 1, paddingVertical: 10 }]}
          placeholder="Votre question"
          placeholderTextColor={couleurs.discret}
          value={saisie}
          onChangeText={setSaisie}
          onSubmitEditing={envoyer}
          returnKeyType="send"
          maxLength={1000}
        />
        <Bouton titre="Envoyer" desactive={attente || !saisie.trim()} onPress={envoyer} />
      </View>
      <Text style={[s.discret, { paddingBottom: 12 }]}>Réponses générées par une IA : elles peuvent contenir des erreurs.</Text>
    </KeyboardAvoidingView>
  );
}
