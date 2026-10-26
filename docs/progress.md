# Progress

Updated 2026-10-27. [Implementation plan](implementation-plan.md) is the canonical phase sequence. [ADR 0004](decisions/0004-decentralized-gitops.md) records the architecture decision.

## Completed in this working tree

- Root `backend/`, `frontend/`, `infra/` ownership and separate `oss/` workspace. OSS has no Python or control-plane service dependency.
- Fictional OpenAPI 3.0/3.1 subset detection, three deterministic ts-morph recipes, approved fixture mappings, ambiguity and documentation-only abstention, generated local mock proof and hashed evidence.
- OSS `scan`, `plan`, `patch`, `prove`, `verify` and `evidence` commands. `publish` refuses. `make demo` uses the offline OSS path.
- Registered local `--config` scan/plan reads bounded, nonsymlinked files inside its root and records exact hashes. One declared direct-fetch endpoint migration can produce a one-line read-only AST patch proposal. A separate registered path proof accepts two explicit test vectors and runs six checks in the caller environment. Mapping and expected outputs are self-declared, so its verdict is `LOCAL_CHECKS_PASSED`, never a verified customer claim.
- Optional control API source includes metadata routes, local development identity, PostgreSQL migration/RLS and protected artifact access, all gated. It is not customer-ready.
- Read-only CI configuration, schema/lock checks and local regression targets.
- The configured OSS CI job now emits both fictional fixture and registered local proof artifacts with read-only checkout and no retained repository credentials; the remote workflow has not run.
- A revalidated registered bundle can render a draft PR preview with identities, check matrix and explicit publication blockers. The CLI still has no GitHub write path.
- Consolidated the current GitOps plan and removed the superseded master prompt, centralized phase reports, redundant audit snapshots and duplicate fixture evidence exports. The remaining checked-in examples are the OSS fictional proof packs.

## Recorded checks

The latest local OSS run on Node 22.23.1 and TypeScript 5.9.3 passed build and **14 tests**. Registered tests cover exact hashes, direct-fetch classification/proposal, missing mapping, uncertain usage, malformed/escaped refs, traversal, symlinks, protected paths, local proof/revalidation, changed GET semantics and wrong-candidate rejection. Supported fictional path/field/query fixtures each yielded six passing local checks; ambiguity and unchanged cases abstained; the wrong-path patch passed static/policy checks and failed repaired behavior. [OSS evidence](evidence/oss-local/README.md) and [registered evidence](evidence/registered-local/README.md) were regenerated and revalidated. These are unsigned fictional development artifacts, not customer CI attestations.

After cleanup, `make oss-ci` again passed all seven tests and emitted a six-check path proof. `make PYTHON=python3 test-unit` passed 94 tests (one upstream warning); `make check-locks`, `git diff --check`, local manifest JSON and Markdown link checks, and a search for removed-document references passed. The optional local environment manifest no longer requires Temporal or a central runner. These checks do not authenticate the proof or replace remote CI.

The prior broader local run passed Python lint/types, 94 unit, 35 security and 16 integration tests, both Node suites, schema/lock checks and backend/frontend builds. The five provider HTTP E2E tests were not rerun for this tree because this sandbox denies loopback binding. Earlier Python fixture assessments are historical and do not validate current OSS or control-plane code.

For this registered-proof change, `make oss-ci`, `make PYTHON=python3 lint typecheck check-schemas test-unit`, `make check-locks`, Markdown link validation and `git diff --check` passed locally. The Python unit suite passed 94 tests with one upstream TestClient warning. Remote CI, clean install and real customer repository execution remain unrun.

A fresh temporary export without `node_modules` accepted the frozen lockfile but could not finish `pnpm install --offline --frozen-lockfile --ignore-scripts --filter @migratelens/oss-core`: the local store lacked packages and registry requests failed with `ENOTFOUND`. The run was stopped after retries began. This is a blocked clean-install gate, not a package acceptance result. The pinned `oasdiff` release asset also could not be reached because GitHub DNS resolution failed.

## Open gates

- Clean frozen OSS installation and remote CI unverified; registry metadata was unavailable in this shell.
- Registered admission and proof are narrow: one direct-fetch path, two self-declared vectors and unchanged GET operation. Imported consumer dependencies have no acceptance coverage. Pinned oasdiff, broad usage discovery, registered field/query proof and authenticated customer CI provenance remain unimplemented.
- License, GitHub Action/App, separate trusted publisher, redaction and live draft PR unavailable.
- Optional enterprise live PostgreSQL/RLS, OIDC, evidence ingestion and outbox recovery unverified; Temporal deferred.
- No customer source execution, pilot, deployment, merge or external publication authorized or performed.

## Next executable task

Run a clean frozen `pnpm` installation and OSS CI job with registry access. Then integrate pinned oasdiff, expand bounded usage discovery and run the registered proof pack in read-only customer-style CI with artifact provenance and secret scanning. Retain the three repair classes and rerun proof identities after each code or policy change.
