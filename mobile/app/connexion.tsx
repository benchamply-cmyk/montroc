import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text, View } from 'react-native';

import { Bouton, Champ, Puces, s } from '../components/ui';
import { api, ErreurApi } from '../lib/api';
import { useSession } from '../lib/session';
import { couleurs } from '../lib/theme';
import type { ResultatConnexion } from '../lib/types';

// Comme sur le site (#79) : deux onglets, puis le code à 6 chiffres reçu par e-mail.
type Onglet = 'connexion' | 'inscription';
type Etape = 'formulaire' | 'code';

const CODE = /^\d{6}$/;

export default function Connexion() {
  const session = useSession();
  // toptroc://connexion?jeton=… (lien de l'e-mail ouvert dans l'app) entre directement.
  const params = useLocalSearchParams<{ jeton?: string }>();
  const [onglet, setOnglet] = useState<Onglet>('connexion');
  const [etape, setEtape] = useState<Etape>('formulaire');
  // Vrai quand le code servira à créer le compte : on demande alors pseudo, ville et mot de passe.
  const [creation, setCreation] = useState(false);
  const [email, setEmail] = useState('');
  const [motDePasse, setMotDePasse] = useState('');
  const [code, setCode] = useState('');
  const [pseudo, setPseudo] = useState('');
  const [pseudoLibre, setPseudoLibre] = useState<boolean | null>(null);
  const [zone, setZone] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  async function tenter(action: () => Promise<void>) {
    setErreur(null);
    setInfo(null);
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
      // Code valide mais pas encore de compte : le même code resservira avec le pseudo.
      setEmail(r.email ?? email);
      setCreation(true);
      setInfo('Pas encore de compte avec cet e-mail : choisissez un pseudo pour le créer.');
      return;
    }
    await session.ouvrir(r);
    router.back();
  }

  // Le pseudo est vérifié pendant la saisie, une demi-seconde après la dernière touche.
  useEffect(() => {
    const p = pseudo.trim();
    setPseudoLibre(null);
    if (p.length < 2) return;
    const minuterie = setTimeout(async () => {
      try {
        const r = await api<{ libre: boolean }>(`/auth/pseudo?pseudo=${encodeURIComponent(p)}`);
        setPseudoLibre(r.libre);
      } catch {
        // Hors ligne : l'API refusera de toute façon un pseudo pris à la création.
      }
    }, 500);
    return () => clearTimeout(minuterie);
  }, [pseudo]);

  useEffect(() => {
    if (!params.jeton) return;
    tenter(async () => terminer(await api<ResultatConnexion>('/auth/verifier', { corps: { jeton: params.jeton } })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.jeton]);

  const seConnecter = () =>
    tenter(async () => terminer(await api<ResultatConnexion>('/auth/connexion', { corps: { email, mot_de_passe: motDePasse } })));

  const recevoirCode = () =>
    tenter(async () => {
      await api('/auth/lien', { corps: { email } });
      setCreation(false);
      setCode('');
      setEtape('code');
    });

  const sInscrire = () =>
    tenter(async () => {
      await api('/auth/inscription', { corps: { email, pseudo: pseudo.trim() } });
      setCreation(true);
      setCode('');
      setEtape('code');
    });

  const validerCode = () =>
    tenter(async () =>
      terminer(
        await api<ResultatConnexion>('/auth/code', {
          corps: {
            email,
            code,
            ...(creation && {
              pseudo: pseudo.trim(),
              zone: zone.trim() || null,
              mot_de_passe: motDePasse || null,
            }),
          },
        }),
      ),
    );

  const renvoyer = () =>
    tenter(async () => {
      // Seul le dernier code envoyé compte : l'ancien ne marche plus.
      await api(creation && onglet === 'inscription' ? '/auth/inscription' : '/auth/lien', {
        corps: creation && onglet === 'inscription' ? { email, pseudo: pseudo.trim() } : { email },
      });
      setCode('');
      setInfo('Nouveau code envoyé.');
    });

  const emailValide = /^\S+@\S+\.\S+$/.test(email.trim());
  const pseudoOk = pseudo.trim().length >= 2 && pseudoLibre !== false;
  const motDePasseOk = motDePasse.length === 0 || motDePasse.length >= 8;

  return (
    <KeyboardAvoidingView style={s.ecran} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ padding: 20, gap: 16 }} keyboardShouldPersistTaps="handled">
        {etape === 'formulaire' && (
          <>
            <Puces
              options={[
                { valeur: 'connexion', libelle: 'Se connecter' },
                { valeur: 'inscription', libelle: 'Créer un compte' },
              ]}
              choisies={[onglet]}
              onChange={([o]) => {
                setOnglet(o as Onglet);
                setErreur(null);
              }}
            />
            <Champ
              libelle="E-mail"
              value={email}
              onChangeText={(t) => setEmail(t.trim())}
              autoCapitalize="none"
              keyboardType="email-address"
              autoComplete="email"
              textContentType="emailAddress"
            />

            {onglet === 'connexion' ? (
              <>
                <Champ
                  libelle="Mot de passe"
                  value={motDePasse}
                  onChangeText={setMotDePasse}
                  secureTextEntry
                  autoComplete="current-password"
                  textContentType="password"
                />
                <Bouton titre="Se connecter" desactive={envoi || !emailValide || !motDePasse} onPress={seConnecter} />
                <Bouton titre="Pas de mot de passe ? Recevoir un code" secondaire desactive={envoi || !emailValide} onPress={recevoirCode} />
              </>
            ) : (
              <>
                <Champ libelle="Pseudo" value={pseudo} onChangeText={setPseudo} autoCapitalize="none" autoCorrect={false} />
                {pseudoLibre === false && <Text style={[s.erreur, { textAlign: 'left' }]}>Ce pseudo est déjà pris.</Text>}
                {pseudoLibre === true && <Text style={{ color: couleurs.ok }}>Pseudo disponible</Text>}
                <Bouton titre="Recevoir mon code" desactive={envoi || !emailValide || !pseudoOk} onPress={sInscrire} />
              </>
            )}
          </>
        )}

        {etape === 'code' && (
          <>
            <Text style={s.texte}>
              Code envoyé à {email}. Il est valable 20 minutes. Vous pouvez aussi ouvrir le lien de l'e-mail.
            </Text>
            <Champ
              libelle="Code à 6 chiffres"
              value={code}
              onChangeText={(t) => setCode(t.replace(/\D/g, '').slice(0, 6))}
              keyboardType="number-pad"
              autoComplete="one-time-code"
              textContentType="oneTimeCode"
              maxLength={6}
              style={[s.champ, { fontSize: 28, letterSpacing: 10, textAlign: 'center' }]}
            />

            {creation && (
              <View style={{ gap: 16 }}>
                {onglet !== 'inscription' && (
                  <Champ libelle="Pseudo" value={pseudo} onChangeText={setPseudo} autoCapitalize="none" autoCorrect={false} />
                )}
                <Champ libelle="Ville ou quartier (facultatif)" value={zone} onChangeText={setZone} placeholder="Marseille" />
                <Champ
                  libelle="Mot de passe (facultatif, 8 caractères minimum)"
                  value={motDePasse}
                  onChangeText={setMotDePasse}
                  secureTextEntry
                  autoComplete="new-password"
                  textContentType="newPassword"
                />
              </View>
            )}

            <Bouton
              titre={creation ? 'Créer mon compte' : 'Valider'}
              desactive={envoi || !CODE.test(code) || (creation && (!pseudoOk || !motDePasseOk))}
              onPress={validerCode}
            />
            <Bouton titre="Renvoyer un code" secondaire desactive={envoi} onPress={renvoyer} />
            <Bouton
              titre="Modifier l'e-mail"
              secondaire
              onPress={() => {
                setEtape('formulaire');
                setErreur(null);
                setInfo(null);
              }}
            />
          </>
        )}

        {info && <Text style={[s.discret, { color: couleurs.marque }]}>{info}</Text>}
        {erreur && <Text style={s.erreur}>{erreur}</Text>}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
