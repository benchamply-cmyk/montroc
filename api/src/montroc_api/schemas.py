"""Formats d'entrée et de sortie de l'API (validation Pydantic)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from .models import Reponse, StatutEchange, StatutObjet


class Lecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CategorieCreation(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=50, examples=["siege-auto"])
    libelle: str = Field(min_length=1, max_length=100, examples=["Siège auto"])


class CategorieLecture(CategorieCreation, Lecture):
    pass


class UtilisateurCreation(BaseModel):
    email: EmailStr
    pseudo: str = Field(min_length=2, max_length=40)
    zone: str | None = Field(default=None, max_length=80, examples=["Lyon"])


class UtilisateurLecture(Lecture):
    id: int
    pseudo: str
    zone: str | None
    fiabilite: float
    cree_le: datetime


class ObjetCreation(BaseModel):
    categorie_slug: str
    titre: str = Field(min_length=1, max_length=120)
    description: str | None = None


class ObjetModification(BaseModel):
    titre: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    # Seuls ces deux statuts se changent à la main ; les autres suivent les échanges.
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
    statut: StatutObjet
    cree_le: datetime


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


class EtapeBoucle(BaseModel):
    donneur_id: int
    receveur_id: int
    objet_id: int
    objet_titre: str
    acceptation_auto: bool


class BoucleProposee(BaseModel):
    """Une boucle calculée par le moteur, pas encore enregistrée."""

    longueur: int
    proba_reussite: float
    etapes: list[EtapeBoucle]


class EchangeCreation(BaseModel):
    """Enregistrer une boucle suggérée : les objets dans l'ordre de la boucle."""

    objets: list[int] = Field(min_length=2, max_length=3)


class TransfertLecture(Lecture):
    id: int
    position: int
    donneur_id: int
    receveur_id: int
    objet_id: int
    reponse: Reponse
    repondu_le: datetime | None


class EchangeLecture(Lecture):
    id: int
    statut: StatutEchange
    proba_reussite: float
    cree_le: datetime
    expire_le: datetime
    transferts: list[TransfertLecture]


class ReponseTransfert(BaseModel):
    # Provisoire : sera remplacé par l'utilisateur connecté (branche feature/authentification).
    utilisateur_id: int
    accepte: bool


class ResultatMathTrade(BaseModel):
    optimal: bool
    duree_s: float
    nb_objets_echanges: int
    echanges: list[EchangeLecture]
