# Registered proof composite action (pilot interface)

`action.yml` provides a narrow GitHub Action for one registered direct-fetch path migration. It installs the pinned OSS package with lifecycle scripts disabled, builds it inside the action checkout, and runs `prove --config` inside the caller's checked-out repository. It writes the full proof to runner temporary storage and exposes only the metadata JSON path as its `metadata` output. It never creates branches, PRs, comments, checks or merges.

The caller must pin the MigrateLens action to a reviewed commit, grant the job only `contents: read`, check out the consumer with `persist-credentials: false`, and keep production secrets out of the job. The action requires the checkout root to match `GITHUB_WORKSPACE` and rejects retained local HTTP extraheaders or an unreadable Git credential configuration, but it cannot detect every credential source or isolate malicious consumer code. Use an approved customer-owned runner environment. Do not use this action for unreviewed customer source until the runner boundary has been accepted.

Example caller job (replace the placeholder with a reviewed full commit SHA):

```yaml
permissions:
  contents: read
jobs:
  migratelens:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          persist-credentials: false
      - id: proof
        uses: OWNER/MigrateLens@REVIEWED_FULL_COMMIT_SHA
        with:
          config: .migratelens/registration.json
      - uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        with:
          name: migratelens-registered-metadata
          path: ${{ steps.proof.outputs.metadata }}
          if-no-files-found: error
```

The registration and its source/spec files must be in the caller checkout. A `.migratelens/registration.json` resolves declared paths from the repository root. Only the narrow registered path proof is accepted; unsupported changes abstain or fail. The metadata is a local assertion until GitHub attestation and independent origin verification succeed. The repository CI now includes an `action-smoke` job that calls this action on the fictional registration, checks all six metadata outcomes and uploads only the metadata file. That job has not yet run on GitHub. A fictional CI pass will validate wiring, not a customer pilot runner or semantic approval.

The composite action shape follows GitHub's [metadata syntax reference](https://docs.github.com/en/actions/reference/workflows-and-actions/metadata-syntax).

To reproduce the proof step locally after bootstrap, run `make action-smoke-local`. It executes the shell step against fictional inputs, checks six outcomes and a mismatched-workspace rejection. It does not execute the setup-node, dependency-install or artifact-upload steps, so the GitHub job remains an open gate.
