# Registered local endpoint proof example

Generated locally on 2026-10-31 from [the fictional registration](../../../oss/fixtures/registered-path-proof.json). The [path bundle](path/manifest.json) has verdict `LOCAL_CHECKS_PASSED` and fingerprint `f0b4115538d4852ab4d1d5c7042f08b058ee80e79efedbf50696dbe1c97209de`.

It executed baseline-old, reproduced-new, repair-new, regression, strict TypeScript and policy checks against a generated local mock. The mock requires one call to the declared endpoint; reproduction additionally records that the original code called the old route. The declared response vectors passed the supported OpenAPI shape check. Known credential patterns were rejected before artifact creation. The mapping and expected outputs were self-declared in the registration; the bundle is unsigned and has no authenticated CI provenance. It is **not** a customer verification or approval for a draft PR.

```sh
make build-oss
node oss/dist/cli.js verify --config oss/fixtures/registered-path-proof.json --manifest docs/evidence/registered-local/path/manifest.json
```

Changing the registration, source, contracts, candidate, generated tests, implementation or report invalidates this saved bundle.

The [draft PR preview](pr-preview.md) renders the revalidated checks and identities while explicitly blocking publication. It is review material, not a GitHub PR.
