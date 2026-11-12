"""Offres Entreprises et Collectivités : demandes de devis et chiffres d'impact pour les partenaires.

Ce sont les deux premières sources de revenus de TopTroc (avec la commission sur les étiquettes de colis) :
les entreprises (CSE, RSE, bailleurs) et les collectivités (programme local de prévention des déchets) paient
un espace et des journées troc ; les membres, eux, troquent gratuitement.
"""

from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from .. import courriels, nomenclature
from .. import models as m
from ..config import get_settings
from ..deps import SessionDep, UtilisateurOptionnel, est_moderateur
from .objets import _dans_le_rayon

router = APIRouter(tags=["partenaires"])

# Formules présentées sur /pros/ et /collectivites/ : la demande de devis en reprend la clé.
FORMULES = {
    "journee": "Journée troc (entreprise)",
    "espace": "Espace salariés (entreprise)",
    "residences": "Résidences (bailleur)",
    "quartier": "Grand Troc de quartier (collectivité)",
    "territoire": "Territoire (collectivité)",
    "metropole": "Métropole (collectivité)",
    "autre": "Autre demande",
}


class DemandePartenaire(BaseModel):
    type: Literal["entreprise", "collectivite", "bailleur", "association"]
    formule: Literal["journee", "espace", "residences", "quartier", "territoire", "metropole", "autre"] = "autre"
    organisation: str = Field(min_length=2, max_length=120)
    nom: str = Field(min_length=2, max_length=80)
    email: EmailStr
    telephone: str | None = Field(default=None, max_length=30)
    taille: str | None = Field(default=None, max_length=60, description="Salariés, habitants ou logements.")
    message: str = Field(default="", max_length=2000)
    # Champ piège invisible : un robot le remplit, un humain non.
    site_web: str = Field(default="", max_length=200)


class Impact(BaseModel):
    """Chiffres d'impact d'une zone (ou de toute la France), pour les rapports aux partenaires."""

    depuis: datetime
    echanges_termines: int
    objets_reemployes: int
    membres_participants: int
    objets_en_ligne: int
    kg_evites_estimes: float
    co2_evite_kg_estime: float


@router.post("/partenaires/demande", status_code=202)
def demande_de_devis(demande: DemandePartenaire):
    """Une entreprise, une collectivité, un bailleur ou une association demande un devis.

    L'équipe reçoit la demande par e-mail ; le demandeur reçoit un accusé de réception."""
    if demande.site_web:
        return {"recu": True}  # robot : on ne dit rien
    contact = get_settings().contact_partenaires
    formule = FORMULES[demande.formule]
    courriels.envoyer(
        contact,
        f"Demande de devis : {demande.organisation} ({formule})",
        f"Type : {demande.type}\nFormule : {formule}\nOrganisation : {demande.organisation}\n"
        f"Contact : {demande.nom} <{demande.email}>{' · ' + demande.telephone if demande.telephone else ''}\n"
        f"Taille : {demande.taille or 'non précisée'}\n\n{demande.message or '(pas de message)'}",
    )
    courriels.envoyer(
        demande.email,
        "Votre demande à TopTroc",
        f"Bonjour {demande.nom},\n\nMerci pour votre intérêt pour TopTroc ({formule}). "
        "Nous revenons vers vous sous deux jours ouvrés pour en parler.",
    )
    return {"recu": True}


@router.get("/impact", response_model=Impact)
def impact(
    session: SessionDep,
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    rayon_km: float = Query(default=10, ge=1, le=200),
    jours: int = Query(default=365, ge=1, le=3650, description="Période couverte, en jours."),
    espace: str | None = Query(default=None, max_length=60, description="Bilan d'un espace réservé (son slug)."),
    lecteur: UtilisateurOptionnel = None,
):
    """Objets réemployés et déchets évités (estimés) sur une période, dans un rayon ou dans toute la France.

    Un objet compte quand il a changé de mains dans un échange terminé. Le poids vient d'une moyenne par
    catégorie (nomenclature.POIDS_MOYEN_KG) ; le CO₂ évité, d'un facteur moyen par kg d'objet réemployé.
    Avec ``espace`` : le bilan RSE d'un espace réservé, pour ses membres et la modération."""
    depuis = datetime.now(UTC) - timedelta(days=jours)
    requete = (
        select(m.Transfert.objet_id, m.Objet.categorie_slug, m.Transfert.donneur_id, m.Transfert.receveur_id)
        .join(m.Echange, m.Echange.id == m.Transfert.echange_id)
        .join(m.Objet, m.Objet.id == m.Transfert.objet_id)
        .where(m.Echange.statut == m.StatutEchange.termine, m.Echange.cree_le >= depuis)
    )
    en_ligne = select(func.count(m.Objet.id)).where(m.Objet.statut == m.StatutObjet.disponible)
    if espace is not None:
        e = session.scalar(select(m.Espace).where(m.Espace.slug == espace))
        if e is None or not lecteur or not (lecteur.espace_id == e.id or est_moderateur(lecteur)):
            raise HTTPException(404, "Espace introuvable.")
        requete = requete.where(m.Objet.espace_id == e.id)
        en_ligne = en_ligne.where(m.Objet.espace_id == e.id)
    if latitude is not None and longitude is not None:
        requete = requete.where(*_dans_le_rayon(latitude, longitude, rayon_km))
        en_ligne = en_ligne.where(*_dans_le_rayon(latitude, longitude, rayon_km))
    lignes = session.execute(requete).all()
    echanges = session.scalar(
        select(func.count(func.distinct(m.Transfert.echange_id))).where(
            m.Transfert.objet_id.in_([ligne.objet_id for ligne in lignes] or [0]),
            m.Transfert.echange_id.in_(
                select(m.Echange.id).where(m.Echange.statut == m.StatutEchange.termine, m.Echange.cree_le >= depuis)
            ),
        )
    )
    kg = sum(nomenclature.poids_moyen_kg(ligne.categorie_slug) for ligne in lignes)
    return Impact(
        depuis=depuis,
        echanges_termines=echanges or 0,
        objets_reemployes=len(lignes),
        membres_participants=len({i for ligne in lignes for i in (ligne.donneur_id, ligne.receveur_id)}),
        objets_en_ligne=session.scalar(en_ligne) or 0,
        kg_evites_estimes=round(kg, 1),
        co2_evite_kg_estime=round(kg * nomenclature.CO2_PAR_KG_REEMPLOYE, 1),
    )
