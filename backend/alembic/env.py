"""Alembic environment configuration (async, imports all app models)."""
from __future__ import annotations

import asyncio
import sys
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure the backend directory is on the path so app.* imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.base import Base  # noqa: E402

# Import every model so that Alembic autogenerate can detect all tables
import app.models.user  # noqa: F401, E402
import app.models.project  # noqa: F401, E402
import app.models.contract  # noqa: F401, E402
import app.models.audit  # noqa: F401, E402
import app.models.receipt  # noqa: F401, E402
import app.models.runtime  # noqa: F401, E402
import app.models.notification  # noqa: F401, E402
import app.models.api_key  # noqa: F401, E402

config = context.config
# Override sqlalchemy.url from DATABASE_URL env var so only that one variable
# is required when running Alembic (SECRET_KEY, REDIS_URL, etc. are not needed
# for migrations and may not be set in migration-only environments).
_db_url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
if not _db_url:
    raise RuntimeError(
        "DATABASE_URL must be set (via environment variable or alembic.ini "
        "sqlalchemy.url) before running Alembic migrations."
    )
config.set_main_option("sqlalchemy.url", _db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # type: ignore[type-arg]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations through a sync connection."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using asyncpg."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
