# Trust and threat model

Updated 2026-10-27. [ADR 0004](decisions/0004-decentralized-gitops.md) places proof execution in developer local or customer CI. The optional enterprise control plane consumes metadata and authenticated evidence; it does not need customer source by default. A separate publisher holds narrowly scoped GitHub write authority.

| Threat | Required boundary or gate | Current status |
|---|---|---|
| Malicious OpenAPI or repository text | Bounded local parsing, no remote refs or shell evaluation during scan/plan/patch | Fictional parser and fixture tests only |
| Malicious code during proof | Customer-controlled CI runner, read-only checkout, no production secrets, time/network limits | Local fictional proof; no customer CI acceptance |
| Model prompt injection | Structured recipe only; policy, mappings and verdict outside model | Model adapter not built |
| Secret leakage to evidence/PR | Redact and scan before artifact or PR publication | Publication disabled; scanner pending |
| Forged or stale evidence | Exact input hashes plus authenticated CI run/commit identity and compare-before-publish | Registered local proof revalidates exact bytes and checks; CI provenance still absent |
| Unauthorized repository writes | Separate publisher with selected-repository installation token; never in repair process | No publisher credentials or live publishing |
| Cross-tenant metadata/artifacts | Application authorization plus PostgreSQL RLS and scoped storage/logs | Source/unit coverage; live DB gate open |
| Duplicate events and budget abuse | Idempotency key, bounded retries/cancellation and accounted limits | GitHub loop not built |
| Supply-chain compromise | Exact locks, restricted workflow permissions and verified dependency/action provenance | Local lock checks; remote clean CI unverified |

The retained Python host runner admits only reviewed bundled fictional sources and strips process environment, but it is not an OS isolation boundary. Neither package structure nor local mocks establish customer isolation. No customer onboarding, production calls, merge or deployment is enabled.

Before a pilot: execute adversarial spec/repository/model and secret canary cases in a customer-style CI job; verify evidence origin, revocation, stale approval and tenant isolation with real dependencies. Record residual risks and an accountable approver in the release report.
