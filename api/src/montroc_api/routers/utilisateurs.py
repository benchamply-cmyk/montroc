"""Utilisateurs, leurs objets, leurs souhaits et leurs échanges possibles."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from .. import models as m
from .. import services
from ..deps import SessionDep, obtenir_ou_404
from ..schemas import (
    BoucleProposee,
    EtapeBoucle,
    ObjetCreation,
    ObjetLecture,
    SouhaitCreation,
    SouhaitLecture,
    UtilisateurCreation,
    UtilisateurLecture,
)

router = APIRouter(prefix="/utilisateurs", tags=["utilisateurs"])


@router.post("", response_model=UtilisateurLecture, status_code=201)
def creer(donnees: UtilisateurCreation, session: SessionDep):
    email = str(donnees.email)
    if session.scalar(select(m.Utilisateur.id).where(func.lower(m.Utilisateur.email) == email.lower())):
        raise HTTPException(409, "Un compte existe déjà avec cet e-mail.")
    if session.scalar(select(m.Utilisateur.id).where(m.Utilisateur.pseudo == donnees.pseudo)):
        raise HTTPException(409, "Ce pseudo est déjà pris.")
    utilisateur = m.Utilisateur(email=email, pseudo=donnees.pseudo, zone=donnees.zone)
    session.add(utilisateur)
    session.commit()
    return utilisateur


@router.get("/{utilisateur_id}", response_model=UtilisateurLecture)
def lire(utilisateur_id: int, session: SessionDep):
    return obtenir_ou_404(session, m.Utilisateur, utilisateur_id)


@router.delete("/{utilisateur_id}", status_code=204)
def supprimer(utilisateur_id: int, session: SessionDep):
    session.delete(obtenir_ou_404(session, m.Utilisateur, utilisateur_id))
    session.commit()


@router.post("/{utilisateur_id}/objets", response_model=ObjetLecture, status_code=201)
def ajouter_objet(utilisateur_id: int, donnees: ObjetCreation, session: SessionDep):
    obtenir_ou_404(session, m.Utilisateur, utilisateur_id)
    obtenir_ou_404(session, m.Categorie, donnees.categorie_slug)
    objet = m.Objet(proprietaire_id=utilisateur_id, **donnees.model_dump())
    session.add(objet)
    session.commit()
    return objet


@router.get("/{utilisateur_id}/objets", response_model=list[ObjetLecture])
def lister_objets(utilisateur_id: int, session: SessionDep):
    return obtenir_ou_404(session, m.Utilisateur, utilisateur_id).objets


@router.post("/{utilisateur_id}/souhaits", response_model=SouhaitLecture, status_code=201)
def ajouter_souhait(utilisateur_id: int, donnees: SouhaitCreation, session: SessionDep):
    obtenir_ou_404(session, m.Utilisateur, utilisateur_id)
    if donnees.categorie_slug is not None:
        obtenir_ou_404(session, m.Categorie, donnees.categorie_slug)
    if donnees.objet_id is not None:
        objet = obtenir_ou_404(session, m.Objet, donnees.objet_id)
        if objet.proprietaire_id == utilisateur_id:
            raise HTTPException(409, "On ne peut pas souhaiter son propre objet.")
    souhait = m.Souhait(utilisateur_id=utilisateur_id, **donnees.model_dump())
    session.add(souhait)
    session.commit()
    return souhait


@router.get("/{utilisateur_id}/souhaits", response_model=list[SouhaitLecture])
def lister_souhaits(utilisateur_id: int, session: SessionDep):
    return obtenir_ou_404(session, m.Utilisateur, utilisateur_id).souhaits


@router.get("/{utilisateur_id}/boucles", response_model=list[BoucleProposee])
def boucles_possibles(utilisateur_id: int, session: SessionDep, limite: int = Query(10, ge=1, le=50)):
    """« Mes échanges possibles » : boucles de 2 et 3 personnes, les plus sûres d'abord."""
    obtenir_ou_404(session, m.Utilisateur, utilisateur_id)
    return [
        BoucleProposee(
            longueur=b.longueur,
            proba_reussite=b.proba_reussite,
            etapes=[
                EtapeBoucle(
                    donneur_id=int(t.donneur),
                    receveur_id=int(t.receveur),
                    objet_id=int(t.objet.id),
                    objet_titre=t.objet.titre,
                    acceptation_auto=t.auto,
                )
                for t in b.transferts
            ],
        )
        for b in services.suggestions(session, utilisateur_id, limite)
    ]
