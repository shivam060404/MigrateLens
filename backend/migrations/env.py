"""Explicit migration credential boundary; never fall back to runtime credentials."""

import os
from alembic import context
from sqlalchemy import create_engine, pool
from src.infrastructure.persistence.schema import metadata

if context.is_offline_mode():
    context.configure(dialect_name="postgresql", literal_binds=True, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    url = os.environ.get("ML_MIGRATION_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "ML_MIGRATION_DATABASE_URL is required; runtime credentials are not migration credentials"
        )
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Migrations require PostgreSQL; no SQLite fallback")
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
