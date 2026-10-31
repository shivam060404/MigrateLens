# Metadata provenance gate

The optional `attest-metadata` job signs the digest of `registered.json` using GitHub artifact attestations. It runs on a fresh runner, downloads only the metadata artifact from the same workflow run, and does not check out or execute repository code. Proof execution retains only the workflow's `contents: read` permission. OIDC and attestation write permissions exist only in the attestation job.

This job is disabled unless an owner sets repository variable `ML_ENABLE_ATTESTATIONS=true` and manually dispatches CI on `main`. Enabling it authorizes uploading the metadata digest and workflow provenance to GitHub's attestation service. No attestation has been generated in this local session.

After an authorized run, download the `registered-metadata` artifact and verify it with the GitHub CLI:

```sh
python3 scripts/verify_ci_provenance.py registered.json \
  --repo OWNER/REPOSITORY --commit EXACT_40_CHARACTER_COMMIT \
  --fingerprint EXPECTED_64_CHARACTER_EVIDENCE_FINGERPRINT \
  --artifact-hash sha256:EXPECTED_64_CHARACTER_ARTIFACT_DIGEST \
  --gh-binary /absolute/path/to/trusted/gh
```

The adapter requires an explicit absolute path to a trusted operator-installed `gh` executable outside this repository; a relative, missing, non-executable or world-writable path is rejected. It must support the flags in the [official verifier manual](https://cli.github.com/manual/gh_attestation_verify). It verifies a private snapshot of the metadata bytes and constrains the repository, workflow, source and signer commits, main ref, OIDC issuer and hosted runner. Missing CLI, failed verification and fingerprint mismatch fail closed. Expected values must come from trusted policy or review, not the downloaded artifact itself. Local tests substitute the verifier process; no live cryptographic verification has passed here.

The consumer must still compare all input identities and current approval scope, and validate run freshness/revocation. Those acceptance conditions remain unimplemented. `CI_ORIGIN_VERIFIED` explicitly returns `publicationAuthorized: false`.

The adapter validates the complete registered export shape, six unique passing checks, identity hash formats, and the exact artifact digest before invoking GitHub verification. Obtain the expected digest from a trusted review record; computing it from an untrusted download only checks consistency and does not establish approval. Duplicate JSON keys and unexpected fields are rejected. This gate accepts only the current single-source registered proof format.

Artifact admission supports macOS/Linux regular files only. It rejects symlinks and special files, opens without following the final symlink, checks the opened file identity and reads at most 64 KiB plus one overflow byte. Invalid UTF-8, duplicate keys, non-JSON numeric constants and excessive parser nesting fail before invoking `gh`. These controls do not authenticate a document; the expected digest and cryptographic verifier remain mandatory.

An attestation authenticates the origin and bytes of the exported metadata. It does not prove semantic equivalence, independently approve test vectors, or authorize a PR. The export keeps its `LOCAL_CHECKS_PASSED` verdict. Protect `main` and workflow edits; an authorized workflow change can otherwise change what gets attested.

GitHub supports artifact attestations for public repositories and for private/internal repositories on Enterprise Cloud; Enterprise Server is not supported by this action. See the [official action documentation](https://github.com/actions/attest/blob/main/README.md). The action and artifact downloader are pinned to verified release commit SHAs in the workflow.
