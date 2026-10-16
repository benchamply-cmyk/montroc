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
  cree_le: string;
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
}
