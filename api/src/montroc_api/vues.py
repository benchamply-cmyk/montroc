"""Mise en forme des réponses qui dépendent de la personne qui les lit."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from troc_echanges import Boucle, distance_km

from . import matchs, services
from . import models as m
from .schemas import (
    BoucleProposee,
    CarteMatch,
    EchangeLecture,
    EtapeBoucle,
    Interesse,
    MatchLecture,
    Membre,
    ObjetLecture,
    ObjetResume,
    TransfertLecture,
)


def _voit_le_code(e: m.Echange, t: m.Transfert, lecteur_id: int | None) -> bool:
    """Le donneur marque son paquet avec le code ; le receveur ne l'obtient qu'une fois tout déposé."""
    if e.statut == m.StatutEchange.accepte:
        return lecteur_id == t.donneur_id
    return e.statut == m.StatutEchange.termine and lecteur_id == t.receveur_id


def _voit_l_adresse(t: m.Transfert, lecteur_id: int | None) -> bool:
    return lecteur_id in (t.donneur_id, t.receveur_id)


def echange(e: m.Echange, lecteur_id: int | None = None) -> EchangeLecture:
    modes = {t.mode for t in e.transferts}
    return EchangeLecture(
        id=e.id,
        statut=e.statut,
        proba_reussite=e.proba_reussite,
        cree_le=e.cree_le,
        expire_le=e.expire_le,
        grand_troc_jour=e.grand_troc.jour if e.grand_troc else None,
        par_match=e.par_match,
        point_de_depot=(services.point_de_depot(e) or None) if "point_relais" in modes else None,
        lieu_de_rencontre=(services.lieu_de_rencontre(e) or None) if "main_propre" in modes else None,
        avant_premiere=services.en_avant_premiere(e),
        transferts=[
            TransfertLecture(
                id=t.id,
                position=t.position,
                donneur_id=t.donneur_id,
                donneur_pseudo=t.donneur.pseudo,
                receveur_id=t.receveur_id,
                receveur_pseudo=t.receveur.pseudo,
                objet=ObjetResume.model_validate(t.objet),
                reponse=t.reponse,
                repondu_le=t.repondu_le,
                depose_le=t.depose_le,
                code_retrait=t.code_retrait if _voit_le_code(e, t, lecteur_id) else None,
                mode=t.mode,
                transporteur=t.transporteur,
                numero_suivi=t.numero_suivi,
                garantie=t.garantie,
                adresse_livraison=t.adresse_livraison if _voit_l_adresse(t, lecteur_id) else None,
            )
            for t in e.transferts
        ],
    )


def boucles(session: Session, liste: list[Boucle]) -> list[BoucleProposee]:
    ids_objets = {int(t.objet.id) for b in liste for t in b.transferts}
    ids_utilisateurs = {int(u) for b in liste for t in b.transferts for u in (t.donneur, t.receveur)}
    objets = {o.id: o for o in session.scalars(select(m.Objet).where(m.Objet.id.in_(ids_objets)))}
    pseudos = {
        u.id: u.pseudo
        for u in session.execute(
            select(m.Utilisateur.id, m.Utilisateur.pseudo).where(m.Utilisateur.id.in_(ids_utilisateurs))
        )
    }
    return [
        BoucleProposee(
            longueur=b.longueur,
            proba_reussite=b.proba_reussite,
            etapes=[
                EtapeBoucle(
                    donneur_id=int(t.donneur),
                    donneur_pseudo=pseudos[int(t.donneur)],
                    receveur_id=int(t.receveur),
                    receveur_pseudo=pseudos[int(t.receveur)],
                    objet=ObjetResume.model_validate(objets[int(t.objet.id)]),
                    acceptation_auto=t.auto,
                )
                for t in b.transferts
            ],
        )
        for b in liste
    ]


def _distance(lecteur: m.Utilisateur | None, objet: m.Objet) -> float | None:
    """Distance (km, arrondie) entre l'objet et la zone d'intérêt la plus proche du lecteur."""
    position = services.position(objet)
    if lecteur is None or position is None or not lecteur.zones_interet:
        return None
    return round(min(distance_km((z["latitude"], z["longitude"]), position) for z in lecteur.zones_interet), 1)


def carte(c: matchs.Carte, lecteur: m.Utilisateur | None = None) -> CarteMatch:
    return CarteMatch(
        distance_km=_distance(lecteur, c.objet),
        par_colis=lecteur is not None and services.acces(lecteur, c.objet) == "loin",
        objet=ObjetLecture.model_validate(c.objet),
        proprietaire=Membre.model_validate(c.objet.proprietaire),
        souhait_categorie=c.souhait.categorie_slug if c.souhait else None,
        souhait_sous_categorie=c.souhait.sous_categorie_slug if c.souhait else None,
        correspond_a_mes_souhaits=c.souhait is not None,
        il_aime=[ObjetResume.model_validate(o) for o in c.il_aime],
        il_cherche=[ObjetResume.model_validate(o) for o in c.il_cherche],
        sa_demande=c.sa_demande,
    )


def match(x: matchs.Match) -> MatchLecture:
    return MatchLecture(
        avec=Membre.model_validate(x.avec),
        ses_objets=[ObjetResume.model_validate(o) for o in x.ses_objets],
        mes_objets=[ObjetResume.model_validate(o) for o in x.mes_objets],
        depuis=x.depuis,
        echange_id=x.echange.id if x.echange else None,
    )


def interesse(i: matchs.Interesse) -> Interesse:
    return Interesse(
        membre=Membre.model_validate(i.membre),
        depuis=i.depuis,
        super_jaime=i.super,
        en_tete=i.en_tete,
        ses_objets=[ObjetResume.model_validate(o) for o in i.ses_objets],
    )
