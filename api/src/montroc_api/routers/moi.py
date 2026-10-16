"""Mon espace : profil, mes objets, mes souhaits, mes échanges possibles et en cours."""

import hashlib
import time

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from .. import models as m
from .. import nomenclature, services, vues
from ..config import get_settings
from ..deps import SessionDep, UtilisateurConnecte, obtenir_ou_404
from ..schemas import (
    BoucleProposee,
    EchangeLecture,
    Moi,
    MoiModification,
    MonObjet,
    ObjetCreation,
    ObjetModification,
    PhotoSignature,
    SouhaitCreation,
    SouhaitLecture,
)
from .auth import moi

router = APIRouter(prefix="/moi", tags=["mon espace"])


@router.get("", response_model=Moi)
def lire(utilisateur: UtilisateurConnecte):
    return moi(utilisateur)


@router.patch("", response_model=Moi)
def modifier(donnees: MoiModification, utilisateur: UtilisateurConnecte, session: SessionDep):
    if donnees.pseudo is not None and session.scalar(
        select(m.Utilisateur.id).where(
            func.lower(m.Utilisateur.pseudo) == donnees.pseudo.lower(), m.Utilisateur.id != utilisateur.id
        )
    ):
        raise HTTPException(409, "Ce pseudo est déjà pris.")
    for champ, valeur in donnees.model_dump(exclude_unset=True).items():
        setattr(utilisateur, champ, valeur)
    session.commit()
    return moi(utilisateur)


@router.delete("", status_code=204)
def supprimer(utilisateur: UtilisateurConnecte, session: SessionDep):
    """Supprime le compte et ses données. Les échanges en cours sont d'abord annulés pour les autres."""
    for echange in services.echanges_de(session, utilisateur.id, actifs=True):
        services.annuler(session, echange, f"{utilisateur.pseudo} a quitté TrocTroc.")
    session.flush()
    session.delete(utilisateur)
    session.commit()


# --- Objets ---


@router.get("/photos/signature", response_model=PhotoSignature)
def signature_photo(_utilisateur: UtilisateurConnecte):
    """Autorise le navigateur à envoyer une photo sur Cloudinary (signature valable une heure)."""
    cloudinary = get_settings().cloudinary
    if cloudinary is None:
        raise HTTPException(503, "L'envoi de photos n'est pas encore configuré.")
    nom, cle, secret = cloudinary
    parametres = {"folder": "objets", "timestamp": int(time.time())}
    a_signer = "&".join(f"{k}={v}" for k, v in sorted(parametres.items())) + secret
    return PhotoSignature(
        url_envoi=f"https://api.cloudinary.com/v1_1/{nom}/image/upload",
        api_key=cle,
        signature=hashlib.sha1(a_signer.encode()).hexdigest(),
        **parametres,
    )


def _mes_souhaits(session, utilisateur: m.Utilisateur, ids: list[int]) -> list[m.Souhait]:
    """Les souhaits d'une liste « contre » : seulement les miens."""
    souhaits = session.scalars(
        select(m.Souhait).where(m.Souhait.id.in_(set(ids)), m.Souhait.utilisateur_id == utilisateur.id)
    ).all()
    if len(souhaits) != len(set(ids)):
        raise HTTPException(409, "Un objet ne se donne que contre vos propres souhaits.")
    return list(souhaits)


@router.post("/objets", response_model=MonObjet, status_code=201)
def ajouter_objet(donnees: ObjetCreation, utilisateur: UtilisateurConnecte, session: SessionDep):
    obtenir_ou_404(session, m.Categorie, donnees.categorie_slug)
    contre = _mes_souhaits(session, utilisateur, donnees.contre_souhait_ids)
    objet = m.Objet(proprietaire_id=utilisateur.id, contre=contre, **donnees.model_dump(exclude={"contre_souhait_ids"}))
    session.add(objet)
    session.commit()
    return objet


@router.get("/objets", response_model=list[MonObjet])
def lister_objets(utilisateur: UtilisateurConnecte, session: SessionDep):
    return session.scalars(
        select(m.Objet)
        .where(m.Objet.proprietaire_id == utilisateur.id, m.Objet.statut != m.StatutObjet.echange)
        .order_by(m.Objet.cree_le.desc())
    ).all()


@router.patch("/objets/{objet_id}", response_model=MonObjet)
def modifier_objet(objet_id: int, donnees: ObjetModification, utilisateur: UtilisateurConnecte, session: SessionDep):
    objet = obtenir_ou_404(session, m.Objet, objet_id)
    if objet.proprietaire_id != utilisateur.id:
        raise HTTPException(404, f"Objet {objet_id} introuvable.")
    changements = donnees.model_dump(exclude_unset=True)
    if objet.statut == m.StatutObjet.modere:
        raise HTTPException(409, "Cet objet a été retiré par la modération.")
    if "statut" in changements and objet.statut not in (m.StatutObjet.disponible, m.StatutObjet.retire):
        raise HTTPException(409, "Cet objet est engagé dans un échange.")
    if changements.get("statut") == m.StatutObjet.disponible and not (objet.photo_url and objet.etat):
        raise HTTPException(409, "Ajoutez une photo et l'état avant de remettre cet objet en ligne.")
    if (ids := changements.pop("contre_souhait_ids", None)) is not None:
        objet.contre = _mes_souhaits(session, utilisateur, ids)
    if changements.get("contre_strict", False) is None:
        del changements["contre_strict"]
    for champ in ("caracteristiques", "modes_echange"):
        if champ in changements and changements[champ] is None:
            del changements[champ]
    if "sous_categorie_slug" in changements or "caracteristiques" in changements:
        sous_categorie = changements.get("sous_categorie_slug", objet.sous_categorie_slug)
        valeurs = changements.get("caracteristiques", objet.caracteristiques)
        try:
            changements["caracteristiques"] = nomenclature.verifier(
                objet.categorie_slug, sous_categorie, valeurs, demande=False
            )
        except ValueError as e:
            raise HTTPException(422, str(e)) from None
    for champ, valeur in changements.items():
        setattr(objet, champ, valeur)
    session.commit()
    return objet


# --- Souhaits ---


@router.post("/souhaits", response_model=SouhaitLecture, status_code=201)
def ajouter_souhait(donnees: SouhaitCreation, utilisateur: UtilisateurConnecte, session: SessionDep):
    for slug in {donnees.categorie_slug} | {a.categorie_slug for a in donnees.alternatives}:
        if slug is not None:
            obtenir_ou_404(session, m.Categorie, slug)
    if donnees.objet_id is not None:
        objet = obtenir_ou_404(session, m.Objet, donnees.objet_id)
        if objet.proprietaire_id == utilisateur.id:
            raise HTTPException(409, "On ne peut pas souhaiter son propre objet.")
    souhait = m.Souhait(utilisateur_id=utilisateur.id, **donnees.model_dump())
    session.add(souhait)
    session.commit()
    return souhait


@router.get("/souhaits", response_model=list[SouhaitLecture])
def lister_souhaits(utilisateur: UtilisateurConnecte):
    return utilisateur.souhaits


@router.delete("/souhaits/{souhait_id}", status_code=204)
def supprimer_souhait(souhait_id: int, utilisateur: UtilisateurConnecte, session: SessionDep):
    souhait = obtenir_ou_404(session, m.Souhait, souhait_id)
    if souhait.utilisateur_id != utilisateur.id:
        raise HTTPException(404, f"Souhait {souhait_id} introuvable.")
    session.delete(souhait)
    session.commit()


# --- Échanges ---


@router.get("/boucles", response_model=list[BoucleProposee])
def boucles_possibles(utilisateur: UtilisateurConnecte, session: SessionDep, limite: int = Query(10, ge=1, le=50)):
    """« Mes échanges possibles » : boucles de 2 et 3 personnes, les plus sûres d'abord."""
    return vues.boucles(session, services.suggestions(session, utilisateur.id, limite))


@router.get("/echanges", response_model=list[EchangeLecture])
def mes_echanges(utilisateur: UtilisateurConnecte, session: SessionDep):
    """Mes échanges, en cours et passés, les plus récents d'abord."""
    return [vues.echange(e, utilisateur.id) for e in services.echanges_de(session, utilisateur.id)]
