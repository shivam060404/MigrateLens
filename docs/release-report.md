# Release report

Updated 2026-10-30. **Not ready for a public or enterprise release.**

| Area | Recorded result | Limit |
|---|---|---|
| OSS fictional proof | Local build and 21 tests passed; path/field/query six-check packs passed; wrong patch, wrong HTTP origin/method, imports, executable top-level code, synthetic secret canary, stale metadata export and unrecognized contract changes rejected | Unsigned, fixture-only, local execution |
| Registered repository input | Bounded scan, one-line endpoint proposal, six-check local path proof and blocked draft preview pass tests | Self-declared vectors; no authenticated semantic approval, CI provenance or GitHub publication |
| Abstention | Ambiguous and unchanged fixtures do not produce verified patches | General source/spec input unsupported |
| Current local baseline | Explicit installed `python3`: lint/types, schemas/locks, 111 unit, 35 security, 16 integration, both TypeScript suites and backend/frontend/OSS builds passed | Venv remains incomplete; offline sync lacks cached Alembic. All five HTTP E2E tests failed at sandbox-denied socket binding. Live database gate remains open |
| CI | Read-only proof job, checksum pinned oasdiff audit, metadata-only export and separate opt-in attestation job configured; four CI boundary tests passed | No remote run or signed attestation recorded; oasdiff archive download blocked by GitHub DNS here |
| Security | Local admission/policy tests exist; GitHub publication disabled | No customer CI provenance, secret canary gate or live identity/RLS acceptance |
| Benchmark | Synthetic fictional fixtures only | Manual/agent comparisons and real partner cases not run |
| Local development PostgreSQL | Approved migration committed in `MigrateLens`; revision, 14 tables, 14 forced-RLS flags, 14 policies and restricted runtime group verified through pgAdmin | Application login and automated tenant-isolation acceptance remain open |

The product phrase is **“Verified for Declared Scope”** only when exact contracts, consumer commit, patch, policy, tests, tool/runner identity and required executed checks are recorded in an approved environment. Current local fixture output establishes that phrase only for its fictional scope; it is not a customer or production claim.

Release blockers: clean install, license, general repository path, customer CI proof, authenticated GitHub draft publication, adversarial security review, pilot evidence and optional enterprise live gates. See [plan](implementation-plan.md), [progress](progress.md) and [blockers](blockers.md). No merge or deployment is enabled.

The origin-verification adapter now validates complete metadata and a trusted expected artifact digest before invoking GitHub CLI with exact identity constraints. Ten focused local tests passed using a substituted verifier. No live signature verification has run; freshness, revocation and semantic approval remain open.

The latest origin-admission run passed 18 focused tests, including special-file and malformed-JSON rejection. The current OSS export passed parser validation. This is local boundary coverage, not evidence of a completed GitHub attestation verification.

The registered-proof composite Action is a local pilot interface only. Its metadata contract is tested, but no GitHub-hosted run or customer acceptance evidence exists.
