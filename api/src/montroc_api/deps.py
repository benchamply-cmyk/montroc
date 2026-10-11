"""Dépendances partagées par les routes."""

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from .db import get_session

SessionDep = Annotated[Session, Depends(get_session)]


def obtenir_ou_404(session: Session, modele, id_: int):
    obj = session.get(modele, id_)
    if obj is None:
        raise HTTPException(404, f"{modele.__name__} {id_} introuvable.")
    return obj
