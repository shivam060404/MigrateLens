# Local Compose gate

Full Compose implementation is pending verified image selection and service integration. Docker CLI presence alone is not evidence that the stack runs.

Required topology: frontend → control API; control/worker → PostgreSQL, Temporal, object storage; isolated execution without control/publisher credentials. Expose development ports only on loopback. Keep persistent volumes on ordinary shutdown.

Acceptance: fresh startup, health/readiness, migration from empty database, seeded fictional cases, worker restart/recovery, cancellation, artifact authorization and clean shutdown. None of these Compose checks has run yet.
