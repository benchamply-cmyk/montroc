"""Les tests tournent sur une vraie base PostgreSQL (``montroc_test`` par défaut).

La base est remise à zéro par les migrations Alembic au début de la session de
tests (ce qui teste aussi les migrations), puis vidée entre chaque test.
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://montroc:montroc@localhost:5432/montroc_test"),
)

# Réglages de test : photos sur un compte Cloudinary fictif, une modératrice, un secret pour les tâches.
os.environ["CLOUDINARY_URL"] = "cloudinary://cle:secret@troc-test"
os.environ["MODERATEURS"] = "modo@exemple.fr"
os.environ["TACHES_SECRET"] = "secret-des-taches"
os.environ["SMTP_MOT_DE_PASSE"] = ""
os.environ["BREVO_API_KEY"] = ""

import re  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from montroc_api import courriels  # noqa: E402
from montroc_api.db import engine  # noqa: E402
from montroc_api.main import app  # noqa: E402

RACINE_API = Path(__file__).resolve().parents[1]
PHOTO = "https://res.cloudinary.com/troc-test/image/upload/v1/objets/photo.jpg"


@pytest.fixture(scope="session", autouse=True)
def schema():
    config = Config(str(RACINE_API / "alembic.ini"))
    config.set_main_option("script_location", str(RACINE_API / "alembic"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield


@pytest.fixture(autouse=True)
def base_vide():
    courriels.ENVOYES.clear()
    yield
    with engine.begin() as conn:
        tables = "signalements, sessions, jetons_connexion, transferts, echanges, souhaits, objets, utilisateurs"
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


def jeton_du_dernier_lien(email: str) -> str:
    courriel = next(c for c in reversed(courriels.ENVOYES) if c.destinataire == email)
    return re.search(r"#connexion=(\S+)", courriel.texte).group(1)


@dataclass
class Compte:
    id: int
    email: str
    pseudo: str
    headers: dict


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def creer(client):
    """Petits raccourcis pour peupler la base via l'API, connexion par lien magique comprise."""

    class Fabrique:
        def utilisateur(self, pseudo, zone="Lyon", email=None) -> Compte:
            email = email or f"{pseudo}@exemple.fr"
            assert client.post("/auth/lien", json={"email": email}).status_code == 202
            r = client.post(
                "/auth/verifier", json={"jeton": jeton_du_dernier_lien(email), "pseudo": pseudo, "zone": zone}
            )
            assert r.status_code == 200, r.text
            corps = r.json()
            return Compte(corps["utilisateur"]["id"], email, pseudo, {"Authorization": f"Bearer {corps['jeton']}"})

        def objet(self, proprietaire: Compte, categorie, titre=None):
            r = client.post(
                "/moi/objets",
                json={"categorie_slug": categorie, "titre": titre or categorie, "etat": "bon", "photo_url": PHOTO},
                headers=proprietaire.headers,
            )
            assert r.status_code == 201, r.text
            return r.json()["id"]

        def souhait(self, utilisateur: Compte, categorie, **options):
            r = client.post("/moi/souhaits", json={"categorie_slug": categorie, **options}, headers=utilisateur.headers)
            assert r.status_code == 201, r.text
            return r.json()["id"]

        def boucle_abc(self, auto=False):
            """A a une poussette et veut un siège ; B a un siège et veut un vélo ; C a un vélo et veut une poussette."""
            a, b, c = self.utilisateur("alice"), self.utilisateur("bruno"), self.utilisateur("chloe")
            objets = (self.objet(a, "poussette"), self.objet(b, "siege-auto"), self.objet(c, "velo"))
            self.souhait(a, "siege-auto", acceptation_auto=auto)
            self.souhait(b, "velo", acceptation_auto=auto)
            self.souhait(c, "poussette", acceptation_auto=auto)
            return (a, b, c), objets

        def echange_abc(self, auto=False):
            """La boucle à trois, proposée par Alice."""
            (a, b, c), objets = self.boucle_abc(auto)
            ordre = [e["objet"]["id"] for e in client.get("/moi/boucles", headers=a.headers).json()[0]["etapes"]]
            r = client.post("/echanges", json={"objets": ordre}, headers=a.headers)
            assert r.status_code == 201, r.text
            return (a, b, c), r.json()

    return Fabrique()
