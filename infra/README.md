# Optional enterprise infrastructure

The OSS CLI and customer CI proof path do not depend on this directory. No infrastructure has been provisioned or deployed.

- `compose/` records the pending local enterprise topology.
- `containers/` records role-separated build requirements.
- `environments/` holds non-secret environment manifests.

The optional control plane needs a real PostgreSQL isolation gate, identity, evidence storage and operational recovery before customer use. Start orchestration with a durable outbox; Temporal is deferred until multi-repository campaigns justify it. Infrastructure must never put GitHub publisher credentials into code-execution jobs.
