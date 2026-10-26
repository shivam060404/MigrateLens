# Optional local Compose gate

Compose remains unimplemented and unverified. A future enterprise topology should run the control API, frontend, PostgreSQL and evidence storage with real migrations, readiness, retention and recovery. A durable outbox worker can follow after the live database gate. Temporal is not an OSS or V1 prerequisite.

The customer CI proof path is separate and runs without this stack. Do not report in-process API or mock proof checks as Compose acceptance.
