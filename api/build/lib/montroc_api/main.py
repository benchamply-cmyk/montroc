"""Point d'entrée de l'API : ``uvicorn montroc_api.main:app --reload``.

Documentation interactive générée automatiquement sur /docs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import __version__
from .config import get_settings
from .deps import SessionDep
from .routers import auth, catalogue, echanges, grand_troc, matchs, moi, objets, signalements, taches, utilisateurs

app = FastAPI(
    title="API montroc",
    version=__version__,
    description=(
        "TrocTroc, troc sans prix ni monnaie : le Match (accords 1 à 1 à tout moment) et le Grand Troc du "
        "dimanche (boucles d'échange de 2 ou 3 personnes)."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().liste_cors,
    allow_origin_regex=get_settings().cors_regex or None,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, moi, catalogue, objets, utilisateurs, matchs, echanges, grand_troc, signalements, taches):
    app.include_router(module.router)


@app.get("/sante", tags=["supervision"])
def sante(session: SessionDep):
    """Vérifie que l'API répond et que la base est joignable (utilisé par Render)."""
    session.execute(text("SELECT 1"))
    return {"statut": "ok", "version": __version__}
