# Dependency and toolchain record

Updated 2026-10-27. Exact versions are in `oss/package.json`, `frontend/package.json`, `backend/analyzer-ts/package.json`, `backend/requirements.lock` and `pnpm-lock.yaml`; those files are authoritative.

| Track | Current pinned tools | Verification limit |
|---|---|---|
| OSS V1 | Node 22.23.1, pnpm 11.11.0, TypeScript 5.9.3, ts-morph 26.0.0 | Local build/tests with installed packages; clean frozen install and remote CI open |
| Optional control | Python 3.14.6, FastAPI 0.139.0, SQLAlchemy 2.0.51, Alembic 1.18.5 | Local unit/in-process checks; live PostgreSQL isolation open |
| Optional UI | Next.js 16.2.12, React 19.2.4 | Local build only |

This record is not a full transitive license, vulnerability or supply-chain review. No public OSS license, container base image digest or customer CI action release has been selected. Verify those before publication. Official API references: [ts-morph](https://ts-morph.com/details/expressions), [FastAPI](https://fastapi.tiangolo.com/tutorial/bigger-applications/), [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html).
