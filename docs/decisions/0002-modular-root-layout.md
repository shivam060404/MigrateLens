# ADR 0002: backend, frontend and infrastructure ownership

Status: accepted by user direction, 2026-10-20.

## Decision

Use three primary root directories: `backend/`, `frontend/`, `infra/`. Supporting cross-cutting assets remain in `contracts/`, `fixtures/`, `docs/`, `scripts/`, and `benchmarks/`. Root manifests orchestrate the workspace; each application owns its dependencies and source.

The backend starts as a modular monolith with explicit application ports. Domain code owns deterministic policy and acceptance. Application code coordinates use cases. Infrastructure implements I/O adapters. HTTP and CLI are entrypoints. `bootstrap.py` is the composition root that connects interfaces to implementations. Architecture tests reject outward domain/application imports.

The TypeScript analyzer is a separate Node workspace under `backend/analyzer-ts/`, because it is a backend capability with a different runtime. It is not a frontend dependency.

The Next.js frontend uses `src/app/` for routing, `src/features/` for product features, and `src/shared/` for reusable API/UI utilities. Generated transport contracts come from backend canonical schemas. Frontend code cannot make acceptance or authorization decisions.

Infrastructure owns deployment topology, runtime images, network policy, secret references, monitoring and environment manifests. Database schema migrations remain backend-owned; provisioning the database belongs to infrastructure.

## Deployment and trust

Do not deploy each Python package as a microservice. Start with one control application and a small workflow/analysis worker set. Untrusted execution and publishing remain separate credential and runtime boundaries even though their implementation belongs to this monorepo. Scale process roles only when queue/latency/resource measurements justify it.

Production readiness is an executed gate, not a directory convention. OIDC, PostgreSQL/RLS, Temporal recovery, object authorization, isolated execution and live publication are not complete.

## Migration

| Earlier specification path | Current owner |
|---|---|
| `apps/web/` | `frontend/` |
| `services/control/` | `backend/src/api/`, `application/`, future persistence adapters |
| `services/analyzer-ts/` | `backend/analyzer-ts/` |
| `services/executor/` | `backend/src/infrastructure/execution/` |
| `services/verifier/` | `backend/src/infrastructure/verification/`, `domain/assessment.py` |
| `packages/python-core/` | `backend/src/domain/` and application contracts |
| `packages/contracts/` | `contracts/` |
| `tools/cli/` | `backend/src/cli/` |
| `services/orchestrator/`, `services/publisher/` | Future backend worker/publisher entrypoints; no working implementation claimed |

No compatibility aliases are needed: the original repository had no external callers or released package. Update commands, generated outputs and documentation atomically. Existing evidence remains immutable history and is not relabeled as validation of the moved implementation.
