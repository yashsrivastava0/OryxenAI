"""Pytest configuration and fixtures.

Integration/worker tests use OryxenAI_CONFIG_OVERLAY=config/app.test.toml
to point to a dedicated test database (oryxenai_test) so the application
database is never touched.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

# ── Ensure the test overlay is loaded for integration / worker tests. ──────

AUTO_CONFTEST_FLAG = "_ORYXENAI_CONFTEST_RAN"


@pytest.fixture(autouse=True)
def _set_test_overlay(monkeypatch, request):
    """Automatically set the test configuration overlay for integration
    and worker tests so they use the dedicated test database."""
    marks = [m.name for m in request.node.iter_markers()]
    if "integration" in marks or "worker" in marks:
        monkeypatch.setenv("OryxenAI_CONFIG_OVERLAY", "config/app.test.toml")
        # Clear cached settings so the overlay takes effect.
        from oryxenai.core.settings import reset_settings

        reset_settings()
        # Ensure only one conftest run sets the overlay (fixtures are re-run
        # per test, but the env var + reset is idempotent).


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# ── DB fixtures (integration + worker) ─────────────────────────────────────


@pytest_asyncio.fixture
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Per-test async engine for integration/worker tests.

    Uses the test overlay (config/app.test.toml -> oryxenai_test).
    Creates/drops all tables per test. Skipped when PostgreSQL is unreachable.
    """
    from sqlalchemy import text

    from oryxenai.core.settings import get_settings
    from oryxenai.db.base import Base
    from oryxenai.db.session import get_engine, reset_engine_cache

    reset_engine_cache()

    settings = get_settings()
    try:
        engine = get_engine(settings)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("PostgreSQL unavailable")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
    reset_engine_cache()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Per-test DB session with automatic cleanup."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session
        await session.rollback()
        await session.execute(text("DELETE FROM background_jobs"))
        await session.execute(text("DELETE FROM service_heartbeats"))
        await session.execute(text("DELETE FROM agent_runs"))
        await session.execute(text("DELETE FROM portfolio_sessions"))
        await session.commit()
