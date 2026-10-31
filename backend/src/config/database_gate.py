"""Admission for disposable live tenant-isolation test connections."""

from sqlalchemy.engine import make_url


def validate_test_database_urls(admin_url: str, runtime_url: str) -> str:
    admin = make_url(admin_url)
    runtime = make_url(runtime_url)
    for url in (admin, runtime):
        if (
            url.drivername != "postgresql+psycopg2"
            or not url.database
            or not url.database.endswith("_test")
            or not url.host
            or not url.port
            or not url.username
            or url.query
        ):
            raise ValueError(
                "Live isolation tests require explicit PostgreSQL host, port, role and disposable *_test database"
            )
    if (admin.host, admin.port, admin.database) != (
        runtime.host,
        runtime.port,
        runtime.database,
    ):
        raise ValueError(
            "Admin and runtime connections must target the same host, port and database"
        )
    if admin.username == runtime.username:
        raise ValueError("Admin and runtime connections must use distinct roles")
    assert admin.database is not None
    return admin.database
