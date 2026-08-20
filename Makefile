PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
PNPM ?= pnpm

.PHONY: setup dev lint typecheck test test-unit test-integration test-e2e test-all test-live-providers demo migrate

setup:
	python3.12 -m venv .venv
	$(PIP) install -e '.[dev]'
	$(PNPM) install
	$(PNPM) --dir apps/web exec playwright install chromium

dev:
	docker compose up --build

lint:
	$(PYTHON) -m ruff check apps workers packages tests
	$(PNPM) lint:web

typecheck:
	$(PYTHON) -m mypy apps workers packages
	$(PNPM) typecheck:web

test: test-unit

test-unit:
	$(PYTHON) -m pytest tests/unit
	$(PNPM) test:web

test-integration:
	$(PYTHON) -m pytest -m integration tests/integration

test-e2e:
	$(PNPM) test:e2e

test-all: lint typecheck test-unit test-integration test-e2e

test-live-providers:
	$(PYTHON) -m pytest -m live_provider

migrate:
	$(PYTHON) -m alembic -c apps/api/alembic.ini upgrade head

demo:
	$(PYTHON) -m voice_evals_sdk.cli demo-load
