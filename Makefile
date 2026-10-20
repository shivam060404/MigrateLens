PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
export PYTHONPATH := $(CURDIR)/backend
export UV_CACHE_DIR := $(CURDIR)/.local/uv-cache
export NEXT_TELEMETRY_DISABLED := 1

.PHONY: bootstrap dev dev-backend dev-frontend health schemas lint format typecheck test-unit test-integration test-e2e demo seed-demo benchmark-smoke verify-local migrate down
bootstrap:
	$(PYTHON) -c 'import sys; assert sys.version_info[:2] == (3,14), "Python 3.14 required"'
	node -e 'if (process.versions.node.split(".")[0] !== "22") process.exit(1)'
	pnpm --version
	uv venv --python python3 .venv
	uv pip sync --python .venv/bin/python backend/requirements.lock
	pnpm install --frozen-lockfile --ignore-scripts
	$(MAKE) schemas health

dev:
	$(PYTHON) scripts/dev.py

dev-backend:
	$(PYTHON) -m uvicorn src.api.app:create_app --factory --host 127.0.0.1 --port 8000

dev-frontend:
	pnpm --filter @migratelens/frontend dev

health:
	$(PYTHON) scripts/health_check.py

schemas:
	$(PYTHON) scripts/generate_contracts.py

lint:
	$(PYTHON) -m ruff check --config backend/pyproject.toml backend/src backend/tests scripts
	$(PYTHON) -m ruff format --check --config backend/pyproject.toml backend/src backend/tests scripts

format:
	$(PYTHON) -m ruff check --fix --config backend/pyproject.toml backend/src backend/tests scripts
	$(PYTHON) -m ruff format --config backend/pyproject.toml backend/src backend/tests scripts

typecheck:
	$(PYTHON) -m mypy --config-file backend/pyproject.toml backend/src
	node node_modules/typescript/bin/tsc --noEmit -p frontend/tsconfig.json
	node node_modules/typescript/bin/tsc --noEmit -p backend/analyzer-ts/tsconfig.json

test-unit:
	$(PYTHON) -m pytest -c backend/pyproject.toml backend/tests/unit -q

test-integration:
	$(PYTHON) -m pytest -c backend/pyproject.toml backend/tests/integration -q

test-e2e:
	$(PYTHON) -m pytest -c backend/pyproject.toml backend/tests/e2e -q

demo seed-demo:
	$(PYTHON) -m src.cli.main demo

benchmark-smoke:
	$(PYTHON) -m src.cli.main benchmark

verify-local: lint typecheck test-unit test-integration test-e2e

migrate:
	$(PYTHON) scripts/pending_gate.py 'PostgreSQL migrations (Phase 2)'

down:
	$(PYTHON) scripts/pending_gate.py 'Background shutdown; current make dev runs in foreground and stops both children on Ctrl-C'
