"""Logique métier : passerelle entre la base et le moteur ``troc_echanges``.

Le moteur travaille en mémoire sur un ``Marche`` ; on le construit à partir des
objets disponibles et des souhaits en base, puis on enregistre les boucles
retenues sous forme d'``Echange``. Les e-mails des moments clés partent d'ici,
une fois la transaction validée.
"""

import secrets
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from troc_echanges import Boucle, Contraintes, Marche, boucles_autour, math_trade
from troc_echanges import Souhait as SouhaitMoteur

from . import courriels, sms
from . import models as m
from .config import get_settings

DELAI_REPONSE = timedelta(hours=48)
RAPPEL_AVANT = timedelta(hours=12)
DELAI_DEPOT = timedelta(days=7)

# Le Grand Troc du dimanche : chaque dimanche à 18 h (heure de Paris), le math trade tourne sur tout le stock.
# Toutes les propositions arrivent en même temps, on a 48 h pour répondre (jusqu'au mardi 18 h), puis les
# dépôts se font dans la semaine, jusqu'au dimanche suivant midi : les objets d'un échange qui n'a pas abouti
# repartent ainsi dans le Grand Troc du soir même.
PARIS = ZoneInfo("Europe/Paris")
DIMANCHE = 6
HEURE_GRAND_TROC = time(18)
FIN_DES_DEPOTS = (timedelta(days=7), time(12))
DUREE_MAX_GRAND_TROC_S = 30.0
# Repêchage : à la fin des 48 h de réponse (mardi 18 h), une seconde passe sur le stock du dimanche resté libre.
# Il faut encore le temps de répondre (48 h) avant la fin des dépôts du dimanche midi.
MARGE_REPECHAGE = DELAI_REPONSE

# Fiabilité = (tenus + LISSAGE) / (tenus + manqués + LISSAGE) : 1 au départ, 0,9 après un premier manquement,
# et un manquement pèse de moins en moins à mesure que les engagements tenus s'accumulent.
LISSAGE_FIABILITE = 9


class ErreurMetier(Exception):
    """Règle métier non respectée : renvoyée au client en 409."""


def lien_echange(echange: m.Echange) -> str:
    return f"{get_settings().site_url}/#echange-{echange.id}"


def construire_marche(session: Session, stock_avant: datetime | None = None) -> Marche:
    """Le marché du moteur : comptes actifs, leurs souhaits et les objets disponibles.

    ``stock_avant`` : seulement les objets publiés avant cette date (repêchage sur le stock du dimanche).
    """
    marche = Marche()
    utilisateurs = session.scalars(
        select(m.Utilisateur).where(m.Utilisateur.suspendu_le.is_(None)).options(selectinload(m.Utilisateur.souhaits))
    ).all()
    # Indice de chaque souhait dans la liste de son auteur : c'est ainsi que le moteur désigne les listes « contre ».
    indice_souhait: dict[int, int] = {}
    for u in utilisateurs:
        indice_souhait.update({s.id: i for i, s in enumerate(u.souhaits)})
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
    requete = select(m.Objet).where(m.Objet.statut == m.StatutObjet.disponible).options(selectinload(m.Objet.contre))
    if stock_avant is not None:
        requete = requete.where(m.Objet.cree_le <= stock_avant)
    for o in session.scalars(requete).all():
        if str(o.proprietaire_id) not in marche.utilisateurs:
            continue  # compte suspendu
        # Liste vide (souhaits tous supprimés) : l'objet repart contre n'importe lequel des souhaits.
        contre = {indice_souhait[s.id] for s in o.contre if s.utilisateur_id == o.proprietaire_id}
        marche.ajouter_objet(
            str(o.id), str(o.proprietaire_id), o.categorie_slug, o.titre, contre=contre, contre_strict=o.contre_strict
        )
    return marche


def suggestions(session: Session, utilisateur_id: int, limite: int = 10) -> list[Boucle]:
    return boucles_autour(construire_marche(session), str(utilisateur_id), limite=limite)


def _code_retrait() -> str:
    return "TRC-" + "".join(secrets.choice("23456789ABCDEFGHJKMNPQRSTUVWXYZ") for _ in range(5))


def proposer(
    session: Session, boucle: Boucle, auteur_id: int | None = None, grand_troc: m.GrandTroc | None = None
) -> m.Echange:
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
    echange = m.Echange(
        proba_reussite=boucle.proba_reussite, expire_le=maintenant + DELAI_REPONSE, grand_troc=grand_troc
    )
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
                    grand_troc is not None,
                )
                # Au Grand Troc, un seul SMS par personne pour toutes ses boucles : envoyé par lancer_grand_troc.
                if grand_troc is None and t.receveur.telephone:
                    courriels.apres_validation(
                        session, sms.boucle_proposee, t.receveur.telephone, 1, lien_echange(echange), False
                    )
    return echange


def proposer_par_objets(session: Session, objet_ids: list[int], auteur_id: int) -> m.Echange:
    """Enregistre la boucle suggérée formée par ces objets (dans l'ordre), après l'avoir revérifiée."""
    if not get_settings().echanges_a_la_demande:
        raise ErreurMetier(
            "Les échanges se décident au Grand Troc du dimanche : cette boucle vous sera proposée dimanche "
            "si elle est toujours possible."
        )
    cible = tuple(str(i) for i in objet_ids)
    for b in boucles_autour(construire_marche(session), str(auteur_id), limite=None, options_par_transfert=10):
        if b.objets == cible:
            return proposer(session, b, auteur_id)
    raise ErreurMetier("Ces objets ne forment pas une boucle d'échange valide pour vous.")


def prochain_grand_troc(apres: datetime) -> datetime:
    """Le prochain dimanche 18 h (heure de Paris) strictement après ``apres``."""
    local = apres.astimezone(PARIS)
    dimanche = local.date() + timedelta(days=(DIMANCHE - local.weekday()) % 7)
    rendez_vous = datetime.combine(dimanche, HEURE_GRAND_TROC, tzinfo=PARIS)
    if rendez_vous <= local:
        rendez_vous = datetime.combine(dimanche + timedelta(days=7), HEURE_GRAND_TROC, tzinfo=PARIS)
    return rendez_vous


def fin_des_depots(jour_grand_troc: date) -> datetime:
    decalage, heure = FIN_DES_DEPOTS
    return datetime.combine(jour_grand_troc + decalage, heure, tzinfo=PARIS)


def _maintenant() -> datetime:
    return datetime.now(PARIS)


def dernier_grand_troc(session: Session) -> m.GrandTroc | None:
    return session.scalars(select(m.GrandTroc).order_by(m.GrandTroc.jour.desc()).limit(1)).first()


def lancer_grand_troc(session: Session, force: bool = False) -> tuple[m.GrandTroc | None, list[m.Echange], bool, str]:
    """Le Grand Troc du dimanche : maximum d'objets échangés sur tout le stock, une seule fois par dimanche.

    La tâche planifiée appelle cette fonction plusieurs fois le dimanche (l'heure d'été change l'heure UTC) :
    elle ne fait rien avant 18 h, ni si le Grand Troc du jour a déjà eu lieu. ``force`` lance le Grand Troc
    tout de suite, quel que soit le jour (lancement manuel) ; il reste unique par jour.
    Renvoie (le Grand Troc du jour ou None, les échanges proposés, vrai s'il vient d'avoir lieu, une explication).
    """
    maintenant = _maintenant()
    if not force and (maintenant.weekday() != DIMANCHE or maintenant.time() < HEURE_GRAND_TROC):
        return (
            None,
            [],
            False,
            f"Pas encore l'heure : prochain Grand Troc le {prochain_grand_troc(maintenant):%d/%m à %H h}.",
        )
    jour = maintenant.date()
    deja = session.scalars(select(m.GrandTroc).where(m.GrandTroc.jour == jour)).first()
    if deja is not None:
        return deja, [], False, "Le Grand Troc de ce jour a déjà eu lieu."

    solution = math_trade(construire_marche(session), longueur_max=3, duree_max_s=DUREE_MAX_GRAND_TROC_S)
    grand_troc = m.GrandTroc(
        jour=jour,
        optimal=solution.optimal,
        duree_s=solution.duree_s,
        nb_boucles=len(solution.boucles),
        nb_objets=solution.nb_objets_echanges,
        nb_participants=len(solution.participants),
    )
    session.add(grand_troc)
    session.flush()
    echanges = [proposer(session, b, grand_troc=grand_troc) for b in solution.boucles]
    _sms_du_grand_troc(session, echanges)
    return grand_troc, echanges, True, f"{len(echanges)} boucle(s) proposée(s), {solution.nb_objets_echanges} objets."


def _sms_du_grand_troc(session: Session, echanges: list[m.Echange]) -> None:
    """Un SMS par personne qui a au moins une réponse à donner, avec le nombre d'échanges et un lien."""
    a_prevenir: dict[int, tuple[m.Utilisateur, list[m.Echange]]] = {}
    for echange in echanges:
        if echange.statut != m.StatutEchange.propose:
            continue
        for t in echange.transferts:
            if t.reponse == m.Reponse.en_attente and t.receveur.telephone:
                a_prevenir.setdefault(t.receveur_id, (t.receveur, []))[1].append(echange)
    for utilisateur, siens in a_prevenir.values():
        lien = lien_echange(siens[0]) if len(siens) == 1 else f"{get_settings().site_url}/#echanges"
        courriels.apres_validation(session, sms.boucle_proposee, utilisateur.telephone, len(siens), lien, True)


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
        _noter_manquements(echange)
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
    noter_engagement(transfert.donneur, tenu=True)
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
        if echange.grand_troc is not None:
            echange.expire_le = fin_des_depots(echange.grand_troc.jour)
        else:
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
                echange.expire_le,
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
            raison = "Tous les objets n'ont pas été déposés à temps : chacun récupère le sien."
        _noter_manquements(echange)
        annuler(session, echange, raison)
    return rappels, len(expires)


def noter_engagement(utilisateur: m.Utilisateur, tenu: bool) -> None:
    """Compte un engagement tenu (objet déposé) ou manqué, et recalcule la fiabilité qui en découle.

    La fiabilité entre dans la chance de réussite des boucles : le math trade évite ainsi, à égalité,
    de faire dépendre une boucle de quelqu'un qui laisse souvent les autres en plan.
    """
    if tenu:
        utilisateur.engagements_tenus += 1
    else:
        utilisateur.engagements_manques += 1
    tenus = utilisateur.engagements_tenus + LISSAGE_FIABILITE
    utilisateur.fiabilite = tenus / (tenus + utilisateur.engagements_manques)


def _noter_manquements(echange: m.Echange) -> None:
    """Échange expiré : qui n'a pas répondu dans les 48 h, ou qui a accepté sans déposer. Un refus n'en est pas un."""
    for t in echange.transferts:
        if echange.statut == m.StatutEchange.propose and t.reponse == m.Reponse.en_attente:
            noter_engagement(t.receveur, tenu=False)
        elif echange.statut == m.StatutEchange.accepte and t.depose_le is None:
            noter_engagement(t.donneur, tenu=False)


def repechage(session: Session) -> int | None:
    """Repêchage du mardi : à la fin des 48 h de réponse au Grand Troc, une seconde passe du math trade.

    Les boucles refusées ou restées sans réponse ont libéré des objets : on relance le math trade sur le stock
    du dimanche resté libre (les objets publiés depuis attendent le dimanche suivant), sans reproposer un
    objet à qui l'a refusé ni solliciter qui n'a pas répondu. Les boucles trouvées suivent le calendrier du
    Grand Troc (48 h pour répondre, dépôts jusqu'au dimanche midi). Une seule fois par Grand Troc.
    Renvoie le nombre d'objets repêchés, ou None s'il n'y avait rien à faire à cette heure.
    """
    maintenant = _maintenant()
    grand_troc = dernier_grand_troc(session)
    if grand_troc is None or grand_troc.repeche_le is not None:
        return None
    if maintenant < grand_troc.cree_le + DELAI_REPONSE or any(
        e.statut == m.StatutEchange.propose for e in grand_troc.echanges
    ):
        return None  # les réponses ne sont pas toutes rentrées
    grand_troc.repeche_le = maintenant
    if maintenant + MARGE_REPECHAGE > fin_des_depots(grand_troc.jour):
        return 0  # trop tard pour répondre et déposer avant dimanche : tout repart au prochain Grand Troc

    contraintes = Contraintes()
    for e in grand_troc.echanges:
        if e.statut != m.StatutEchange.annule:
            continue
        refus = [t for t in e.transferts if t.reponse == m.Reponse.refusee]
        for t in refus:
            contraintes.transferts_refuses.add((str(t.donneur_id), str(t.objet_id), str(t.receveur_id)))
        if not refus:  # annulé faute de réponse : ceux qui n'ont pas répondu ne sont pas resollicités
            contraintes.utilisateurs_exclus.update(
                str(t.receveur_id) for t in e.transferts if t.reponse == m.Reponse.en_attente
            )
    marche = construire_marche(session, stock_avant=grand_troc.cree_le)
    solution = math_trade(marche, longueur_max=3, contraintes=contraintes, duree_max_s=DUREE_MAX_GRAND_TROC_S)
    echanges = [proposer(session, b, grand_troc=grand_troc) for b in solution.boucles]
    _sms_du_grand_troc(session, echanges)
    grand_troc.nb_objets_repeches = solution.nb_objets_echanges
    return solution.nb_objets_echanges
