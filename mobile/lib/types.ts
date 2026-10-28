// Reflet des schémas de l'API (api/src/montroc_api/schemas.py) utilisés par l'app.

export type Etat = 'neuf' | 'comme_neuf' | 'tres_bon' | 'bon' | 'correct';
export type StatutObjet = 'disponible' | 'reserve' | 'echange' | 'retire' | 'modere';

export interface Objet {
  id: number;
  proprietaire_id: number;
  categorie_slug: string;
  sous_categorie_slug: string | null;
  caracteristiques: Record<string, string>;
  titre: string;
  description: string | null;
  etat: Etat | null;
  photo_url: string | null;
  statut: StatutObjet;
  modes_echange: string[];
  lieu?: string | null;
  format_colis?: string | null;
  cree_le: string;
}

/** Mes objets : avec le lien de l'annonce d'origine (GET /moi/objets). */
export interface MonObjet extends Objet {
  annonce_origine: string | null;
}

export interface ObjetResume {
  id: number;
  titre: string;
  categorie_slug: string;
  etat: Etat | null;
  photo_url: string | null;
}

export interface Moi {
  id: number;
  email: string;
  pseudo: string;
  zone: string | null;
  telephone: string | null;
  fiabilite: number;
  cree_le: string;
  est_moderateur: boolean;
  a_un_mot_de_passe: boolean;
  echanges_menes?: number;
  reputation?: string;
  verifie?: boolean;
  // Troc Premium : la formule dont je profite (la mienne ou celle de ma famille), jusqu'à quand, ses avantages.
  formule?: string | null;
  premium_jusqu_au?: string | null;
  avantages?: string[];
  essai_disponible?: boolean;
  super_jaime_restants?: number;
  zones_interet?: ZoneInteret[];
  zones_max?: number;
  toute_la_france?: boolean;
}

/** Une zone où je troque en main propre : une ville et un rayon. */
export interface ZoneInteret {
  libelle: string;
  latitude: number;
  longitude: number;
  rayon_km: number;
}

export interface ResultatConnexion {
  inscription_requise: boolean;
  email: string | null;
  jeton: string | null;
  utilisateur: Moi | null;
}

export interface Membre {
  id: number;
  pseudo: string;
  zone: string | null;
  fiabilite: number;
  echanges_menes?: number;
  reputation?: string;
  verifie?: boolean;
}

export interface CarteMatch {
  objet: Objet;
  proprietaire: Membre;
  souhait_categorie: string | null;
  souhait_sous_categorie: string | null;
  correspond_a_mes_souhaits: boolean;
  sa_demande: string | null;
  il_aime: ObjetResume[];
  il_cherche: ObjetResume[];
  distance_km?: number | null;
  par_colis?: boolean;
}

export interface MatchLecture {
  avec: Membre;
  ses_objets: ObjetResume[];
  mes_objets: ObjetResume[];
  depuis: string;
  echange_id: number | null;
}

export interface Categorie {
  slug: string;
  libelle: string;
}

export interface InfosGrandTroc {
  prochain: string;
  dernier: { jour: string; nb_boucles: number; nb_objets: number; nb_participants: number } | null;
  // Vrai si l'on peut aussi proposer une boucle tout de suite (POST /echanges), sans attendre dimanche.
  echanges_a_la_demande?: boolean;
}

export interface Caracteristique {
  cle: string;
  libelle: string;
  // Choix fixes ; null : texte libre (marque, modèle…).
  options: string[] | null;
  // Sous-catégories où elle se précise ; null : toute la catégorie.
  pour: string[] | null;
}

export interface CategorieDetaillee extends Categorie {
  sous_categories: Categorie[];
  caracteristiques: Caracteristique[];
}

export type ModeRecherche = 'precise' | 'flexible' | 'ouverte';

export interface Souhait {
  id: number;
  categorie_slug: string | null;
  objet_id: number | null;
  sous_categorie_slug: string | null;
  caracteristiques: Record<string, string>;
  preferences: Record<string, string>;
  precisions: string | null;
  etat_min: Etat | null;
  mode_recherche: ModeRecherche;
  modes_echange: string[];
  zones: string[];
  rang: number;
  quantite: number;
  acceptation_auto: boolean;
}

export interface PhotoSignature {
  url_envoi: string;
  api_key: string;
  timestamp: number;
  folder: string;
  signature: string;
}

export type StatutEchange = 'propose' | 'accepte' | 'annule' | 'termine';

export interface TransfertLecture {
  id: number;
  position: number;
  donneur_id: number;
  donneur_pseudo: string;
  receveur_id: number;
  receveur_pseudo: string;
  objet: ObjetResume;
  reponse: 'en_attente' | 'acceptee' | 'refusee';
  repondu_le: string | null;
  depose_le: string | null;
  // Visible seulement du donneur et du receveur.
  code_retrait: string | null;
  mode: string;
  transporteur: string | null;
  numero_suivi: string | null;
  garantie: boolean;
  adresse_livraison: string | null;
}

export interface EchangeLecture {
  id: number;
  statut: StatutEchange;
  proba_reussite: number;
  cree_le: string;
  expire_le: string;
  grand_troc_jour: string | null;
  par_match: boolean;
  point_de_depot: string | null;
  lieu_de_rencontre: string | null;
  avant_premiere: boolean;
  transferts: TransfertLecture[];
}

/** Une boucle calculée par le moteur, pas encore enregistrée (GET /moi/boucles, /match/boucles). */
export interface BoucleProposee {
  longueur: number;
  proba_reussite: number;
  etapes: {
    donneur_id: number;
    donneur_pseudo: string;
    receveur_id: number;
    receveur_pseudo: string;
    objet: ObjetResume;
    acceptation_auto: boolean;
  }[];
}

export interface FormulePremium {
  cle: string;
  nom: string;
  prix_mois: number | null;
  prix_an: number | null;
  prix_unique: number | null;
  avantages: string[];
  super_jaime_par_semaine: number;
  // « mois », « an » ou « pass » : liens de paiement Stripe.
  liens: Record<string, string>;
}

export interface CataloguePremium {
  formules: FormulePremium[];
  formats_colis: { cle: string; libelle: string; poids_max_kg: number | null }[];
  jours_essai: number;
  portail: string | null;
  publicite_texte: string | null;
  publicite_lien: string | null;
}

export interface ListeInteresses {
  nb_jaime: number;
  convoite: boolean;
  interesses: { membre: Membre; depuis: string; super_jaime: boolean; en_tete: boolean; ses_objets: ObjetResume[] }[];
}

export interface UtilisateurPublic {
  id: number;
  pseudo: string;
  zone: string | null;
  fiabilite: number;
  echanges_menes: number;
  reputation: string;
  cree_le: string;
}

export type MotifSignalement = 'illegal' | 'dangereux' | 'contrefacon' | 'arnaque' | 'inapproprie' | 'autre';
