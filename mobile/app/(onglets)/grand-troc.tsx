import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, Linking, RefreshControl, ScrollView, Text, View } from 'react-native';

import { Boucle } from '../../components/Boucle';
import { Bouton, Encart, EtatRequete, s, Section } from '../../components/ui';
import { api, ErreurApi } from '../../lib/api';
import { useSession } from '../../lib/session';
import { couleurs, SITE } from '../../lib/theme';
import type { BoucleProposee, EchangeLecture, InfosGrandTroc } from '../../lib/types';
import { useRequete } from '../../lib/useRequete';

/** « dans 2 j 5 h », « dans 3 h 12 min », « maintenant ». */
function compteARebours(cible: Date, maintenant: number) {
  const min = Math.max(0, Math.round((cible.getTime() - maintenant) / 60000));
  if (min === 0) return 'maintenant';
  const j = Math.floor(min / 1440);
  const h = Math.floor((min % 1440) / 60);
  return j ? `dans ${j} j ${h} h` : h ? `dans ${h} h ${min % 60} min` : `dans ${min} min`;
}

/** Le Grand Troc du dimanche : le rendez-vous de 18 h où les boucles de 2 et 3 personnes sont proposées. */
export default function GrandTroc() {
  const { moi } = useSession();
  const infos = useRequete<InfosGrandTroc>('/grand-troc');
  const [maintenant, setMaintenant] = useState(Date.now());

  useEffect(() => {
    const minuterie = setInterval(() => setMaintenant(Date.now()), 30_000);
    return () => clearInterval(minuterie);
  }, []);

  const prochain = infos.donnees ? new Date(infos.donnees.prochain) : null;
  const dernier = infos.donnees?.dernier;

  return (
    <ScrollView
      style={s.ecran}
      contentContainerStyle={{ padding: 16, gap: 24 }}
      refreshControl={<RefreshControl refreshing={false} onRefresh={infos.recharger} tintColor={couleurs.accent} />}
    >
      <EtatRequete {...infos} />
      {prochain && (
        <Encart titre="Prochain Grand Troc">
          <Text style={s.grandTitre}>{compteARebours(prochain, maintenant)}</Text>
          <Text style={s.texte}>
            {prochain.toLocaleString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })}
          </Text>
        </Encart>
      )}

      <View style={{ gap: 8 }}>
        <Text style={s.texte}>
          Chaque dimanche à 18 h, TopTroc cherche toutes les boucles possibles entre les objets proposés : je donne à Léa, Léa donne
          à Karim, Karim me donne. Chacun reçoit ce qu'il demande, sans argent.
        </Text>
        <Text style={s.texte}>
          Vous avez 48 heures pour accepter votre proposition, puis une semaine pour remettre votre objet. Proposez vos objets et
          dites ce qui vous serait utile avant dimanche.
        </Text>
        <Bouton titre="En savoir plus" secondaire onPress={() => Linking.openURL(`${SITE}/grand-troc/`)} />
      </View>

      {dernier && (
        <Section titre={`Dernier Grand Troc · ${new Date(dernier.jour).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })}`}>
          <Text style={s.texte}>
            {dernier.nb_boucles} boucle{dernier.nb_boucles > 1 ? 's' : ''}, {dernier.nb_objets} objet{dernier.nb_objets > 1 ? 's' : ''} échangé
            {dernier.nb_objets > 1 ? 's' : ''} entre {dernier.nb_participants} membre{dernier.nb_participants > 1 ? 's' : ''}.
          </Text>
        </Section>
      )}

      {moi ? (
        <>
          <MatchATrois moiId={moi.id} />
          <MesBoucles moiId={moi.id} aLaDemande={!!infos.donnees?.echanges_a_la_demande} />
        </>
      ) : (
        <View style={{ gap: 12 }}>
          <Text style={s.texte}>Connectez-vous pour voir vos échanges possibles.</Text>
          <Bouton titre="Se connecter" onPress={() => router.push('/connexion')} />
        </View>
      )}
    </ScrollView>
  );
}

/** Proposer une boucle ; ma part est acceptée, les autres ont 48 h. */
function useProposer(route: string) {
  const [envoi, setEnvoi] = useState<number | null>(null);
  async function proposer(index: number, boucle: BoucleProposee, apres: () => void) {
    setEnvoi(index);
    try {
      const e = await api<EchangeLecture>(route, { corps: { objets: boucle.etapes.map((x) => x.objet.id) } });
      apres();
      router.push(`/echange/${e.id}`);
    } catch (err) {
      Alert.alert('Échange impossible', err instanceof ErreurApi ? err.message : String(err));
    } finally {
      setEnvoi(null);
    }
  }
  return { envoi, proposer };
}

/** Le Match à trois : boucles à trois possibles tout de suite, où chacun reçoit ce qu'il a demandé ou aimé. */
function MatchATrois({ moiId }: { moiId: number }) {
  const boucles = useRequete<BoucleProposee[]>('/match/boucles');
  const { envoi, proposer } = useProposer('/match/boucle');
  if (!boucles.donnees?.length && !boucles.erreur) return null;
  return (
    <Section titre="Match à trois, tout de suite">
      <EtatRequete {...boucles} />
      {boucles.donnees?.map((b, i) => (
        <Boucle key={i} boucle={b} moiId={moiId} action="Proposer cette boucle" envoi={envoi === i} onAction={() => proposer(i, b, boucles.recharger)} />
      ))}
    </Section>
  );
}

/** « Mes échanges possibles » : un aperçu de ce que dimanche pourrait me proposer. */
function MesBoucles({ moiId, aLaDemande }: { moiId: number; aLaDemande: boolean }) {
  const boucles = useRequete<BoucleProposee[]>('/moi/boucles');
  const { envoi, proposer } = useProposer('/echanges');
  return (
    <Section titre={aLaDemande ? 'Mes échanges possibles' : 'Aperçu pour dimanche'}>
      <EtatRequete {...boucles} />
      {boucles.donnees?.length === 0 && (
        <Text style={s.discret}>Rien pour l'instant. Ajoutez des objets et des souhaits pour multiplier les boucles possibles.</Text>
      )}
      {boucles.donnees?.map((b, i) => (
        <Boucle
          key={i}
          boucle={b}
          moiId={moiId}
          action={aLaDemande ? 'Proposer cet échange' : undefined}
          envoi={envoi === i}
          onAction={() => proposer(i, b, boucles.recharger)}
        />
      ))}
    </Section>
  );
}
