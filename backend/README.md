# Backend

Python code lives under `src/`; the Node analyzer is a separate workspace in `analyzer-ts/`. The layer rules and process boundaries are documented in [architecture](../docs/architecture.md).

Run from the repository root:

```sh
make health
make dev-backend
make test-unit
make test-integration
make test-e2e
PYTHONPATH=backend python3 -m src.cli.main scan --scenario path
PYTHONPATH=backend python3 -m src.cli.main analyze --scenario field
PYTHONPATH=backend python3 -m src.cli.main repair --scenario query
```

`make health` checks the ASGI app in-process. E2E requires permission to listen on loopback and execute Node. Failed/unavailable provider checks never validate a repair. `/api/v1/health/ready` deliberately returns 503 while release gates are incomplete.

Future persistence adapters, Alembic migrations, Temporal workers and the publisher belong here. They are not yet implemented. The local runner is not safe for customer repositories.
