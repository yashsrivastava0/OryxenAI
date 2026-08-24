"""Application startup/shutdown lifecycle helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from oryxenai.core.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


logger = get_logger("oryxenai.lifecycle")


async def check_database_ready(engine: AsyncEngine) -> bool:
    """Verify PostgreSQL connectivity and the minimum application schema.

    Returns True when the database is reachable, False otherwise.
    Never raises — callers decide how to react.
    """
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT "
                    "to_regclass('public.alembic_version') IS NOT NULL "
                    "AND to_regclass('public.portfolio_sessions') IS NOT NULL "
                    "AND to_regclass('public.background_jobs') IS NOT NULL "
                    "AND to_regclass('public.app_users') IS NOT NULL"
                )
            )
        return bool(result.scalar_one())
    except Exception as exc:
        logger.warning("database readiness check failed: %s", type(exc).__name__)
        return False


async def dispose_engine(engine: AsyncEngine) -> None:
    """Dispose the async engine on shutdown."""
    try:
        await engine.dispose()
        logger.info("database engine disposed")
    except Exception as exc:
        logger.error("error disposing database engine: %s", type(exc).__name__)
