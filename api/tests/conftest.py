"""Les tests tournent sur une vraie base PostgreSQL (``montroc_test`` par défaut).

La base est remise à zéro par les migrations Alembic au début de la session de
tests (ce qui teste aussi les migrations), puis vidée entre chaque test.
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://montroc:montroc@localhost:5432/montroc_test"),
)

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from montroc_api.db import engine  # noqa: E402
from montroc_api.main import app  # noqa: E402

RACINE_API = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def schema():
    config = Config(str(RACINE_API / "alembic.ini"))
    config.set_main_option("script_location", str(RACINE_API / "alembic"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield


@pytest.fixture(autouse=True)
def base_vide():
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE transferts, echanges, souhaits, objets, utilisateurs RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def creer(client):
    """Petits raccourcis pour peupler la base via l'API."""

    class Fabrique:
        def utilisateur(self, pseudo, zone="Lyon"):
            r = client.post("/utilisateurs", json={"email": f"{pseudo}@exemple.fr", "pseudo": pseudo, "zone": zone})
            assert r.status_code == 201, r.text
            return r.json()["id"]

        def objet(self, proprietaire, categorie, titre=None):
            r = client.post(
                f"/utilisateurs/{proprietaire}/objets", json={"categorie_slug": categorie, "titre": titre or categorie}
            )
            assert r.status_code == 201, r.text
            return r.json()["id"]

        def souhait(self, utilisateur, categorie, **options):
            r = client.post(f"/utilisateurs/{utilisateur}/souhaits", json={"categorie_slug": categorie, **options})
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

    return Fabrique()
