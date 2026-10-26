"""Troc Premium : le catalogue des formules, l'essai gratuit, la famille, le paiement Stripe et la modération."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import func, select

from .. import models as m
from .. import nomenclature, premium
from ..config import get_settings
from ..deps import Moderateur, SessionDep, UtilisateurConnecte, obtenir_ou_404
from ..schemas import (
    CataloguePremium,
    FormatColis,
    FormuleLecture,
    MembreFamille,
    Moi,
    PremiumModeration,
    UtilisateurResume,
    VerificationModeration,
)
from .auth import moi

router = APIRouter(tags=["troc premium"])
journal = logging.getLogger("montroc.premium")


def _liens(cle: str) -> dict[str, str]:
    liens = get_settings().liens_stripe
    if cle == "pass":
        return {"pass": liens["pass"]} if "pass" in liens else {}
    return {periode: liens[f"{cle}_{periode}"] for periode in ("mois", "an") if f"{cle}_{periode}" in liens}


@router.get("/premium", response_model=CataloguePremium)
def catalogue():
    """Les formules, leurs prix et avantages, les formats de colis, et l'encart publicitaire du moment."""
    reglages = get_settings()
    texte, _, lien = reglages.encart_publicite.partition("|")
    return CataloguePremium(
        formules=[
            FormuleLecture(
                cle=f.cle,
                nom=f.nom,
                prix_mois=f.prix_mois,
                prix_an=f.prix_an,
                prix_unique=f.prix_unique,
                avantages=sorted(f.avantages),
                super_jaime_par_semaine=f.super_jaime_par_semaine,
                liens=_liens(f.cle),
            )
            for f in premium.FORMULES.values()
        ],
        formats_colis=[
            FormatColis(cle=cle, libelle=libelle, poids_max_kg=poids)
            for cle, (libelle, poids) in nomenclature.FORMATS_COLIS.items()
        ],
        jours_essai=reglages.jours_essai_premium,
        portail=reglages.stripe_portail or None,
        publicite_texte=texte.strip() or None,
        publicite_lien=lien.strip() if lien.strip().startswith("https://") else None,
    )


@router.post("/premium/essai", response_model=Moi)
def essai(utilisateur: UtilisateurConnecte, session: SessionDep):
    """Un mois de Premium Plus offert, une fois par compte."""
    try:
        premium.commencer_essai(utilisateur)
    except ValueError as e:
        raise HTTPException(409, str(e)) from None
    session.commit()
    return moi(utilisateur)


@router.get("/premium/famille", response_model=list[UtilisateurResume])
def famille(utilisateur: UtilisateurConnecte, session: SessionDep):
    return session.scalars(select(m.Utilisateur).where(m.Utilisateur.payeur_famille_id == utilisateur.id)).all()


@router.post("/premium/famille", response_model=list[UtilisateurResume], status_code=201)
def ajouter_a_la_famille(donnees: MembreFamille, utilisateur: UtilisateurConnecte, session: SessionDep):
    """Formule Famille : trois autres comptes TrocTroc profitent des mêmes avantages."""
    if utilisateur.formule != "famille" or premium.formule_active(utilisateur) is None:
        raise HTTPException(409, "Ajouter des proches demande la formule Famille.")
    membre = session.scalars(
        select(m.Utilisateur).where(func.lower(m.Utilisateur.email) == donnees.email.lower())
    ).first()
    if membre is None:
        raise HTTPException(404, "Aucun compte TrocTroc avec cet e-mail : invitez d'abord cette personne.")
    if membre.id == utilisateur.id or membre.payeur_famille_id not in (None, utilisateur.id):
        raise HTTPException(409, "Ce compte ne peut pas rejoindre votre famille.")
    deja = famille(utilisateur, session)
    if membre not in deja and len(deja) >= premium.MEMBRES_FAMILLE:
        raise HTTPException(409, f"La formule Famille couvre {premium.MEMBRES_FAMILLE} proches au plus.")
    membre.payeur_famille_id = utilisateur.id
    session.commit()
    return famille(utilisateur, session)


@router.delete("/premium/famille/{membre_id}", status_code=204)
def retirer_de_la_famille(membre_id: int, utilisateur: UtilisateurConnecte, session: SessionDep):
    """Le payeur retire un proche, ou un proche quitte la famille."""
    membre = obtenir_ou_404(session, m.Utilisateur, membre_id)
    if membre.payeur_famille_id is None or utilisateur.id not in (membre.id, membre.payeur_famille_id):
        raise HTTPException(404, f"Utilisateur {membre_id} introuvable.")
    membre.payeur_famille_id = None
    session.commit()


@router.post("/premium/stripe", status_code=200)
async def webhook_stripe(request: Request, session: SessionDep, stripe_signature: str = Header("")):
    """Appelé par Stripe après un paiement (ouverture) ou un renouvellement (prolongation)."""
    corps = await request.body()
    try:
        evenement = premium.verifier_signature(corps, stripe_signature, get_settings().stripe_webhook_secret)
        resultat = premium.traiter_evenement(session, evenement)
    except premium.SignatureInvalide as e:
        raise HTTPException(400, str(e)) from None
    except ValueError as e:
        journal.error("Paiement Stripe non appliqué : %s", e)
        raise HTTPException(400, str(e)) from None
    session.commit()
    journal.info("Stripe : %s", resultat)
    return {"resultat": resultat}


@router.put("/moderation/utilisateurs/{utilisateur_id}/premium", response_model=UtilisateurResume)
def fixer_premium(utilisateur_id: int, donnees: PremiumModeration, _moderateur: Moderateur, session: SessionDep):
    utilisateur = obtenir_ou_404(session, m.Utilisateur, utilisateur_id)
    if donnees.formule is not None and (donnees.jusqu_au is None or donnees.jusqu_au <= datetime.now(UTC)):
        raise HTTPException(422, "Indiquez une date de fin à venir.")
    utilisateur.formule = donnees.formule
    utilisateur.premium_jusqu_au = donnees.jusqu_au if donnees.formule else None
    session.commit()
    return utilisateur


@router.put("/moderation/utilisateurs/{utilisateur_id}/verification", response_model=UtilisateurResume)
def verifier(utilisateur_id: int, donnees: VerificationModeration, _moderateur: Moderateur, session: SessionDep):
    """Badge « profil vérifié » (pièce d'identité ou téléphone confirmé par la modération)."""
    utilisateur = obtenir_ou_404(session, m.Utilisateur, utilisateur_id)
    if not donnees.verifie:
        utilisateur.verifie_le = None
    elif utilisateur.verifie_le is None:
        utilisateur.verifie_le = datetime.now(UTC)
    session.commit()
    return utilisateur
