# Optional enterprise control API and historical fixture

The FastAPI source uses direct `src/{api,application,domain,infrastructure,config,cli}` modules and `bootstrap.py` composition. The control API is disabled by default; it cannot execute customer repositories. See [architecture](../docs/architecture.md).

From the root, `make health` checks in-process ASGI, `make test-unit test-security test-integration` runs local checks, and `make test-e2e` requires loopback access for the fictional HTTP provider. The retained Python fixture CLI is for historical regression only; the V1 migration CLI is in `oss/`.

For a local development identity, `make PYTHON=python3 identity-init` creates ignored keys and `make PYTHON=python3 identity-token SUBJECT=alice` issues a short-lived token. Enable metadata routes only with a migrated disposable PostgreSQL database, unprivileged runtime role, `ML_AUTH_MODE=local_token`, `ML_CONTROL_API_ENABLED=true`, `ML_IDENTITY_PUBLIC_KEY_PATH=.local/identity/public.pem` and `ML_DATABASE_URL` outside source control. `make test-database` is the strict live isolation gate. It has not passed in this environment; local tokens are not production OIDC.
