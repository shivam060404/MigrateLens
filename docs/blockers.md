# Blockers and open gates

Updated 2026-10-30. These are evidence gates, not permission to replace real dependencies with mocks.

| Gate | Current observation | Next executable action |
|---|---|---|
| OSS clean install | Temporary source export accepted lockfile, then lacked cached packages; npm registry DNS returned `ENOTFOUND` | Run frozen install and OSS CI in a clean networked environment; verify standalone packaging |
| Remote CI | Workflow is configured, no run recorded | Run on a committed checkout and inspect artifact/check matrix |
| Local Python venv and HTTP E2E | Installed `python3` passes 111 unit, 35 security and 16 integration tests plus builds; offline venv sync lacks Alembic; five HTTP E2E tests fail at denied socket binding | Bootstrap the locked venv with registry access and run HTTP E2E in an environment permitting loopback |
| General OSS input | Registered bounded local scan and one direct-fetch path proof exist; checksum pinned oasdiff installer and independent CI audit added but binary could not be downloaded because GitHub DNS failed | Execute pinned diff audit in networked CI, compare with narrow detector, expand usage coverage and keep uncertain cases abstained |
| License and publication | No license, GitHub installation, CI attestation or publisher | Choose license; build trusted draft-only integration after proof provenance |
| Customer security | No customer source executed; secret canary/adversarial CI gate absent | Verify customer-style CI permissions and malicious input controls |
| Optional enterprise | Live PostgreSQL/RLS test blocked by unavailable disposable database/daemon; OIDC and recovery unfinished | Run migrated DB tests, then implement evidence ingestion and outbox recovery |
| Pilot benchmark | No authorized historical cases or design partners | Obtain explicit partner access and adjudicate real cases separately from synthetic |

The earlier Python HTTP fixture has a host assessment for an older source snapshot. It does not validate the current OSS or control-plane tree. This execution sandbox denies loopback binding, so current HTTP E2E was not rerun.
