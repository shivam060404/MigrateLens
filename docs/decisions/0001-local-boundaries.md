# ADR 0001: local fixture execution and external pilot gates

Control owns plans, policy, checks and evidence. Execution receives sanitized inputs and no credentials. Publisher is a separate module/process boundary and has no execution operations.

The first local adapter uses fresh temporary directories and a minimal subprocess environment for repository-owned fictional fixtures only. It is not a sandbox and must reject customer work. A future pilot adapter must provide VM isolation, network enforcement, TTL cleanup and authenticated results; merely implementing the interface is insufficient.

Use actual local HTTP fixture servers. No live integration is silently mocked. Docker daemon availability is independent of this fixture path. PostgreSQL and Temporal remain explicit dependencies of durable orchestration, never silently replaced by SQLite or in-memory production state.
