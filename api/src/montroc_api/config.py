"""Réglages lus dans les variables d'environnement (ou un fichier ``.env``)."""

from functools import lru_cache
from urllib.parse import unquote, urlsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # postgresql+psycopg://utilisateur:mot_de_passe@hote:5432/base
    database_url: str = "postgresql+psycopg://montroc:montroc@localhost:5432/montroc"
    # Origines autorisées à appeler l'API depuis un navigateur, séparées par des virgules.
    cors_origins: str = "http://localhost:8000,https://troctroc.fr,https://www.troctroc.fr"
    environnement: str = "local"
    # Adresse du site, pour les liens dans les e-mails (lien magique, « une boucle vous attend »…).
    site_url: str = "https://troctroc.fr"

    # E-mails sortants. Render gratuit bloque les ports SMTP : en production, on passe par l'API HTTPS
    # de Brevo (BREVO_API_KEY). Le SMTP (OVH) reste possible sur une offre Render payante ou en local.
    # Sans l'un ni l'autre, les e-mails sont écrits dans le journal : pratique en local et dans les tests.
    brevo_api_key: str = ""
    smtp_hote: str = "ssl0.ovh.net"
    smtp_port: int = 465
    smtp_utilisateur: str = ""
    smtp_mot_de_passe: str = ""
    email_expediteur: str = "TrocTroc <bonjour@troctroc.fr>"

    # Photos : la variable CLOUDINARY_URL du tableau de bord Cloudinary (cloudinary://clé:secret@nom).
    cloudinary_url: str = ""

    # E-mails des comptes qui ont accès à la modération, séparés par des virgules.
    moderateurs: str = ""
    # Secret partagé avec la tâche planifiée GitHub Actions qui appelle /taches/… (rappels, math trade).
    taches_secret: str = ""
    # Lieu de dépôt affiché aux participants d'un échange accepté (adresse, horaires).
    point_de_depot: str = ""

    @property
    def database_url_normalisee(self) -> str:
        """Neon, Render ou Heroku donnent souvent ``postgres://`` : SQLAlchemy veut le pilote explicite."""
        url = self.database_url
        for prefixe in ("postgres://", "postgresql://"):
            if url.startswith(prefixe):
                return "postgresql+psycopg://" + url[len(prefixe) :]
        return url

    @property
    def smtp_configure(self) -> bool:
        return bool(self.smtp_utilisateur and self.smtp_mot_de_passe)

    @property
    def envoi_configure(self) -> bool:
        return bool(self.brevo_api_key) or self.smtp_configure

    @property
    def cloudinary(self) -> tuple[str, str, str] | None:
        """(nom du cloud, clé, secret) lus dans CLOUDINARY_URL, ou None si les photos ne sont pas configurées."""
        url = urlsplit(self.cloudinary_url)
        if url.scheme != "cloudinary" or not (url.hostname and url.username and url.password):
            return None
        return url.hostname, unquote(url.username), unquote(url.password)

    @property
    def liste_moderateurs(self) -> set[str]:
        return {e.strip().lower() for e in self.moderateurs.split(",") if e.strip()}

    @property
    def liste_cors(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
