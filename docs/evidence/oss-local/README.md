# Standalone OSS fictional proof examples

Generated locally on 2026-10-27 with Node 22.23.1 and TypeScript 5.9.3 from the new `oss/` package. These are **unsigned fictional development artifacts**, not authenticated customer CI results. Each directory contains copied source/candidate, local OpenAPI contracts, an executable mock proof test, patch, manifest and report.

| Example | Verdict | Fingerprint |
|---|---|---|
| `path/` | VERIFIED_FOR_DECLARED_SCOPE | `e374c7d4103757dbc27d56874b5cc9bef054f870ccb3aabede1f044f42117296` |
| `wrong-path/` | VALIDATION_FAILED | `c6f6290af46740cddf2f7c6f35782e24cc19560149d8897a6e868ec2956e602f` |
| `ambiguous/` | NEEDS_CLARIFICATION | `a6aa44bd8cc0fc3b1ad7df32dea65c6ed88a013365638ac04963993cc3748a1b` |

The wrong patch passes STATIC and POLICY, then fails REPAIR_NEW and REGRESSION. The ambiguous mapping produces an empty patch and runs no repair checks. Revalidate a saved example against the current package and fixture with:

```sh
make build-oss
node oss/dist/cli.js verify --manifest docs/evidence/oss-local/path/manifest.json
```

Any change to the relevant implementation, fixture, contracts, patch, generated test or report invalidates the recorded snapshot. Regenerate evidence after such a change; do not update fingerprints by hand.
