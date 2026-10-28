import { Stack, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, KeyboardAvoidingView, Platform, RefreshControl, ScrollView, Text, View } from 'react-native';

import { Bouton, Champ, Encart, EtatRequete, s, Section, Vignette } from '../../components/ui';
import { api, ErreurApi } from '../../lib/api';
import { STATUTS_ECHANGE } from '../../lib/echanges';
import { useSession } from '../../lib/session';
import { couleurs, MODES_ECHANGE } from '../../lib/theme';
import type { EchangeLecture, TransfertLecture } from '../../lib/types';
import { useRequete } from '../../lib/useRequete';

const date = (iso: string) => new Date(iso).toLocaleString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' });

/** Un échange : répondre (48 h), donner son adresse pour un colis, remettre son objet (7 jours). */
export default function Echange() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { moi } = useSession();
  const requete = useRequete<EchangeLecture>(`/echanges/${id}`);
  const [envoi, setEnvoi] = useState(false);
  const e = requete.donnees;

  async function agir(route: string, corps: unknown, succes?: string) {
    setEnvoi(true);
    try {
      requete.setDonnees(await api<EchangeLecture>(`/echanges/${id}/${route}`, { corps }));
      if (succes) Alert.alert(succes);
    } catch (err) {
      Alert.alert('Échange', err instanceof ErreurApi ? err.message : String(err));
      requete.recharger();
    } finally {
      setEnvoi(false);
    }
  }

  function refuser() {
    Alert.alert("Refuser l'échange ?", "L'échange sera annulé pour tous les participants.", [
      { text: 'Annuler', style: 'cancel' },
      { text: 'Refuser', style: 'destructive', onPress: () => agir('reponse', { accepte: false }) },
    ]);
  }

  const recu = e?.transferts.find((t) => t.receveur_id === moi?.id);
  const donne = e?.transferts.find((t) => t.donneur_id === moi?.id);

  return (
    <KeyboardAvoidingView style={s.ecran} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView
        contentContainerStyle={{ padding: 16, gap: 22, paddingBottom: 48 }}
        keyboardShouldPersistTaps="handled"
        refreshControl={<RefreshControl refreshing={false} onRefresh={requete.recharger} tintColor={couleurs.accent} />}
      >
        <Stack.Screen options={{ title: e?.par_match ? 'Accord du Match' : 'Échange' }} />
        <EtatRequete {...requete} />
        {e && moi && (
          <>
            <Encart titre={STATUTS_ECHANGE[e.statut] ?? e.statut} couleur={e.statut === 'annule' ? couleurs.danger : e.statut === 'termine' ? couleurs.ok : couleurs.marque}>
              {e.statut === 'propose' && <Text style={s.texte}>Réponses attendues avant {date(e.expire_le)}.</Text>}
              {e.statut === 'accepte' && <Text style={s.texte}>Objets à remettre avant {date(e.expire_le)}.</Text>}
              {e.avant_premiere && <Text style={s.discret}>Vue en avant-première (Troc Premium).</Text>}
              {e.lieu_de_rencontre && <Text style={s.texte}>Lieu conseillé pour la remise en main propre : {e.lieu_de_rencontre}</Text>}
              {e.point_de_depot && <Text style={s.texte}>Point de dépôt : {e.point_de_depot}</Text>}
            </Encart>

            {recu && e.statut === 'propose' && recu.reponse === 'en_attente' && (
              <View style={{ gap: 10 }}>
                <Text style={s.titre}>Vous recevriez :</Text>
                <Vignette objet={recu.objet} />
                <Bouton titre={envoi ? 'Envoi…' : "J'accepte"} desactive={envoi} onPress={() => agir('reponse', { accepte: true }, 'Merci ! Les autres participants sont prévenus.')} />
                <Bouton titre="Je refuse" secondaire desactive={envoi} onPress={refuser} />
              </View>
            )}

            {recu && recu.mode === 'colis' && !recu.depose_le && (e.statut === 'propose' || e.statut === 'accepte') && (
              <Adresse transfert={recu} envoi={envoi} onEnvoyer={(adresse) => agir('adresse', { adresse }, 'Adresse transmise à votre expéditeur.')} />
            )}

            {donne && e.statut === 'accepte' && !donne.depose_le && (
              <Remise transfert={donne} envoi={envoi} onRemettre={(corps) => agir('depot', corps, 'Remise enregistrée.')} />
            )}

            <Section titre="Qui donne quoi">
              {e.transferts.map((t) => (
                <Transfert key={t.id} t={t} moiId={moi.id} />
              ))}
            </Section>
          </>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Transfert({ t, moiId }: { t: TransfertLecture; moiId: number }) {
  const qui = (id: number, pseudo: string) => (id === moiId ? 'moi' : pseudo);
  const reponse = t.reponse === 'acceptee' ? '✓ accepté' : t.reponse === 'refusee' ? '✕ refusé' : '… en attente';
  return (
    <View style={{ gap: 4 }}>
      <Text style={[s.discret, { textAlign: 'left' }]}>
        De {qui(t.donneur_id, t.donneur_pseudo)} à {qui(t.receveur_id, t.receveur_pseudo)} · {MODES_ECHANGE[t.mode] ?? t.mode} · {reponse}
        {t.depose_le ? ' · remis' : ''}
      </Text>
      <Vignette objet={t.objet} />
      {t.code_retrait && <Text style={s.texte}>Code de retrait : {t.code_retrait}</Text>}
      {t.numero_suivi && <Text style={s.texte}>Suivi : {[t.transporteur, t.numero_suivi].filter(Boolean).join(' ')}</Text>}
      {t.adresse_livraison && t.donneur_id === moiId && <Text style={s.texte}>À envoyer à : {t.adresse_livraison}</Text>}
      {t.garantie && <Text style={s.discret}>Colis couvert par la Garantie TopTroc.</Text>}
    </View>
  );
}

function Adresse({ transfert, envoi, onEnvoyer }: { transfert: TransfertLecture; envoi: boolean; onEnvoyer: (a: string) => void }) {
  const [adresse, setAdresse] = useState(transfert.adresse_livraison ?? '');
  return (
    <View style={{ gap: 10 }}>
      <Text style={s.titre}>Où recevoir le colis ?</Text>
      <Champ libelle="Adresse ou point relais (seul votre expéditeur la voit)" value={adresse} onChangeText={setAdresse} multiline maxLength={300} />
      <Bouton titre={transfert.adresse_livraison ? "Modifier l'adresse" : "Envoyer l'adresse"} secondaire desactive={envoi || adresse.trim().length < 5} onPress={() => onEnvoyer(adresse.trim())} />
    </View>
  );
}

function Remise({ transfert, envoi, onRemettre }: { transfert: TransfertLecture; envoi: boolean; onRemettre: (c: object) => void }) {
  const [transporteur, setTransporteur] = useState('');
  const [suivi, setSuivi] = useState('');
  const colis = transfert.mode === 'colis';
  return (
    <View style={{ gap: 10 }}>
      <Text style={s.titre}>{colis ? 'Envoyer mon objet' : 'Remettre mon objet'}</Text>
      {colis && (
        <>
          <Champ libelle="Transporteur" value={transporteur} onChangeText={setTransporteur} placeholder="Colissimo, Mondial Relay…" maxLength={40} />
          <Champ libelle="Numéro de suivi" value={suivi} onChangeText={setSuivi} autoCapitalize="characters" maxLength={60} />
        </>
      )}
      <Bouton
        titre={colis ? "J'ai envoyé le colis" : "J'ai remis mon objet"}
        desactive={envoi || (colis && !suivi.trim())}
        onPress={() => onRemettre(colis ? { transporteur: transporteur.trim() || null, numero_suivi: suivi.trim() } : {})}
      />
    </View>
  );
}
