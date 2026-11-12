"""Espaces réservés : l'offre « Espace salariés » (et « Résidences ») des entreprises et des bailleurs.

La modération crée l'espace d'un client (nom, domaines d'e-mail, lieu de remise). Un membre dont l'adresse
e-mail, déjà vérifiée à l'inscription, est sur un de ces domaines le rejoint d'un clic depuis le lien
/#espace=<slug> ; il peut alors réserver ses objets à ses collègues. Ces objets ne sont visibles que des
membres de l'espace (catalogue, Match, Grand Troc) et se remettent sur place, au lieu de remise de l'espace.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from .. import models as m
from ..deps import Moderateur, SessionDep, UtilisateurConnecte
from ..schemas import EspaceEcriture, EspaceLecture, EspaceResume, Moi
from .auth import moi

router = APIRouter(tags=["espaces réservés"])


def _domaine(email: str) -> str:
    return email.rsplit("@", 1)[-1].strip().lower()


def _espace(session, slug: str) -> m.Espace:
    espace = session.scalar(select(m.Espace).where(m.Espace.slug == slug, m.Espace.actif))
    if espace is None:
        raise HTTPException(404, "Cet espace n'existe pas ou n'est plus ouvert.")
    return espace


def _lecture(session, espace: m.Espace) -> EspaceLecture:
    membres = session.scalar(select(func.count()).where(m.Utilisateur.espace_id == espace.id))
    objets = session.scalar(
        select(func.count()).where(m.Objet.espace_id == espace.id, m.Objet.statut == m.StatutObjet.disponible)
    )
    return EspaceLecture.model_validate(espace).model_copy(update={"membres": membres, "objets_en_ligne": objets})


@router.get("/espaces/{slug}", response_model=EspaceResume)
def lire(slug: str, session: SessionDep):
    """Nom et lieu de remise d'un espace ouvert, pour la page d'accueil de son lien d'invitation."""
    return _espace(session, slug)


@router.post("/espaces/{slug}/rejoindre", response_model=Moi)
def rejoindre(slug: str, utilisateur: UtilisateurConnecte, session: SessionDep):
    espace = _espace(session, slug)
    if _domaine(utilisateur.email) not in espace.domaines:
        raise HTTPException(403, f"Cet espace est réservé aux adresses {', '.join('@' + d for d in espace.domaines)}.")
    utilisateur.espace_id = espace.id
    session.commit()
    session.refresh(utilisateur)
    return moi(utilisateur)


@router.delete("/moi/espace", response_model=Moi)
def quitter(utilisateur: UtilisateurConnecte, session: SessionDep):
    """Je quitte mon espace : mes objets réservés redeviennent ouverts à tous."""
    if utilisateur.espace_id is not None:
        for objet in session.scalars(
            select(m.Objet).where(m.Objet.proprietaire_id == utilisateur.id, m.Objet.espace_id.is_not(None))
        ):
            objet.espace_id = None
        utilisateur.espace_id = None
        session.commit()
        session.refresh(utilisateur)
    return moi(utilisateur)


@router.get("/moderation/espaces", response_model=list[EspaceLecture])
def lister(_moderateur: Moderateur, session: SessionDep):
    return [_lecture(session, e) for e in session.scalars(select(m.Espace).order_by(m.Espace.nom))]


@router.post("/moderation/espaces", response_model=EspaceLecture, status_code=201)
def creer(donnees: EspaceEcriture, _moderateur: Moderateur, session: SessionDep):
    if session.scalar(select(m.Espace).where(m.Espace.slug == donnees.slug)):
        raise HTTPException(409, "Ce nom court est déjà pris.")
    espace = m.Espace(**donnees.model_dump())
    session.add(espace)
    session.commit()
    return _lecture(session, espace)


@router.put("/moderation/espaces/{espace_id}", response_model=EspaceLecture)
def modifier(espace_id: int, donnees: EspaceEcriture, _moderateur: Moderateur, session: SessionDep):
    espace = session.get(m.Espace, espace_id)
    if espace is None:
        raise HTTPException(404, "Espace introuvable.")
    for cle, valeur in donnees.model_dump().items():
        setattr(espace, cle, valeur)
    session.commit()
    return _lecture(session, espace)
