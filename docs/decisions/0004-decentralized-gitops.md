# ADR 0004: decentralized GitOps verification

Date: 2026-10-27. Status: accepted for new V1 work.

## Decision

MigrateLens V1 runs the OSS migration engine and proof checks in the developer's local environment or the consumer repository's CI. The optional enterprise control plane receives metadata and evidence; it does not receive or execute customer source by default. Draft PR publication belongs to a separate, explicitly authorized GitHub boundary. Human review and merge remain outside MigrateLens automation.

The repository stays a monorepo with root `backend/`, `frontend/`, `infra/` and a separate `oss/` Node workspace. Existing Python fixture evidence remains historical and continues to identify its exact source snapshot. New OSS evidence has its own schema and cannot inherit a previous verification verdict.

## Execution and credentials

| Role | Executes consumer code? | Credentials |
|---|---|---|
| OSS scan/plan/patch | No | No provider, model or GitHub key required |
| OSS prove/verify | Yes, only when invoked locally or in customer CI | Inherits that environment; recommend a job with read-only checkout and no production secrets |
| Enterprise control plane | No by default | Tenant metadata and narrowly scoped integration credentials, never passed to proof jobs |
| Trusted publisher | No consumer execution | GitHub installation token scoped to approved repository and draft PR operations |

The OSS tool generates a bounded patch and executable proof pack. `prove` may run the pack in the caller's environment. This is not a sandbox; the customer controls the CI runner and its secrets. Production calls are excluded from V1 verification. Evidence is stored in the consumer repository's CI artifact store or a local output directory; optional enterprise ingestion accepts manifests and redacted metadata.

## Scope and verification

Initial repairs remain TypeScript/Node, JSON REST, OpenAPI 3.0/3.1, and three mapped classes: endpoint path, response field relocation, and query parameter rename. Semantic mapping requires approved evidence. Unsupported syntax, uncertain mapping, missing checks or stale identities abstain. “Verified for declared scope” requires recorded baseline, incompatibility reproduction, repaired behavior, regression, static and policy checks, plus exact identities and an approved execution environment. A locally generated unsigned manifest is not an authenticated CI attestation.

## Product boundary

The OSS core owns contract parsing, usage discovery, deterministic recipes, proof generation, verification and local evidence. The enterprise plane owns registrations, cross-repository campaigns, RBAC, policy, approvals, usage and audit. The enterprise plane remains optional for OSS operation. Temporal, S3 and PostgreSQL are not OSS prerequisites. Existing Phase 2 control-plane code becomes an optional later product track; it must not gate the CLI proof loop.

## Consequences

- Prior work on PostgreSQL/RLS and development identity is retained but deprioritized until the OSS proof loop is stable.
- The existing Python fixture pipeline is a reference and regression asset; it is not the long-term OSS implementation.
- No customer source upload, central arbitrary shell runner, autonomous merge or live publication is enabled by this ADR.
- GitHub Action and publisher work follows independent local proof acceptance and requires real installation scope and CI evidence checks.

## Open decisions

Choose a public license, contribution policy and repository release layout before publication. Select a CI attestation and artifact retention model before accepting external evidence as authenticated. Benchmark comparisons A–C and customer pilot infrastructure remain unrun.
