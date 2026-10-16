"""Formats d'entrée et de sortie de l'API (validation Pydantic)."""

import re
from datetime import date, datetime
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from . import nomenclature
from .config import get_settings
from .models import EtatObjet, MotifSignalement, Reponse, StatutEchange, StatutObjet, StatutSignalement


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


class ConnexionMotDePasse(BaseModel):
    email: EmailStr
    mot_de_passe: str = Field(min_length=1, max_length=200)


class ChoixMotDePasse(BaseModel):
    mot_de_passe: str = Field(min_length=8, max_length=200)


class Moi(Lecture):
    id: int
    email: str
    pseudo: str
    zone: str | None
    telephone: str | None = None
    fiabilite: float
    cree_le: datetime
    est_moderateur: bool = False
    a_un_mot_de_passe: bool = False


class MoiModification(AvecTelephone):
    pseudo: str | None = Field(default=None, min_length=2, max_length=40)
    zone: str | None = Field(default=None, max_length=80)
    # null ou "" pour ne plus recevoir de SMS.
    telephone: str | None = Field(default=None, max_length=30)


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
    cree_le: datetime


# --- Objets et souhaits ---


def _photo_cloudinary(url: str) -> str:
    """N'accepte que des photos envoyées sur notre compte Cloudinary : pas d'image hébergée n'importe où."""
    cloudinary = get_settings().cloudinary
    prefixe = f"https://res.cloudinary.com/{cloudinary[0]}/image/upload/" if cloudinary else None
    if prefixe is None or not url.startswith(prefixe):
        raise ValueError("La photo doit être envoyée depuis le site TrocTroc.")
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


class ObjetCreation(BaseModel):
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

    _photo = field_validator("photo_url")(_photo_cloudinary)
    _origine = field_validator("annonce_origine")(_annonce_origine)

    @model_validator(mode="after")
    def detail(self):
        self.caracteristiques = nomenclature.verifier(
            self.categorie_slug, self.sous_categorie_slug, self.caracteristiques, demande=False
        )
        return self


class ObjetModification(BaseModel):
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
    cree_le: datetime


class MonObjet(ObjetLecture):
    """Mes objets : avec le lien de l'annonce d'origine et la liste « contre », que les autres ne voient pas."""

    annonce_origine: str | None
    contre_souhait_ids: list[int]
    contre_strict: bool


class SouhaitCreation(BaseModel):
    categorie_slug: str | None = None
    objet_id: int | None = None
    # « Je demande » en détail : sous-catégorie, caractéristiques à choix fixes (elles filtrent les objets
    # proposés) et description libre de ce qui est cherché.
    sous_categorie_slug: str | None = Field(default=None, max_length=50)
    caracteristiques: Caracteristiques
    precisions: str | None = Field(default=None, max_length=500)
    rang: int = Field(default=1, ge=1)
    quantite: int = Field(default=1, ge=1)
    acceptation_auto: bool = False

    @model_validator(mode="after")
    def categorie_ou_objet(self):
        if (self.categorie_slug is None) == (self.objet_id is None):
            raise ValueError("Un souhait porte soit sur une catégorie, soit sur un objet précis.")
        self.caracteristiques = nomenclature.verifier(
            self.categorie_slug, self.sous_categorie_slug, self.caracteristiques, demande=True
        )
        self.precisions = (self.precisions or "").strip() or None
        return self


class SouhaitLecture(Lecture):
    id: int
    utilisateur_id: int
    categorie_slug: str | None
    objet_id: int | None
    sous_categorie_slug: str | None
    caracteristiques: dict[str, str]
    precisions: str | None
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
    transferts: list[TransfertLecture]


# --- Le Match ---


class Membre(Lecture):
    id: int
    pseudo: str
    zone: str | None
    fiabilite: float


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


class AvisCreation(BaseModel):
    objet_id: int
    aime: bool


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
    # Repêchage du mardi 18 h : None s'il n'a pas eu lieu à cet appel.
    objets_repeches: int | None = None


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
