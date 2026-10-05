"""Alembic env.py — resolves the database URL from application settings.

Does NOT import the running FastAPI app. Reads config/app.toml + .env via
the central Settings object.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from oryxenai.core.settings import get_settings
from oryxenai.db.base import Base

# Import all models so Base.metadata is fully populated.
from oryxenai.db.models import (  # noqa: F401
    AgentRun,
    AppUser,
    AppUserCapacity,
    BackgroundJob,
    ModelBudgetReservation,
    ModelCallAttempt,
    ModelCallCache,
    ModelCapacityWindow,
    ModelOperation,
    ModelProviderObservation,
    PortfolioSession,
    ServiceHeartbeat,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Keep the URL out of Alembic's ConfigParser: percent-encoded passwords such as
# %40 are otherwise treated as interpolation syntax and included in errors.
settings = get_settings()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to script)."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    target_metadata.bind = connection
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with an async engine."""
    connectable = create_async_engine(settings.database_url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
