import { Redirect } from 'expo-router';

// L'onglet Proposer ouvre /proposer par-dessus (voir _layout) : cet écran n'est atteint que par un lien direct.
export default function Publier() {
  return <Redirect href="/proposer" />;
}
