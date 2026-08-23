"""FastAPI dependencies for database sessions, repositories, and the runner."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.agents.build_preparation.service import BuildPreparationService
from oryxenai.agents.code_generator.core.development_service import CodeGeneratorDevelopmentService
from oryxenai.agents.code_generator.service import CodeGeneratorService
from oryxenai.agents.content_architect.service import ContentArchitectService
from oryxenai.agents.discovery.service import DiscoveryService
from oryxenai.agents.shared.executor import AgentExecutor
from oryxenai.agents.shared.registry import AgentRegistry, default_registry
from oryxenai.agents.visual_design_director.service import VisualDesignDirectorService
from oryxenai.auth.authorization import PortfolioAccess
from oryxenai.auth.domain import AccountStatus, AuthRole, CurrentUser
from oryxenai.auth.errors import AdminRequiredError, OnboardingRequiredError
from oryxenai.auth.jwt import extract_bearer_token
from oryxenai.auth.service import AuthService
from oryxenai.db.repositories.agent_runs import AgentRunRepository
from oryxenai.db.repositories.build_preparation import BuildPreparationRepository
from oryxenai.db.repositories.code_generator import CodeGeneratorRepository
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository
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


async def get_bearer_token(request: Request) -> str:
    """Read exactly one bounded Authorization header without logging it."""
    values = request.headers.getlist("authorization")
    return extract_bearer_token(values, max_bytes=request.app.state.settings.auth.max_token_bytes)


def get_auth_service(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> AuthService:
    settings = request.app.state.settings
    return AuthService(
        db=db,
        config=settings.auth,
        verifier=request.app.state.auth_verifier,
        provider=request.app.state.auth_provider,
        admin_emails=settings.normalized_admin_bootstrap_emails,
        allowed_emails=settings.normalized_allowed_user_emails,
    )


async def get_current_user(
    token: str = Depends(get_bearer_token),
    service: AuthService = Depends(get_auth_service),
) -> CurrentUser:
    return await service.current_user(token)


async def require_onboarded_user(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Require a current, active local identity with a claimed username."""
    if user.status is not AccountStatus.ACTIVE:
        # AuthService normally maps this before returning.  Keep the
        # dependency fail-closed for explicit test/dependency adapters too.
        from oryxenai.auth.errors import AccountDeletedError, AccountSuspendedError

        if user.status is AccountStatus.DELETED:
            raise AccountDeletedError()
        raise AccountSuspendedError()
    if user.onboarding_required:
        raise OnboardingRequiredError()
    return user


async def require_admin(
    user: CurrentUser = Depends(require_onboarded_user),
) -> CurrentUser:
    if user.role is not AuthRole.ADMIN:
        raise AdminRequiredError()
    return user


@lru_cache(maxsize=1)
def get_agent_registry() -> AgentRegistry:
    return default_registry()


def get_session_repo(db: AsyncSession = Depends(get_db_session)) -> PortfolioSessionRepository:
    return PortfolioSessionRepository(db)


async def require_session_owner_or_admin(
    session_id: str,
    user: CurrentUser = Depends(require_onboarded_user),
    repo: PortfolioSessionRepository = Depends(get_session_repo),
) -> PortfolioAccess:
    """Authorize one portfolio aggregate with a single scoped SQL lookup."""
    try:
        sid = UUID(session_id)
    except ValueError as exc:
        from oryxenai.api.errors import ValidationError

        raise ValidationError("Invalid session ID format.") from exc

    if user.role is AuthRole.ADMIN:
        session = await repo.get_by_id_for_admin(sid)
    else:
        session = await repo.get_owned_by_id(sid, user.id)
    if session is None:
        # Missing, foreign, and quarantined legacy sessions are intentionally
        # indistinguishable to normal users.
        from oryxenai.api.errors import SessionNotFoundError

        raise SessionNotFoundError(session_id)
    return PortfolioAccess(actor=user, session=session)


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


def get_build_preparation_service(
    db: AsyncSession = Depends(get_db_session),
) -> BuildPreparationService:
    return BuildPreparationService(BuildPreparationRepository(db), JobService(db))


def get_code_generator_development_service(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> CodeGeneratorDevelopmentService:
    return CodeGeneratorDevelopmentService(
        CodeGeneratorDevelopmentRepository(db), JobService(db), request.app.state.settings
    )


def get_code_generator_service(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> CodeGeneratorService:
    return CodeGeneratorService(
        CodeGeneratorRepository(db), JobService(db), request.app.state.settings
    )
