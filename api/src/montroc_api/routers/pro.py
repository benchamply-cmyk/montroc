"""TopTroc Pro : les secteurs ouverts, mon profil Pro et la vérification du SIRET par la modération.

Un compte Pro reste un compte TopTroc comme les autres (Match, Grand Troc, catégories des particuliers) ; son
secteur lui ouvre en plus la catégorie réservée aux professionnels de ce secteur (voir nomenclature.DETAIL_PRO).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .. import models as m
from .. import nomenclature
from ..deps import Moderateur, SessionDep, UtilisateurConnecte, obtenir_ou_404
from ..schemas import Moi, ProfilProCreation, SecteurProLecture, UtilisateurLecture
from .auth import moi

router = APIRouter(prefix="/pro", tags=["TopTroc Pro"])


@router.get("/secteurs", response_model=list[SecteurProLecture])
def secteurs():
    """Les secteurs ouverts à TopTroc Pro et la catégorie réservée à chacun."""
    return [
        SecteurProLecture(secteur=s, libelle=libelle, categorie_slug=nomenclature.CATEGORIE_DU_SECTEUR[s])
        for s, libelle in nomenclature.SECTEURS_PRO.items()
    ]


@router.put("/profil", response_model=Moi)
def enregistrer(donnees: ProfilProCreation, utilisateur: UtilisateurConnecte, session: SessionDep):
    """Crée ou modifie mon profil Pro. Un nouveau SIRET repasse par la vérification de la modération.

    Changer de secteur n'est possible qu'une fois retirés mes objets et demandes de l'ancienne catégorie Pro."""
    ancienne = nomenclature.CATEGORIE_DU_SECTEUR.get(utilisateur.pro_secteur)
    if utilisateur.pro_secteur not in (None, donnees.secteur) and _encore_actif(session, utilisateur, ancienne):
        raise HTTPException(409, "Retirer d'abord vos objets et demandes de votre catégorie Pro actuelle.")
    if donnees.siret != utilisateur.pro_siret:
        utilisateur.pro_verifie_le = None
    utilisateur.pro_secteur = donnees.secteur
    utilisateur.pro_raison_sociale = donnees.raison_sociale.strip()
    utilisateur.pro_siret = donnees.siret
    utilisateur.pro_metier = (donnees.metier or "").strip() or None
    session.commit()
    return moi(utilisateur)


@router.delete("/profil", response_model=Moi)
def quitter(utilisateur: UtilisateurConnecte, session: SessionDep):
    """Repasse en compte particulier. Mes objets et demandes de la catégorie Pro doivent être retirés avant."""
    if utilisateur.pro_secteur is None:
        return moi(utilisateur)
    if _encore_actif(session, utilisateur, nomenclature.CATEGORIE_DU_SECTEUR[utilisateur.pro_secteur]):
        raise HTTPException(409, "Retirer d'abord vos objets et demandes de votre catégorie Pro.")
    utilisateur.pro_secteur = utilisateur.pro_raison_sociale = utilisateur.pro_siret = None
    utilisateur.pro_metier = utilisateur.pro_verifie_le = None
    session.commit()
    return moi(utilisateur)


@router.post("/{utilisateur_id}/verification", response_model=UtilisateurLecture)
def verifier(utilisateur_id: int, _moderateur: Moderateur, session: SessionDep):
    """Modération : le SIRET correspond bien à l'entreprise (annuaire-entreprises.data.gouv.fr).

    Le membre reçoit le badge « Pro vérifié »."""
    membre = obtenir_ou_404(session, m.Utilisateur, utilisateur_id)
    if membre.pro_secteur is None:
        raise HTTPException(409, "Ce membre n'a pas de profil Pro.")
    membre.pro_verifie_le = datetime.now(UTC)
    session.commit()
    return membre


def _encore_actif(session, utilisateur: m.Utilisateur, categorie: str | None) -> bool:
    if categorie is None:
        return False
    objet = session.scalar(
        select(m.Objet.id).where(
            m.Objet.proprietaire_id == utilisateur.id,
            m.Objet.categorie_slug == categorie,
            m.Objet.statut.in_([m.StatutObjet.disponible, m.StatutObjet.reserve]),
        )
    )
    souhait = session.scalar(
        select(m.Souhait.id).where(m.Souhait.utilisateur_id == utilisateur.id, m.Souhait.categorie_slug == categorie)
    )
    return objet is not None or souhait is not None
