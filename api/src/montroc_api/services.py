"""Logique métier : passerelle entre la base et le moteur ``troc_echanges``.

Le moteur travaille en mémoire sur un ``Marche`` ; on le construit à partir des
objets disponibles et des souhaits en base, puis on enregistre les boucles
retenues sous forme d'``Echange``. Les e-mails des moments clés partent d'ici,
une fois la transaction validée.
"""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from troc_echanges import Boucle, Marche, boucles_autour, math_trade
from troc_echanges import Souhait as SouhaitMoteur

from . import courriels
from . import models as m
from .config import get_settings

DELAI_REPONSE = timedelta(hours=48)
RAPPEL_AVANT = timedelta(hours=12)
DELAI_DEPOT = timedelta(days=7)


class ErreurMetier(Exception):
    """Règle métier non respectée : renvoyée au client en 409."""


def lien_echange(echange: m.Echange) -> str:
    return f"{get_settings().site_url}/#echange-{echange.id}"


def construire_marche(session: Session) -> Marche:
    marche = Marche()
    utilisateurs = session.scalars(
        select(m.Utilisateur).where(m.Utilisateur.suspendu_le.is_(None)).options(selectinload(m.Utilisateur.souhaits))
    ).all()
    for u in utilisateurs:
        souhaits = [
            SouhaitMoteur(
                categorie=s.categorie_slug,
                objet_id=None if s.objet_id is None else str(s.objet_id),
                rang=s.rang,
                quantite=s.quantite,
                acceptation_auto=s.acceptation_auto,
            )
            for s in u.souhaits
        ]
        marche.ajouter_utilisateur(str(u.id), souhaits, zone=u.zone, fiabilite=u.fiabilite)
    objets = session.scalars(select(m.Objet).where(m.Objet.statut == m.StatutObjet.disponible)).all()
    for o in objets:
        marche.ajouter_objet(str(o.id), str(o.proprietaire_id), o.categorie_slug, o.titre)
    return marche


def suggestions(session: Session, utilisateur_id: int, limite: int = 10) -> list[Boucle]:
    return boucles_autour(construire_marche(session), str(utilisateur_id), limite=limite)


def _code_retrait() -> str:
    return "TRC-" + "".join(secrets.choice("23456789ABCDEFGHJKMNPQRSTUVWXYZ") for _ in range(5))


def proposer(session: Session, boucle: Boucle, auteur_id: int | None = None) -> m.Echange:
    """Enregistre une boucle, réserve ses objets et prévient les participants. À appeler dans une transaction.

    ``auteur_id`` : le participant qui a choisi cette boucle ; la proposer vaut accord pour sa part.
    """
    ids = [int(t.objet.id) for t in boucle.transferts]
    # Verrou ligne : deux propositions simultanées ne peuvent pas réserver le même objet.
    objets = session.scalars(select(m.Objet).where(m.Objet.id.in_(ids)).with_for_update()).all()
    if len(objets) != len(ids) or any(o.statut != m.StatutObjet.disponible for o in objets):
        raise ErreurMetier("Un objet de cette boucle n'est plus disponible.")
    par_id = {o.id: o for o in objets}
    for o in objets:
        o.statut = m.StatutObjet.reserve

    maintenant = datetime.now(UTC)
    echange = m.Echange(proba_reussite=boucle.proba_reussite, expire_le=maintenant + DELAI_REPONSE)
    for i, t in enumerate(boucle.transferts):
        # Souhait coché « j'accepte d'office », ou boucle choisie par le receveur : pas besoin de redemander.
        d_office = t.auto or int(t.receveur) == auteur_id
        echange.transferts.append(
            m.Transfert(
                position=i,
                donneur_id=int(t.donneur),
                receveur_id=int(t.receveur),
                objet=par_id[int(t.objet.id)],
                reponse=m.Reponse.acceptee if d_office else m.Reponse.en_attente,
                repondu_le=maintenant if d_office else None,
                code_retrait=_code_retrait(),
            )
        )
    session.add(echange)
    session.flush()  # identifiants, pour les liens des e-mails
    if not _mettre_a_jour_statut(session, echange):
        for t in echange.transferts:
            if t.reponse == m.Reponse.en_attente:
                donne = _transfert_du_donneur(echange, t.receveur_id).objet.titre
                courriels.apres_validation(
                    session,
                    courriels.boucle_vous_attend,
                    t.receveur.email,
                    t.receveur.pseudo,
                    donne,
                    t.objet.titre,
                    lien_echange(echange),
                )
    return echange


def proposer_par_objets(session: Session, objet_ids: list[int], auteur_id: int) -> m.Echange:
    """Enregistre la boucle suggérée formée par ces objets (dans l'ordre), après l'avoir revérifiée."""
    cible = tuple(str(i) for i in objet_ids)
    for b in boucles_autour(construire_marche(session), str(auteur_id), limite=None, options_par_transfert=10):
        if b.objets == cible:
            return proposer(session, b, auteur_id)
    raise ErreurMetier("Ces objets ne forment pas une boucle d'échange valide pour vous.")


def lancer_math_trade(session: Session, duree_max_s: float = 10.0):
    solution = math_trade(construire_marche(session), longueur_max=3, duree_max_s=duree_max_s)
    echanges = [proposer(session, b) for b in solution.boucles]
    return solution, echanges


def _transfert_du_donneur(echange: m.Echange, utilisateur_id: int) -> m.Transfert:
    return next(t for t in echange.transferts if t.donneur_id == utilisateur_id)


def _transfert_du_receveur(echange: m.Echange, utilisateur_id: int) -> m.Transfert:
    transfert = next((t for t in echange.transferts if t.receveur_id == utilisateur_id), None)
    if transfert is None:
        raise ErreurMetier("Vous ne participez pas à cet échange.")
    return transfert


def repondre(session: Session, echange: m.Echange, utilisateur_id: int, accepte: bool) -> m.Echange:
    """Le participant accepte ou refuse l'objet qu'il recevrait (et donc de donner le sien)."""
    if echange.statut != m.StatutEchange.propose:
        raise ErreurMetier("Cet échange n'attend plus de réponse.")
    if echange.expire_le < datetime.now(UTC):
        annuler(session, echange, "Le délai de réponse de 48 h est dépassé.")
        raise ErreurMetier("Le délai de réponse de 48 h est dépassé ; l'échange est annulé.")
    transfert = _transfert_du_receveur(echange, utilisateur_id)
    transfert.reponse = m.Reponse.acceptee if accepte else m.Reponse.refusee
    transfert.repondu_le = datetime.now(UTC)
    _mettre_a_jour_statut(session, echange)
    return echange


def deposer(session: Session, echange: m.Echange, utilisateur_id: int) -> m.Echange:
    """Le donneur indique qu'il a déposé son objet ; quand tout est déposé, chacun peut récupérer le sien."""
    if echange.statut != m.StatutEchange.accepte:
        raise ErreurMetier("On ne dépose qu'une fois l'échange accepté par tous.")
    transfert = next((t for t in echange.transferts if t.donneur_id == utilisateur_id), None)
    if transfert is None:
        raise ErreurMetier("Vous ne participez pas à cet échange.")
    if transfert.depose_le is not None:
        raise ErreurMetier("Votre dépôt est déjà enregistré.")
    transfert.depose_le = datetime.now(UTC)
    restants = [t for t in echange.transferts if t.depose_le is None]
    point = get_settings().point_de_depot
    if restants:
        deposant = transfert.donneur.pseudo
        for t in echange.transferts:
            if t.receveur_id != utilisateur_id:
                courriels.apres_validation(
                    session,
                    courriels.a_depose,
                    t.receveur.email,
                    t.receveur.pseudo,
                    deposant,
                    len(restants),
                    lien_echange(echange),
                )
        return echange

    echange.statut = m.StatutEchange.termine
    for t in echange.transferts:
        t.objet.statut = m.StatutObjet.echange
        courriels.apres_validation(
            session,
            courriels.tout_est_depose,
            t.receveur.email,
            t.receveur.pseudo,
            t.objet.titre,
            t.code_retrait,
            point,
        )
    return echange


def _mettre_a_jour_statut(session: Session, echange: m.Echange) -> bool:
    """Passe l'échange à « accepte » ou « annule » si les réponses le permettent ; vrai s'il a changé."""
    reponses = {t.reponse for t in echange.transferts}
    if m.Reponse.refusee in reponses:
        annuler(session, echange, "Un participant a décliné l'échange.")
        return True
    if reponses == {m.Reponse.acceptee}:
        echange.statut = m.StatutEchange.accepte
        echange.expire_le = datetime.now(UTC) + DELAI_DEPOT
        point = get_settings().point_de_depot
        for t in echange.transferts:
            courriels.apres_validation(
                session,
                courriels.echange_accepte,
                t.donneur.email,
                t.donneur.pseudo,
                t.objet.titre,
                t.code_retrait,
                point,
                lien_echange(echange),
            )
        return True
    return False


def annuler(session: Session, echange: m.Echange, raison: str) -> None:
    """Annule, libère les objets pour la prochaine recherche et prévient les participants."""
    echange.statut = m.StatutEchange.annule
    for t in echange.transferts:
        if t.objet is not None and t.objet.statut == m.StatutObjet.reserve:
            t.objet.statut = m.StatutObjet.disponible
        courriels.apres_validation(
            session, courriels.echange_annule, t.receveur.email, t.receveur.pseudo, raison, lien_echange(echange)
        )


def echanges_de(session: Session, utilisateur_id: int, actifs: bool = False) -> list[m.Echange]:
    """Les échanges où cette personne donne ou reçoit, les plus récents d'abord."""
    requete = (
        select(m.Echange)
        .join(m.Echange.transferts)
        .where(or_(m.Transfert.donneur_id == utilisateur_id, m.Transfert.receveur_id == utilisateur_id))
        .distinct()
        .order_by(m.Echange.cree_le.desc())
    )
    if actifs:
        requete = requete.where(m.Echange.statut.in_([m.StatutEchange.propose, m.StatutEchange.accepte]))
    else:
        requete = requete.limit(50)
    return list(session.scalars(requete))


def taches_horaires(session: Session) -> tuple[int, int]:
    """Rappel 12 h avant la fin du délai de réponse, puis annulation des échanges dont le délai est dépassé."""
    maintenant = datetime.now(UTC)
    a_rappeler = session.scalars(
        select(m.Echange).where(
            m.Echange.statut == m.StatutEchange.propose,
            m.Echange.rappel_envoye_le.is_(None),
            m.Echange.expire_le > maintenant,
            m.Echange.expire_le <= maintenant + RAPPEL_AVANT,
        )
    ).all()
    rappels = 0
    for echange in a_rappeler:
        echange.rappel_envoye_le = maintenant
        for t in echange.transferts:
            if t.reponse == m.Reponse.en_attente:
                rappels += 1
                courriels.apres_validation(
                    session,
                    courriels.plus_que_12_h,
                    t.receveur.email,
                    t.receveur.pseudo,
                    t.objet.titre,
                    lien_echange(echange),
                )

    expires = session.scalars(
        select(m.Echange).where(
            m.Echange.statut.in_([m.StatutEchange.propose, m.StatutEchange.accepte]),
            m.Echange.expire_le <= maintenant,
        )
    ).all()
    for echange in expires:
        if echange.statut == m.StatutEchange.propose:
            raison = "Tout le monde n'a pas répondu dans les 48 h."
        else:
            raison = "Tous les objets n'ont pas été déposés dans les 7 jours : chacun récupère le sien."
        annuler(session, echange, raison)
    return rappels, len(expires)
