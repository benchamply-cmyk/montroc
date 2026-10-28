import Constants from 'expo-constants';
import { Linking, ScrollView, Text } from 'react-native';

import { LigneMenu, s, Section } from '../components/ui';
import { SITE } from '../lib/theme';

// Les pages publiques du site, ouvertes dans le navigateur : une seule version des textes à tenir à jour.
const PAGES: [string, [string, string][]][] = [
  [
    'Découvrir TopTroc',
    [
      ['Le concept', '/concept/'],
      ['Comment ça marche', '/comment-ca-marche/'],
      ['Le Grand Troc', '/grand-troc/'],
    ],
  ],
  [
    'Pour qui ?',
    [
      ['Particuliers', '/particuliers/'],
      ['Professionnels', '/pros/'],
      ['Collectivités', '/collectivites/'],
    ],
  ],
  [
    'Aide',
    [
      ['FAQ et contact', '/faq/'],
      ['Règles et signalements', '/regles/'],
    ],
  ],
  [
    'Informations légales',
    [
      ["Conditions générales d'utilisation", '/cgu/'],
      ['Confidentialité', '/confidentialite/'],
      ['Mentions légales', '/mentions-legales/'],
    ],
  ],
];

export default function Infos() {
  return (
    <ScrollView style={s.ecran} contentContainerStyle={{ padding: 16, gap: 24, paddingBottom: 48 }}>
      {PAGES.map(([titre, liens]) => (
        <Section key={titre} titre={titre}>
          {liens.map(([libelle, chemin]) => (
            <LigneMenu key={chemin} titre={libelle} onPress={() => Linking.openURL(SITE + chemin)} />
          ))}
        </Section>
      ))}
      <Section titre="Nous écrire">
        <LigneMenu titre="contact@toptroc.com" onPress={() => Linking.openURL('mailto:contact@toptroc.com')} />
      </Section>
      <Text style={s.discret}>TopTroc {Constants.expoConfig?.version ?? ''}</Text>
    </ScrollView>
  );
}
