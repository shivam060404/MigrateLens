# Draft PR preview — publication blocked

## Detected change

- Provider: fictional-northstar
- Rule: ML-PATH-001
- Consumer file: `client.ts`
- Old contract: `sha256:e0e0c939f4a8416ee89fa01c00be3fe2e65c4ad936f00e9d2ce6d5cdb96e2f5c`
- New contract: `sha256:aa0bb9f085689fbe7d53872b1fed7eeffa4b5c62b425bdaf460aa9ee121e6a96`

## Proposed repair

- One direct-fetch endpoint path edit
- Source: `sha256:42da31964e1bb8050ed8022ad4c65129f798c4c8d027b928f234f69d3a560201`
- Candidate: `sha256:a66b98b4cdd260298a473f73b0b453025baabea85c9b05bc9467e9d6fbcd4e98`
- Patch: `sha256:ef6c1a6e9ad8bf75bb7df3aad3e681b0a348c522e90e3112b33277081951faee`

## Local proof

| Check | Result |
|---|---|
| BASELINE_OLD | PASS |
| REPRO_NEW | PASS |
| REPAIR_NEW | PASS |
| REGRESSION | PASS |
| STATIC | PASS |
| POLICY | PASS |

Evidence fingerprint: `96ebd7f52170361e2886b3ce309903b366889ea0b313b6594905d54a9474264b`

## Publication gate

This is an unsigned local proposal. Mapping and expected outputs are self-declared. Customer CI provenance, authenticated semantic approval, secret scanning and trusted GitHub installation scope are not established. Do not publish this as a verified migration.
