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

/** Choix parmi quelques valeurs, en puces : une seule (ou aucune si `facultatif`), ou plusieurs avec `multiple`. */
export function Puces(p: {
  libelle?: string;
  options: { valeur: string; libelle: string }[];
  choisies: string[];
  onChange: (choisies: string[]) => void;
  multiple?: boolean;
  facultatif?: boolean;
}) {
  function basculer(valeur: string) {
    const deja = p.choisies.includes(valeur);
    if (p.multiple) p.onChange(deja ? p.choisies.filter((v) => v !== valeur) : [...p.choisies, valeur]);
    else if (deja) p.facultatif && p.onChange([]);
    else p.onChange([valeur]);
  }
  return (
    <View style={{ gap: 6 }}>
      {p.libelle && <Text style={[s.discret, { textAlign: 'left' }]}>{p.libelle}</Text>}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
        {p.options.map((o) => {
          const active = p.choisies.includes(o.valeur);
          return (
            <Pressable key={o.valeur} onPress={() => basculer(o.valeur)} style={[s.puce, active && s.puceActive]}>
              <Text style={[s.puceTexte, active && { color: couleurs.accentEncre }]}>{o.libelle}</Text>
            </Pressable>
          );
        })}
      </View>
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
  puce: { borderWidth: 1, borderColor: couleurs.trait, borderRadius: 999, paddingVertical: 8, paddingHorizontal: 14 },
  puceActive: { backgroundColor: couleurs.accent, borderColor: couleurs.accent },
  puceTexte: { color: couleurs.encre, fontSize: 14 },
  vignette: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 10, backgroundColor: couleurs.surface, borderRadius: rayon },
  vignettePhoto: { width: 56, height: 56, borderRadius: 10, backgroundColor: couleurs.trait },
});
