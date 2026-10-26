# MigrateLens registered local proof

Verdict: **LOCAL_CHECKS_PASSED**

Fingerprint: `96ebd7f52170361e2886b3ce309903b366889ea0b313b6594905d54a9474264b`

| Check | Result |
|---|---|
| BASELINE_OLD | PASS |
| REPRO_NEW | PASS |
| REPAIR_NEW | PASS |
| REGRESSION | PASS |
| STATIC | PASS |
| POLICY | PASS |

Mapping and expected outputs are self-declared, not independently approved.
Proof executes consumer source in the caller environment; it is not a sandbox.
Local hashes do not authenticate CI origin or authorize publication.
Only one direct-fetch path migration with unchanged GET operation is covered.
