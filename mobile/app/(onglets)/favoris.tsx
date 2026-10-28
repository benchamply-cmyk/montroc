import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Alert, FlatList, RefreshControl, Text, View } from 'react-native';

import { CarteObjet } from '../../components/CarteObjet';
import { Bouton, Champ, Encart, EtatRequete, s } from '../../components/ui';
import { api, ErreurApi } from '../../lib/api';
import { useFavoris } from '../../lib/favoris';
import { useSession } from '../../lib/session';
import { CLE_RECHERCHES, CLE_SUIVI, ecrire, lire, type Recherche } from '../../lib/stockage';
import { couleurs } from '../../lib/theme';
import type { Objet } from '../../lib/types';

/** Mes favoris (l'étoile) : dans le compte pour un membre, 24 h sur le téléphone pour un visiteur. */
export default function Favoris() {
  const { moi } = useSession();
  const { etoiles, locaux } = useFavoris();
  const [objets, setObjets] = useState<Objet[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(false);

  const charger = useCallback(async () => {
    setChargement(true);
    setErreur(null);
    try {
      if (moi) setObjets(await api<Objet[]>('/moi/favoris'));
      else {
        // Un objet échangé ou retiré entre-temps disparaît de la liste.
        const lus = await Promise.all(locaux.map((f) => api<Objet>(`/objets/${f.objet_id}`).catch(() => null)));
        setObjets(lus.filter((o): o is Objet => o !== null && o.statut !== 'retire'));
      }
    } catch (e) {
      setErreur(e instanceof ErreurApi ? e.message : String(e));
    } finally {
      setChargement(false);
    }
  }, [moi, locaux]);

  useFocusEffect(
    useCallback(() => {
      charger();
    }, [charger]),
  );

  // Une étoile retirée sur une carte la retire aussitôt de la liste.
  const visibles = (objets ?? []).filter((o) => etoiles.has(o.id));
  const plusAncien = locaux.length ? Math.min(...locaux.map((f) => new Date(f.ajoute_le).getTime())) : null;
  const heuresRestantes = plusAncien ? Math.max(1, Math.round((plusAncien + 24 * 3600e3 - Date.now()) / 3600e3)) : null;

  return (
    <View style={s.ecran}>
      <FlatList
        data={visibles}
        keyExtractor={(o) => String(o.id)}
        numColumns={2}
        columnWrapperStyle={{ gap: 12 }}
        contentContainerStyle={{ padding: 16, gap: 12 }}
        refreshControl={<RefreshControl refreshing={false} onRefresh={charger} tintColor={couleurs.accent} />}
        ListHeaderComponent={
          <View style={{ gap: 12, marginBottom: 4 }}>
            {!moi && (
              <Encart titre="Favoris gardés 24 heures">
                <Text style={s.texte}>
                  Sans compte, vos favoris restent sur ce téléphone pendant 24 heures
                  {heuresRestantes ? ` (le premier s'efface dans environ ${heuresRestantes} h)` : ''}. Avec un compte, ils sont gardés et
                  vous pouvez matcher.
                </Text>
                <Bouton titre="Créer un compte ou se connecter" onPress={() => router.push('/connexion')} />
              </Encart>
            )}
            <EtatRequete chargement={chargement && objets === null} reveil={false} erreur={erreur} recharger={charger} />
          </View>
        }
        ListEmptyComponent={
          objets !== null ? <Text style={s.discret}>Touchez l'étoile ☆ d'un objet pour le retrouver ici.</Text> : null
        }
        ListFooterComponent={!moi ? <AlertesSansCompte /> : null}
        renderItem={({ item }) => <CarteObjet objet={item} />}
      />
    </View>
  );
}

/** Mode visiteur : être prévenu par e-mail ou SMS des nouveautés de ses recherches et favoris (POST /suivis). */
function AlertesSansCompte() {
  const { locaux } = useFavoris();
  const [suivi, setSuivi] = useState<string | null>(null);
  const [contact, setContact] = useState('');
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    lire<string | null>(CLE_SUIVI, null).then(setSuivi);
  }, []);

  async function demander() {
    const valeur = contact.trim();
    if (!valeur) return;
    setEnvoi(true);
    try {
      const recherches = await lire<Recherche[]>(CLE_RECHERCHES, []);
      const email = valeur.includes('@');
      await api('/suivis', {
        corps: {
          ...(email ? { email: valeur } : { telephone: valeur }),
          recherches: recherches.map((r) => ({ q: r.q, categorie: r.categorie })),
          favoris: locaux,
        },
      });
      // Le jeton du suivi arrive avec le lien de confirmation : on garde seulement l'information « demandé ».
      await ecrire(CLE_SUIVI, 'demande');
      setSuivi('demande');
      Alert.alert('Presque fini', email ? 'Ouvrez le lien reçu par e-mail pour confirmer les alertes.' : 'Ouvrez le lien reçu par SMS pour confirmer les alertes.');
    } catch (e) {
      Alert.alert('Alertes', e instanceof ErreurApi ? e.message : String(e));
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <View style={{ gap: 10, marginTop: 24 }}>
      <Text style={s.titre}>Être prévenu sans compte</Text>
      {suivi ? (
        <Text style={s.texte}>Alertes demandées : confirmez avec le lien reçu. Chaque message contient un lien pour les arrêter.</Text>
      ) : (
        <>
          <Text style={[s.discret, { textAlign: 'left' }]}>
            Un message au plus par jour quand un objet arrive dans vos recherches, et un rappel avant que vos favoris s'effacent.
          </Text>
          <Champ libelle="E-mail ou téléphone" value={contact} onChangeText={setContact} autoCapitalize="none" keyboardType="email-address" placeholder="vous@exemple.fr ou 06 12 34 56 78" />
          <Bouton titre={envoi ? 'Envoi…' : 'Me prévenir'} desactive={envoi || !contact.trim()} onPress={demander} secondaire />
        </>
      )}
    </View>
  );
}
