import { Image } from 'expo-image';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { Pressable, ScrollView, Text, View } from 'react-native';

import { BoutonsFavori } from '../../components/CarteObjet';
import { Bouton, EtatRequete, s } from '../../components/ui';
import { useSession } from '../../lib/session';
import { couleurs, ETATS, FORMATS_COLIS, MODES_ECHANGE, rayon, REPUTATIONS } from '../../lib/theme';
import type { CategorieDetaillee, Objet, UtilisateurPublic } from '../../lib/types';
import { useRequete } from '../../lib/useRequete';

export default function FicheObjet() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { moi } = useSession();
  const requete = useRequete<Objet>(`/objets/${id}`);
  const objet = requete.donnees;
  const categories = useRequete<CategorieDetaillee[]>('/categories');
  const proprietaire = useRequete<UtilisateurPublic>(objet ? `/utilisateurs/${objet.proprietaire_id}` : null);

  const categorie = categories.donnees?.find((c) => c.slug === objet?.categorie_slug);
  const sous = categorie?.sous_categories.find((c) => c.slug === objet?.sous_categorie_slug);
  const libelle = (cle: string) => categorie?.caracteristiques.find((c) => c.cle === cle)?.libelle ?? cle.replace(/_/g, ' ');
  const modes = objet?.modes_echange.length ? objet.modes_echange : ['main_propre', 'point_relais'];
  const mien = moi?.id === objet?.proprietaire_id;

  return (
    <ScrollView style={s.ecran} contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 48 }}>
      <Stack.Screen options={{ title: objet?.titre ?? '' }} />
      <EtatRequete {...requete} />
      {objet && (
        <>
          <View>
            <Image source={objet.photo_url} style={{ aspectRatio: 1, borderRadius: rayon, backgroundColor: couleurs.surface }} contentFit="cover" />
            <View style={{ position: 'absolute', top: 12, right: 12 }}>
              <BoutonsFavori objet={objet} grand />
            </View>
          </View>
          <Text style={s.grandTitre}>{objet.titre}</Text>
          <Text style={[s.discret, { textAlign: 'left' }]}>
            {[categorie?.libelle, sous?.libelle, objet.etat && ETATS[objet.etat], objet.lieu].filter(Boolean).join(' · ')}
          </Text>
          {objet.statut === 'reserve' && <Text style={[s.texte, { color: couleurs.marque }]}>Réservé : un échange est en cours.</Text>}
          {objet.description && <Text style={s.texte}>{objet.description}</Text>}
          {Object.entries(objet.caracteristiques).map(([cle, valeur]) => (
            <View key={cle} style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <Text style={s.discret}>{libelle(cle)}</Text>
              <Text style={s.texte}>{valeur}</Text>
            </View>
          ))}
          <Text style={s.texte}>
            Remise : {modes.map((m) => MODES_ECHANGE[m] ?? m).join(', ')}
            {objet.format_colis ? ` · ${FORMATS_COLIS[objet.format_colis] ?? objet.format_colis}` : ''}
          </Text>

          {proprietaire.donnees && (
            <View style={[s.vignette, { justifyContent: 'space-between' }]}>
              <View style={{ gap: 2, flex: 1 }}>
                <Text style={s.titre}>{proprietaire.donnees.pseudo}</Text>
                <Text style={[s.discret, { textAlign: 'left' }]}>
                  {[REPUTATIONS[proprietaire.donnees.reputation] ?? proprietaire.donnees.reputation, `${proprietaire.donnees.echanges_menes} échange${proprietaire.donnees.echanges_menes > 1 ? 's' : ''} mené${proprietaire.donnees.echanges_menes > 1 ? 's' : ''}`, proprietaire.donnees.zone]
                    .filter(Boolean)
                    .join(' · ')}
                </Text>
              </View>
            </View>
          )}

          <Text style={[s.discret, { textAlign: 'left' }]}>
            Pas de prix : cet objet s'échange contre ce qui est utile à son propriétaire, directement grâce au Match ou en boucle au Grand
            Troc du dimanche.
          </Text>

          {mien ? (
            <Bouton titre="Gérer mon objet" onPress={() => router.push(`/mon-objet/${objet.id}`)} />
          ) : moi ? (
            <Text style={s.texte}>Touchez le cœur ♡ pour dire « J'aime » : si son propriétaire aime un de vos objets, c'est un match.</Text>
          ) : (
            <Bouton titre="Créer un compte pour l'échanger" onPress={() => router.push('/connexion')} />
          )}

          {!mien && (
            <Pressable onPress={() => router.push({ pathname: '/signaler', params: { objet: String(objet.id) } })} hitSlop={8}>
              <Text style={[s.discret, { textDecorationLine: 'underline' }]}>Signaler cet objet</Text>
            </Pressable>
          )}
        </>
      )}
    </ScrollView>
  );
}
