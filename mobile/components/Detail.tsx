import { View } from 'react-native';

import type { CategorieDetaillee } from '../lib/types';
import { Champ, Puces } from './ui';

export interface ValeurDetail {
  categorie: string | null;
  sousCategorie: string | null;
  caracteristiques: Record<string, string>;
}

export const DETAIL_VIDE: ValeurDetail = { categorie: null, sousCategorie: null, caracteristiques: {} };

/** Les caractéristiques visibles : celles de toute la catégorie, plus celles de la sous-catégorie choisie. */
function visibles(categorie: CategorieDetaillee | undefined, sousCategorie: string | null) {
  return (categorie?.caracteristiques ?? []).filter((c) => !c.pour || (sousCategorie !== null && c.pour.includes(sousCategorie)));
}

/** Ne garde que les valeurs renseignées et encore visibles : l'API refuse une caractéristique hors de sa sous-catégorie. */
export function caracteristiquesPropres(categories: CategorieDetaillee[], v: ValeurDetail): Record<string, string> {
  const cles = new Set(visibles(categories.find((c) => c.slug === v.categorie), v.sousCategorie).map((c) => c.cle));
  return Object.fromEntries(Object.entries(v.caracteristiques).filter(([cle, val]) => cles.has(cle) && val.trim()));
}

/**
 * Catégorie, sous-catégorie et caractéristiques (même nomenclature que GET /categories et le site).
 * `demande` : pour un souhait, où ne rien choisir veut dire « peu importe ».
 */
export function Detail(p: { categories: CategorieDetaillee[]; valeur: ValeurDetail; onChange: (v: ValeurDetail) => void; demande?: boolean }) {
  const { valeur: v } = p;
  const categorie = p.categories.find((c) => c.slug === v.categorie);
  const changer = (modif: Partial<ValeurDetail>) => p.onChange({ ...v, ...modif });

  return (
    <View style={{ gap: 16 }}>
      <Puces
        libelle="Catégorie"
        options={p.categories.map((c) => ({ valeur: c.slug, libelle: c.libelle }))}
        choisies={v.categorie ? [v.categorie] : []}
        // Les caractéristiques d'une autre catégorie n'ont plus de sens : on repart de zéro.
        onChange={([c]) => p.onChange({ categorie: c ?? null, sousCategorie: null, caracteristiques: {} })}
      />
      {categorie && categorie.sous_categories.length > 0 && (
        <Puces
          libelle={p.demande ? 'Sous-catégorie (toutes si aucune)' : 'Sous-catégorie'}
          options={categorie.sous_categories.map((c) => ({ valeur: c.slug, libelle: c.libelle }))}
          choisies={v.sousCategorie ? [v.sousCategorie] : []}
          onChange={([c]) => changer({ sousCategorie: c ?? null })}
          facultatif
        />
      )}
      {visibles(categorie, v.sousCategorie).map((c) =>
        c.options ? (
          <Puces
            key={c.cle}
            libelle={c.libelle}
            options={c.options.map((o) => ({ valeur: o, libelle: o }))}
            choisies={v.caracteristiques[c.cle] ? [v.caracteristiques[c.cle]] : []}
            onChange={([o]) => changer({ caracteristiques: { ...v.caracteristiques, [c.cle]: o ?? '' } })}
            facultatif
          />
        ) : (
          <Champ
            key={c.cle}
            libelle={c.libelle}
            value={v.caracteristiques[c.cle] ?? ''}
            onChangeText={(t) => changer({ caracteristiques: { ...v.caracteristiques, [c.cle]: t } })}
            placeholder={p.demande ? 'Peu importe' : 'Facultatif'}
            maxLength={60}
          />
        ),
      )}
    </View>
  );
}
