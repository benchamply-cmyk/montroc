"""Signalements de contenus (DSA, art. 16) et décisions de modération motivées (art. 17)."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .. import courriels, services
from .. import models as m
from ..config import get_settings
from ..deps import Moderateur, SessionDep, UtilisateurOptionnel, obtenir_ou_404
from ..schemas import Decision, SignalementCreation, SignalementLecture, SignalementRecu

router = APIRouter(tags=["signalements et modération"])

MOTIFS = {
    m.MotifSignalement.illegal: "contenu ou objet illicite",
    m.MotifSignalement.dangereux: "produit dangereux ou rappelé",
    m.MotifSignalement.contrefacon: "contrefaçon",
    m.MotifSignalement.arnaque: "arnaque ou tromperie",
    m.MotifSignalement.inapproprie: "photo ou texte inapproprié",
    m.MotifSignalement.autre: "autre motif",
}


@router.post("/signalements", response_model=SignalementRecu, status_code=201)
def signaler(donnees: SignalementCreation, auteur: UtilisateurOptionnel, session: SessionDep):
    """Ouvert à tous, avec ou sans compte (sans compte, une adresse e-mail est demandée pour la réponse)."""
    if auteur is None and donnees.email_contact is None:
        raise HTTPException(422, "Indiquez votre e-mail pour être informé de la suite donnée.")
    if donnees.objet_id is not None:
        objet = session.get(m.Objet, donnees.objet_id)
        if objet is None or objet.statut == m.StatutObjet.modere:
            raise HTTPException(404, "Objet introuvable.")
    else:
        obtenir_ou_404(session, m.Utilisateur, donnees.utilisateur_id)
    signalement = m.Signalement(
        objet_id=donnees.objet_id,
        utilisateur_vise_id=donnees.utilisateur_id,
        auteur_id=auteur.id if auteur else None,
        email_contact=None if auteur else str(donnees.email_contact),
        motif=donnees.motif,
        explication=donnees.explication.strip(),
    )
    session.add(signalement)
    session.flush()
    contact = auteur.email if auteur else str(donnees.email_contact)
    courriels.apres_validation(
        session,
        courriels.decision_moderation,
        contact,
        "Signalement reçu",
        f"Bonjour,\n\nNous avons bien reçu votre signalement n° {signalement.id} ({MOTIFS[donnees.motif]}). "
        "Il sera examiné par une personne, et nous vous informerons de la décision prise.",
    )
    for email in get_settings().liste_moderateurs:
        courriels.apres_validation(
            session,
            courriels.decision_moderation,
            email,
            f"Nouveau signalement n° {signalement.id}",
            f"Motif : {MOTIFS[donnees.motif]}\n\n{signalement.explication}\n\n"
            f"À traiter : {get_settings().site_url}/#moderation",
        )
    session.commit()
    return signalement


@router.get("/moderation/signalements", response_model=list[SignalementLecture])
def lister(
    _moderateur: Moderateur, session: SessionDep, statut: m.StatutSignalement | None = m.StatutSignalement.ouvert
):
    requete = select(m.Signalement).order_by(m.Signalement.cree_le)
    if statut is not None:
        requete = requete.where(m.Signalement.statut == statut)
    return session.scalars(requete.limit(200)).all()


def _suspendre(session, utilisateur: m.Utilisateur) -> None:
    utilisateur.suspendu_le = datetime.now(UTC)
    for echange in services.echanges_de(session, actifs=True, utilisateur_id=utilisateur.id):
        services.annuler(session, echange, "Un participant a été suspendu par la modération.")
    for objet in utilisateur.objets:
        if objet.statut in (m.StatutObjet.disponible, m.StatutObjet.reserve):
            objet.statut = m.StatutObjet.retire
    for s in session.scalars(select(m.SessionUtilisateur).where(m.SessionUtilisateur.utilisateur_id == utilisateur.id)):
        session.delete(s)


@router.post("/moderation/signalements/{signalement_id}/decision", response_model=SignalementLecture)
def decider(signalement_id: int, donnees: Decision, moderateur: Moderateur, session: SessionDep):
    signalement = obtenir_ou_404(session, m.Signalement, signalement_id)
    if signalement.statut != m.StatutSignalement.ouvert:
        raise HTTPException(409, "Ce signalement a déjà été traité.")
    signalement.statut = m.StatutSignalement.retenu if donnees.retenir else m.StatutSignalement.rejete
    signalement.decision = donnees.motivation.strip()
    signalement.traite_le = datetime.now(UTC)
    signalement.traite_par_id = moderateur.id

    objet = signalement.objet
    concerne = objet.proprietaire if objet is not None else signalement.utilisateur_vise
    if donnees.retenir and concerne is not None:
        mesures = []
        if objet is not None and objet.statut != m.StatutObjet.modere:
            for echange in services.echanges_de(session, actifs=True, utilisateur_id=concerne.id):
                if any(t.objet_id == objet.id for t in echange.transferts):
                    services.annuler(session, echange, "Un objet de l'échange a été retiré par la modération.")
            objet.statut = m.StatutObjet.modere
            mesures.append(f"votre objet « {objet.titre} » a été retiré")
        if (donnees.suspendre_compte or objet is None) and concerne.suspendu_le is None:
            _suspendre(session, concerne)
            mesures.append("votre compte est suspendu")
        # Exposé des motifs (DSA, art. 17) : quoi, pourquoi, et comment contester.
        courriels.apres_validation(
            session,
            courriels.decision_moderation,
            concerne.email,
            "Décision de modération",
            f"Bonjour {concerne.pseudo},\n\nÀ la suite d'un signalement ({MOTIFS[signalement.motif]}), "
            f"{' et '.join(mesures) or 'aucune nouvelle mesure n’a été prise'}.\n\nMotif de la décision : "
            f"{signalement.decision}\n\nCette décision a été prise par une personne, pas par un automate. "
            "Pour la contester, répondez simplement à cet e-mail en expliquant pourquoi : elle sera réexaminée.",
        )

    contact = signalement.auteur.email if signalement.auteur else signalement.email_contact
    if contact:
        suite = "a été retenu : le contenu a été retiré" if donnees.retenir else "n'a pas été retenu"
        courriels.apres_validation(
            session,
            courriels.decision_moderation,
            contact,
            "Suite donnée à votre signalement",
            f"Bonjour,\n\nVotre signalement n° {signalement.id} {suite}.\n\nMotif : {signalement.decision}",
        )
    session.commit()
    return signalement
