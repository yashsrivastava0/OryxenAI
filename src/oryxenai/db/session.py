"""Async SQLAlchemy engine and session factory.

The engine is created lazily from settings so that importing this module
never triggers a database connection (no import-time I/O).

Pool settings are read from committed configuration (config/app.toml),
not hardcoded. The same engine-creation function is used by the API,
worker, and migration env, each with different pool sizing where needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

if TYPE_CHECKING:
    from oryxenai.core.settings import Settings

_engine_cache: dict[str, AsyncEngine] = {}


def get_engine(settings: Settings) -> AsyncEngine:
    """Create and cache the async engine keyed by the database URL string.

    Pool values come from committed configuration under [database.pool].
    """
    url = settings.database_url
    if url not in _engine_cache:
        pool = settings.pool
        _engine_cache[url] = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=pool.pool_size,
            max_overflow=pool.max_overflow,
            pool_timeout=pool.pool_timeout,
            pool_recycle=pool.pool_recycle if pool.pool_recycle > 0 else -1,
            echo=False,
        )
    return _engine_cache[url]


def get_sessionmaker(settings: Settings) -> async_sessionmaker[AsyncSession]:
    """Return an async session factory bound to the cached engine."""
    return async_sessionmaker(
        get_engine(settings),
        class_=AsyncSession,
        expire_on_commit=False,
    )


def reset_engine_cache() -> None:
    """Clear the cached engine — used by tests that swap settings."""
    _engine_cache.clear()
