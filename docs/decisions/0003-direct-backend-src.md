# ADR 0003: Direct backend source modules

Date: 2026-10-21. Status: accepted by user direction.

## Decision

Remove the extra `backend/src/migratelens/` package level. Modules live directly in `backend/src/{api,application,domain,infrastructure,config,cli}` with `bootstrap.py` as the composition root. Python imports use `src.*`; root commands set `PYTHONPATH=backend`. The distribution and CLI command remain named `migratelens`.

## Consequences

Imports, package discovery, entry points, schema generation and documentation use the same layout. Use a dedicated virtual environment to avoid collisions with another distribution named `src`. The wheel packages these modules; fictional CLI execution currently requires the source checkout's fixtures and Node workspace, so the wheel alone is not a complete deployment artifact.

Boundary audit changes retain the modular monolith: entry points handle transport, application commands orchestrate, domain modules decide acceptance, and adapters own I/O. Package layout does not provide execution isolation. No additional services are introduced.

## Verification

Architecture import tests, CLI delegation tests, Python types, schema drift, adapter integration and wheel/sdist build pass. The source tree contains no `backend/src/migratelens` directory. Fresh macOS installation from download caches passes in a clean source export; user host HTTP acceptance also passes. Remote CI and cold-cache online installation remain unverified; see the Phase 0 audit.
