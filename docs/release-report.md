# Release evidence — modular foundation

Date: 2026-10-20. Source state: uncommitted; repository Git initialization was denied. Environment: macOS, Python 3.14.6, Node 22.23.1, pnpm 11.11.0. Tests used installed dependencies; no clean install claim.

**Local reference incomplete. Pilot not ready.** Root architecture and a tested subset of Phase 0/1 are implemented. No live services were silently replaced with mocks. No PR, deployment or cloud provisioning occurred.

| Requirement | Status | Command / review evidence | Environment | Limitation | Accountable role |
|---|---|---|---|---|---|
| Backend/frontend/infra root ownership | Implemented, checked | Architecture tests + ADR 0002 | Local uncommitted | Infrastructure files currently define ownership/gates; deployment unimplemented | Engineering |
| Application/domain dependency direction | PASS | `make test-unit` | Local | Static import check; not runtime security isolation | Engineering |
| Strict settings / rejected production startup | PASS | Unit tests | Local | Live OIDC/pilot adapters unimplemented | Engineering/security |
| Minimal API health | PASS | `make health`, unit tests | In-process ASGI | No listening HTTP server; readiness deliberately 503 | Engineering |
| JSON Schema/OpenAPI generation | PASS | `make schemas` | Local | HTTP schema exposes implemented health routes only | Engineering |
| Lint and formatting | PASS | `make lint` | Local | 40 Python source/test/tool files checked | Engineering |
| Backend types | PASS | `make typecheck` | Local | mypy: 31 source files | Engineering |
| Frontend/analyzer types | PASS | `make typecheck` | Local | Compiler checks, not browser/build verification | Engineering |
| Unit boundaries / policy | 21 PASS | `make test-unit` | Local | One upstream TestClient/httpx deprecation warning retained | Engineering |
| Recipes and ambiguity export | 4 PASS | `make test-integration` | Real Node/ts-morph/tsc | No provider-runtime claim | Engineering |
| Endpoint/field/query HTTP validation | 3 FAIL / environment blocked | `make test-e2e` | Restricted local sandbox | Bind denied; checks UNAVAILABLE; no validated repair | Environment owner/engineering |
| Wrong-patch behavioral rejection | 1 FAIL / environment blocked | `make test-e2e` | Restricted local sandbox | Provider preconditions unavailable; verifier not reached | Environment owner/engineering |
| Fresh locked bootstrap | NOT VERIFIED | uv resolution and pnpm install attempts failed | Network-restricted shell | Python installed closure; Node cache lock/native optional packages need audit | Engineering |
| Next.js production build / browser E2E | NOT RUN | No evidence yet | Local | UI is a foundation connection shell | Engineering |
| PostgreSQL / RLS / migrations | NOT IMPLEMENTED | `make migrate` fails explicitly | None | No durable tenant control plane | Engineering |
| Temporal / S3 / OIDC / publisher | NOT IMPLEMENTED | Roadmap only | None | No recovery or live integration claims | Engineering |
| Isolated customer runner | NOT IMPLEMENTED | Host fixture adapter only | Local | No sandbox security claim | Security/engineering |
| Live GitHub / pilot provider / commercial benchmark | NOT RUN | Access/authorization absent | None | Synthetic fixture checks imply no customer correctness or savings | Pilot owner |

Executed output is retained in [modular checks](evidence/modular-checks.txt) and [HTTP gate summary](evidence/http-acceptance.txt). Evidence is historical: changes to code, tests, policy or source identities require affected checks to run again.
