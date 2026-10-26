"""Logique métier : passerelle entre la base et le moteur ``troc_echanges``.

Le moteur travaille en mémoire sur un ``Marche`` ; on le construit à partir des
objets disponibles et des souhaits en base, puis on enregistre les boucles
retenues sous forme d'``Echange``. Les e-mails des moments clés partent d'ici,
une fois la transaction validée.
"""

import json
import logging
import secrets
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from troc_echanges import Boucle, Contraintes, Marche, boucles_autour, math_trade
from troc_echanges import Objet as ObjetMoteur
from troc_echanges import Souhait as SouhaitMoteur

from . import courriels, sms
from . import models as m
from .config import get_settings

journal = logging.getLogger("montroc.services")

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
# Boucles de 2 à 4 personnes ; le moteur raccourcit à 3 si le marché est trop grand pour les calculer.
LONGUEUR_GRAND_TROC = 4
# Repêchage : à la fin des 48 h de réponse (mardi 18 h), une seconde passe sur le stock du dimanche resté libre.
# Il faut encore le temps de répondre (48 h) avant la fin des dépôts du dimanche midi.
MARGE_REPECHAGE = DELAI_REPONSE

# Fiabilité = (tenus + LISSAGE) / (tenus + manqués + LISSAGE) : 1 au départ, 0,9 après un premier manquement,
# et un manquement pèse de moins en moins à mesure que les engagements tenus s'accumulent.
LISSAGE_FIABILITE = 9
# Chance de dire oui à une boucle = (oui + 7) / (réponses + 10) : 70 % au départ (la valeur commune d'avant),
# puis le taux de chacun prend le dessus à mesure qu'il répond. Un refus prédit le prochain refus.
LISSAGE_ACCEPTATION = (7, 10)

# Équité, règle publique : à nombre d'objets échangés égal, le Grand Troc sert d'abord ceux qui ont le moins reçu
# ces 4 dernières semaines. Priorité = 1 + (3 - objets reçus), au moins 1 : 4 pour qui n'a rien reçu, 1 dès 3.
FENETRE_EQUITE = timedelta(days=28)
PLAFOND_EQUITE = 3


class ErreurMetier(Exception):
    """Règle métier non respectée : renvoyée au client en 409."""


def lien_echange(echange: m.Echange) -> str:
    return f"{get_settings().site_url}/#echange-{echange.id}"


def zone(z: str | None) -> str | None:
    """Zone comparable : « Marseille » et « marseille » sont la même ville."""
    return " ".join(z.split()).lower() if z and z.strip() else None


def souhait_moteur(s: m.Souhait) -> SouhaitMoteur:
    return SouhaitMoteur(
        categorie=s.categorie_slug,
        objet_id=None if s.objet_id is None else str(s.objet_id),
        rang=s.rang,
        quantite=s.quantite,
        acceptation_auto=s.acceptation_auto,
        sous_categorie=s.sous_categorie_slug,
        criteres=tuple(sorted(s.caracteristiques.items())),
        preferences=tuple(sorted(s.preferences.items())),
        etat_min=s.etat_min and s.etat_min.value,
        alternatives=tuple((a["categorie_slug"], a.get("sous_categorie_slug")) for a in s.alternatives),
        mode=s.mode_recherche.value,
        modes=frozenset(s.modes_echange),
        zones=frozenset(zone(z) for z in s.zones),
        ref=None if s.id is None else str(s.id),
    )


def objet_moteur(o: m.Objet, contre=frozenset()) -> ObjetMoteur:
    return ObjetMoteur(
        str(o.id),
        str(o.proprietaire_id),
        o.categorie_slug,
        o.titre,
        contre=frozenset(contre),
        contre_strict=o.contre_strict,
        sous_categorie=o.sous_categorie_slug,
        caracteristiques=tuple(sorted(o.caracteristiques.items())),
        etat=o.etat and o.etat.value,
        modes=frozenset(o.modes_echange),
        disponible=o.statut == m.StatutObjet.disponible,
    )


def souhait_correspond(souhait: m.Souhait, objet: m.Objet) -> bool:
    """La règle du moteur (``troc_echanges.Souhait.correspond``) : l'objet précis, ou l'objet visé ou une
    alternative selon le mode de recherche, l'état minimum, les critères obligatoires et un mode d'échange commun.
    La zone se vérifie à part (``zone_acceptee``)."""
    return souhait_moteur(souhait).correspond(objet_moteur(objet))


def zone_acceptee(souhait: m.Souhait | None, receveur: m.Utilisateur, donneur: m.Utilisateur) -> bool:
    """Comme au Grand Troc : la zone du donneur parmi celles de la demande si elle en précise, sinon la même
    que le receveur ; une ville inconnue ne bloque pas."""
    zd = zone(donneur.zone)
    if zd is None:
        return True
    if souhait is not None and souhait.zones:
        return zd in {zone(z) for z in souhait.zones}
    zr = zone(receveur.zone)
    return zr is None or zr == zd


def priorites(session: Session) -> dict[int, int]:
    """Priorité d'équité de ceux qui ont reçu un objet ces 4 dernières semaines (les autres : la plus haute)."""
    depuis = _maintenant() - FENETRE_EQUITE
    recus = session.execute(
        select(m.Transfert.receveur_id, func.count())
        .join(m.Transfert.echange)
        .where(m.Echange.cree_le >= depuis, m.Echange.statut != m.StatutEchange.annule)
        .group_by(m.Transfert.receveur_id)
    )
    return {u: 1 + max(0, PLAFOND_EQUITE - n) for u, n in recus}


def construire_marche(session: Session, stock_avant: datetime | None = None) -> Marche:
    """Le marché du moteur : comptes actifs, leurs souhaits et les objets disponibles.

    Les « J'aime » du Match sur des objets encore disponibles (qui ne répondent pas déjà à un de ses souhaits)
    forment un souhait de ces objets précis, de quantité 1 par défaut : un match qui n'a pas été conclu en 1 à 1
    peut ainsi aboutir au Grand Troc, à deux ou dans une boucle à trois.
    ``stock_avant`` : seulement les objets publiés avant cette date (repêchage sur le stock du dimanche).
    Chacun reçoit sa priorité d'équité (``priorites``).
    """
    marche = Marche()
    utilisateurs = session.scalars(
        select(m.Utilisateur).where(m.Utilisateur.suspendu_le.is_(None)).options(selectinload(m.Utilisateur.souhaits))
    ).all()
    coups_de_coeur: dict[int, list[m.Objet]] = {}
    for avis, objet in session.execute(
        select(m.Avis, m.Objet)
        .join(m.Avis.objet)
        .where(m.Avis.aime, m.Objet.statut == m.StatutObjet.disponible)
        .order_by(m.Avis.cree_le)
    ):
        coups_de_coeur.setdefault(avis.utilisateur_id, []).append(objet)
    # Indice de chaque souhait dans la liste de son auteur : c'est ainsi que le moteur désigne les listes « contre ».
    indice_souhait: dict[int, int] = {}
    priorite = priorites(session)
    reglages = get_settings()
    for u in utilisateurs:
        indice_souhait.update({s.id: i for i, s in enumerate(u.souhaits)})
        souhaits = [souhait_moteur(s) for s in u.souhaits]
        # Après les souhaits : les indices des listes « contre » restent ceux des souhaits. Tous ses « J'aime »
        # forment un seul souhait, classé après ses souhaits déclarés : dix coups de cœur ne lui font pas
        # recevoir dix objets le même dimanche (réglage COUPS_DE_COEUR_PAR_GRAND_TROC).
        aimes = {
            str(o.id) for o in coups_de_coeur.get(u.id, []) if not any(souhait_correspond(s, o) for s in u.souhaits)
        }
        if aimes:
            souhaits.append(
                SouhaitMoteur(
                    objets=frozenset(aimes),
                    rang=max((s.rang for s in u.souhaits), default=0) + 1,
                    quantite=reglages.coups_de_coeur_par_grand_troc,
                )
            )
        marche.ajouter_utilisateur(
            str(u.id),
            souhaits,
            zone=zone(u.zone),
            fiabilite=u.fiabilite,
            priorite=priorite.get(u.id, 1 + PLAFOND_EQUITE),
            acceptation=acceptation(u),
        )
    requete = select(m.Objet).where(m.Objet.statut == m.StatutObjet.disponible).options(selectinload(m.Objet.contre))
    if stock_avant is not None:
        requete = requete.where(m.Objet.cree_le <= stock_avant)
    for o in session.scalars(requete).all():
        if str(o.proprietaire_id) not in marche.utilisateurs:
            continue  # compte suspendu
        # Liste vide (souhaits tous supprimés) : l'objet repart contre n'importe lequel des souhaits.
        contre = {indice_souhait[s.id] for s in o.contre if s.utilisateur_id == o.proprietaire_id}
        marche.objets[str(o.id)] = objet_moteur(o, contre)
    return marche


def appliquer_plafond(session: Session, marche: Marche, grand_troc: m.GrandTroc | None = None) -> None:
    """Plafond d'échanges par personne et par Grand Troc (réglage ``PLAFOND_ECHANGES_GRAND_TROC``, 0 : aucun).

    Au repêchage, les boucles du dimanche encore en cours (proposées, acceptées ou terminées) comptent déjà."""
    plafond = get_settings().plafond_echanges_grand_troc
    if not plafond:
        return
    deja: dict[int, int] = {}
    if grand_troc is not None:
        deja = dict(
            session.execute(
                select(m.Transfert.receveur_id, func.count())
                .join(m.Transfert.echange)
                .where(m.Echange.grand_troc_id == grand_troc.id, m.Echange.statut.in_(ECHANGES_QUI_COMBLENT))
                .group_by(m.Transfert.receveur_id)
            ).all()
        )
    for u in marche.utilisateurs.values():
        u.plafond = max(0, plafond - deja.get(int(u.id), 0))


def contraintes_du_match(session: Session) -> Contraintes:
    """Les « Non merci » du Match : le Grand Troc ne propose pas un objet à qui l'a écarté."""
    contraintes = Contraintes()
    for utilisateur_id, objet_id, proprietaire_id in session.execute(
        select(m.Avis.utilisateur_id, m.Avis.objet_id, m.Objet.proprietaire_id)
        .join(m.Avis.objet)
        .where(m.Avis.aime.is_(False), m.Objet.statut == m.StatutObjet.disponible)
    ):
        contraintes.transferts_refuses.add((str(proprietaire_id), str(objet_id), str(utilisateur_id)))
    return contraintes


# Échanges dont les transferts comptent dans la quantité des souhaits : tous, sauf les annulés.
ECHANGES_QUI_COMBLENT = (m.StatutEchange.propose, m.StatutEchange.accepte, m.StatutEchange.termine)


def souhaits_consommes(session: Session, marche: Marche) -> dict[tuple[str, int], int]:
    """Ce que chaque souhait du marché a déjà reçu (ou va recevoir) : {(membre, indice du souhait) : objets}.

    Un échange proposé, accepté ou terminé compte ; un échange annulé libère le souhait.
    """
    recus = dict(
        session.execute(
            select(m.Transfert.souhait_id, func.count())
            .join(m.Transfert.echange)
            .where(m.Transfert.souhait_id.is_not(None), m.Echange.statut.in_(ECHANGES_QUI_COMBLENT))
            .group_by(m.Transfert.souhait_id)
        ).all()
    )
    consommes = {}
    for u in marche.utilisateurs.values():
        for i, s in enumerate(u.souhaits):
            n = recus.get(int(s.ref), 0) if s.ref is not None else 0
            if n:
                consommes[(u.id, i)] = n
    return consommes


def contraintes_du_marche(session: Session, marche: Marche) -> Contraintes:
    """Les contraintes de toute recherche sur ce marché : les « Non merci » du Match et les souhaits déjà comblés."""
    contraintes = contraintes_du_match(session)
    contraintes.souhaits_consommes.update(souhaits_consommes(session, marche))
    return contraintes


def suggestions(session: Session, utilisateur_id: int, limite: int = 10) -> list[Boucle]:
    marche = construire_marche(session)
    contraintes = contraintes_du_marche(session, marche)
    return boucles_autour(marche, str(utilisateur_id), limite=limite, contraintes=contraintes)


def _code_retrait() -> str:
    return "TRC-" + "".join(secrets.choice("23456789ABCDEFGHJKMNPQRSTUVWXYZ") for _ in range(5))


def proposer(
    session: Session,
    boucle: Boucle,
    auteur_id: int | None = None,
    grand_troc: m.GrandTroc | None = None,
    par_match: bool = False,
    remplacement: bool = False,
) -> m.Echange:
    """Enregistre une boucle, réserve ses objets et prévient les participants. À appeler dans une transaction.

    ``auteur_id`` : le participant qui a choisi cette boucle ; la proposer vaut accord pour sa part.
    ``par_match`` : accord 1 à 1 proposé après un match (voir ``matchs.conclure``).
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
        proba_reussite=boucle.proba_reussite,
        expire_le=maintenant + DELAI_REPONSE,
        grand_troc=grand_troc,
        par_match=par_match,
        remplacement=remplacement,
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
                souhait_id=None if t.souhait_ref is None else int(t.souhait_ref),
            )
        )
    session.add(echange)
    session.flush()  # identifiants, pour les liens des e-mails
    if not _mettre_a_jour_statut(session, echange):
        for t in echange.transferts:
            if t.reponse == m.Reponse.en_attente:
                donne = _transfert_du_donneur(echange, t.receveur_id).objet.titre
                if par_match:
                    courriels.apres_validation(
                        session,
                        courriels.accord_propose,
                        t.receveur.email,
                        t.receveur.pseudo,
                        t.donneur.pseudo,
                        donne,
                        t.objet.titre,
                        lien_echange(echange),
                    )
                else:
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
    marche = construire_marche(session)
    contraintes = contraintes_du_marche(session, marche)
    for b in boucles_autour(marche, str(auteur_id), limite=None, options_par_transfert=10, contraintes=contraintes):
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

    Il complète le Match (accords 1 à 1 à tout moment) : il trouve les boucles à trois et les échanges à deux
    que personne n'a vus, sur les objets sans match ou dont le match n'a pas été conclu.

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

    marche = construire_marche(session)
    appliquer_plafond(session, marche)
    solution = math_trade(
        marche,
        longueur_max=LONGUEUR_GRAND_TROC,
        objectif=get_settings().objectif_grand_troc,
        contraintes=contraintes_du_marche(session, marche),
        duree_max_s=DUREE_MAX_GRAND_TROC_S,
    )
    grand_troc = m.GrandTroc(
        jour=jour,
        optimal=solution.optimal,
        duree_s=solution.duree_s,
        nb_boucles=0,
        nb_objets=0,
        nb_participants=0,
        calcul=trace_du_calcul(solution),
    )
    session.add(grand_troc)
    session.flush()
    echanges = _proposer_les_boucles(session, solution.boucles, grand_troc)
    # Les chiffres de ce qui a vraiment été proposé (une boucle devenue impossible pendant le calcul est sautée).
    grand_troc.nb_boucles = len(echanges)
    grand_troc.nb_objets = sum(len(e.transferts) for e in echanges)
    grand_troc.nb_participants = len({t.donneur_id for e in echanges for t in e.transferts})
    _sms_du_grand_troc(session, echanges)
    return grand_troc, echanges, True, f"{len(echanges)} boucle(s) proposée(s), {grand_troc.nb_objets} objets."


def _proposer_les_boucles(
    session: Session, boucles: list[Boucle], grand_troc: m.GrandTroc, remplacement: bool = False
) -> list[m.Echange]:
    """Propose chaque boucle du Grand Troc ou du repêchage. Une boucle dont un objet n'est plus disponible
    (réservé par un accord du Match pendant le calcul, retiré par son propriétaire) est sautée : les autres
    partent quand même, au lieu d'annuler tout le Grand Troc. ``proposer`` vérifie avant de rien modifier."""
    echanges = []
    for b in boucles:
        try:
            echanges.append(proposer(session, b, grand_troc=grand_troc, remplacement=remplacement))
        except ErreurMetier as e:
            journal.warning("Grand Troc %s : boucle %s sautée (%s)", grand_troc.jour, b.objets, e)
    return echanges


def trace_du_calcul(solution) -> dict:
    """Ce que le moteur a fait, à garder avec le Grand Troc : moteur (exact ou heuristique), optimum prouvé,
    longueur de boucle retenue, statuts des étapes de CP-SAT, nombre de copies ou de boucles candidates…
    Sans cette trace, impossible de savoir après coup si la production a basculé en mode dégradé."""
    trace = {
        "moteur": solution.moteur,
        "optimal": solution.optimal,
        "duree_s": round(solution.duree_s, 3),
        "candidats": solution.candidats,
        **solution.stats,
    }
    return json.loads(json.dumps(trace, default=str))  # JSON pur : nombres, textes, listes


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
    if not echange.par_match:  # un accord du Match, qu'on a demandé soi-même, ne dit rien du Grand Troc
        noter_reponse(transfert.receveur, accepte)
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
    maintenant = _maintenant()
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


def noter_reponse(utilisateur: m.Utilisateur, oui: bool) -> None:
    """Compte un « oui » ou un « non » à une boucle proposée (voir ``acceptation``)."""
    if oui:
        utilisateur.reponses_oui += 1
    else:
        utilisateur.reponses_non += 1


def acceptation(utilisateur: m.Utilisateur) -> float:
    """Chance qu'il dise oui à la prochaine boucle : son taux de « oui », lissé vers 70 % (``LISSAGE_ACCEPTATION``).
    Une absence de réponse n'y entre pas : c'est un manquement, compté dans la fiabilité."""
    a_priori, poids = LISSAGE_ACCEPTATION
    reponses = (utilisateur.reponses_oui or 0) + (utilisateur.reponses_non or 0)
    return ((utilisateur.reponses_oui or 0) + a_priori) / (reponses + poids)


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
        e.statut == m.StatutEchange.propose and not e.remplacement for e in grand_troc.echanges
    ):
        return None  # les réponses ne sont pas toutes rentrées
    grand_troc.repeche_le = maintenant
    if maintenant + MARGE_REPECHAGE > fin_des_depots(grand_troc.jour):
        return 0  # trop tard pour répondre et déposer avant dimanche : tout repart au prochain Grand Troc

    # Les boucles acceptées dimanche comptent dans les souhaits : pas de deuxième poussette au repêchage.
    marche, contraintes = _marche_apres_refus(session, grand_troc)
    solution = math_trade(
        marche,
        longueur_max=LONGUEUR_GRAND_TROC,
        objectif=get_settings().objectif_grand_troc,
        contraintes=contraintes,
        duree_max_s=DUREE_MAX_GRAND_TROC_S,
    )
    echanges = _proposer_les_boucles(session, solution.boucles, grand_troc)
    _sms_du_grand_troc(session, echanges)
    grand_troc.nb_objets_repeches = sum(len(e.transferts) for e in echanges)
    grand_troc.calcul_repechage = trace_du_calcul(solution)
    return grand_troc.nb_objets_repeches


def _marche_apres_refus(session: Session, grand_troc: m.GrandTroc) -> tuple[Marche, Contraintes]:
    """Le stock du dimanche resté libre, sans reproposer un objet à qui l'a refusé ni solliciter qui n'a pas
    répondu (repêchage du mardi et remplaçants), sous le plafond d'échanges par personne."""
    marche = construire_marche(session, stock_avant=grand_troc.cree_le)
    appliquer_plafond(session, marche, grand_troc)
    contraintes = contraintes_du_marche(session, marche)
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
    return marche, contraintes


def remplacements(session: Session) -> int | None:
    """Remplaçants plus tôt : dès qu'un refus annule une boucle du Grand Troc, ses objets libérés repartent.

    Appelé chaque heure pendant les 48 h de réponse. Au lieu d'attendre le repêchage du mardi 18 h (qui exige
    toutes les réponses), on relance le math trade sur le stock du dimanche resté libre et on ne garde que les
    boucles qui utilisent au moins un objet libéré depuis le dernier passage : les partenaires lâchés reçoivent
    une autre proposition dans l'heure. Ces boucles suivent le calendrier du Grand Troc ; elles n'empêchent pas
    le repêchage du mardi, qui reprend ce qui reste.
    Renvoie le nombre d'objets proposés, ou None s'il n'y avait aucun objet libéré à replacer.
    """
    maintenant = _maintenant()
    grand_troc = dernier_grand_troc(session)
    if grand_troc is None or grand_troc.repeche_le is not None:
        return None
    if maintenant >= grand_troc.cree_le + DELAI_REPONSE:
        return None  # le repêchage du mardi prend le relais
    nouveaux = [
        e for e in grand_troc.echanges if e.statut == m.StatutEchange.annule and e.remplacants_cherches_le is None
    ]
    if not nouveaux:
        return None
    for e in nouveaux:
        e.remplacants_cherches_le = maintenant
    liberes = {
        str(t.objet_id)
        for e in nouveaux
        for t in e.transferts
        if t.objet is not None and t.objet.statut == m.StatutObjet.disponible
    }
    if not liberes or maintenant + MARGE_REPECHAGE > fin_des_depots(grand_troc.jour):
        return 0

    marche, contraintes = _marche_apres_refus(session, grand_troc)
    solution = math_trade(
        marche,
        longueur_max=LONGUEUR_GRAND_TROC,
        objectif=get_settings().objectif_grand_troc,
        contraintes=contraintes,
        duree_max_s=DUREE_MAX_GRAND_TROC_S,
    )
    boucles = [b for b in solution.boucles if liberes & set(b.objets)]
    echanges = _proposer_les_boucles(session, boucles, grand_troc, remplacement=True)
    _sms_du_grand_troc(session, echanges)
    remplaces = sum(len(e.transferts) for e in echanges)
    grand_troc.nb_objets_remplaces += remplaces
    return remplaces
