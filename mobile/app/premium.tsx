import { useState } from 'react';
import { Alert, Linking, ScrollView, Text, View } from 'react-native';

import { Bouton, Champ, Encart, EtatRequete, s, Section } from '../components/ui';
import { CarteObjet } from '../components/CarteObjet';
import { api, ErreurApi } from '../lib/api';
import { useSession } from '../lib/session';
import { AVANTAGES, couleurs, rayon } from '../lib/theme';
import type { CataloguePremium, FormulePremium, Moi, Objet } from '../lib/types';
import { useRequete } from '../lib/useRequete';

const euros = (x: number | null) => (x == null ? '' : x.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' }));

/** Troc Premium : les 5 formules (GET /premium), l'essai gratuit, la famille et l'aperçu du stock, comme web/premium.js. */
export default function Premium() {
  const { moi, rafraichir } = useSession();
  const catalogue = useRequete<CataloguePremium>('/premium');
  const [envoi, setEnvoi] = useState(false);
  if (!moi) return null;
  const actuelle = moi.formule ? catalogue.donnees?.formules.find((f) => f.cle === moi.formule) : undefined;

  async function essayer() {
    setEnvoi(true);
    try {
      await api<Moi>('/premium/essai', { method: 'POST' });
      await rafraichir();
      Alert.alert('Bienvenue dans Troc Premium Plus !');
    } catch (e) {
      Alert.alert('Essai', e instanceof ErreurApi ? e.message : String(e));
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <ScrollView style={s.ecran} contentContainerStyle={{ padding: 16, gap: 22, paddingBottom: 48 }}>
      <EtatRequete {...catalogue} />
      {catalogue.donnees && actuelle && (
        <>
          <Encart titre={`Troc Premium ${actuelle.nom}`} couleur={couleurs.ok}>
            {moi.premium_jusqu_au && <Text style={s.texte}>Jusqu'au {new Date(moi.premium_jusqu_au).toLocaleDateString('fr-FR')}.</Text>}
            {(moi.avantages ?? []).map((a) => (
              <Text key={a} style={s.texte}>• {AVANTAGES[a] ?? a}</Text>
            ))}
          </Encart>
          {(moi.avantages ?? []).includes('apercu_du_stock') && <Apercu />}
          {moi.formule === 'famille' && moi.premium_jusqu_au && <Famille />}
          {catalogue.donnees.portail && <Bouton titre="Gérer ou résilier mon abonnement" secondaire onPress={() => Linking.openURL(catalogue.donnees!.portail!)} />}
        </>
      )}
      {catalogue.donnees && !actuelle && (
        <>
          <Text style={s.texte}>
            Échanger reste gratuit et illimité. Premium ajoute du confort et vous fait passer en premier quand plusieurs membres veulent
            le même objet, sans jamais faire perdre un échange à personne.
          </Text>
          {moi.essai_disponible && catalogue.donnees.jours_essai > 0 && (
            <Bouton titre={envoi ? 'Un instant…' : `Essayer Premium Plus ${catalogue.donnees.jours_essai} jours, gratuitement`} desactive={envoi} onPress={essayer} />
          )}
          {catalogue.donnees.formules.map((f) => (
            <Formule key={f.cle} f={f} moi={moi} />
          ))}
        </>
      )}
    </ScrollView>
  );
}

function Formule({ f, moi }: { f: FormulePremium; moi: Moi }) {
  // Même lien de paiement Stripe que le site : le webhook retrouve le compte avec client_reference_id.
  const lien = (url: string, achat: string) => `${url}?client_reference_id=${moi.id}-${achat}&prefilled_email=${encodeURIComponent(moi.email)}`;
  const prix = f.prix_unique != null ? `${euros(f.prix_unique)} le dimanche` : `${euros(f.prix_mois)} par mois ou ${euros(f.prix_an)} par an`;
  return (
    <View style={{ gap: 6, padding: 14, borderRadius: rayon, borderWidth: f.cle === 'plus' ? 2 : 1, borderColor: f.cle === 'plus' ? couleurs.accent : couleurs.trait }}>
      <Text style={s.grandTitre}>{f.nom}</Text>
      <Text style={[s.titre, { color: couleurs.marque }]}>{prix}</Text>
      {f.avantages.map((a) => (
        <Text key={a} style={s.texte}>• {AVANTAGES[a] ?? a}</Text>
      ))}
      {f.super_jaime_par_semaine > 0 && <Text style={s.texte}>• {f.super_jaime_par_semaine} Super J'aime par semaine</Text>}
      {Object.entries(f.liens).map(([periode, url]) => (
        <Bouton
          key={periode}
          titre={periode === 'an' ? "À l'année" : periode === 'mois' ? 'Au mois' : 'Acheter'}
          secondaire={f.cle !== 'plus'}
          onPress={() => Linking.openURL(lien(url, periode === 'pass' ? 'pass' : `${f.cle}_${periode}`))}
        />
      ))}
    </View>
  );
}

function Apercu() {
  const [objets, setObjets] = useState<Objet[] | null>(null);
  return (
    <Section titre="Aperçu du stock du dimanche">
      {objets === null ? (
        <Bouton titre="Voir les objets pour mes demandes" secondaire onPress={() => api<Objet[]>('/moi/apercu').then(setObjets, (e) => Alert.alert('Aperçu', e.message))} />
      ) : objets.length === 0 ? (
        <Text style={s.discret}>Rien pour vos demandes en ce moment.</Text>
      ) : (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}>
          {objets.map((o) => (
            <View key={o.id} style={{ width: '47%' }}>
              <CarteObjet objet={o} />
            </View>
          ))}
        </View>
      )}
    </Section>
  );
}

function Famille() {
  const membres = useRequete<{ id: number; pseudo: string }[]>('/premium/famille');
  const [email, setEmail] = useState('');
  async function ajouter() {
    try {
      membres.setDonnees(await api('/premium/famille', { corps: { email: email.trim() } }));
      setEmail('');
    } catch (e) {
      Alert.alert('Famille', e instanceof ErreurApi ? e.message : String(e));
    }
  }
  async function retirer(id: number) {
    await api(`/premium/famille/${id}`, { method: 'DELETE' }).catch(() => undefined);
    membres.recharger();
  }
  return (
    <Section titre="Ma famille (3 proches)">
      {membres.donnees?.map((m) => (
        <View key={m.id} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text style={s.texte}>{m.pseudo}</Text>
          <Bouton titre="Retirer" secondaire onPress={() => retirer(m.id)} />
        </View>
      ))}
      <Champ libelle="Ajouter un proche (e-mail de son compte TopTroc)" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
      <Bouton titre="Ajouter" secondaire desactive={!email.includes('@')} onPress={ajouter} />
    </Section>
  );
}
