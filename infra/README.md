# Infrastructure ownership

This directory owns deployment configuration, container definitions, network boundaries, environment manifests and operational tooling. No infrastructure has been provisioned or deployed.

- `compose/`: local service topology, once dependency versions/images and startup are verified.
- `containers/`: separate control/frontend/worker/publisher build definitions; no shared publisher credentials with execution.
- `environments/`: non-secret environment manifests and release prerequisites.

The full local topology must contain PostgreSQL, Temporal, object storage and application processes. An unavailable dependency must fail visibly; do not replace these services with an in-memory implementation and call it durable.

Current blocker: Docker daemon is stopped and loopback listening is denied by this execution environment. Container and Compose definitions have not been validated. The host fixture and in-process API paths are separately documented in the root README.

Before a pilot, select one authorized cloud/runner path, pin verified image digests, implement workload identity, network restrictions, backups/restore, TTL cleanup and retention. Do not create deployment credentials or provision paid resources as a bootstrap side effect.
