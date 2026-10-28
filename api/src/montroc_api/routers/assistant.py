"""La bulle d'aide du site : questions sur TopTroc, sans compte et sans accès aux données des membres."""

from fastapi import APIRouter, HTTPException, Request

from .. import assistant
from ..config import get_settings
from ..schemas import EtatAssistant, QuestionAssistant, ReponseAssistant

router = APIRouter(prefix="/assistant", tags=["assistant"])

LIMITES = {
    "ip": "Vous avez posé beaucoup de questions : réessayez dans un moment, ou consultez la FAQ.",
    "jour": "L'assistant a beaucoup servi aujourd'hui : il revient demain. La FAQ répond aux questions courantes.",
}


def adresse_ip(request: Request) -> str:
    # Render place l'adresse du visiteur en tête de X-Forwarded-For.
    transmise = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return transmise or (request.client.host if request.client else "inconnue")


@router.get("", response_model=EtatAssistant)
def etat():
    """La bulle ne s'affiche que si l'assistant est configuré."""
    return EtatAssistant(actif=bool(get_settings().anthropic_api_key))


@router.post("", response_model=ReponseAssistant)
def poser(question: QuestionAssistant, request: Request):
    reglages = get_settings()
    if not reglages.anthropic_api_key:
        raise HTTPException(503, "L'assistant n'est pas disponible pour l'instant.")
    limite = assistant.QUOTAS.accepter(
        adresse_ip(request), reglages.assistant_questions_par_heure, reglages.assistant_questions_par_jour
    )
    if limite:
        raise HTTPException(429, LIMITES[limite])
    try:
        texte = assistant.repondre([(m.role, m.contenu) for m in question.messages], question.langue, question.page)
    except assistant.AssistantIndisponible:
        raise HTTPException(503, "L'assistant n'est pas disponible pour l'instant.") from None
    return ReponseAssistant(reponse=texte)
