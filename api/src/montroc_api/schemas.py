"""Formats d'entrée et de sortie de l'API (validation Pydantic)."""

import re
from datetime import date, datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from . import nomenclature
from .config import get_settings
from .models import EtatObjet, ModeRecherche, MotifSignalement, Reponse, StatutEchange, StatutObjet, StatutSignalement


class Lecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CategorieCreation(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=50, examples=["siege-auto"])
    libelle: str = Field(min_length=1, max_length=100, examples=["Siège auto"])


class CategorieLecture(CategorieCreation, Lecture):
    pass


class SousCategorie(BaseModel):
    slug: str
    libelle: str


class CaracteristiqueLecture(BaseModel):
    cle: str
    libelle: str
    # Choix fixes ; None : texte libre (qui décrit un objet, sans filtrer les demandes).
    options: list[str] | None
    # Sous-catégories où elle se précise ; None : toute la catégorie.
    pour: list[str] | None = None


class CategorieDetaillee(CategorieLecture):
    """Une catégorie avec ses sous-catégories et ses caractéristiques (voir nomenclature.py)."""

    sous_categories: list[SousCategorie]
    caracteristiques: list[CaracteristiqueLecture]


# --- Connexion par lien magique ---


class DemandeLien(BaseModel):
    email: EmailStr
    langue: Literal["fr", "en", "es"] = "fr"


def normaliser_telephone(valeur: str | None) -> str | None:
    """« 06 12 34 56 78 », « +33 6 12… » ou « 0033 6… » → « +33612345678 ». Vide → None."""
    if valeur is None:
        return None
    numero = re.sub(r"[\s.\-()]", "", valeur)
    if not numero:
        return None
    if numero.startswith("00"):
        numero = "+" + numero[2:]
    elif re.fullmatch(r"0[1-9]\d{8}", numero):
        numero = "+33" + numero[1:]
    if not re.fullmatch(r"\+[1-9]\d{7,14}", numero):
        raise ValueError("Numéro de téléphone invalide : par exemple 06 12 34 56 78.")
    return numero


class AvecTelephone(BaseModel):
    @field_validator("telephone", mode="before", check_fields=False)
    @classmethod
    def _telephone(cls, v):
        return normaliser_telephone(v)


class Verification(AvecTelephone):
    jeton: str = Field(min_length=20, max_length=100)
    # À fournir seulement à la première connexion, quand l'API répond « inscription_requise ».
    pseudo: str | None = Field(default=None, min_length=2, max_length=40)
    zone: str | None = Field(default=None, max_length=80, examples=["Marseille"])
    # Facultatif : pour recevoir un SMS quand le Grand Troc vous propose un échange.
    telephone: str | None = Field(default=None, max_length=30, examples=["06 12 34 56 78"])
    # Facultatif : pour se connecter ensuite sans attendre d'e-mail.
    mot_de_passe: str | None = Field(default=None, min_length=8, max_length=200)


class DemandeInscription(BaseModel):
    """Inscription depuis la fenêtre du haut de page : vérifie e-mail et pseudo, puis envoie le code."""

    email: EmailStr
    pseudo: str = Field(min_length=2, max_length=40)
    langue: Literal["fr", "en", "es"] = "fr"


class VerificationCode(AvecTelephone):
    """Le code à 6 chiffres reçu par e-mail. Pseudo, ville et mot de passe : à la création du compte seulement."""

    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")
    pseudo: str | None = Field(default=None, min_length=2, max_length=40)
    zone: str | None = Field(default=None, max_length=80, examples=["Marseille"])
    telephone: str | None = Field(default=None, max_length=30, examples=["06 12 34 56 78"])
    mot_de_passe: str | None = Field(default=None, min_length=8, max_length=200)


class ConnexionMotDePasse(BaseModel):
    email: EmailStr
    mot_de_passe: str = Field(min_length=1, max_length=200)


class ChoixMotDePasse(BaseModel):
    mot_de_passe: str = Field(min_length=8, max_length=200)


class ZoneInteret(BaseModel):
    """Une zone où je veux troquer en main propre : « autour de moi » ou une ville, et un rayon."""

    libelle: str = Field(min_length=1, max_length=80, examples=["Marseille 6e"])
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    rayon_km: float = Field(default=10, ge=1, le=200)

    @field_validator("latitude", "longitude")
    @classmethod
    def _arrondi(cls, v: float) -> float:
        return arrondir(v)


def arrondir(coordonnee: float) -> float:
    """0,01° ≈ 1 km : on ne garde jamais une position précise (domicile)."""
    return round(coordonnee, 2)


class Moi(Lecture):
    id: int
    email: str
    pseudo: str
    zone: str | None
    telephone: str | None = None
    fiabilite: float
    echanges_menes: int
    reputation: str
    cree_le: datetime
    est_moderateur: bool = False
    a_un_mot_de_passe: bool = False
    zones_interet: list[ZoneInteret] = Field(default_factory=list)
    toute_la_france: bool = False
    verifie: bool = False
    # Troc Premium : la formule dont je profite (la mienne ou celle de ma famille), jusqu'à quand, ses avantages.
    formule: str | None = None
    premium_jusqu_au: datetime | None = None
    avantages: list[str] = Field(default_factory=list)
    essai_disponible: bool = False
    super_jaime_restants: int = 0
    zones_max: int = 1


class MoiModification(AvecTelephone):
    pseudo: str | None = Field(default=None, min_length=2, max_length=40)
    zone: str | None = Field(default=None, max_length=80)
    # null ou "" pour ne plus recevoir de SMS.
    telephone: str | None = Field(default=None, max_length=30)
    # Zones d'intérêt (une, trois avec Troc Premium) et « toute la France » (objets lointains, par colis).
    zones_interet: list[ZoneInteret] | None = Field(default=None, max_length=3)
    toute_la_france: bool | None = None


class ResultatConnexion(BaseModel):
    inscription_requise: bool = False
    email: str | None = None
    jeton: str | None = None  # jeton de session, à envoyer dans l'en-tête Authorization: Bearer …
    utilisateur: Moi | None = None


class UtilisateurLecture(Lecture):
    id: int
    pseudo: str
    zone: str | None
    fiabilite: float
    # Échanges menés au bout et réputation (nouveau, membre, fiable, a_confirmer) : voir ``Utilisateur.reputation``.
    echanges_menes: int
    reputation: str
    cree_le: datetime


# --- Objets et souhaits ---


def _photo_cloudinary(url: str) -> str:
    """N'accepte que des photos envoyées sur notre compte Cloudinary : pas d'image hébergée n'importe où."""
    cloudinary = get_settings().cloudinary
    prefixe = f"https://res.cloudinary.com/{cloudinary[0]}/image/upload/" if cloudinary else None
    if prefixe is None or not url.startswith(prefixe):
        raise ValueError("La photo doit être envoyée depuis le site TopTroc.")
    return url


# Vinted (vinted.fr, vinted.be…) ou Leboncoin. Rien n'est téléchargé depuis ces sites : leurs conditions
# d'utilisation interdisent la récupération automatique. Le lien est seulement gardé comme référence.
_SITES_ORIGINE = re.compile(r"^(www\.)?(vinted\.[a-z]{2,3}(\.[a-z]{2})?|leboncoin\.fr)$")


def _annonce_origine(url: str | None) -> str | None:
    """Garde un lien d'annonce Vinted ou Leboncoin, sans les paramètres de suivi."""
    if url is None or not url.strip():
        return None
    morceaux = urlsplit(url.strip())
    hote = (morceaux.hostname or "").lower()
    if morceaux.scheme not in ("http", "https") or not _SITES_ORIGINE.match(hote) or morceaux.path in ("", "/"):
        raise ValueError("Collez le lien d'une annonce Vinted ou Leboncoin.")
    return f"https://{hote}{morceaux.path}"


Caracteristiques = Annotated[dict[str, str], Field(default_factory=dict, max_length=12)]


def _modes_echange(modes: list[str] | None) -> list[str] | None:
    """Modes acceptés par une demande : tous cochés = aucun précisé, la liste vide les accepte tous (colis compris :
    recevoir un colis ne coûte rien au receveur)."""
    if modes is None:
        return None
    inconnus = set(modes) - set(nomenclature.MODES_ECHANGE)
    if inconnus:
        raise ValueError(f"Mode d'échange inconnu : {', '.join(sorted(inconnus))}.")
    propres = sorted(set(modes))
    return [] if len(propres) == len(nomenclature.MODES_ECHANGE) else propres


def _modes_objet(modes: list[str] | None) -> list[str] | None:
    """Modes possibles pour un objet : la liste vide vaut les modes par défaut (main propre, point de dépôt) ;
    le colis, payé par l'expéditeur, doit être coché."""
    if not modes:
        return modes
    propres = _modes_echange(modes) or sorted(nomenclature.MODES_ECHANGE)
    return [] if set(propres) == set(nomenclature.MODES_PAR_DEFAUT) else propres


class Localisation(BaseModel):
    """La localisation d'un objet (« Ajouter une localisation ») et son format d'envoi, s'il peut partir en colis."""

    lieu: str | None = Field(default=None, max_length=120, examples=["Marseille 6e"])
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    format_colis: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def _localisation(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Une localisation a une latitude et une longitude.")
        if self.latitude is not None:
            self.latitude, self.longitude = arrondir(self.latitude), arrondir(self.longitude)
        if self.format_colis is not None and self.format_colis not in nomenclature.FORMATS_COLIS:
            raise ValueError(f"Format de colis inconnu : {self.format_colis}.")
        modes = getattr(self, "modes_echange", None) or []
        if "colis" in modes and nomenclature.FORMATS_COLIS.get(self.format_colis or "", ("", None))[1] is None:
            raise ValueError("Pour un envoi par colis, indiquez un format de colis (30 kg au plus).")
        return self


ModesEchange = Annotated[list[str], Field(default_factory=list, max_length=len(nomenclature.MODES_ECHANGE))]


class ObjetCreation(Localisation):
    categorie_slug: str
    sous_categorie_slug: str | None = Field(default=None, max_length=50)
    caracteristiques: Caracteristiques
    titre: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    etat: EtatObjet
    photo_url: str = Field(max_length=500)
    photo_id: str | None = Field(default=None, max_length=200)
    annonce_origine: str | None = Field(default=None, max_length=500)
    # « Je le donne contre… » : des souhaits du propriétaire ; vide = contre n'importe lequel de ses souhaits.
    contre_souhait_ids: list[int] = Field(default_factory=list, max_length=50)
    contre_strict: bool = False
    modes_echange: ModesEchange

    _photo = field_validator("photo_url")(_photo_cloudinary)
    _modes = field_validator("modes_echange")(_modes_objet)
    _origine = field_validator("annonce_origine")(_annonce_origine)

    @model_validator(mode="after")
    def detail(self):
        self.caracteristiques = nomenclature.verifier(
            self.categorie_slug, self.sous_categorie_slug, self.caracteristiques, demande=False
        )
        return self


class ObjetModification(Localisation):
    titre: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    etat: EtatObjet | None = None
    # Seuls ces deux statuts se changent à la main ; les autres suivent les échanges et la modération.
    statut: StatutObjet | None = None
    contre_souhait_ids: list[int] | None = Field(default=None, max_length=50)
    contre_strict: bool | None = None
    # Vérifiés avec la catégorie de l'objet, dans la route.
    sous_categorie_slug: str | None = Field(default=None, max_length=50)
    caracteristiques: dict[str, str] | None = Field(default=None, max_length=12)
    modes_echange: list[str] | None = Field(default=None, max_length=len(nomenclature.MODES_ECHANGE))

    _modes = field_validator("modes_echange")(_modes_objet)

    @model_validator(mode="after")
    def statut_manuel(self):
        if self.statut not in (None, StatutObjet.disponible, StatutObjet.retire):
            raise ValueError("Un objet ne peut être que remis « disponible » ou « retire » à la main.")
        return self


class ObjetLecture(Lecture):
    id: int
    proprietaire_id: int
    categorie_slug: str
    sous_categorie_slug: str | None
    caracteristiques: dict[str, str]
    titre: str
    description: str | None
    etat: EtatObjet | None
    photo_url: str | None
    statut: StatutObjet
    modes_echange: list[str]
    lieu: str | None = None
    format_colis: str | None = None
    cree_le: datetime


class MonObjet(ObjetLecture):
    """Mes objets : avec le lien de l'annonce d'origine et la liste « contre », que les autres ne voient pas."""

    annonce_origine: str | None
    contre_souhait_ids: list[int]
    contre_strict: bool
    latitude: float | None = None
    longitude: float | None = None


class Alternative(BaseModel):
    """Une autre catégorie (ou une de ses sous-catégories) acceptée par une demande flexible ou ouverte."""

    categorie_slug: str
    sous_categorie_slug: str | None = Field(default=None, max_length=50)


class SouhaitCreation(BaseModel):
    categorie_slug: str | None = None
    objet_id: int | None = None
    # « Je demande » en détail : sous-catégorie, critères obligatoires (``caracteristiques``) et préférentiels
    # (``preferences``), état minimum, et description libre de ce qui est cherché.
    sous_categorie_slug: str | None = Field(default=None, max_length=50)
    caracteristiques: Caracteristiques
    preferences: Caracteristiques
    precisions: str | None = Field(default=None, max_length=500)
    etat_min: EtatObjet | None = None
    # Recherche précise, flexible (avec des alternatives) ou ouverte (toutes les catégories d'intérêt).
    mode_recherche: ModeRecherche = ModeRecherche.flexible
    alternatives: list[Alternative] = Field(default_factory=list, max_length=20)
    # Logistique : modes d'échange acceptés (vide : tous) et autres zones acceptées que la sienne.
    modes_echange: ModesEchange
    zones: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(default_factory=list, max_length=10)
    rang: int = Field(default=1, ge=1)
    quantite: int = Field(default=1, ge=1)
    acceptation_auto: bool = False

    _modes = field_validator("modes_echange")(_modes_echange)

    @model_validator(mode="after")
    def categorie_ou_objet(self):
        if (self.categorie_slug is None) == (self.objet_id is None):
            raise ValueError("Un souhait porte soit sur une catégorie, soit sur un objet précis.")
        self.caracteristiques = nomenclature.verifier(
            self.categorie_slug, self.sous_categorie_slug, self.caracteristiques, demande=True
        )
        self.preferences = nomenclature.verifier(
            self.categorie_slug, self.sous_categorie_slug, self.preferences, demande=True
        )
        if set(self.caracteristiques) & set(self.preferences):
            raise ValueError("Un critère est soit obligatoire, soit préférentiel.")
        if self.categorie_slug is None and (self.alternatives or self.etat_min):
            raise ValueError("Un objet précis se demande sans alternative ni état minimum.")
        vues = set()
        for a in self.alternatives:
            if a.sous_categorie_slug is not None:
                nomenclature.verifier(a.categorie_slug, a.sous_categorie_slug, {}, demande=True)
            cle = (a.categorie_slug, a.sous_categorie_slug)
            if cle in vues or cle == (self.categorie_slug, self.sous_categorie_slug):
                raise ValueError("Une alternative est donnée deux fois.")
            vues.add(cle)
        self.zones = sorted({" ".join(z.split()) for z in self.zones if z.strip()})
        self.precisions = (self.precisions or "").strip() or None
        return self


class SouhaitLecture(Lecture):
    id: int
    utilisateur_id: int
    categorie_slug: str | None
    objet_id: int | None
    sous_categorie_slug: str | None
    caracteristiques: dict[str, str]
    preferences: dict[str, str]
    precisions: str | None
    etat_min: EtatObjet | None
    mode_recherche: ModeRecherche
    alternatives: list[Alternative]
    modes_echange: list[str]
    zones: list[str]
    rang: int
    quantite: int
    acceptation_auto: bool


class PhotoSignature(BaseModel):
    """De quoi envoyer une photo directement du navigateur à Cloudinary, sans passer par l'API."""

    url_envoi: str
    api_key: str
    timestamp: int
    folder: str
    signature: str


# --- Échanges ---


class ObjetResume(Lecture):
    id: int
    titre: str
    categorie_slug: str
    etat: EtatObjet | None
    photo_url: str | None


class EtapeBoucle(BaseModel):
    donneur_id: int
    donneur_pseudo: str
    receveur_id: int
    receveur_pseudo: str
    objet: ObjetResume
    acceptation_auto: bool


class BoucleProposee(BaseModel):
    """Une boucle calculée par le moteur, pas encore enregistrée."""

    longueur: int
    proba_reussite: float
    etapes: list[EtapeBoucle]


class EchangeCreation(BaseModel):
    """Enregistrer une boucle suggérée : les objets dans l'ordre de la boucle."""

    objets: list[int] = Field(min_length=2, max_length=3)


class TransfertLecture(BaseModel):
    id: int
    position: int
    donneur_id: int
    donneur_pseudo: str
    receveur_id: int
    receveur_pseudo: str
    objet: ObjetResume
    reponse: Reponse
    repondu_le: datetime | None
    depose_le: datetime | None
    # Visible seulement du donneur (pour marquer le paquet) et du receveur (pour le récupérer).
    code_retrait: str | None = None
    # Main propre, colis (payé par le donneur) ou point de dépôt ; pour un colis, le suivi et la garantie.
    mode: str = "main_propre"
    transporteur: str | None = None
    numero_suivi: str | None = None
    garantie: bool = False
    # Où envoyer le colis : visible du receveur qui l'a donnée et de son donneur seulement.
    adresse_livraison: str | None = None


class EchangeLecture(BaseModel):
    id: int
    statut: StatutEchange
    proba_reussite: float
    cree_le: datetime
    expire_le: datetime
    # Le dimanche du Grand Troc qui a trouvé cette boucle (vide pour une boucle choisie à la demande).
    grand_troc_jour: date | None = None
    # Accord 1 à 1 conclu après un match.
    par_match: bool = False
    point_de_depot: str | None = None
    # Lieu public conseillé pour les remises en main propre (réglage LIEUX_DE_RENCONTRE).
    lieu_de_rencontre: str | None = None
    # Boucle du Grand Troc vue en avant-première (Troc Premium), avant l'annonce de 18 h.
    avant_premiere: bool = False
    transferts: list[TransfertLecture]


# --- Le Match ---


class Membre(Lecture):
    id: int
    pseudo: str
    zone: str | None
    fiabilite: float
    echanges_menes: int
    reputation: str
    verifie: bool = False


class CarteMatch(BaseModel):
    """Un objet du carrousel, avec ce qui le rend prometteur."""

    objet: ObjetLecture
    proprietaire: Membre
    # Le souhait auquel il répond : une catégorie, ou None pour un objet précis ou une simple réciprocité.
    souhait_categorie: str | None
    souhait_sous_categorie: str | None = None
    correspond_a_mes_souhaits: bool
    # Sa description libre (« Je demande ») des souhaits auxquels mes objets répondent.
    sa_demande: str | None = None
    # Mes objets que son propriétaire aime déjà : « J'aime » fait un match tout de suite.
    il_aime: list[ObjetResume]
    # Mes objets qui répondent à ses souhaits.
    il_cherche: list[ObjetResume]
    # Distance depuis ma zone d'intérêt la plus proche, et s'il faudrait passer par un colis.
    distance_km: float | None = None
    par_colis: bool = False


class AvisCreation(BaseModel):
    objet_id: int
    aime: bool
    # « Super J'aime » (Troc Premium, quota par semaine) : le propriétaire est prévenu.
    super_jaime: bool = False


class Interesse(BaseModel):
    membre: Membre
    depuis: datetime
    super_jaime: bool
    en_tete: bool
    ses_objets: list[ObjetResume]


class ListeInteresses(BaseModel):
    """Qui aime mon objet : la ShortList d'un objet convoité, ou tous les intéressés avec Troc Premium."""

    nb_jaime: int
    convoite: bool
    interesses: list[Interesse]


class MatchLecture(BaseModel):
    avec: Membre
    ses_objets: list[ObjetResume]
    mes_objets: list[ObjetResume]
    depuis: datetime
    # L'accord 1 à 1 en cours entre vous deux, s'il y en a un.
    echange_id: int | None


class ResultatAvis(BaseModel):
    match: MatchLecture | None


class AccordCreation(BaseModel):
    """Proposer l'accord d'un match : je donne ``mon_objet_id``, je reçois ``son_objet_id``."""

    mon_objet_id: int
    son_objet_id: int


class ReponseEchange(BaseModel):
    accepte: bool


class Remise(BaseModel):
    """J'ai remis ou envoyé mon objet ; pour un colis, le transporteur et le numéro de suivi."""

    transporteur: str | None = Field(default=None, max_length=40)
    numero_suivi: str | None = Field(default=None, max_length=60)


class AdresseLivraison(BaseModel):
    adresse: str = Field(min_length=5, max_length=300)


# --- Troc Premium ---


class FormuleLecture(BaseModel):
    cle: str
    nom: str
    prix_mois: float | None
    prix_an: float | None
    prix_unique: float | None
    avantages: list[str]
    super_jaime_par_semaine: int
    # Liens de paiement Stripe : « mois », « an » ou « pass » (vides tant que le paiement n'est pas configuré).
    liens: dict[str, str]


class FormatColis(BaseModel):
    cle: str
    libelle: str
    poids_max_kg: int | None


class CataloguePremium(BaseModel):
    formules: list[FormuleLecture]
    formats_colis: list[FormatColis]
    jours_essai: int
    portail: str | None
    # Encart publicitaire, montré seulement à qui n'a pas « sans publicité ».
    publicite_texte: str | None
    publicite_lien: str | None


class PremiumModeration(BaseModel):
    """La modération ouvre ou ferme une formule (geste commercial, partenaire, remboursement)."""

    formule: Literal["essentiel", "plus", "famille", "pro", "pass"] | None
    jusqu_au: datetime | None = None


class VerificationModeration(BaseModel):
    verifie: bool


class MembreFamille(BaseModel):
    email: EmailStr


class GrandTrocLecture(Lecture):
    jour: date
    cree_le: datetime
    nb_boucles: int
    nb_objets: int
    nb_participants: int
    optimal: bool
    duree_s: float
    repeche_le: datetime | None
    nb_objets_repeches: int
    nb_objets_remplaces: int


class InfosGrandTroc(BaseModel):
    """Le rendez-vous du dimanche : quand a lieu le prochain, ce qu'a donné le dernier."""

    prochain: datetime
    dernier: GrandTrocLecture | None
    # Vrai si l'on peut aussi proposer une boucle tout de suite (POST /echanges), sans attendre dimanche.
    echanges_a_la_demande: bool


class ResultatGrandTroc(BaseModel):
    lance: bool
    message: str
    grand_troc: GrandTrocLecture | None
    echanges: list[EchangeLecture]


class ResultatTaches(BaseModel):
    rappels_envoyes: int
    echanges_expires: int
    # Remplaçants après un refus, pendant les 48 h de réponse : None s'il n'y avait rien à chercher.
    objets_remplaces: int | None = None
    # Repêchage du mardi 18 h : None s'il n'a pas eu lieu à cet appel.
    objets_repeches: int | None = None
    # Mode visiteur : alertes envoyées aux visiteurs qui suivent leurs recherches et leurs favoris.
    alertes_visiteurs: int | None = None


# --- Signalements et modération ---


class SignalementCreation(BaseModel):
    objet_id: int | None = None
    utilisateur_id: int | None = None
    motif: MotifSignalement
    explication: str = Field(min_length=10, max_length=2000)
    # Obligatoire sans compte : pour vous informer de la décision.
    email_contact: EmailStr | None = None

    @model_validator(mode="after")
    def une_cible(self):
        if (self.objet_id is None) == (self.utilisateur_id is None):
            raise ValueError("Un signalement porte soit sur un objet, soit sur un compte.")
        return self


class SignalementRecu(Lecture):
    id: int
    statut: StatutSignalement
    cree_le: datetime


class UtilisateurResume(Lecture):
    id: int
    pseudo: str
    suspendu_le: datetime | None


class SignalementLecture(Lecture):
    id: int
    cree_le: datetime
    motif: MotifSignalement
    explication: str
    statut: StatutSignalement
    objet: ObjetLecture | None
    utilisateur_vise: UtilisateurResume | None
    auteur: UtilisateurResume | None
    email_contact: str | None
    decision: str | None
    traite_le: datetime | None


class Decision(BaseModel):
    retenir: bool
    # Signalement retenu : l'objet visé est retiré ; avec ce choix, le compte concerné est aussi suspendu.
    suspendre_compte: bool = False
    motivation: str = Field(min_length=10, max_length=2000)


# --- Mode visiteur : favoris et suivi sans compte ---


class FavoriCreation(BaseModel):
    objet_id: int


class RechercheSuivie(BaseModel):
    q: str = Field(default="", max_length=100)
    categorie: str | None = Field(default=None, max_length=50)


class FavoriSuivi(BaseModel):
    objet_id: int
    ajoute_le: datetime


class ListesSuivies(BaseModel):
    """Ce que le navigateur du visiteur garde : ses dernières recherches et ses favoris (24 h)."""

    recherches: list[RechercheSuivie] = Field(default_factory=list, max_length=10)
    favoris: list[FavoriSuivi] = Field(default_factory=list, max_length=50)


class DemandeSuivi(AvecTelephone, ListesSuivies):
    """E-mail ou téléphone (l'un des deux suffit) pour être prévenu sans créer de compte."""

    email: EmailStr | None = None
    telephone: str | None = Field(default=None, max_length=30, examples=["06 12 34 56 78"])

    @model_validator(mode="after")
    def _un_contact(self):
        if not self.email and not self.telephone:
            raise ValueError("Indiquez un e-mail ou un numéro de téléphone.")
        return self


class SuiviLecture(ListesSuivies):
    email: str | None
    telephone: str | None
    confirme_le: datetime | None


class MessageAssistant(BaseModel):
    role: Literal["user", "assistant"]
    contenu: str = Field(min_length=1, max_length=1000)


class QuestionAssistant(BaseModel):
    """La conversation telle que la bulle la garde (rien n'est stocké côté serveur)."""

    messages: list[MessageAssistant] = Field(min_length=1, max_length=20)
    langue: Literal["fr", "en", "es"] = "fr"
    page: str = Field(default="/", max_length=120)

    @model_validator(mode="after")
    def alternance(self):
        if self.messages[0].role != "user" or self.messages[-1].role != "user":
            raise ValueError("La conversation commence et se termine par une question.")
        return self


class ReponseAssistant(BaseModel):
    reponse: str


class EtatAssistant(BaseModel):
    actif: bool
