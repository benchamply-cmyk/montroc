"""Mise en forme des réponses qui dépendent de la personne qui les lit."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from troc_echanges import Boucle

from . import matchs
from . import models as m
from .config import get_settings
from .schemas import (
    BoucleProposee,
    CarteMatch,
    EchangeLecture,
    EtapeBoucle,
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


def echange(e: m.Echange, lecteur_id: int | None = None) -> EchangeLecture:
    return EchangeLecture(
        id=e.id,
        statut=e.statut,
        proba_reussite=e.proba_reussite,
        cree_le=e.cree_le,
        expire_le=e.expire_le,
        grand_troc_jour=e.grand_troc.jour if e.grand_troc else None,
        par_match=e.par_match,
        point_de_depot=get_settings().point_de_depot or None,
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


def carte(c: matchs.Carte) -> CarteMatch:
    return CarteMatch(
        objet=ObjetLecture.model_validate(c.objet),
        proprietaire=Membre.model_validate(c.objet.proprietaire),
        souhait_categorie=c.souhait.categorie_slug if c.souhait else None,
        correspond_a_mes_souhaits=c.souhait is not None,
        il_aime=[ObjetResume.model_validate(o) for o in c.il_aime],
        il_cherche=[ObjetResume.model_validate(o) for o in c.il_cherche],
    )


def match(x: matchs.Match) -> MatchLecture:
    return MatchLecture(
        avec=Membre.model_validate(x.avec),
        ses_objets=[ObjetResume.model_validate(o) for o in x.ses_objets],
        mes_objets=[ObjetResume.model_validate(o) for o in x.mes_objets],
        depuis=x.depuis,
        echange_id=x.echange.id if x.echange else None,
    )
