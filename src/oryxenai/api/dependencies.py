"""FastAPI dependencies for database sessions, repositories, and the runner."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.agents.content_architect.service import ContentArchitectService
from oryxenai.agents.discovery.service import DiscoveryService
from oryxenai.agents.shared.executor import AgentExecutor
from oryxenai.agents.shared.registry import AgentRegistry, default_registry
from oryxenai.agents.visual_design_director.service import VisualDesignDirectorService
from oryxenai.db.repositories.agent_runs import AgentRunRepository
from oryxenai.db.repositories.content_architect import ContentArchitectRepository
from oryxenai.db.repositories.discovery import DiscoveryRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.db.repositories.visual_design_director import VisualDesignDirectorRepository
from oryxenai.db.session import reset_engine_cache  # noqa: F401 (re-export for tests)
from oryxenai.jobs.service import JobService
from oryxenai.runtime.mock_runner import MockRunner


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield an async DB session; commit on success, rollback on error."""
    sessionmaker = request.app.state.sessionmaker
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@lru_cache(maxsize=1)
def get_agent_registry() -> AgentRegistry:
    return default_registry()


def get_session_repo(db: AsyncSession = Depends(get_db_session)) -> PortfolioSessionRepository:
    return PortfolioSessionRepository(db)


def get_run_repo(db: AsyncSession = Depends(get_db_session)) -> AgentRunRepository:
    return AgentRunRepository(db)


def get_executor(
    registry: AgentRegistry = Depends(get_agent_registry),
    session_repo: PortfolioSessionRepository = Depends(get_session_repo),
    run_repo: AgentRunRepository = Depends(get_run_repo),
) -> AgentExecutor:
    """Build an executor bound to the per-request session and repositories."""
    return AgentExecutor(registry, session_repo, run_repo)


def get_mock_runner(
    registry: AgentRegistry = Depends(get_agent_registry),
    executor: AgentExecutor = Depends(get_executor),
) -> MockRunner:
    return MockRunner(registry, executor)


def get_discovery_service(
    db: AsyncSession = Depends(get_db_session),
    registry: AgentRegistry = Depends(get_agent_registry),
) -> DiscoveryService:
    """Build a Discovery service bound to the request transaction."""
    return DiscoveryService(DiscoveryRepository(db), JobService(db), registry)


def get_content_architect_service(
    db: AsyncSession = Depends(get_db_session),
    registry: AgentRegistry = Depends(get_agent_registry),
) -> ContentArchitectService:
    """Build a Content Architect service bound to the request transaction."""
    return ContentArchitectService(ContentArchitectRepository(db), JobService(db), registry)


def get_visual_design_director_service(
    db: AsyncSession = Depends(get_db_session),
    registry: AgentRegistry = Depends(get_agent_registry),
) -> VisualDesignDirectorService:
    """Build a Visual Design Director service bound to the request transaction."""
    return VisualDesignDirectorService(VisualDesignDirectorRepository(db), JobService(db), registry)
