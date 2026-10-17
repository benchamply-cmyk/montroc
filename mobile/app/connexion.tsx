import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text } from 'react-native';

import { Bouton, Champ, s } from '../components/ui';
import { api, ErreurApi } from '../lib/api';
import { useSession } from '../lib/session';
import type { ResultatConnexion } from '../lib/types';

type Etape = 'motdepasse' | 'lien' | 'lien-envoye' | 'inscription';

/** Le lien de l'e-mail est https://troctroc.fr/#connexion=<jeton> : on accepte le lien entier ou le seul jeton. */
function extraireJeton(texte: string): string {
  const t = texte.trim();
  const m = t.match(/connexion=([\w-]+)/);
  return m ? m[1] : t;
}

export default function Connexion() {
  const session = useSession();
  // troctroc://connexion?jeton=… ouvre directement cet écran.
  const params = useLocalSearchParams<{ jeton?: string }>();
  const [etape, setEtape] = useState<Etape>('motdepasse');
  const [email, setEmail] = useState('');
  const [motDePasse, setMotDePasse] = useState('');
  const [lienColle, setLienColle] = useState('');
  const [pseudo, setPseudo] = useState('');
  const [zone, setZone] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  async function tenter(action: () => Promise<void>) {
    setErreur(null);
    setEnvoi(true);
    try {
      await action();
    } catch (e) {
      setErreur(e instanceof ErreurApi ? e.message : String(e));
    } finally {
      setEnvoi(false);
    }
  }

  async function terminer(r: ResultatConnexion) {
    if (r.inscription_requise) {
      setEmail(r.email ?? email);
      setEtape('inscription');
      return;
    }
    await session.ouvrir(r);
    router.back();
  }

  const verifier = (jeton: string, inscription?: { pseudo: string; zone: string }) =>
    tenter(async () =>
      terminer(
        await api<ResultatConnexion>('/auth/verifier', {
          corps: { jeton, ...(inscription && { pseudo: inscription.pseudo, zone: inscription.zone || null }) },
        }),
      ),
    );

  useEffect(() => {
    if (params.jeton) {
      setLienColle(params.jeton);
      verifier(params.jeton);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.jeton]);

  return (
    <KeyboardAvoidingView style={s.ecran} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ padding: 20, gap: 16 }} keyboardShouldPersistTaps="handled">
        {etape === 'motdepasse' && (
          <>
            <Champ libelle="E-mail" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" autoComplete="email" />
            <Champ libelle="Mot de passe" value={motDePasse} onChangeText={setMotDePasse} secureTextEntry autoComplete="password" />
            <Bouton
              titre="Se connecter"
              desactive={envoi}
              onPress={() =>
                tenter(async () =>
                  terminer(await api<ResultatConnexion>('/auth/connexion', { corps: { email, mot_de_passe: motDePasse } })),
                )
              }
            />
            <Bouton titre="Recevoir un lien par e-mail" secondaire onPress={() => setEtape('lien')} />
          </>
        )}

        {etape === 'lien' && (
          <>
            <Text style={s.texte}>Nouveau sur TrocTroc ou mot de passe oublié ? Recevez un lien de connexion.</Text>
            <Champ libelle="E-mail" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
            <Bouton
              titre="Envoyer le lien"
              desactive={envoi}
              onPress={() =>
                tenter(async () => {
                  await api('/auth/lien', { corps: { email } });
                  setEtape('lien-envoye');
                })
              }
            />
            <Bouton titre="J'ai un mot de passe" secondaire onPress={() => setEtape('motdepasse')} />
          </>
        )}

        {etape === 'lien-envoye' && (
          <>
            <Text style={s.texte}>
              Lien envoyé à {email}. Il est valable 20 minutes. Dans l'e-mail, appuyez longuement sur le bouton, copiez
              le lien et collez-le ici.
            </Text>
            <Champ libelle="Lien de connexion" value={lienColle} onChangeText={setLienColle} autoCapitalize="none" />
            <Bouton titre="Valider" desactive={envoi || !lienColle} onPress={() => verifier(extraireJeton(lienColle))} />
          </>
        )}

        {etape === 'inscription' && (
          <>
            <Text style={s.texte}>Bienvenue ! Choisissez un pseudo pour créer votre compte {email}.</Text>
            <Champ libelle="Pseudo" value={pseudo} onChangeText={setPseudo} autoCapitalize="none" />
            <Champ libelle="Ville ou quartier" value={zone} onChangeText={setZone} placeholder="Marseille" />
            <Bouton
              titre="Créer mon compte"
              desactive={envoi || pseudo.trim().length < 2}
              onPress={() => verifier(extraireJeton(lienColle), { pseudo: pseudo.trim(), zone: zone.trim() })}
            />
          </>
        )}

        {erreur && <Text style={s.erreur}>{erreur}</Text>}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
