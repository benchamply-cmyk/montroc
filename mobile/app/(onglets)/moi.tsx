import { router, useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { Alert, Pressable, ScrollView, Text, View } from 'react-native';

import { Bouton, EtatRequete, LigneMenu, s, Section, Vignette } from '../../components/ui';
import { api, ErreurApi } from '../../lib/api';
import { aFaire } from '../../lib/echanges';
import { useSession } from '../../lib/session';
import { couleurs, rayon, REPUTATIONS } from '../../lib/theme';
import type { EchangeLecture, InfosGrandTroc, MatchLecture, ObjetResume } from '../../lib/types';
import { useRequete } from '../../lib/useRequete';

const STATUTS: Record<string, string> = { disponible: 'En ligne', reserve: 'Réservé', echange: 'Échangé', retire: 'Retiré', modere: 'Modéré' };

export default function MonEspace() {
  const { pret, moi, fermer } = useSession();
  const connecte = pret && moi !== null;
  const grandTroc = useRequete<InfosGrandTroc>('/grand-troc');
  const objets = useRequete<(ObjetResume & { statut: string })[]>(connecte ? '/moi/objets' : null);
  const matchs = useRequete<MatchLecture[]>(connecte ? '/match' : null);
  const echanges = useRequete<EchangeLecture[]>(connecte ? '/moi/echanges' : null);

  // Au retour de « Proposer un objet » ou d'un autre onglet : la liste a pu changer. Le premier affichage charge déjà.
  const dejaVu = useRef(false);
  const { recharger: rechargerObjets } = objets;
  const { recharger: rechargerMatchs } = matchs;
  const { recharger: rechargerEchanges } = echanges;
  useFocusEffect(
    useCallback(() => {
      if (dejaVu.current) {
        rechargerObjets();
        rechargerMatchs();
        rechargerEchanges();
      }
      dejaVu.current = true;
    }, [rechargerObjets, rechargerMatchs, rechargerEchanges]),
  );
  const nbAFaire = moi ? (echanges.donnees ?? []).filter((e) => aFaire(e, moi.id)).length : 0;
  const enCours = (echanges.donnees ?? []).filter((e) => e.statut === 'propose' || e.statut === 'accepte').length;

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
          <Bouton titre="Proposer un objet" secondaire onPress={() => router.push('/proposer')} />
          <LigneMenu titre="Infos et aide" detail="Le concept, FAQ, CGU, confidentialité" onPress={() => router.push('/infos')} />
        </View>
      ) : (
        <>
          <View>
            <Text style={s.grandTitre}>{moi.pseudo}</Text>
            <Text style={[s.discret, { textAlign: 'left' }]}>
              {[moi.reputation && (REPUTATIONS[moi.reputation] ?? moi.reputation), moi.zone ?? 'Zone non renseignée', moi.formule && 'Troc Premium']
                .filter(Boolean)
                .join(' · ')}
            </Text>
          </View>

          <View style={{ gap: 8 }}>
            <LigneMenu
              titre={nbAFaire ? `Mes échanges · ${nbAFaire} à faire` : 'Mes échanges'}
              detail={enCours ? `${enCours} en cours` : 'Réponses, remises, codes de retrait'}
              onPress={() => router.push('/echanges')}
            />
            <LigneMenu titre="Troc Premium" detail={moi.formule ? 'Ma formule et ses avantages' : 'Les 5 formules, essai gratuit'} onPress={() => router.push('/premium')} />
            <LigneMenu titre="Mon compte" detail="Profil, zones, téléphone, mot de passe" onPress={() => router.push('/compte')} />
            <LigneMenu titre="Infos et aide" detail="Le concept, FAQ, CGU, confidentialité" onPress={() => router.push('/infos')} />
          </View>

          <Section titre="Mes matchs">
            <EtatRequete {...matchs} />
            {matchs.donnees?.length === 0 && <Text style={s.discret}>Pas encore de match : allez voir l'onglet Match.</Text>}
            {matchs.donnees?.map((m) => <MonMatch key={m.avec.id} match={m} onConclu={matchs.recharger} />)}
          </Section>

          <View style={{ gap: 10 }}>
            <Bouton titre="Proposer un objet" onPress={() => router.push('/proposer')} />
            <Bouton titre="Mes souhaits" secondaire onPress={() => router.push('/souhaits')} />
          </View>

          <Section titre="Mes objets">
            <EtatRequete {...objets} />
            {objets.donnees?.length === 0 && <Text style={s.discret}>Aucun objet proposé pour l'instant.</Text>}
            {objets.donnees?.map((o) => (
              <Pressable key={o.id} onPress={() => router.push(`/mon-objet/${o.id}`)}>
                <Vignette objet={o} droite={<Text style={s.discret}>{STATUTS[o.statut] ?? o.statut}</Text>} />
              </Pressable>
            ))}
          </Section>

          <Bouton titre="Se déconnecter" secondaire onPress={fermer} />
        </>
      )}
    </ScrollView>
  );
}

/** Un objet à choisir pour l'accord : surligné quand il est choisi. */
function Choix({ objet, choisi, onPress }: { objet: ObjetResume; choisi: boolean; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={{ borderRadius: rayon, borderWidth: 2, borderColor: choisi ? couleurs.accent : 'transparent' }}>
      <Vignette objet={objet} droite={<Text style={{ color: choisi ? couleurs.accent : couleurs.discret, fontSize: 18 }}>{choisi ? '●' : '○'}</Text>} />
    </Pressable>
  );
}

/** Un match : choisir l'objet reçu et l'objet donné, puis proposer l'accord 1 à 1 (l'autre a 48 h pour dire oui). */
function MonMatch({ match, onConclu }: { match: MatchLecture; onConclu: () => void }) {
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
