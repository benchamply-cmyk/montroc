import { Text, View } from 'react-native';

import { couleurs, rayon } from '../lib/theme';
import type { BoucleProposee } from '../lib/types';
import { Bouton, s, Vignette } from './ui';

/** Une boucle possible : qui donne quoi à qui, et sa chance de réussite. */
export function Boucle(p: { boucle: BoucleProposee; moiId: number; action?: string; envoi?: boolean; onAction?: () => void }) {
  const { boucle } = p;
  return (
    <View style={{ gap: 8, padding: 12, borderWidth: 1, borderColor: couleurs.trait, borderRadius: rayon }}>
      <Text style={s.titre}>
        Boucle à {boucle.longueur} · {Math.round(boucle.proba_reussite * 100)} % de réussite estimée
      </Text>
      {boucle.etapes.map((e) => (
        <View key={e.objet.id} style={{ gap: 4 }}>
          <Text style={[s.discret, { textAlign: 'left' }]}>
            {e.donneur_id === p.moiId ? 'Je donne' : e.donneur_pseudo + ' donne'} à {e.receveur_id === p.moiId ? 'moi' : e.receveur_pseudo}
          </Text>
          <Vignette objet={e.objet} />
        </View>
      ))}
      {p.action && p.onAction && <Bouton titre={p.envoi ? 'Envoi…' : p.action} desactive={p.envoi} onPress={p.onAction} />}
    </View>
  );
}
