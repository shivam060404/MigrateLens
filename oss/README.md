# MigrateLens OSS core — fictional local reference

This Node workspace is the new standalone migration engine. It does not import the enterprise backend or require PostgreSQL, Temporal, S3, GitHub credentials or a model key. The current release is a **fictional fixture slice**, not general repository support or a published npm package.

After the root pnpm workspace is installed with exact pins:

```sh
make build-oss
node oss/dist/cli.js scan --fixture path
node oss/dist/cli.js plan --fixture field
node oss/dist/cli.js patch --fixture query
node oss/dist/cli.js prove --fixture path --output artifacts/oss-proof
node oss/dist/cli.js verify --manifest artifacts/oss-proof/<run>/manifest.json
make test-oss
```

`prove` creates `source.ts`, `candidate.ts`, old/new OpenAPI JSON, a one-line patch, executable `node:test` mock checks, an evidence manifest and Markdown report. It executes baseline, reproduction, repair and regression checks with local mocks, runs strict TypeScript compilation, and checks the bounded patch. The test process runs in the caller's local or CI environment; it is **not a sandbox**. Configure customer CI without production secrets. The current harness supports only the checked-in fictional `getCustomer` and `listCustomers` consumer shapes. Unknown mappings abstain.

`--negative-control` with the path fixture deliberately proposes the wrong endpoint. It must pass static checks and fail repaired behavior. `verify` reruns checks and compares current source, contracts, recipe output, test code, report and evidence identities. These hashes are unsigned and do not authenticate CI provenance. GitHub publication is disabled; `publish` returns an explicit error.

## Registered local analysis and path proposal

Place a `migratelens.json` registration at the repository root, or use `.migratelens/registration.json`. In the hidden-directory layout, source and contract paths resolve from the repository root; in other layouts they resolve from the registration file's directory. Paths cannot escape that root. See [the sample](fixtures/registered-path.json) and [registration schema](schemas/registration.schema.json). The runtime validates exact keys, size limits, regular files, path containment and protected source paths; the schema is a description of the format, not the runtime security check.

```sh
node oss/dist/cli.js scan --config oss/fixtures/registered-path.json
node oss/dist/cli.js plan --config oss/fixtures/registered-path.json
node oss/dist/cli.js patch --config oss/fixtures/registered-path.json
```

Registered `scan` identifies supported contract changes and classifies each listed TypeScript file as confirmed, candidate, unresolved or unaffected. An exact mapping declaration records an evidence reference but is **not an authenticated semantic approval**. Registered `patch` emits a one-line endpoint path proposal only for one confirmed direct `fetch` template; it does not write source. Its verdict remains `ANALYSIS_ONLY`. Registered field/query patching and proof are gated; a registration without valid path proof vectors causes `prove --config` to fail. Publication remains disabled.

The narrow detector now returns `UNSUPPORTED` when it sees contract changes outside its known repair rules, including an extra change bundled with a path, field or query migration. Documentation and provider info changes remain analysis-only. This does not replace a full OpenAPI diff audit.

For a single direct `fetch` endpoint migration, a registration can also include two explicit `proof.cases`. The [fictional proof example](fixtures/registered-path-proof.json) demonstrates the format:

```sh
node oss/dist/cli.js prove --config oss/fixtures/registered-path-proof.json --output artifacts/registered-proof
node oss/dist/cli.js verify --config oss/fixtures/registered-path-proof.json --manifest artifacts/registered-proof/<run>/manifest.json
node oss/dist/cli.js preview --config oss/fixtures/registered-path-proof.json --manifest artifacts/registered-proof/<run>/manifest.json
node oss/dist/cli.js export --config oss/fixtures/registered-path-proof.json --manifest artifacts/registered-proof/<run>/manifest.json
```

This generates local mocks from the registered path and response vectors and executes baseline, reproduction, repair, regression, static and policy checks. It requires otherwise identical GET operations, one direct `fetch` path edit and a fixture-only base URL. The mock requires a GET request to `http://fixture.invalid` with the declared path and no query or body. Registered proof rejects consumer modules with imports, `require`, or executable top-level statements before execution. Its verdict is `LOCAL_CHECKS_PASSED`, never `VERIFIED_FOR_DECLARED_SCOPE`: mapping and expected values are self-declared, tests run in the caller environment, and CI origin is unauthenticated. Registered field/query proof, imported consumer dependencies, broad consumer shapes and publication are outside the tested scope. See the [saved registered example](../docs/evidence/registered-local/README.md).

Registered proof rejects common credential patterns and the synthetic secret canary before writing its artifact folder. This check cannot detect every secret; use a customer-approved secret scanner and credential-free CI job for repository code execution.

For CI artifact upload, pass `--summary artifacts/evidence/registered.json` to registered `prove`. The summary contains revalidated hashes and check outcomes without source, contract bodies or test vectors. The configured OSS CI job uploads this metadata file for the registered example. It does not authenticate the CI origin or certify semantic approval. Keep the full local proof folder inside the trusted runner for review and revalidation.

`preview` revalidates a passing registered bundle and prints a draft PR description labeled **publication blocked**. It does not call GitHub or write repository content.

## Pinned contract diff audit

On a networked machine, `make oasdiff-install` downloads the official oasdiff 1.34.1 release archive for macOS or Linux and verifies the release SHA256 before installing only the executable into `.local/bin/`. `make oasdiff-audit` runs its JSON diff on the fictional path contracts with external references disabled. This is an independent CI audit; the registered repair decision still uses the deliberately narrow in-process detector. A passing audit does not confer semantic approval or CI provenance. The release hashes are from [oasdiff's 1.34.1 release](https://github.com/oasdiff/oasdiff/releases/tag/v1.34.1), and the diff flags follow its [official documentation](https://github.com/oasdiff/oasdiff/blob/main/docs/DIFF.md).

The package is marked private until a license, contribution policy, release artifact and clean-install acceptance are chosen. See [ADR 0004](../docs/decisions/0004-decentralized-gitops.md) and the [implementation plan](../docs/implementation-plan.md).

The pilot [composite GitHub Action](../docs/github-action.md) runs registered proof in the caller CI and emits metadata only; it has no publication path or customer-run acceptance evidence yet.
