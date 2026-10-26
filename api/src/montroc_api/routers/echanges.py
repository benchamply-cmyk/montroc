"""Échanges : enregistrer une boucle, répondre, déposer."""

from fastapi import APIRouter, HTTPException

from .. import models as m
from .. import services, vues
from ..deps import SessionDep, UtilisateurConnecte, obtenir_ou_404
from ..schemas import AdresseLivraison, EchangeCreation, EchangeLecture, Remise, ReponseEchange

router = APIRouter(prefix="/echanges", tags=["échanges"])


def metier(fonction, session, *args):
    """Exécute une opération métier dans une transaction ; une règle non respectée devient un 409."""
    try:
        resultat = fonction(session, *args)
        session.commit()
        return resultat
    except services.ErreurMetier as e:
        session.commit()  # garde une éventuelle annulation (délai dépassé)
        raise HTTPException(409, str(e)) from e


def _mon_echange(session, echange_id: int, utilisateur: m.Utilisateur) -> m.Echange:
    echange = obtenir_ou_404(session, m.Echange, echange_id)
    if not any(utilisateur.id in (t.donneur_id, t.receveur_id) for t in echange.transferts):
        raise HTTPException(404, f"Echange {echange_id} introuvable.")
    if not services.visible_par(echange, utilisateur):  # avant-première, avant l'annonce de 18 h
        raise HTTPException(404, f"Echange {echange_id} introuvable.")
    return echange


@router.post("", response_model=EchangeLecture, status_code=201)
def creer(donnees: EchangeCreation, utilisateur: UtilisateurConnecte, session: SessionDep):
    """Je choisis une de mes boucles possibles : ma part est acceptée, les autres participants sont prévenus."""
    echange = metier(services.proposer_par_objets, session, donnees.objets, utilisateur.id)
    return vues.echange(echange, utilisateur.id)


@router.get("/{echange_id}", response_model=EchangeLecture)
def lire(echange_id: int, utilisateur: UtilisateurConnecte, session: SessionDep):
    return vues.echange(_mon_echange(session, echange_id, utilisateur), utilisateur.id)


@router.post("/{echange_id}/reponse", response_model=EchangeLecture)
def repondre(echange_id: int, donnees: ReponseEchange, utilisateur: UtilisateurConnecte, session: SessionDep):
    echange = _mon_echange(session, echange_id, utilisateur)
    metier(services.repondre, session, echange, utilisateur.id, donnees.accepte)
    return vues.echange(echange, utilisateur.id)


@router.post("/{echange_id}/depot", response_model=EchangeLecture)
def deposer(echange_id: int, utilisateur: UtilisateurConnecte, session: SessionDep, donnees: Remise | None = None):
    """J'ai remis mon objet en main propre, envoyé mon colis (avec son suivi) ou déposé mon objet."""
    echange = _mon_echange(session, echange_id, utilisateur)
    donnees = donnees or Remise()
    metier(services.deposer, session, echange, utilisateur.id, donnees.transporteur, donnees.numero_suivi)
    return vues.echange(echange, utilisateur.id)


@router.post("/{echange_id}/adresse", response_model=EchangeLecture)
def adresse(echange_id: int, donnees: AdresseLivraison, utilisateur: UtilisateurConnecte, session: SessionDep):
    """Où je veux recevoir le colis (adresse ou point relais) : seul celui qui me l'envoie la voit."""
    echange = _mon_echange(session, echange_id, utilisateur)
    metier(services.indiquer_adresse, session, echange, utilisateur.id, donnees.adresse.strip())
    return vues.echange(echange, utilisateur.id)
