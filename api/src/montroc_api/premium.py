"""Troc Premium : les formules d'abonnement, leurs avantages et le paiement Stripe.

Échanger reste gratuit et illimité (publier, souhaits, Match, Grand Troc, main propre). Premium ajoute du confort
et une priorité encadrée : elle ne sert qu'à départager, après le nombre d'objets échangés ; un Premium ne fait
jamais tomber une boucle qui existait sans lui (voir ``services.priorite_premium``).
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models as m
from .config import get_settings

# Les avantages, chacun vérifié là où il sert.
SANS_PUB = "sans_pub"  # pas d'encart publicitaire
VOIR_QUI_AIME = "voir_qui_aime"  # la liste de ceux qui aiment chacun de mes objets
RETOUR_ARRIERE = "retour_arriere"  # annuler un « Non merci » du carrousel
APERCU_DU_STOCK = "apercu_du_stock"  # les objets qui iront au prochain Grand Troc et répondent à mes souhaits
AVANT_PREMIERE = "avant_premiere"  # mes propositions du Grand Troc dès 17 h, une heure avant tout le monde
SHORTLIST = "shortlist"  # mes demandes passent en tête des ShortLists des objets convoités
PRIORITE = "priorite"  # à nombre d'échanges égal, le Grand Troc me départage en premier
ZONES_MULTIPLES = "zones_multiples"  # jusqu'à 3 zones d'intérêt
GARANTIE_COLIS = "garantie_colis"  # mes envois par colis sont couverts par la Garantie TrocTroc
FAMILLE = "famille"  # 3 autres comptes profitent de ma formule

_CONFORT = {SANS_PUB, VOIR_QUI_AIME, RETOUR_ARRIERE, APERCU_DU_STOCK}
_PLUS = _CONFORT | {AVANT_PREMIERE, SHORTLIST, PRIORITE, ZONES_MULTIPLES, GARANTIE_COLIS}


@dataclass(frozen=True)
class Formule:
    cle: str
    nom: str
    prix_mois: float | None
    prix_an: float | None
    avantages: frozenset[str]
    super_jaime_par_semaine: int
    # Prix unique d'un passage (Pass Dimanche), valable ``duree_pass``.
    prix_unique: float | None = None


FORMULES = {
    f.cle: f
    for f in (
        Formule("essentiel", "Essentiel", 2.99, 24, frozenset(_CONFORT), 1),
        Formule("plus", "Plus", 5.99, 49, frozenset(_PLUS), 3),
        Formule("famille", "Famille", 8.99, 79, frozenset(_PLUS | {FAMILLE}), 3),
        Formule("pro", "Pro", 19, 190, frozenset(_CONFORT | {AVANT_PREMIERE, ZONES_MULTIPLES, GARANTIE_COLIS}), 0),
        Formule("pass", "Pass Dimanche", None, None, frozenset({AVANT_PREMIERE, APERCU_DU_STOCK}), 0, 1.99),
    )
}
DUREE_PASS = timedelta(days=7)
DUREE_MOIS = timedelta(days=31)
DUREE_AN = timedelta(days=366)
# Marge après la fin d'une période payée : le renouvellement Stripe a le temps d'arriver.
MARGE_RENOUVELLEMENT = timedelta(days=2)
FORMULE_ESSAI = "plus"
MEMBRES_FAMILLE = 3

# Zones d'intérêt : une sans Premium, trois avec ``ZONES_MULTIPLES``.
ZONES_GRATUITES = 1
ZONES_PREMIUM = 3
# Un objet devient « convoité » à partir de ce nombre de « J'aime » : son propriétaire voit sa ShortList.
SEUIL_CONVOITE = 5
TAILLE_SHORTLIST = 5
# Seuls les « J'aime » les plus récents d'un Premium passent en tête des ShortLists (« 5 actives »).
SHORTLISTS_ACTIVES = 5
# Bonus de priorité au Grand Troc : il s'ajoute à la priorité d'équité, qui ne départage qu'à nombre d'objets égal.
BONUS_PRIORITE = 2


def formule_active(utilisateur: m.Utilisateur, maintenant: datetime | None = None) -> Formule | None:
    """La formule dont le membre profite aujourd'hui : la sienne si elle court encore, sinon celle de la famille
    qui l'a ajouté."""
    maintenant = maintenant or datetime.now(UTC)
    if utilisateur.formule and utilisateur.premium_jusqu_au and utilisateur.premium_jusqu_au > maintenant:
        return FORMULES.get(utilisateur.formule)
    payeur = utilisateur.payeur_famille
    if payeur is not None and payeur.payeur_famille_id is None:
        formule = formule_active(payeur, maintenant)
        if formule is not None and FAMILLE in formule.avantages:
            return formule
    return None


def avantages(utilisateur: m.Utilisateur) -> frozenset[str]:
    formule = formule_active(utilisateur)
    return formule.avantages if formule else frozenset()


def a(utilisateur: m.Utilisateur, avantage: str) -> bool:
    return avantage in avantages(utilisateur)


def zones_max(utilisateur: m.Utilisateur) -> int:
    return ZONES_PREMIUM if a(utilisateur, ZONES_MULTIPLES) else ZONES_GRATUITES


def debut_de_semaine(maintenant: datetime) -> datetime:
    return (maintenant - timedelta(days=maintenant.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def super_jaime_restants(session: Session, utilisateur: m.Utilisateur) -> int:
    formule = formule_active(utilisateur)
    if formule is None:
        return 0
    deja = session.scalar(
        select(func.count())
        .select_from(m.Avis)
        .where(
            m.Avis.utilisateur_id == utilisateur.id,
            m.Avis.super,
            m.Avis.cree_le >= debut_de_semaine(datetime.now(UTC)),
        )
    )
    return max(0, formule.super_jaime_par_semaine - (deja or 0))


def activer(utilisateur: m.Utilisateur, cle: str, duree: timedelta, depuis: datetime | None = None) -> None:
    """Ouvre ou prolonge une formule. Une formule en cours est prolongée depuis sa fin, pas depuis aujourd'hui."""
    if cle not in FORMULES:
        raise ValueError(f"Formule inconnue : {cle}.")
    maintenant = depuis or datetime.now(UTC)
    debut = maintenant
    if utilisateur.formule == cle and utilisateur.premium_jusqu_au and utilisateur.premium_jusqu_au > maintenant:
        debut = utilisateur.premium_jusqu_au
    utilisateur.formule = cle
    utilisateur.premium_jusqu_au = debut + duree


def commencer_essai(utilisateur: m.Utilisateur) -> None:
    jours = get_settings().jours_essai_premium
    if not jours:
        raise ValueError("Pas d'essai gratuit en ce moment.")
    if utilisateur.essai_premium_le is not None:
        raise ValueError("L'essai gratuit a déjà été utilisé sur ce compte.")
    if formule_active(utilisateur) is not None:
        raise ValueError("Vous profitez déjà de Troc Premium.")
    utilisateur.essai_premium_le = datetime.now(UTC)
    activer(utilisateur, FORMULE_ESSAI, timedelta(days=jours))


# --- Paiement Stripe ---
#
# Les formules se vendent par des liens de paiement Stripe (Payment Links, réglage STRIPE_LIENS) : le site ajoute
# au lien ``client_reference_id = <membre>-<formule>_<mois|an>`` (ou ``-pass``). Stripe appelle ensuite
# /premium/stripe : ``checkout.session.completed`` ouvre la formule, ``invoice.paid`` la prolonge à chaque
# renouvellement. La vente se fait sur le site, pas dans les stores, pour éviter leur commission.

TOLERANCE_SIGNATURE_S = 300


class SignatureInvalide(Exception):
    pass


def verifier_signature(corps: bytes, entete: str, secret: str, maintenant: float | None = None) -> dict:
    """Vérifie l'en-tête ``Stripe-Signature`` (``t=…,v1=…``) et renvoie l'événement."""
    morceaux = [p.split("=", 1) for p in entete.split(",") if "=" in p]
    horodatage = next((v for k, v in morceaux if k == "t"), None)
    signatures = [v for k, v in morceaux if k == "v1"]
    if not secret or horodatage is None or not signatures:
        raise SignatureInvalide("Signature absente.")
    if abs((maintenant or time.time()) - int(horodatage)) > TOLERANCE_SIGNATURE_S:
        raise SignatureInvalide("Signature trop ancienne.")
    attendu = hmac.new(secret.encode(), f"{horodatage}.".encode() + corps, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(attendu, s) for s in signatures):
        raise SignatureInvalide("Signature incorrecte.")
    return json.loads(corps)


def duree_achetee(achat: str) -> tuple[str, timedelta]:
    """« plus_an » → (« plus », 366 jours) ; « pass » → (« pass », 7 jours)."""
    if achat == "pass":
        return "pass", DUREE_PASS
    cle, _, periode = achat.rpartition("_")
    if cle not in FORMULES or cle == "pass" or periode not in ("mois", "an"):
        raise ValueError(f"Achat inconnu : {achat}.")
    return cle, DUREE_MOIS if periode == "mois" else DUREE_AN


def traiter_evenement(session: Session, evenement: dict) -> str:
    """Applique un événement Stripe ; renvoie ce qui a été fait (pour le journal)."""
    objet = evenement.get("data", {}).get("object", {})
    genre = evenement.get("type")
    if genre == "checkout.session.completed":
        reference = objet.get("client_reference_id") or ""
        membre, _, achat = reference.partition("-")
        utilisateur = session.get(m.Utilisateur, int(membre)) if membre.isdigit() else None
        if utilisateur is None:
            return "paiement sans membre reconnu"
        cle, duree = duree_achetee(achat)
        activer(utilisateur, cle, duree)
        if objet.get("customer"):
            utilisateur.stripe_client = objet["customer"]
        return f"{cle} ouvert pour le membre {utilisateur.id}"
    if genre == "invoice.paid" and objet.get("billing_reason") != "subscription_create":
        utilisateur = session.scalars(
            select(m.Utilisateur).where(m.Utilisateur.stripe_client == objet.get("customer"))
        ).first()
        lignes = objet.get("lines", {}).get("data", [])
        fin = max((ligne.get("period", {}).get("end", 0) for ligne in lignes), default=0)
        if utilisateur is None or not fin or not utilisateur.formule:
            return "renouvellement ignoré"
        jusqu_au = datetime.fromtimestamp(fin, UTC) + MARGE_RENOUVELLEMENT
        if utilisateur.premium_jusqu_au is None or jusqu_au > utilisateur.premium_jusqu_au:
            utilisateur.premium_jusqu_au = jusqu_au
        return f"{utilisateur.formule} prolongé pour le membre {utilisateur.id}"
    return f"événement {genre} ignoré"
