import { router } from 'expo-router';
import { ScrollView, Text, View } from 'react-native';

import { Bouton, EtatRequete, s, Vignette } from '../../components/ui';
import { useSession } from '../../lib/session';
import { couleurs } from '../../lib/theme';
import type { InfosGrandTroc, MatchLecture, ObjetResume } from '../../lib/types';
import { useRequete } from '../../lib/useRequete';

const STATUTS: Record<string, string> = { disponible: 'En ligne', reserve: 'Réservé', echange: 'Échangé', retire: 'Retiré', modere: 'Modéré' };

function Section({ titre, children }: { titre: string; children: React.ReactNode }) {
  return (
    <View style={{ gap: 10 }}>
      <Text style={[s.titre, { color: couleurs.discret, textTransform: 'uppercase', fontSize: 12, letterSpacing: 1 }]}>{titre}</Text>
      {children}
    </View>
  );
}

export default function MonEspace() {
  const { pret, moi, fermer } = useSession();
  const connecte = pret && moi !== null;
  const grandTroc = useRequete<InfosGrandTroc>('/grand-troc');
  const objets = useRequete<(ObjetResume & { statut: string })[]>(connecte ? '/moi/objets' : null);
  const matchs = useRequete<MatchLecture[]>(connecte ? '/match' : null);

  const prochain = grandTroc.donnees
    ? new Date(grandTroc.donnees.prochain).toLocaleString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <ScrollView style={s.ecran} contentContainerStyle={{ padding: 16, gap: 24 }}>
      {prochain && (
        <View style={{ backgroundColor: couleurs.surface, padding: 16, borderRadius: 14, gap: 4 }}>
          <Text style={[s.titre, { color: couleurs.marque }]}>Prochain Grand Troc</Text>
          <Text style={s.texte}>{prochain}</Text>
        </View>
      )}

      {!connecte ? (
        <View style={{ gap: 12 }}>
          <Text style={s.texte}>Connectez-vous pour proposer vos objets, dire ce qui vous serait utile et matcher.</Text>
          <Bouton titre="Se connecter" onPress={() => router.push('/connexion')} />
        </View>
      ) : (
        <>
          <View>
            <Text style={s.grandTitre}>{moi.pseudo}</Text>
            <Text style={[s.discret, { textAlign: 'left' }]}>{moi.zone ?? 'Zone non renseignée'} · {moi.email}</Text>
          </View>

          <Section titre="Mes matchs">
            <EtatRequete {...matchs} />
            {matchs.donnees?.length === 0 && <Text style={s.discret}>Pas encore de match : allez voir l'onglet Match.</Text>}
            {matchs.donnees?.map((m) => (
              <View key={m.avec.id} style={{ gap: 6 }}>
                <Text style={s.texte}>Avec {m.avec.pseudo}{m.echange_id ? ' · accord en cours' : ''}</Text>
                {m.ses_objets.map((o) => <Vignette key={o.id} objet={o} />)}
              </View>
            ))}
          </Section>

          <Section titre="Mes objets">
            <EtatRequete {...objets} />
            {objets.donnees?.length === 0 && <Text style={s.discret}>Aucun objet proposé pour l'instant.</Text>}
            {objets.donnees?.map((o) => (
              <Vignette key={o.id} objet={o} droite={<Text style={s.discret}>{STATUTS[o.statut] ?? o.statut}</Text>} />
            ))}
          </Section>

          <Bouton titre="Se déconnecter" secondaire onPress={fermer} />
        </>
      )}
    </ScrollView>
  );
}
