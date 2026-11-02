"""Troc & Services : fiches métier, professionnels certifiés, négociations et contrats (voir services_pro.py)."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .. import courriels, nomenclature, services_pro
from .. import models as m
from ..deps import Moderateur, SessionDep, UtilisateurConnecte, est_moderateur, obtenir_ou_404
from ..schemas import (
    ConditionsAccord,
    ContratLecture,
    DecisionPro,
    MessageCreation,
    MessageLecture,
    MetierLecture,
    NegociationCreation,
    NegociationLecture,
    NegociationResume,
    ObjetLecture,
    Partie,
    ProfilProCreation,
    ProfilProModeration,
    ProfilProPrive,
    ProfilProPublic,
)
from ..services import ErreurMetier

router = APIRouter(tags=["Troc & Services"])

# Ce qui, modifié, demande une nouvelle vérification : l'identité de l'entreprise et ses justificatifs.
CHAMPS_VERIFIES = ("nom_commercial", "siret", "assurance", "qualifications", "justificatifs")


def _metier(slug: str) -> MetierLecture:
    f = nomenclature.METIERS[slug]
    return MetierLecture(
        slug=slug,
        libelle=services_pro.libelle_metier(slug),
        famille=f.famille,
        description=f.description,
        exemples=list(f.exemples),
        justificatifs=list(f.justificatifs),
    )


def _public(session, p: m.ProfilPro) -> ProfilProPublic:
    u = p.utilisateur
    return ProfilProPublic(
        id=p.id,
        utilisateur_id=u.id,
        pseudo=u.pseudo,
        reputation=u.reputation,
        echanges_menes=u.echanges_menes,
        metier=p.metier,
        metier_libelle=services_pro.libelle_metier(p.metier),
        nom_commercial=p.nom_commercial,
        description=p.description,
        experience_annees=p.experience_annees,
        zone_intervention=p.zone_intervention,
        qualifications=p.qualifications,
        certifie_le=p.certifie_le,
        services=[ObjetLecture.model_validate(o) for o in services_pro.services_du_pro(session, p)],
    )


@router.get("/services/metiers", response_model=list[MetierLecture])
def metiers():
    """Les métiers de Troc & Services, avec leur fiche : ce qu'on peut demander et ce que TopTroc vérifie."""
    return [_metier(slug) for slug in nomenclature.METIERS]


@router.get("/services/pros", response_model=list[ProfilProPublic])
def pros(session: SessionDep, metier: str | None = None):
    """Les professionnels certifiés (comptes actifs), par métier, les plus anciennement certifiés d'abord."""
    requete = (
        select(m.ProfilPro)
        .join(m.ProfilPro.utilisateur)
        .where(m.ProfilPro.statut == m.StatutProfilPro.certifie, m.Utilisateur.suspendu_le.is_(None))
        .order_by(m.ProfilPro.certifie_le, m.ProfilPro.id)
    )
    if metier:
        requete = requete.where(m.ProfilPro.metier == metier)
    return [_public(session, p) for p in session.scalars(requete)]


@router.get("/services/pros/{profil_id}", response_model=ProfilProPublic)
def pro(profil_id: int, session: SessionDep):
    p = session.get(m.ProfilPro, profil_id)
    if p is None or p.statut != m.StatutProfilPro.certifie or p.utilisateur.suspendu_le is not None:
        raise HTTPException(404, "Professionnel introuvable.")
    return _public(session, p)


# --- Mon activité pro ---


@router.get("/moi/pro", response_model=list[ProfilProPrive])
def mes_profils(utilisateur: UtilisateurConnecte, session: SessionDep):
    return session.scalars(
        select(m.ProfilPro).where(m.ProfilPro.utilisateur_id == utilisateur.id).order_by(m.ProfilPro.id)
    ).all()


@router.post("/moi/pro", response_model=ProfilProPrive, status_code=201)
def deposer_profil(donnees: ProfilProCreation, utilisateur: UtilisateurConnecte, session: SessionDep):
    """Déclarer (ou mettre à jour) mon activité pour un métier. Un nouveau dossier, ou un changement d'entreprise ou
    de justificatif, part en vérification : les offres de ce métier attendent la certification."""
    profil = session.scalar(
        select(m.ProfilPro).where(m.ProfilPro.utilisateur_id == utilisateur.id, m.ProfilPro.metier == donnees.metier)
    )
    valeurs = donnees.model_dump()
    if profil is None:
        profil = m.ProfilPro(utilisateur_id=utilisateur.id, **valeurs)
        session.add(profil)
    else:
        a_reverifier = any(getattr(profil, c) != valeurs[c] for c in CHAMPS_VERIFIES)
        for champ, valeur in valeurs.items():
            setattr(profil, champ, valeur)
        if a_reverifier or profil.statut == m.StatutProfilPro.refuse:
            if profil.statut == m.StatutProfilPro.certifie:
                services_pro.retirer_services(session, profil)
            profil.statut, profil.motif, profil.certifie_le, profil.certifie_par_id = (
                m.StatutProfilPro.en_attente,
                None,
                None,
                None,
            )
    session.commit()
    return profil


@router.delete("/moi/pro/{profil_id}", status_code=204)
def supprimer_profil(profil_id: int, utilisateur: UtilisateurConnecte, session: SessionDep):
    profil = session.get(m.ProfilPro, profil_id)
    if profil is None or profil.utilisateur_id != utilisateur.id:
        raise HTTPException(404, "Activité introuvable.")
    services_pro.retirer_services(session, profil)
    session.delete(profil)
    session.commit()


# --- Modération : certification des professionnels ---


def _moderation(p: m.ProfilPro) -> ProfilProModeration:
    return ProfilProModeration.model_validate(
        {**ProfilProPrive.model_validate(p).model_dump(), "utilisateur_id": p.utilisateur_id,
         "pseudo": p.utilisateur.pseudo, "email": p.utilisateur.email}
    )  # fmt: skip


@router.get("/moderation/pros", response_model=list[ProfilProModeration])
def a_verifier(_moderateur: Moderateur, session: SessionDep, statut: m.StatutProfilPro = m.StatutProfilPro.en_attente):
    """Les dossiers pro à vérifier (ou déjà certifiés / refusés), les plus anciens d'abord."""
    return [
        _moderation(p)
        for p in session.scalars(select(m.ProfilPro).where(m.ProfilPro.statut == statut).order_by(m.ProfilPro.id))
    ]


@router.post("/moderation/pros/{profil_id}/decision", response_model=ProfilProModeration)
def certifier(profil_id: int, donnees: DecisionPro, moderateur: Moderateur, session: SessionDep):
    profil = obtenir_ou_404(session, m.ProfilPro, profil_id)
    metier = services_pro.libelle_metier(profil.metier)
    if donnees.certifier:
        profil.statut, profil.motif = m.StatutProfilPro.certifie, None
        profil.certifie_le, profil.certifie_par_id = datetime.now(UTC), moderateur.id
        sujet = f"Votre activité « {metier} » est certifiée"
        texte = (
            f"Bonjour {profil.utilisateur.pseudo},\n\nTopTroc a vérifié vos justificatifs : votre activité "
            f"« {metier} » est certifiée. Vous pouvez maintenant proposer vos services en Troc & Services."
        )
    else:
        if profil.statut == m.StatutProfilPro.certifie:
            services_pro.retirer_services(session, profil)
        profil.statut, profil.motif = m.StatutProfilPro.refuse, donnees.motif.strip()
        profil.certifie_le, profil.certifie_par_id = None, None
        sujet = f"Votre activité « {metier} » n'est pas encore certifiée"
        texte = (
            f"Bonjour {profil.utilisateur.pseudo},\n\nTopTroc n'a pas pu certifier votre activité « {metier} » :\n\n"
            f"{profil.motif}\n\nComplétez votre dossier depuis Mon espace : il repartira en vérification."
        )
    courriels.apres_validation(session, courriels.envoyer, profil.utilisateur.email, sujet, texte)
    session.commit()
    return _moderation(profil)


# --- Négociations et contrats ---


def _lecture(session, n: m.Negociation) -> NegociationLecture:
    pseudos = {n.initiateur_id: n.initiateur.pseudo, n.destinataire_id: n.destinataire.pseudo}
    return NegociationLecture(
        id=n.id,
        statut=n.statut.value,
        initiateur=Partie(id=n.initiateur_id, pseudo=n.initiateur.pseudo),
        destinataire=Partie(id=n.destinataire_id, pseudo=n.destinataire.pseudo),
        objet=ObjetLecture.model_validate(n.objet),
        contreparties=[ObjetLecture.model_validate(o) for o in services_pro.contreparties(session, n)],
        conditions=n.conditions,
        accord_propose_par_id=n.accord_propose_par_id,
        messages=[
            MessageLecture(
                id=x.id,
                auteur_id=x.auteur_id,
                auteur=pseudos.get(x.auteur_id, "TopTroc"),
                texte=x.texte,
                cree_le=x.cree_le,
            )
            for x in n.messages
        ],
        contrat=n.contrat and ContratLecture.model_validate(n.contrat),
        cree_le=n.cree_le,
        mis_a_jour_le=n.mis_a_jour_le,
    )


def _ma_negociation(session, negociation_id: int, utilisateur: m.Utilisateur) -> m.Negociation:
    n = session.get(m.Negociation, negociation_id)
    if n is None or (utilisateur.id not in (n.initiateur_id, n.destinataire_id) and not est_moderateur(utilisateur)):
        raise HTTPException(404, "Conversation introuvable.")
    return n


def _agir(session, n: m.Negociation, action, *args):
    try:
        action(session, n, *args)
    except ErreurMetier as e:
        session.rollback()
        raise HTTPException(409, str(e)) from e
    session.commit()
    session.refresh(n)
    return _lecture(session, n)


@router.post("/negociations", response_model=NegociationLecture, status_code=201)
def ouvrir(donnees: NegociationCreation, utilisateur: UtilisateurConnecte, session: SessionDep):
    """« Proposer des articles en échange » : ouvre la conversation avec le propriétaire de l'annonce."""
    try:
        n = services_pro.ouvrir(session, utilisateur, donnees.objet_id, donnees.contreparties, donnees.message)
    except ErreurMetier as e:
        session.rollback()
        raise HTTPException(409, str(e)) from e
    session.commit()
    return _lecture(session, n)


@router.get("/moi/negociations", response_model=list[NegociationResume])
def mes_negociations(utilisateur: UtilisateurConnecte, session: SessionDep):
    resumes = []
    for n in services_pro.mes_negociations(session, utilisateur):
        avec = services_pro.autre(n, utilisateur)
        dernier = n.messages[-1] if n.messages else None
        resumes.append(
            NegociationResume(
                id=n.id,
                statut=n.statut.value,
                avec=Partie(id=avec.id, pseudo=avec.pseudo),
                objet_titre=n.objet.titre,
                dernier_message=dernier.texte if dernier else "",
                mis_a_jour_le=n.mis_a_jour_le,
                a_moi_de_repondre=(
                    n.statut == m.StatutNegociation.accord_propose and n.accord_propose_par_id != utilisateur.id
                )
                or (n.statut == m.StatutNegociation.ouverte and dernier is not None and dernier.auteur_id == avec.id),
            )
        )
    return resumes


@router.get("/negociations/{negociation_id}", response_model=NegociationLecture)
def lire(negociation_id: int, utilisateur: UtilisateurConnecte, session: SessionDep):
    return _lecture(session, _ma_negociation(session, negociation_id, utilisateur))


@router.post("/negociations/{negociation_id}/messages", response_model=NegociationLecture)
def ecrire(negociation_id: int, donnees: MessageCreation, utilisateur: UtilisateurConnecte, session: SessionDep):
    n = _ma_negociation(session, negociation_id, utilisateur)
    return _agir(session, n, services_pro.ecrire, utilisateur, donnees.texte)


@router.post("/negociations/{negociation_id}/accord", response_model=NegociationLecture)
def proposer_accord(
    negociation_id: int, donnees: ConditionsAccord, utilisateur: UtilisateurConnecte, session: SessionDep
):
    """Proposer des conditions (prestation, date, lieu, articles) : l'autre partie les accepte ou répond."""
    n = _ma_negociation(session, negociation_id, utilisateur)
    return _agir(session, n, services_pro.proposer_accord, utilisateur, donnees.model_dump(exclude_none=True))


@router.post("/negociations/{negociation_id}/accepter", response_model=NegociationLecture)
def accepter(negociation_id: int, utilisateur: UtilisateurConnecte, session: SessionDep):
    """Accepter les conditions proposées par l'autre partie : TopTroc génère le contrat."""
    n = _ma_negociation(session, negociation_id, utilisateur)
    return _agir(session, n, services_pro.accepter, utilisateur)


@router.post("/negociations/{negociation_id}/annuler", response_model=NegociationLecture)
def annuler(negociation_id: int, utilisateur: UtilisateurConnecte, session: SessionDep):
    n = _ma_negociation(session, negociation_id, utilisateur)
    return _agir(session, n, services_pro.annuler, utilisateur)


@router.post("/contrats/{contrat_id}/confirmer", response_model=NegociationLecture)
def confirmer(contrat_id: int, utilisateur: UtilisateurConnecte, session: SessionDep):
    """Confirmer que tout a été fait (prestation rendue, articles remis) : à deux, l'échange est mené."""
    contrat = session.get(m.ContratService, contrat_id)
    if contrat is None:
        raise HTTPException(404, "Contrat introuvable.")
    n = _ma_negociation(session, contrat.negociation_id, utilisateur)
    return _agir(session, n, lambda s, _n, u: services_pro.confirmer(s, contrat, u), utilisateur)
