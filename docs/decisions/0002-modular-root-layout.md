# ADR 0002: Modular root ownership

## Decision

Keep `backend/`, `frontend/` and `infra/` as clear root modules, with shared `contracts/`, `fixtures/`, `docs/` and `scripts/`. ADR 0004 adds `oss/` as the independent V1 product; it supersedes the original centralized execution sequence without moving the established roots.

The backend uses domain, application, infrastructure and API layers with `bootstrap.py` as its composition root. The Next.js frontend owns presentation and transport only. Infrastructure owns optional enterprise deployment. The OSS Node package owns migration/proof logic and has no backend or cloud dependency.

The retained `backend/analyzer-ts/` and Python fixture pipeline are reference/regression code from the earlier local implementation, not the V1 customer execution path. The control plane must not import them to run customer source. See [architecture](../architecture.md) and [ADR 0004](0004-decentralized-gitops.md).
