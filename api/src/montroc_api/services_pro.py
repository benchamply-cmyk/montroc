"""Troc & Services : professionnels certifiés, négociations et contrats.

Un service professionnel est un ``Objet`` de la catégorie ``services`` (une sous-catégorie par métier) : il entre
tel quel dans le Match et dans les boucles du Grand Troc (contre des articles, ou contre un autre service), et
reste en ligne une fois rendu. Seul un membre dont le dossier pro est certifié par la modération pour ce métier peut
en proposer un.

À côté des boucles, la négociation permet d'engager un professionnel : le membre choisit le service, propose des
articles en échange, la conversation s'ouvre ; quand l'un propose des conditions (prestation, date, lieu, articles)
et que l'autre les accepte, TopTroc génère le contrat, qui fige l'accord. Les articles promis sont alors réservés,
et l'échange est mené quand les deux parties ont confirmé que tout a été fait.
"""

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from . import courriels, nomenclature, services
from . import models as m
from .config import get_settings
from .services import ErreurMetier

PIED_DE_CONTRAT = (
    "Ce contrat d'échange (troc, articles 1702 et suivants du Code civil) est conclu directement entre les deux "
    "parties ; TopTroc met en relation, vérifie les justificatifs des professionnels et conserve ce contrat, mais "
    "n'est pas partie à la prestation. Le professionnel reste seul responsable de la bonne exécution de sa "
    "prestation, de ses assurances et de ses obligations fiscales et sociales (un troc professionnel se déclare "
    "comme une vente). En cas de désaccord, chaque partie peut saisir la modération de TopTroc depuis le site."
)


def libelle_metier(slug: str) -> str:
    return dict(nomenclature.sous_categories(nomenclature.SERVICES)).get(slug, slug)


def est_certifie(session: Session, utilisateur: m.Utilisateur, metier: str | None) -> bool:
    return (
        metier is not None
        and session.scalar(
            select(m.ProfilPro.id).where(
                m.ProfilPro.utilisateur_id == utilisateur.id,
                m.ProfilPro.metier == metier,
                m.ProfilPro.statut == m.StatutProfilPro.certifie,
            )
        )
        is not None
    )


def retirer_services(session: Session, profil: m.ProfilPro) -> None:
    """Un dossier refusé ou supprimé : ses offres de service quittent le catalogue (celles engagées restent)."""
    for objet in session.scalars(
        select(m.Objet).where(
            m.Objet.proprietaire_id == profil.utilisateur_id,
            m.Objet.categorie_slug == nomenclature.SERVICES,
            m.Objet.sous_categorie_slug == profil.metier,
            m.Objet.statut == m.StatutObjet.disponible,
        )
    ):
        objet.statut = m.StatutObjet.retire


def services_du_pro(session: Session, profil: m.ProfilPro) -> list[m.Objet]:
    return list(
        session.scalars(
            select(m.Objet)
            .where(
                m.Objet.proprietaire_id == profil.utilisateur_id,
                m.Objet.categorie_slug == nomenclature.SERVICES,
                m.Objet.sous_categorie_slug == profil.metier,
                m.Objet.statut == m.StatutObjet.disponible,
            )
            .order_by(m.Objet.cree_le.desc())
        )
    )


def _objets_de(session: Session, utilisateur_id: int, ids: list[int]) -> list[m.Objet]:
    """Les objets ``ids`` de ce membre, dans l'ordre donné, tous disponibles ; sinon ErreurMetier."""
    if len(set(ids)) != len(ids):
        raise ErreurMetier("Un même article est proposé deux fois.")
    objets = {o.id: o for o in session.scalars(select(m.Objet).where(m.Objet.id.in_(ids)))}
    if any(objets.get(i) is None or objets[i].proprietaire_id != utilisateur_id for i in ids):
        raise ErreurMetier("On ne propose en échange que ses propres articles ou services.")
    if any(objets[i].statut != m.StatutObjet.disponible for i in ids):
        raise ErreurMetier("Un des articles proposés n'est plus disponible.")
    return [objets[i] for i in ids]


def contreparties(session: Session, negociation: m.Negociation) -> list[m.Objet]:
    if not negociation.contreparties:
        return []
    objets = {o.id: o for o in session.scalars(select(m.Objet).where(m.Objet.id.in_(negociation.contreparties)))}
    return [objets[i] for i in negociation.contreparties if i in objets]


def ouvrir(session: Session, initiateur: m.Utilisateur, objet_id: int, ids: list[int], message: str) -> m.Negociation:
    objet = session.get(m.Objet, objet_id)
    if objet is None or objet.statut != m.StatutObjet.disponible or objet.proprietaire.suspendu_le is not None:
        raise ErreurMetier("Ce service ou cet objet n'est plus proposé.")
    if objet.proprietaire_id == initiateur.id:
        raise ErreurMetier("C'est votre propre annonce.")
    proposes = _objets_de(session, initiateur.id, ids)
    if not objet.est_un_service and not any(o.est_un_service for o in proposes):
        raise ErreurMetier(
            "Troc & Services : au moins un service doit entrer dans l'échange. Pour des objets seuls, passez par le "
            "Match."
        )
    deja = session.scalar(
        select(m.Negociation.id).where(
            m.Negociation.initiateur_id == initiateur.id,
            m.Negociation.objet_id == objet.id,
            m.Negociation.statut.in_([m.StatutNegociation.ouverte, m.StatutNegociation.accord_propose]),
        )
    )
    if deja is not None:
        raise ErreurMetier(f"Une conversation est déjà ouverte sur cette annonce (n° {deja}).")
    negociation = m.Negociation(
        initiateur_id=initiateur.id,
        destinataire_id=objet.proprietaire_id,
        objet=objet,
        contreparties=[o.id for o in proposes],
    )
    negociation.messages.append(m.MessageNegociation(auteur_id=initiateur.id, texte=message.strip()))
    session.add(negociation)
    session.flush()
    _prevenir(
        session,
        objet.proprietaire,
        f"{initiateur.pseudo} vous propose un échange",
        f"{initiateur.pseudo} propose {_liste(proposes)} contre « {objet.titre} ». Répondez-lui et négociez "
        f"ensemble : {lien(negociation)}",
    )
    return negociation


def partie(negociation: m.Negociation, utilisateur: m.Utilisateur) -> str:
    """« initiateur » ou « destinataire » ; ErreurMetier pour quelqu'un d'autre."""
    if utilisateur.id == negociation.initiateur_id:
        return "initiateur"
    if utilisateur.id == negociation.destinataire_id:
        return "destinataire"
    raise ErreurMetier("Cette conversation ne vous concerne pas.")


def autre(negociation: m.Negociation, utilisateur: m.Utilisateur) -> m.Utilisateur:
    return negociation.destinataire if utilisateur.id == negociation.initiateur_id else negociation.initiateur


def _en_cours(negociation: m.Negociation) -> None:
    if negociation.statut not in (m.StatutNegociation.ouverte, m.StatutNegociation.accord_propose):
        raise ErreurMetier("Cette conversation est close.")


def ecrire(session: Session, negociation: m.Negociation, auteur: m.Utilisateur, texte: str) -> None:
    partie(negociation, auteur)
    _en_cours(negociation)
    negociation.messages.append(m.MessageNegociation(auteur_id=auteur.id, texte=texte.strip()))
    negociation.mis_a_jour_le = datetime.now(UTC)


def proposer_accord(session: Session, negociation: m.Negociation, auteur: m.Utilisateur, conditions: dict) -> None:
    """Des conditions, proposées par l'une ou l'autre partie : l'autre les accepte, ou répond et en propose d'autres."""
    partie(negociation, auteur)
    _en_cours(negociation)
    ids = conditions.pop("contreparties", None)
    if ids is not None:
        negociation.contreparties = [o.id for o in _objets_de(session, negociation.initiateur_id, ids)]
    conditions["date_prevue"] = conditions["date_prevue"].isoformat()
    negociation.conditions = conditions
    negociation.statut = m.StatutNegociation.accord_propose
    negociation.accord_propose_par_id = auteur.id
    negociation.mis_a_jour_le = datetime.now(UTC)
    articles = contreparties(session, negociation)
    negociation.messages.append(
        m.MessageNegociation(
            texte=f"{auteur.pseudo} propose un accord : {conditions['prestation']} — le {conditions['date_prevue']}, "
            f"{conditions['lieu']}, contre {_liste(articles)}. L'autre partie peut l'accepter ou répondre."
        )
    )
    destinataire = autre(negociation, auteur)
    _prevenir(
        session,
        destinataire,
        f"{auteur.pseudo} vous propose un accord",
        f"{auteur.pseudo} propose des conditions pour « {negociation.objet.titre} ». Acceptez-les pour que TopTroc "
        f"génère le contrat, ou répondez : {lien(negociation)}",
    )


def accepter(session: Session, negociation: m.Negociation, utilisateur: m.Utilisateur) -> m.ContratService:
    """L'autre partie accepte les conditions : TopTroc génère le contrat et réserve les articles promis."""
    partie(negociation, utilisateur)
    if negociation.statut != m.StatutNegociation.accord_propose:
        raise ErreurMetier("Aucun accord n'est proposé pour l'instant.")
    if negociation.accord_propose_par_id == utilisateur.id:
        raise ErreurMetier("L'accord se fait à deux : c'est à l'autre partie de l'accepter.")
    articles = _objets_de(session, negociation.initiateur_id, list(negociation.contreparties))
    objet = negociation.objet
    if objet.statut != m.StatutObjet.disponible:
        raise ErreurMetier(f"« {objet.titre} » n'est plus disponible.")
    maintenant = datetime.now(UTC)
    # Les articles partent : réservés jusqu'à la fin de l'échange. Un service, lui, peut être rendu à d'autres.
    for o in [objet, *articles]:
        if not o.est_un_service:
            o.statut = m.StatutObjet.reserve
    negociation.statut = m.StatutNegociation.conclue
    negociation.mis_a_jour_le = maintenant
    contrat = m.ContratService(negociation=negociation, numero="", texte="")
    session.add(contrat)
    session.flush()
    contrat.numero = f"TT-{maintenant.year}-{contrat.id:06d}"
    contrat.texte = texte_du_contrat(negociation, articles, contrat.numero, maintenant)
    negociation.messages.append(
        m.MessageNegociation(
            texte=f"Accord trouvé. TopTroc a généré le contrat n° {contrat.numero} : la prestation est officialisée."
        )
    )
    for u in (negociation.initiateur, negociation.destinataire):
        _prevenir(
            session,
            u,
            f"Contrat {contrat.numero} : votre échange Troc & Services est officialisé",
            f"L'accord est trouvé. Voici votre contrat :\n\n{contrat.texte}\n\nLe retrouver sur le site : "
            f"{lien(negociation)}",
        )
    return contrat


def annuler(session: Session, negociation: m.Negociation, utilisateur: m.Utilisateur) -> None:
    partie(negociation, utilisateur)
    _en_cours(negociation)
    negociation.statut = m.StatutNegociation.annulee
    negociation.mis_a_jour_le = datetime.now(UTC)
    negociation.messages.append(m.MessageNegociation(texte=f"{utilisateur.pseudo} a mis fin à la conversation."))


def confirmer(session: Session, contrat: m.ContratService, utilisateur: m.Utilisateur) -> None:
    """Une partie confirme que tout a été fait (prestation rendue, articles remis). Quand les deux l'ont dit,
    l'échange est mené : les articles sont échangés et chacun gagne un engagement tenu."""
    negociation = contrat.negociation
    role = partie(negociation, utilisateur)
    if contrat.statut != m.StatutContrat.en_cours:
        raise ErreurMetier("Ce contrat n'est plus en cours.")
    maintenant = datetime.now(UTC)
    if role == "initiateur":
        contrat.confirme_initiateur_le = contrat.confirme_initiateur_le or maintenant
    else:
        contrat.confirme_destinataire_le = contrat.confirme_destinataire_le or maintenant
    if contrat.confirme_initiateur_le and contrat.confirme_destinataire_le:
        contrat.statut = m.StatutContrat.realise
        for o in [negociation.objet, *contreparties(session, negociation)]:
            if not o.est_un_service and o.statut == m.StatutObjet.reserve:
                o.statut = m.StatutObjet.echange
        for u in (negociation.initiateur, negociation.destinataire):
            services.noter_engagement(u, tenu=True)
        negociation.messages.append(
            m.MessageNegociation(texte=f"Contrat {contrat.numero} réalisé : merci à tous les deux.")
        )


def texte_du_contrat(negociation: m.Negociation, articles: list[m.Objet], numero: str, maintenant: datetime) -> str:
    """Le contrat, figé au moment de l'accord : parties, engagements de chacun, date et lieu."""
    c = negociation.conditions
    initiateur, destinataire, objet = negociation.initiateur, negociation.destinataire, negociation.objet

    def engagement(u: m.Utilisateur, donnes: list[m.Objet]) -> str:
        lignes = []
        for o in donnes:
            if o.est_un_service:
                lignes.append(f"  - réaliser la prestation « {o.titre} » ({libelle_metier(o.sous_categorie_slug)})")
            else:
                etat = f", {o.etat.value.replace('_', ' ')}" if o.etat else ""
                lignes.append(f"  - remettre l'article « {o.titre} » (annonce n° {o.id}{etat})")
        return f"{u.pseudo} s'engage à :\n" + "\n".join(lignes)

    duree = f"\nDurée prévue : {c['duree']}" if c.get("duree") else ""
    return (
        f"CONTRAT D'ÉCHANGE TROC & SERVICES N° {numero}\n"
        f"Établi par TopTroc le {maintenant:%d/%m/%Y}.\n\n"
        f"Entre {initiateur.pseudo} (membre n° {initiateur.id}) "
        f"et {destinataire.pseudo} (membre n° {destinataire.id}).\n\n"
        f"{engagement(destinataire, [objet])}\n\n"
        f"{engagement(initiateur, articles)}\n\n"
        f"Prestation convenue : {c['prestation']}\n"
        f"Date prévue : {c['date_prevue']}\nLieu : {c['lieu']}{duree}\n\n"
        "Les articles sont remis en main propre au plus tard le jour de la prestation, sauf accord écrit dans la "
        "conversation. Aucune somme d'argent n'est due de part ni d'autre.\n\n"
        f"Accepté en ligne par les deux parties le {maintenant:%d/%m/%Y à %H:%M} (UTC).\n\n{PIED_DE_CONTRAT}"
    )


def mes_negociations(session: Session, utilisateur: m.Utilisateur) -> list[m.Negociation]:
    return list(
        session.scalars(
            select(m.Negociation)
            .where(or_(m.Negociation.initiateur_id == utilisateur.id, m.Negociation.destinataire_id == utilisateur.id))
            .order_by(m.Negociation.mis_a_jour_le.desc(), m.Negociation.id.desc())
        )
    )


def lien(negociation: m.Negociation) -> str:
    return f"{get_settings().site_url}/#negociation-{negociation.id}"


def _liste(objets: list[m.Objet]) -> str:
    return ", ".join(f"« {o.titre} »" for o in objets) or "rien"


def _prevenir(session: Session, u: m.Utilisateur, sujet: str, texte: str) -> None:
    courriels.apres_validation(session, courriels.envoyer, u.email, sujet, f"Bonjour {u.pseudo},\n\n{texte}")
