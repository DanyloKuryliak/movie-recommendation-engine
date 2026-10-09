.DEFAULT_GOAL := help
API_PYTHON := api/.venv/bin/python
COMPOSE := LOCAL_UID=$(shell id -u) LOCAL_GID=$(shell id -g) docker compose --env-file .env.example -f infra/compose.local.yaml --profile training

.PHONY: help api-install api-test api-run ml-sync train mlflow-ui train-compose mlflow-ui-down package-public-model

help:
	@echo "Targets: api-install, api-test, api-run, ml-sync, train, mlflow-ui, train-compose, mlflow-ui-down, package-public-model"

api-install:
	if [ ! -x $(API_PYTHON) ]; then uv venv --python 3.12 api/.venv; fi
	uv pip install --python $(API_PYTHON) -r api/requirements.txt

api-test: api-install
	cd api && .venv/bin/python -m pytest tests -q

api-run: api-install
	$(API_PYTHON) -m uvicorn app.main:app --app-dir api --reload --port 8000

ml-sync:
	uv sync --project ml

train:
	uv run --project ml python ml/run_experiment.py

mlflow-ui:
	$(COMPOSE) up --build -d mlflow

train-compose:
	$(COMPOSE) run --build --rm trainer

mlflow-ui-down:
	$(COMPOSE) stop mlflow

package-public-model:
	python3 scripts/package_public_model.py
