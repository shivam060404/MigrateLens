# Boundary audit — 2026-10-20

Scope: current source, not planned services. Audit performed before restructuring; this file will record remediation and executed evidence.

| Finding | Boundary | Risk | Targeted change |
|---|---|---|---|
| CLI chooses benchmark cases, negative control and success; validates only a digest | CLI/application | Inconsistent outcomes across future entrypoints; malformed evidence accepted | Application command service; domain evidence validation; thin argument/JSON adapter |
| Fixture assertions and reproduction rules embedded in process adapter | Verification/domain | Acceptance coupled to transport; difficult to independently falsify | Pure fixture acceptance module; adapter only collects observations |
| Duplicate check IDs overwrite failures; empty required set validates | Acceptance authority | False verified result | Reject duplicate evidence and empty plans; tests |
| Application mutates a deliberately wrong patch | Application/test fixture | Test behavior inside production workflow | Negative-control analyzer decorator outside the workflow |
| Analyzer rereads source after source fingerprint is frozen | Application/analyzer | Evidence can bind different source from the analyzed source | Pass frozen source bytes through the port; stdin transport |
| Runner accepts any source string, rereads unverified workspace files | Execution admission | Arbitrary host code possible via internal calls or fixture tampering | Digest-pinned bundled inputs and candidate allowlist; recheck before launch; customer denial |
| Runner truncates output only after process exits, lacks descendant cleanup on success | Process adapter | Disk/resource exhaustion and orphan processes | Output monitoring, deadline, cancellation and process-group cleanup |
| Local evidence writer accepts unrestricted tenant/path metadata | Artifact adapter | Traversal or symlink writes if internal caller is compromised | Strict identifiers, fixture-only namespace, symlink rejection and private directories |
| No CI, no build gates, native optional packages missing from Node lock | Delivery | No reproducible baseline | Locked toolchain, frozen installs, schema drift check, builds and strict repair E2E |

Existing health routes contain no migration business rules and need no new abstraction. ts-morph AST mechanics belong in the analyzer integration; semantic approval and acceptance remain outside it. No service split, ORM layer or generic repository abstraction is added without an implementation requirement.

Customer onboarding remains disabled: host subprocess isolation is inadequate, and identity/RLS/VM/network/publisher controls are not implemented. Admission tests cannot establish VM isolation.
