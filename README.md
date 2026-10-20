# MigrateLens

API Compatibility & Repair Intelligence. Detect the change. Understand the impact. Verify the fix.

**Status:** modular local reference under development. No customer execution, live GitHub publication or production readiness claim. See [progress](docs/progress.md) and [release evidence](docs/release-report.md).

## Project structure

| Directory | Responsibility |
|---|---|
| `backend/` | FastAPI, application workflows, domain/policy, analysis, execution, verification, CLI and backend tests |
| `frontend/` | Next.js application, feature components and generated API client types |
| `infra/` | Deployment/container/environment ownership and pending infrastructure gates |
| `contracts/` | Generated JSON Schema and OpenAPI contracts |
| `fixtures/` | Fictional Northstar provider mappings and TypeScript consumer |
| `docs/` | Architecture, decisions, threats, blockers and implementation progress |
| `scripts/` | Local developer tooling and schema generation |

Read [architecture](docs/architecture.md) and [layout ADR](docs/decisions/0002-modular-root-layout.md) for dependency direction and trust boundaries. The original master specification is preserved; the ADR maps its suggested paths to this layout.

## Development

Prerequisites: Python 3.14, Node 22.23.1, pnpm 11.11.0, uv and registry access. Docker is required for future full-stack Compose integration. No model/GitHub credentials are needed for fictional fixtures.

```sh
make bootstrap
make health             # In-process API health, not HTTP/network verification
make dev                # Backend :8000 and frontend :3000; Ctrl-C stops both
make schemas
make lint
make typecheck
make test-unit
make test-integration   # Real Node analyzer/compiler; no provider claims
make test-e2e           # Actual loopback HTTP providers; strict acceptance gates
make demo               # Full fictional scenario matrix and evidence export
make benchmark-smoke   # Synthetic development cases only
```

The Python lock records the exact installed macOS/Python 3.14 dependency closure. A clean network bootstrap and Linux image installation are not yet verified. The Node lock was resolved from cached registry metadata; native optional packages and a fresh frozen installation still require verification. `make bootstrap` fails if dependencies cannot be installed; it does not silently use mocks.

For this environment's existing installed dependencies, `make health`, `make lint`, `make typecheck`, `make test-unit` and `make test-integration` run without installing dependencies. Full HTTP tests require loopback listening permissions, which this execution sandbox currently denies.

## Fixture CLI

```sh
PYTHONPATH=backend python3 -m src.cli.main scan --scenario path
PYTHONPATH=backend python3 -m src.cli.main analyze --scenario field
PYTHONPATH=backend python3 -m src.cli.main repair --scenario query
PYTHONPATH=backend python3 -m src.cli.main repair --scenario ambiguous
```

Outputs are stored under `artifacts/fictional-demo/<fingerprint>/`: manifest, dossier, report, patch, checksums and clearly labeled PR preview. Reports distinguish unavailable, failed and executed checks. Old evidence remains historical after implementation changes.

## Boundaries and cleanup

The host fixture runner executes only bundled fictional input through the supported CLI. It is not an isolation boundary for customer code. The API currently exposes health only. Production startup fails closed. Real identity, tenant authorization, durable orchestration and publication remain implementation gates.

`make dev` terminates both children on Ctrl-C or child failure. Evidence and local dependency caches remain on disk. No infrastructure is started by a test or bootstrap command. `make migrate` explicitly fails as not implemented until Phase 2 migrations exist.
