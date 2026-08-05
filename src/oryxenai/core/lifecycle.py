"""Application startup/shutdown lifecycle helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from oryxenai.core.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


logger = get_logger("oryxenai.lifecycle")


async def check_database_ready(engine: AsyncEngine) -> bool:
    """Run a lightweight SELECT 1 against PostgreSQL.

    Returns True when the database is reachable, False otherwise.
    Never raises — callers decide how to react.
    """
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
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
