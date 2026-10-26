# MigrateLens implementation plan

Updated 2026-10-27. [ADR 0004](decisions/0004-decentralized-gitops.md) defines V1: a standalone TypeScript OSS engine verifies migrations locally or in customer CI; an optional enterprise control plane handles metadata, policy, review and audit. The customer retains execution and secrets. A separate publisher may create authorized draft PRs only.

## Phases and gates

| Phase | Deliverable and acceptance gate | State |
|---|---|---|
| -1 Architecture | Execution, permissions, evidence meaning, OSS and enterprise ownership recorded | Complete in ADR 0004 |
| 0 Foundation | Frozen standalone Node workspace, lint/types/tests/build, offline demo, clean install and release policy | Local build/tests pass; clean install and license open |
| 1 Deterministic engine | OpenAPI 3.0/3.1 diff, registered TypeScript usage, three bounded AST rules, approved mappings, abstention | Registered read-only scan and one path proposal work; general proof, broader usage and pinned oasdiff open |
| 2 Proof pack | Baseline, incompatibility, repair, regression, static/policy checks; exact hashes; wrong patch rejection; customer CI | Fictional pack and one registered local path pack pass; authenticated customer CI and broader packs open |
| 3 Model recipes | Replaceable structured proposal with schema, redaction and budget; verifier alone decides acceptance | Not started |
| 4 GitHub loop | Composite Action and separate publisher; signed events, idempotency, stale-evidence rejection, authorized draft PR | Local blocked draft preview exists; GitHub Action/publisher not started |
| 5 Enterprise | Optional FastAPI metadata/evidence API, PostgreSQL tenant isolation, auth, policy, approval and focused dashboard | Partial source; live database gate open |
| 6 Security | Malicious spec/repo/model, secret canary, forged evidence, revocation and dependency gates | Local fixture tests only |
| 7 Pilot/benchmark | Real permissioned cases, adjudicated A–D comparisons, effort/cost, separate from synthetic fixture | Synthetic fixture only |
| 8 Release | License, clean install, remote CI, contribution guide, runbooks, operational gates and truthful report | Not ready |

## Module contracts

- `oss/` owns contract analysis, usage discovery, recipes, patching, proof generation and local evidence. It must run without `backend/`, `frontend/`, Python, cloud services, GitHub credentials or a model key.
- `backend/` is the optional control API. Domain owns policy and authorization; application coordinates cases; infrastructure implements PostgreSQL, identity and artifact I/O. It does not run arbitrary customer source.
- `frontend/` displays authenticated enterprise case and evidence state. It does not decide verification or authorization.
- `infra/` owns optional enterprise deployment. PostgreSQL and object storage do not gate OSS. Start orchestration with a durable outbox; evaluate Temporal only if campaigns require it.
- A future publisher receives narrowly scoped GitHub installation authority after independent proof and approval checks. The repair engine never holds write credentials.

## Immediate dependency order

1. Verify a clean frozen Node installation and OSS job in remote CI. Select a public license before publishing. Current local compilation used installed exact pins.
2. Expand the new admitted local repository/spec mapping path with a pinned, verified OpenAPI diff tool. Current read-only scan, path policy and patch proposal are intentionally analysis-only. Unknown syntax and semantic changes abstain.
3. Expand ts-morph discovery for direct fetch, Axios, known SDK calls and bounded wrappers; record confirmed, candidate and unresolved usage. Keep three repair classes.
4. Extend the registered local path proof beyond its two self-declared vectors, then execute packs in caller CI with read-only checkout, no production secrets, bounded time and secret scanning. Bind evidence to commit, contracts, patch, policy, tests, tool versions and authenticated runner identity before a verified claim.
5. Add a GitHub Action and trusted draft publisher only after CI provenance, installation scope, stale approval and retry/idempotency checks pass.
6. Resume optional enterprise database/RLS and evidence ingestion when the OSS loop is independently accepted; build focused review UX after real case data exists.

Each phase needs running code, meaningful tests, reproducible commands and an update in [progress](progress.md). Changed bound inputs invalidate affected evidence. Never infer CI authenticity from a local hash or uploaded manifest.

## Current reproduction

```sh
make oss-ci
node oss/dist/cli.js plan --fixture field
node oss/dist/cli.js prove --fixture path --negative-control --output .local/oss-proof
```

These checks apply only to fictional fixtures. `REPRO_NEW: PASS` means the old consumer failed as expected against the new mock. A wrong patch passes static/policy checks and fails repaired behavior. Customer CI execution, general repository support and authenticated publication are not claimed.
