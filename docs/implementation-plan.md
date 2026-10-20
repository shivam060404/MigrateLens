# Implementation plan

Updated: 2026-10-20. Layout follows user direction: root `backend/`, `frontend/`, `infra/`. [ADR 0002](decisions/0002-modular-root-layout.md) supersedes the master specification's illustrative file locations, preserving its functional/security requirements.

## Phase 0 — Modular repository and execution contract (in progress)

- Implemented: backend layers/ports/composition root, separate frontend/analyzer workspaces, strict settings and insecure-production rejection, minimal health API, generated schemas, root developer commands, architecture tests, threat model and dependency pins.
- Implemented: frontend connection shell only; dashboard expansion waits for fixture acceptance.
- Remaining gate: clean bootstrap with verified lock/install behavior, complete dependency/license review and basic CI. Cached installed dependencies do not prove a fresh checkout bootstraps.
- Infra ownership is established. Container/Compose integration remains unimplemented and must not be reported as running.

## Phase 1 — Golden fixture and immutable evidence (partial implementation)

- Backend owns actual HTTP fictional providers, external behavior checks, deterministic pipeline and local evidence adapters.
- `backend/analyzer-ts/` owns the three registered AST transformations.
- `fixtures/` owns original TypeScript input and approved synthetic mappings.
- `contracts/` owns generated plan/proposal/validation/publication schemas.
- Executed: recipe/compiler adapter tests and ambiguity export.
- Blocked gate: all real HTTP acceptance runs require loopback listening permission; current sandbox denies it. Incorrect-patch rejection is not established until its behavioral test actually executes.

## Phase 2 — Tenant-aware persistence and orchestration

Implement backend PostgreSQL models/Alembic migrations, composite ownership/RLS, authorization, protected artifact adapters, Temporal workers/outbox, cancellation/reservations and audit. Infra supplies database, workflow and object-store topology. Test isolation/recovery before exposing customer routes.

## Phase 3 — Monitoring and usage analysis

Extend backend adapters with safe ingestion, pinned oasdiff, registered TypeScript usage patterns, mapping revisions and frozen dossiers. Retain explicit coverage gaps. The current structural fixture detector is not oasdiff.

## Phase 4 — Repair and verification

Harden policy/applied-tree checks, fresh verification, provenance, retries, budgets and model ports. Model-generated plans/patches never determine acceptance. Do not call a host subprocess an isolated customer runner.

## Phase 5 — Isolated runner and trusted publisher

Add one authorized pilot runner and a separate backend publisher entrypoint with no execution capability. Infrastructure enforces credentials/network separation. Verify a live test installation only after scope, credentials and publication authorization exist.

## Phase 6 — Full product workflow

Implement frontend feature modules for inbox, case workspace, verification, review, connections and operations against authenticated API contracts. Add accessible pending/error/stale states and real browser tests. No fabricated metrics.

## Phase 7 — Benchmark and pilot

Implement manifests/adjudication under `benchmarks/`. Report synthetic development, permissioned historical and live results separately. Historical comparisons/design partners remain unavailable prerequisites.

## Phase 8 — Hardening and release

Infra owns pinned images, environment manifests, observability, workload identity, backup/restore and controlled deployment. Backend owns retention/deletion and operational controls. Exercise runbooks and produce requirement-level release evidence. Named owners authorize pilot release; no automatic merge/deployment.

## Next executable work

Finish Phase 0 clean-bootstrap/lock/CI verification. In a permitted environment, run `make test-e2e` and inspect actual provider results, then close the Phase 1 gate. While that environment is unavailable, implement Phase 2 persistence contracts and tests without claiming database/recovery success.
