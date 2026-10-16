"""Le Match : coups de cœur sur les objets des autres, et accord 1 à 1 dès que l'intérêt est réciproque.

Comme sur une appli de rencontre, chacun fait défiler un carrousel d'objets qui correspondent à ses souhaits
et répond « J'aime » ou « Non merci ». Quand deux personnes aiment chacune un objet de l'autre, c'est un
match : elles concluent l'échange tout de suite, sans attendre dimanche. Le Grand Troc du dimanche s'occupe
du reste : les boucles à trois et les échanges à deux que personne n'a vus.
"""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from troc_echanges import Boucle
from troc_echanges import Objet as ObjetMoteur
from troc_echanges import Transfert as TransfertMoteur

from . import courriels
from . import models as m
from .config import get_settings
from .services import ErreurMetier, proposer, souhait_correspond

ACTIFS = (m.StatutEchange.propose, m.StatutEchange.accepte)


def _zone(z: str | None) -> str | None:
    return z.strip().lower() if z and z.strip() else None


def meme_zone(a: m.Utilisateur, b: m.Utilisateur) -> bool:
    """Comme au Grand Troc : une ville inconnue ne bloque pas, deux villes différentes oui."""
    za, zb = _zone(a.zone), _zone(b.zone)
    return za is None or zb is None or za == zb


def lien_match() -> str:
    return f"{get_settings().site_url}/#match"


# Un match reste affiché pendant l'accord en cours, quand ses objets sont réservés.
EN_JEU = (m.StatutObjet.disponible, m.StatutObjet.reserve)


def _mes_objets(session: Session, utilisateur_id: int, statuts=(m.StatutObjet.disponible,)) -> list[m.Objet]:
    return list(
        session.scalars(select(m.Objet).where(m.Objet.proprietaire_id == utilisateur_id, m.Objet.statut.in_(statuts)))
    )


def _coups_de_coeur_recus(session: Session, mes_objets: list[m.Objet]) -> dict[int, list[m.Objet]]:
    """Qui aime lequel de mes objets disponibles : {membre : [mes objets qu'il aime]}."""
    par_id = {o.id: o for o in mes_objets}
    recus: dict[int, list[m.Objet]] = {}
    for avis in session.scalars(
        select(m.Avis).where(m.Avis.objet_id.in_(par_id), m.Avis.aime).order_by(m.Avis.cree_le.desc())
    ):
        recus.setdefault(avis.utilisateur_id, []).append(par_id[avis.objet_id])
    return recus


# --- Le carrousel ---


@dataclass
class Carte:
    objet: m.Objet
    # Le souhait (catégorie ou objet précis) auquel l'objet répond, s'il y en a un.
    souhait: m.Souhait | None
    # Mes objets que son propriétaire aime déjà : un « J'aime » fait un match tout de suite.
    il_aime: list[m.Objet] = field(default_factory=list)
    # Mes objets qui répondent à ses souhaits : il y a des chances qu'il aime aussi.
    il_cherche: list[m.Objet] = field(default_factory=list)
    # Ce qu'il a écrit pour décrire ces souhaits-là (« Je demande »).
    sa_demande: str | None = None

    @property
    def score(self) -> tuple:
        return (
            bool(self.il_aime),
            self.souhait is not None and bool(self.il_cherche),
            self.souhait is not None,
            bool(self.il_cherche),
            -(self.souhait.rang if self.souhait else 99),
            self.objet.cree_le,
        )


def carrousel(session: Session, moi: m.Utilisateur, limite: int = 20) -> list[Carte]:
    """Les objets à montrer, les plus prometteurs d'abord : ceux qui feraient un match tout de suite, puis
    ceux qui répondent à mes souhaits et dont le propriétaire cherche ce que j'ai, puis le reste.

    Un objet déjà aimé ou écarté ne revient pas.
    """
    mes_objets = _mes_objets(session, moi.id)
    # Mes souhaits, le préféré (rang 1) d'abord : une carte répond au premier qui lui correspond.
    mes_souhaits = sorted(moi.souhaits, key=lambda s: (s.rang, s.id))
    categories = {s.categorie_slug for s in mes_souhaits if s.categorie_slug}
    precis = {s.objet_id for s in mes_souhaits if s.objet_id}

    # Ce que les autres cherchent parmi mes objets (souhaits) et ce qu'ils aiment déjà (coups de cœur).
    il_cherche: dict[int, list[m.Objet]] = {}
    sa_demande: dict[int, str] = {}
    if mes_objets:
        for s in session.scalars(
            select(m.Souhait).where(
                m.Souhait.utilisateur_id != moi.id,
                or_(
                    m.Souhait.categorie_slug.in_({o.categorie_slug for o in mes_objets}),
                    m.Souhait.objet_id.in_({o.id for o in mes_objets}),
                ),
            )
        ):
            voulus = [o for o in mes_objets if souhait_correspond(s, o)]
            if voulus:
                liste = il_cherche.setdefault(s.utilisateur_id, [])
                liste += [o for o in voulus if o not in liste]
                if s.precisions:
                    sa_demande.setdefault(s.utilisateur_id, s.precisions)
    il_aime = _coups_de_coeur_recus(session, mes_objets)

    deja_vus = select(m.Avis.objet_id).where(m.Avis.utilisateur_id == moi.id)
    criteres = [m.Objet.proprietaire_id.in_(set(il_cherche) | set(il_aime))]
    if categories:
        criteres.append(m.Objet.categorie_slug.in_(categories))
    if precis:
        criteres.append(m.Objet.id.in_(precis))
    candidats = session.scalars(
        select(m.Objet)
        .join(m.Objet.proprietaire)
        .where(
            m.Objet.statut == m.StatutObjet.disponible,
            m.Objet.proprietaire_id != moi.id,
            m.Utilisateur.suspendu_le.is_(None),
            m.Objet.id.not_in(deja_vus),
            or_(*criteres),
        )
        .options(selectinload(m.Objet.proprietaire))
    )
    cartes = [
        Carte(
            objet=o,
            souhait=next((s for s in mes_souhaits if souhait_correspond(s, o)), None),
            il_aime=il_aime.get(o.proprietaire_id, []),
            il_cherche=il_cherche.get(o.proprietaire_id, []),
            sa_demande=sa_demande.get(o.proprietaire_id),
        )
        for o in candidats
        if meme_zone(moi, o.proprietaire)
    ]
    # La requête prend toute la catégorie : on écarte ce qu'une sous-catégorie ou une taille demandées excluent,
    # sauf si son propriétaire cherche ou aime déjà un de mes objets.
    cartes = [c for c in cartes if c.souhait is not None or c.il_aime or c.il_cherche]
    cartes.sort(key=lambda c: c.score, reverse=True)
    return cartes[:limite]


# --- Coups de cœur et matchs ---


@dataclass
class Match:
    avec: m.Utilisateur
    # Ses objets que j'aime, et mes objets qu'il aime (disponibles, ou réservés par notre accord en cours).
    ses_objets: list[m.Objet]
    mes_objets: list[m.Objet]
    depuis: datetime
    # L'accord 1 à 1 en cours entre nous, s'il y en a un.
    echange: m.Echange | None = None


def donner_avis(session: Session, moi: m.Utilisateur, objet_id: int, aime: bool) -> Match | None:
    """« J'aime » ou « Non merci » sur un objet. Renvoie le match avec son propriétaire, s'il y en a un ;
    l'e-mail « C'est un match » ne part que la première fois."""
    objet = session.get(m.Objet, objet_id)
    if objet is None or objet.proprietaire_id == moi.id or objet.statut != m.StatutObjet.disponible:
        raise ErreurMetier("Cet objet n'est plus proposé.")
    autre = objet.proprietaire
    avant = match_avec(session, moi, autre)

    avis = session.get(m.Avis, (moi.id, objet_id))
    if avis is None:
        session.add(m.Avis(utilisateur_id=moi.id, objet_id=objet_id, aime=aime))
    else:
        avis.aime = aime
    session.flush()
    if not aime:
        return None
    match = match_avec(session, moi, autre)
    if match is not None and avant is None:
        courriels.apres_validation(
            session, courriels.c_est_un_match, autre.email, autre.pseudo, moi.pseudo, lien_match()
        )
    return match


def match_avec(session: Session, moi: m.Utilisateur, autre: m.Utilisateur) -> Match | None:
    return next((x for x in matchs(session, moi, avec_id=autre.id)), None)


def matchs(session: Session, moi: m.Utilisateur, avec_id: int | None = None) -> list[Match]:
    """Mes matchs : les membres dont j'aime un objet et qui aiment un des miens, les plus récents d'abord."""
    recus = _coups_de_coeur_recus(session, _mes_objets(session, moi.id, EN_JEU))
    if avec_id is not None:
        recus = {k: v for k, v in recus.items() if k == avec_id}
    if not recus:
        return []
    donnes: dict[int, list[tuple[m.Objet, datetime]]] = {}
    for avis, objet in session.execute(
        select(m.Avis, m.Objet)
        .join(m.Avis.objet)
        .where(
            m.Avis.utilisateur_id == moi.id,
            m.Avis.aime,
            m.Objet.statut.in_(EN_JEU),
            m.Objet.proprietaire_id.in_(recus),
        )
        .order_by(m.Avis.cree_le.desc())
    ):
        donnes.setdefault(objet.proprietaire_id, []).append((objet, avis.cree_le))

    resultat = []
    for autre_id, siens in donnes.items():
        autre = session.get(m.Utilisateur, autre_id)
        if autre.suspendu_le is not None:
            continue
        # Un objet réservé ne compte que s'il l'est par notre accord (pas par un échange avec quelqu'un d'autre).
        echange = accord_en_cours(session, moi.id, autre_id)
        dans_l_accord = {t.objet_id for t in echange.transferts} if echange else set()

        def en_jeu(o: m.Objet) -> bool:
            return o.statut == m.StatutObjet.disponible or o.id in dans_l_accord  # noqa: B023

        ses_objets = [o for o, _ in siens if en_jeu(o)]
        mes_objets = [o for o in recus[autre_id] if en_jeu(o)]
        if ses_objets and mes_objets:
            resultat.append(Match(autre, ses_objets, mes_objets, max(q for _, q in siens), echange))
    resultat.sort(key=lambda x: x.depuis, reverse=True)
    return resultat


def accord_en_cours(session: Session, a: int, b: int) -> m.Echange | None:
    for echange in session.scalars(
        select(m.Echange)
        .join(m.Echange.transferts)
        .where(m.Echange.par_match, m.Echange.statut.in_(ACTIFS), m.Transfert.donneur_id == a)
        .order_by(m.Echange.cree_le.desc())
    ):
        if any(t.donneur_id == b for t in echange.transferts):
            return echange
    return None


def conclure(session: Session, moi: m.Utilisateur, mon_objet_id: int, son_objet_id: int) -> m.Echange:
    """Je propose l'accord : je donne ``mon_objet``, je reçois ``son_objet``. Ma part est acceptée d'office,
    l'autre a 48 h pour dire oui ; ensuite, comme pour tout échange, chacun dépose dans les 7 jours."""
    mon_objet, son_objet = session.get(m.Objet, mon_objet_id), session.get(m.Objet, son_objet_id)
    if mon_objet is None or mon_objet.proprietaire_id != moi.id:
        raise ErreurMetier("Vous ne pouvez proposer que l'un de vos objets.")
    if son_objet is None or son_objet.proprietaire_id == moi.id:
        raise ErreurMetier("Cet objet n'est plus proposé.")
    autre = son_objet.proprietaire
    if autre.suspendu_le is not None:
        raise ErreurMetier("Cet objet n'est plus proposé.")
    if autre.id not in _coups_de_coeur_recus(session, _mes_objets(session, moi.id)):
        raise ErreurMetier(f"Pas encore de match avec {autre.pseudo} : il faut qu'un de vos objets lui plaise.")
    # Proposer l'échange vaut « J'aime » sur l'objet reçu.
    avis = session.get(m.Avis, (moi.id, son_objet.id))
    if avis is None:
        session.add(m.Avis(utilisateur_id=moi.id, objet_id=son_objet.id, aime=True))
    else:
        avis.aime = True

    def transfert(objet: m.Objet, receveur: m.Utilisateur) -> TransfertMoteur:
        return TransfertMoteur(
            donneur=str(objet.proprietaire_id),
            receveur=str(receveur.id),
            objet=ObjetMoteur(str(objet.id), str(objet.proprietaire_id), objet.categorie_slug, objet.titre),
            souhait_idx=-1,
            rang=1,
            auto=False,
            proba_acceptation=1.0,
        )

    boucle = Boucle(
        transferts=(transfert(mon_objet, autre), transfert(son_objet, moi)),
        proba_reussite=min(1.0, moi.fiabilite * autre.fiabilite),
    )
    return proposer(session, boucle, auteur_id=moi.id, par_match=True)
