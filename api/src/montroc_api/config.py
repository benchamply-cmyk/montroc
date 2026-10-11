"""Réglages lus dans les variables d'environnement (ou un fichier ``.env``)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # postgresql+psycopg://utilisateur:mot_de_passe@hote:5432/base
    database_url: str = "postgresql+psycopg://montroc:montroc@localhost:5432/montroc"
    # Origines autorisées à appeler l'API depuis un navigateur, séparées par des virgules.
    cors_origins: str = "http://localhost:8000,https://montroc.fr,https://www.montroc.fr"
    environnement: str = "local"

    @property
    def database_url_normalisee(self) -> str:
        """Neon, Render ou Heroku donnent souvent ``postgres://`` : SQLAlchemy veut le pilote explicite."""
        url = self.database_url
        for prefixe in ("postgres://", "postgresql://"):
            if url.startswith(prefixe):
                return "postgresql+psycopg://" + url[len(prefixe) :]
        return url

    @property
    def liste_cors(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
