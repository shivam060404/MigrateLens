VENV ?= .venv
PYTHON ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
export PYTHONPATH := $(CURDIR)/backend
export UV_CACHE_DIR := $(CURDIR)/.local/uv-cache
export NEXT_TELEMETRY_DISABLED := 1

.PHONY: bootstrap dev dev-backend dev-frontend health schemas check-schemas check-locks lint format typecheck test test-unit test-integration test-security test-typescript test-oss test-e2e build build-oss build-backend build-frontend demo proof proof-registered action-smoke-local oasdiff-install oasdiff-audit seed-demo benchmark-smoke oss-ci verify-local ci migrate down
bootstrap:
	$(PYTHON) scripts/bootstrap.py --venv "$(VENV)"
	$(MAKE) check-locks check-schemas health VENV="$(VENV)"

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

check-schemas:
	$(PYTHON) scripts/generate_contracts.py --check

check-locks:
	$(PYTHON) scripts/check_lockfiles.py

lint:
	$(PYTHON) -m ruff check --config backend/pyproject.toml backend/src backend/tests scripts
	$(PYTHON) -m ruff format --check --config backend/pyproject.toml backend/src backend/tests scripts

format:
	$(PYTHON) -m ruff check --fix --config backend/pyproject.toml backend/src backend/tests scripts
	$(PYTHON) -m ruff format --config backend/pyproject.toml backend/src backend/tests scripts

typecheck:
	$(PYTHON) -m mypy --config-file backend/pyproject.toml backend/src
	node scripts/frontend.mjs typegen
	node node_modules/typescript/bin/tsc --noEmit -p frontend/tsconfig.json
	node node_modules/typescript/bin/tsc --noEmit -p backend/analyzer-ts/tsconfig.json
	node node_modules/typescript/bin/tsc --noEmit -p oss/tsconfig.json

test: test-unit test-security test-integration test-typescript

test-unit:
	$(PYTHON) -m pytest -c backend/pyproject.toml backend/tests/unit -q --junitxml=.local/test-results/unit.xml

test-integration:
	$(PYTHON) -m pytest -c backend/pyproject.toml backend/tests/integration -q --junitxml=.local/test-results/integration.xml

test-security:
	$(PYTHON) -m pytest -c backend/pyproject.toml backend/tests/security -q --junitxml=.local/test-results/security.xml

test-typescript: build-oss
	node --test backend/analyzer-ts/recipes.test.mjs
	node --test oss/test/oss.test.mjs

test-oss: build-oss
	node --test oss/test/oss.test.mjs

test-e2e:
	$(PYTHON) -m pytest -c backend/pyproject.toml backend/tests/e2e -q --junitxml=.local/test-results/e2e.xml

build: build-oss build-backend build-frontend

build-oss:
	node oss/node_modules/typescript/bin/tsc -p oss/tsconfig.json

build-backend:
	$(PYTHON) -m build --no-isolation --outdir .local/dist backend

build-frontend:
	node scripts/frontend.mjs build

proof: build-oss
	node oss/dist/cli.js prove --fixture path --output artifacts/oss-proof

proof-registered: build-oss
	node oss/dist/cli.js prove --config oss/fixtures/registered-path-proof.json --output artifacts/registered-proof --summary artifacts/evidence/registered.json

action-smoke-local: build-oss
	$(PYTHON) scripts/smoke_action_local.py

oasdiff-install:
	$(PYTHON) scripts/install_oasdiff.py --destination .local/bin/oasdiff

oasdiff-audit:
	@test -x .local/bin/oasdiff || { echo "Run make oasdiff-install first" >&2; exit 1; }
	@mkdir -p artifacts/oasdiff
	.local/bin/oasdiff diff --allow-external-refs=false --format json oss/fixtures/path-old.json oss/fixtures/path-new.json > artifacts/oasdiff/path-diff.json
	$(PYTHON) -m json.tool artifacts/oasdiff/path-diff.json > /dev/null

demo: proof

seed-demo:
	$(PYTHON) -m src.cli.main demo

benchmark-smoke:
	$(PYTHON) -m src.cli.main benchmark

verify-local ci: check-locks check-schemas lint typecheck test-unit test-security test-typescript test-integration build test-e2e benchmark-smoke

oss-ci: build-oss test-oss proof proof-registered

migrate:
	$(PYTHON) -m alembic -c backend/alembic.ini upgrade head

.PHONY: migrate-sql
migrate-sql:
	$(PYTHON) -m alembic -c backend/alembic.ini upgrade head --sql

.PHONY: identity-init identity-token
identity-init:
	$(PYTHON) scripts/local_identity.py init

identity-token:
	$(PYTHON) scripts/local_identity.py token --subject "$(SUBJECT)"

.PHONY: test-database db-smoke
db-smoke:
	$(PYTHON) scripts/check_local_database.py

test-database:
	$(PYTHON) -m pytest -c backend/pyproject.toml backend/tests/database -q --junitxml=.local/test-results/database.xml

down:
	$(PYTHON) scripts/dev.py --stop
