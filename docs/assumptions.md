# Assumptions register

Updated 2026-10-27.

1. The user selected the decentralized GitOps model in [ADR 0004](decisions/0004-decentralized-gitops.md). Root `backend/`, `frontend/` and `infra/` ownership remains; `oss/` is the standalone V1 engine.
2. Only fictional checked-in code is authorized for the current local proof. No customer repository, GitHub installation, production provider, paid infrastructure or deployment credentials have been supplied.
3. Customer local/CI runs future proof packs under its own policy. The OSS local mock process and retained Python fixture runner are not security sandboxes. CI must avoid production secrets and limit network/permissions.
4. Semantic equivalence requires approved evidence; unknown or ambiguous changes abstain. Local hashes identify bytes but do not authenticate CI provenance.
5. Publication requires a separate authorized GitHub boundary and current evidence/approval. It remains disabled. No autonomous merge or deployment.
6. The optional control API must validate tenant/repository authority and live PostgreSQL RLS before use. Its local token issuer is development-only; Temporal is deferred.
7. Tool versions and lockfiles are pinned, but the expanded OSS frozen install and remote CI have not been verified in this environment.
8. Registered local proof vectors and mapping references are repository declarations. They do not establish independent semantic approval or authenticated CI provenance; their `LOCAL_CHECKS_PASSED` verdict cannot authorize publication.
