import { Image } from 'expo-image';
import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View, type TextInputProps } from 'react-native';

import { couleurs, ETATS, rayon } from '../lib/theme';
import type { ObjetResume } from '../lib/types';

/** Chargement, réveil du serveur ou erreur avec bouton « Réessayer ». Rien quand tout va bien. */
export function EtatRequete(p: { chargement: boolean; reveil: boolean; erreur: string | null; recharger: () => void }) {
  if (p.erreur)
    return (
      <View style={s.centre}>
        <Text style={s.erreur}>{p.erreur}</Text>
        <Bouton titre="Réessayer" onPress={p.recharger} secondaire />
      </View>
    );
  if (!p.chargement) return null;
  return (
    <View style={s.centre}>
      <ActivityIndicator color={couleurs.accent} />
      {p.reveil && <Text style={s.discret}>Le serveur se réveille, cela peut prendre jusqu'à une minute…</Text>}
    </View>
  );
}

export function Bouton(p: { titre: string; onPress: () => void; secondaire?: boolean; desactive?: boolean }) {
  return (
    <Pressable
      onPress={p.onPress}
      disabled={p.desactive}
      style={({ pressed }) => [
        s.bouton,
        p.secondaire && s.boutonSecondaire,
        (pressed || p.desactive) && { opacity: 0.6 },
      ]}
    >
      <Text style={[s.boutonTexte, p.secondaire && { color: couleurs.encre }]}>{p.titre}</Text>
    </Pressable>
  );
}

export function Champ(p: TextInputProps & { libelle: string }) {
  return (
    <View style={{ gap: 6 }}>
      <Text style={[s.discret, { textAlign: 'left' }]}>{p.libelle}</Text>
      <TextInput placeholderTextColor={couleurs.discret} style={s.champ} {...p} />
    </View>
  );
}

export function Vignette({ objet, droite }: { objet: ObjetResume; droite?: ReactNode }) {
  return (
    <View style={s.vignette}>
      <Image source={objet.photo_url} style={s.vignettePhoto} contentFit="cover" />
      <View style={{ flex: 1 }}>
        <Text style={s.titre} numberOfLines={2}>
          {objet.titre}
        </Text>
        {objet.etat && <Text style={s.discret}>{ETATS[objet.etat]}</Text>}
      </View>
      {droite}
    </View>
  );
}

export const s = StyleSheet.create({
  ecran: { flex: 1, backgroundColor: couleurs.fond },
  centre: { padding: 24, alignItems: 'center', gap: 12 },
  titre: { color: couleurs.encre, fontSize: 16, fontWeight: '600' },
  grandTitre: { color: couleurs.encre, fontSize: 24, fontWeight: '800' },
  texte: { color: couleurs.encre, fontSize: 15, lineHeight: 21 },
  discret: { color: couleurs.discret, fontSize: 13, textAlign: 'center' },
  erreur: { color: couleurs.danger, fontSize: 14, textAlign: 'center' },
  bouton: { backgroundColor: couleurs.accent, borderRadius: rayon, paddingVertical: 14, paddingHorizontal: 20, alignItems: 'center' },
  boutonSecondaire: { backgroundColor: 'transparent', borderWidth: 1, borderColor: couleurs.trait },
  boutonTexte: { color: couleurs.accentEncre, fontWeight: '700', fontSize: 15 },
  champ: {
    backgroundColor: couleurs.surface,
    borderColor: couleurs.trait,
    borderWidth: 1,
    borderRadius: rayon,
    color: couleurs.encre,
    padding: 14,
    fontSize: 16,
  },
  vignette: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 10, backgroundColor: couleurs.surface, borderRadius: rayon },
  vignettePhoto: { width: 56, height: 56, borderRadius: 10, backgroundColor: couleurs.trait },
});
