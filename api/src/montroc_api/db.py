"""Connexion à la base : un moteur SQLAlchemy et une session par requête HTTP."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

# pool_pre_ping : Neon met la base en veille, une connexion du pool peut être fermée côté serveur.
engine = create_engine(get_settings().database_url_normalisee, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
