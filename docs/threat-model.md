# Initial threat model

## Trust domains

- Control: authenticated grants, frozen plans/policy, budgets, external evaluator, database and evidence signing.
- Execution: untrusted repository/model input, no publisher/database/model/signing credentials, bounded command IDs and output. Local host adapter is ONLY for bundled fictional fixtures and has no isolation guarantee.
- Publishing: narrow GitHub operations, independent eligibility checks, short-lived installation credentials. No merge API or execution capability.

## Required pilot controls

Tenant ownership and RLS; protected artifact metadata before download; raw-body webhook HMAC and replay deduplication; immutable source/patch/contract/plan/policy/test/provider identities; fail-closed unavailable checks; protected evaluator; atomic budget reservations; bounded retry/cancellation; applied-tree path checks; dependency integrity; VM network and metadata denial; TTL cleanup; redacted logs; explicit retention/deletion.

Remote specifications and references are disabled in the local path. JSON size/depth and local reference restrictions reject unsupported input. Model output cannot approve mappings, alter evaluator criteria or publish. Fixture evidence does not establish security for malicious customer code. Real OIDC, VM isolation, restore and live revocation remain release gates.
