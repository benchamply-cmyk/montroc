"""Logique métier : passerelle entre la base et le moteur ``troc_echanges``.

Le moteur travaille en mémoire sur un ``Marche`` ; on le construit à partir des
objets disponibles et des souhaits en base, puis on enregistre les boucles
retenues sous forme d'``Echange``.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from troc_echanges import Boucle, Marche, boucles_autour, math_trade
from troc_echanges import Souhait as SouhaitMoteur

from . import models as m

DELAI_REPONSE = timedelta(hours=48)


class ErreurMetier(Exception):
    """Règle métier non respectée : renvoyée au client en 409."""


def construire_marche(session: Session) -> Marche:
    marche = Marche()
    utilisateurs = session.scalars(select(m.Utilisateur).options(selectinload(m.Utilisateur.souhaits))).all()
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


def proposer(session: Session, boucle: Boucle) -> m.Echange:
    """Enregistre une boucle et réserve ses objets. À appeler dans une transaction."""
    ids = [int(t.objet.id) for t in boucle.transferts]
    # Verrou ligne : deux propositions simultanées ne peuvent pas réserver le même objet.
    objets = session.scalars(select(m.Objet).where(m.Objet.id.in_(ids)).with_for_update()).all()
    if len(objets) != len(ids) or any(o.statut != m.StatutObjet.disponible for o in objets):
        raise ErreurMetier("Un objet de cette boucle n'est plus disponible.")
    par_id = {o.id: o for o in objets}
    for o in objets:
        o.statut = m.StatutObjet.reserve

    echange = m.Echange(proba_reussite=boucle.proba_reussite, expire_le=datetime.now(UTC) + DELAI_REPONSE)
    for i, t in enumerate(boucle.transferts):
        echange.transferts.append(
            m.Transfert(
                position=i,
                donneur_id=int(t.donneur),
                receveur_id=int(t.receveur),
                objet=par_id[int(t.objet.id)],
                # Souhait coché « j'accepte d'office » : pas besoin de redemander.
                reponse=m.Reponse.acceptee if t.auto else m.Reponse.en_attente,
                repondu_le=datetime.now(UTC) if t.auto else None,
            )
        )
    session.add(echange)
    _mettre_a_jour_statut(echange)
    return echange


def proposer_par_objets(session: Session, objet_ids: list[int]) -> m.Echange:
    """Enregistre la boucle suggérée formée par ces objets (dans l'ordre), après l'avoir revérifiée."""
    premier = session.get(m.Objet, objet_ids[0])
    if premier is None:
        raise ErreurMetier("Objet inconnu.")
    cible = tuple(str(i) for i in objet_ids)
    for b in boucles_autour(
        construire_marche(session), str(premier.proprietaire_id), limite=None, options_par_transfert=10
    ):
        if b.objets == cible:
            return proposer(session, b)
    raise ErreurMetier("Ces objets ne forment pas une boucle d'échange valide.")


def lancer_math_trade(session: Session, duree_max_s: float = 10.0):
    solution = math_trade(construire_marche(session), longueur_max=3, duree_max_s=duree_max_s)
    echanges = [proposer(session, b) for b in solution.boucles]
    return solution, echanges


def repondre(session: Session, echange: m.Echange, transfert_id: int, utilisateur_id: int, accepte: bool) -> m.Echange:
    if echange.statut != m.StatutEchange.propose:
        raise ErreurMetier("Cet échange n'attend plus de réponse.")
    if echange.expire_le < datetime.now(UTC):
        _annuler(echange)
        raise ErreurMetier("Le délai de réponse de 48 h est dépassé ; l'échange est annulé.")
    transfert = next((t for t in echange.transferts if t.id == transfert_id), None)
    if transfert is None:
        raise ErreurMetier("Étape inconnue pour cet échange.")
    if transfert.receveur_id != utilisateur_id:
        raise ErreurMetier("Seul le receveur de l'objet peut répondre.")
    transfert.reponse = m.Reponse.acceptee if accepte else m.Reponse.refusee
    transfert.repondu_le = datetime.now(UTC)
    _mettre_a_jour_statut(echange)
    return echange


def terminer(echange: m.Echange) -> m.Echange:
    if echange.statut != m.StatutEchange.accepte:
        raise ErreurMetier("Seul un échange accepté par tous peut être terminé.")
    echange.statut = m.StatutEchange.termine
    for t in echange.transferts:
        t.objet.statut = m.StatutObjet.echange
    return echange


def _mettre_a_jour_statut(echange: m.Echange) -> None:
    reponses = {t.reponse for t in echange.transferts}
    if m.Reponse.refusee in reponses:
        _annuler(echange)
    elif reponses == {m.Reponse.acceptee}:
        echange.statut = m.StatutEchange.accepte


def _annuler(echange: m.Echange) -> None:
    """Annule et libère les objets, pour qu'ils repartent dans la prochaine recherche."""
    echange.statut = m.StatutEchange.annule
    for t in echange.transferts:
        if t.objet is not None and t.objet.statut == m.StatutObjet.reserve:
            t.objet.statut = m.StatutObjet.disponible
