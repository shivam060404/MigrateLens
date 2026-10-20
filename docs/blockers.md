# Blockers

| Prerequisite | Observed result | Impact / owner |
|---|---|---|
| Shell registry network | DNS ENOTFOUND for npm; uv registry unavailable | Attempt offline cache; fresh network bootstrap must be verified elsewhere. Environment owner |
| Docker daemon | Socket absent | Compose execution unverified. Environment owner |
| Git metadata write | `git init` denied on `.git/config` | No commit can be recorded here. Environment owner |
| GitHub App / authorized test repository | Not supplied | Live token, draft PR, revocation/reconciliation tests NOT RUN. Pilot owner |
| Pilot runner / cloud / OIDC / staging | Not supplied | Customer execution and production startup disabled. Security and pilot owners |
| Permissioned historical cases / design partners | Not supplied | Comparative benchmark and commercial validation unavailable. Founder |
| Loopback HTTP binding | Actual fixture server raises `PermissionError` | Four strict HTTP acceptance tests fail; no verified repair claim. Environment owner |
| Missing implementations | PostgreSQL/RLS, Temporal, S3, OIDC, model broker and publisher not implemented | Engineering work remains; do not describe this as credential-only blockage |
| Fresh locked bootstrap | Python closure captured from installed macOS packages; pnpm resolved from cache | Verify clean install and native optional dependencies before Phase 0 completion. Engineering owner |
