"""Formats d'entrée et de sortie de l'API (validation Pydantic)."""

import re
from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .config import get_settings
from .models import EtatObjet, MotifSignalement, Reponse, StatutEchange, StatutObjet, StatutSignalement


class Lecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CategorieCreation(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=50, examples=["siege-auto"])
    libelle: str = Field(min_length=1, max_length=100, examples=["Siège auto"])


class CategorieLecture(CategorieCreation, Lecture):
    pass


# --- Connexion par lien magique ---


class DemandeLien(BaseModel):
    email: EmailStr


class Verification(BaseModel):
    jeton: str = Field(min_length=20, max_length=100)
    # À fournir seulement à la première connexion, quand l'API répond « inscription_requise ».
    pseudo: str | None = Field(default=None, min_length=2, max_length=40)
    zone: str | None = Field(default=None, max_length=80, examples=["Marseille"])


class Moi(Lecture):
    id: int
    email: str
    pseudo: str
    zone: str | None
    fiabilite: float
    cree_le: datetime
    est_moderateur: bool = False


class MoiModification(BaseModel):
    pseudo: str | None = Field(default=None, min_length=2, max_length=40)
    zone: str | None = Field(default=None, max_length=80)


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


class ObjetCreation(BaseModel):
    categorie_slug: str
    titre: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    etat: EtatObjet
    photo_url: str = Field(max_length=500)
    photo_id: str | None = Field(default=None, max_length=200)
    annonce_origine: str | None = Field(default=None, max_length=500)

    _photo = field_validator("photo_url")(_photo_cloudinary)
    _origine = field_validator("annonce_origine")(_annonce_origine)


class ObjetModification(BaseModel):
    titre: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    etat: EtatObjet | None = None
    # Seuls ces deux statuts se changent à la main ; les autres suivent les échanges et la modération.
    statut: StatutObjet | None = None

    @model_validator(mode="after")
    def statut_manuel(self):
        if self.statut not in (None, StatutObjet.disponible, StatutObjet.retire):
            raise ValueError("Un objet ne peut être que remis « disponible » ou « retire » à la main.")
        return self


class ObjetLecture(Lecture):
    id: int
    proprietaire_id: int
    categorie_slug: str
    titre: str
    description: str | None
    etat: EtatObjet | None
    photo_url: str | None
    statut: StatutObjet
    cree_le: datetime


class MonObjet(ObjetLecture):
    """Mes objets : avec le lien de l'annonce d'origine, que les autres ne voient pas."""

    annonce_origine: str | None


class SouhaitCreation(BaseModel):
    categorie_slug: str | None = None
    objet_id: int | None = None
    rang: int = Field(default=1, ge=1)
    quantite: int = Field(default=1, ge=1)
    acceptation_auto: bool = False

    @model_validator(mode="after")
    def categorie_ou_objet(self):
        if (self.categorie_slug is None) == (self.objet_id is None):
            raise ValueError("Un souhait porte soit sur une catégorie, soit sur un objet précis.")
        return self


class SouhaitLecture(Lecture):
    id: int
    utilisateur_id: int
    categorie_slug: str | None
    objet_id: int | None
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
    point_de_depot: str | None = None
    transferts: list[TransfertLecture]


class ReponseEchange(BaseModel):
    accepte: bool


class ResultatMathTrade(BaseModel):
    optimal: bool
    duree_s: float
    nb_objets_echanges: int
    echanges: list[EchangeLecture]


class ResultatTaches(BaseModel):
    rappels_envoyes: int
    echanges_expires: int


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
