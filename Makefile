# Raccourcis de développement (macOS / Linux). Sous Windows, voir les tâches VS Code.
PY := .venv/bin/python

.PHONY: installer base api migrer migration tests lint format site

installer:          ## Crée l'environnement Python et installe tout
	python3 -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ./algorithme -e "./api[dev]"

base:               ## Démarre PostgreSQL en local (Docker)
	docker compose up -d --wait

migrer:             ## Applique les migrations sur la base locale
	cd api && ../$(PY) -m alembic upgrade head

migration:          ## Crée une migration : make migration m="ajoute les photos"
	cd api && ../$(PY) -m alembic revision --autogenerate -m "$(m)"

api: migrer         ## Lance l'API sur http://localhost:8001 (doc : /docs)
	cd api && ../$(PY) -m uvicorn montroc_api.main:app --reload --port 8001

site:               ## Sert le site statique sur http://localhost:8000
	cd web && ../$(PY) -m http.server 8000

tests:              ## Tous les tests (moteur + API)
	cd algorithme && ../$(PY) -m unittest discover -s tests
	cd api && ../$(PY) -m pytest

lint:               ## Vérifie le style
	$(PY) -m ruff check api
	$(PY) -m ruff format --check api

format:             ## Corrige le style
	$(PY) -m ruff check --fix api
	$(PY) -m ruff format api
