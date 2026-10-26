# MigrateLens

MigrateLens detects supported OpenAPI changes, locates affected TypeScript consumers, applies bounded AST recipes and produces executable proof packs. The V1 direction is a standalone OSS CLI running locally or in customer CI, with an optional enterprise control plane. Current code supports a **fictional fixture slice**; general repository support and release readiness remain open.

## Repository map

| Directory | Responsibility |
|---|---|
| `oss/` | Standalone Node CLI, contract/usage analysis, deterministic recipes, local proof and evidence |
| `backend/` | Optional FastAPI control API; retained Python fictional fixture reference and tests |
| `frontend/` | Optional Next.js enterprise review UI |
| `infra/` | Optional enterprise deployment configuration |
| `contracts/` | Control API OpenAPI and JSON schemas |
| `fixtures/` | Earlier fictional provider/consumer inputs; OSS has self-contained fixtures |
| `docs/` | Architecture, current plan, decisions, threat model and release status |

Read [architecture](docs/architecture.md), [plan](docs/implementation-plan.md), [progress](docs/progress.md) and [ADR 0004](docs/decisions/0004-decentralized-gitops.md).

## Standalone local demo

Prerequisites: Node 22.23.1, pnpm 11.11.0 and registry access for initial installation. The package uses exact pins and requires no Python, model key, GitHub credential, database or cloud service.

```sh
pnpm install --frozen-lockfile --ignore-scripts --filter @migratelens/oss-core
make oss-ci
node oss/dist/cli.js plan --fixture field
node oss/dist/cli.js prove --fixture query --output artifacts/oss-proof
```

`make oss-ci` builds and tests the OSS package and writes both fictional fixture and registered local proof examples. The generated checks run in the caller's environment; they are not a sandbox. See [OSS commands and limits](oss/README.md), [fixture evidence](docs/evidence/oss-local/README.md) and [registered evidence](docs/evidence/registered-local/README.md). `publish` is disabled.

An admitted local repository can run read-only `scan`/`plan` and a bounded endpoint `patch` proposal using `--config`; see the [registration example](oss/fixtures/registered-path.json). A narrower [registered proof example](oss/fixtures/registered-path-proof.json) runs explicit local mock vectors and produces `LOCAL_CHECKS_PASSED` evidence. This is still unattested local validation, not an approved customer migration.

## Optional control-plane development

The backend/frontend path additionally needs Python 3.14.6 and uv 0.11.32. `make bootstrap` installs locked dependencies; `make lint typecheck test-unit test-security test-integration check-schemas check-locks build` exercises local checks. `make test-e2e` starts temporary fictional HTTP providers and requires loopback permission. `make demo` uses the OSS fixture; `make seed-demo` runs the earlier Python fixture.

`make health` is an in-process API check. The control API is disabled by default and its live PostgreSQL isolation gate has not passed. Local development tokens and migrations are documented in [backend/README.md](backend/README.md). Do not enable customer onboarding from local fixture results.

## Trust and release status

The repair engine holds no repository write credentials. A future trusted publisher must verify approved CI evidence, exact source/contract/patch/policy/test identities, installation scope and review state before creating a draft PR. No automatic merge or deployment is planned. See [threat model](docs/threat-model.md), [blockers](docs/blockers.md) and [release report](docs/release-report.md). No public license has been selected, so `oss/` remains a private workspace.
