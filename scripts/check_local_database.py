"""Interactive, read-only check of the local development runtime database role."""

import argparse
from getpass import getpass
from importlib.util import find_spec


def check(host: str, port: int, password: str) -> None:
    import sqlalchemy as sa
    from sqlalchemy.engine import URL

    from src.infrastructure.persistence.database import Database

    if not password:
        raise ValueError("A nonempty password is required")
    url = URL.create(
        "postgresql+psycopg2",
        username="ml_development",
        password=password,
        host=host,
        port=port,
        database="MigrateLens",
    )
    engine = sa.create_engine(
        url, pool_pre_ping=True, hide_parameters=True, connect_args={"connect_timeout": 5}
    )
    try:
        Database(engine).check_runtime_role()
        with engine.connect() as connection:
            identity = connection.execute(
                sa.text("SELECT current_user, session_user, current_database()")
            ).one()
            if identity != ("ml_development", "ml_development", "MigrateLens"):
                raise ValueError(
                    "Connected identity or database differs from the development runtime"
                )
            if not connection.execute(
                sa.text("SELECT pg_has_role(current_user, 'ml_runtime', 'USAGE')")
            ).scalar_one():
                raise ValueError("Runtime privileges are not inherited")
            # A direct read without a tenant context must see no tenant rows.
            visible = connection.execute(sa.text("SELECT count(*) FROM ml.tenants")).scalar_one()
            if visible != 0:
                raise ValueError("Tenant rows are visible without a tenant context")
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the local MigrateLens runtime login")
    parser.add_argument("--host", default="::1")
    parser.add_argument("--port", type=int, default=5433)
    args = parser.parse_args()
    if find_spec("sqlalchemy") is None or find_spec("psycopg2") is None:
        print(
            "Database dependencies are missing from this Python. Run "
            "`uv pip sync --python .venv/bin/python backend/requirements.lock`, "
            "then `make db-smoke` (without PYTHON=python3)."
        )
        return 2
    import sqlalchemy as sa

    from src.domain.control import AccessDenied

    password = getpass("ml_development password (not echoed): ")
    try:
        check(args.host, args.port, password)
    except (sa.exc.SQLAlchemyError, AccessDenied, ValueError) as exc:
        # Never print the exception: drivers may include connection details.
        print(f"Local database check failed ({type(exc).__name__}).")
        return 1
    print(
        "Local database check passed: restricted login, inherited grants, and empty tenant scope."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
