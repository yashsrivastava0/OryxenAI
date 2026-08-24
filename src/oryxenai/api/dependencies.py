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
from oryxenai.auth.admin.service import AdminService
from oryxenai.auth.authorization import DurableAuthorizationContext, PortfolioAccess
from oryxenai.auth.domain import AccountStatus, AuthRole, CurrentUser
from oryxenai.auth.entitlements import PortfolioEntitlementRepository
from oryxenai.auth.errors import (
    AdminRequiredError,
    AuthRequiredError,
    OnboardingRequiredError,
    PortfolioReadOnlyError,
)
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


def get_admin_service(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> AdminService:
    return AdminService(
        db=db,
        provider=request.app.state.auth_admin_provider,
        preview_storage=getattr(request.app.state, "preview_storage", None),
        artifact_store=getattr(request.app.state, "artifact_store", None),
        settings=request.app.state.settings,
    )


def get_session_repo(db: AsyncSession = Depends(get_db_session)) -> PortfolioSessionRepository:
    return PortfolioSessionRepository(db)


async def get_current_user(
    token: str = Depends(get_bearer_token),
    service: AuthService = Depends(get_auth_service),
) -> CurrentUser:
    return await service.current_user(token)


async def require_onboarded_user(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Require a current, active local identity with a claimed username."""
    return _assert_onboarded(user)


def _assert_onboarded(user: CurrentUser) -> CurrentUser:
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


def is_detached_pipeline(request: Request) -> bool:
    """Return the server-selected temporary pipeline mode."""
    return bool(request.app.state.settings.auth.pipeline_mode == "detached")


async def get_pipeline_user(
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> CurrentUser | None:
    """Resolve auth only for the attached pipeline mode."""
    if is_detached_pipeline(request):
        return None
    token = await get_bearer_token(request)
    return _assert_onboarded(await service.current_user(token))


async def require_pipeline_session(
    request: Request,
    session_id: str,
    user: CurrentUser | None = Depends(get_pipeline_user),
    repo: PortfolioSessionRepository = Depends(get_session_repo),
) -> PortfolioAccess:
    """Authorize a main-pipeline session in attached or detached mode."""
    try:
        sid = UUID(session_id)
    except ValueError as exc:
        from oryxenai.api.errors import ValidationError

        raise ValidationError("Invalid session ID format.") from exc

    if is_detached_pipeline(request):
        session = await repo.get_detached_by_id(sid)
        if session is None:
            from oryxenai.api.errors import SessionNotFoundError

            raise SessionNotFoundError(session_id)
        return PortfolioAccess(actor=None, session=session)

    if user is None:
        raise AuthRequiredError()
    if user.role is AuthRole.ADMIN:
        session = await repo.get_by_id_for_admin(sid)
    else:
        session = await repo.get_owned_by_id(sid, user.id)
    if session is None:
        from oryxenai.api.errors import SessionNotFoundError

        raise SessionNotFoundError(session_id)
    return PortfolioAccess(actor=user, session=session)


async def require_detached_pipeline_mode(request: Request) -> None:
    """Keep restart available for idempotent retries after old-row deletion."""
    if not is_detached_pipeline(request):
        from oryxenai.api.errors import SessionNotFoundError

        raise SessionNotFoundError("detached-pipeline")


async def require_pipeline_mutable(
    access: PortfolioAccess = Depends(require_pipeline_session),
    db: AsyncSession = Depends(get_db_session),
) -> PortfolioAccess:
    """Guard main-pipeline mutations without weakening other API routes."""
    if access.actor is None:
        return access
    if access.actor.role is AuthRole.ADMIN:
        return access
    if access.actor.entitlement is not None and access.actor.entitlement.read_only:
        raise PortfolioReadOnlyError()
    row = await PortfolioEntitlementRepository(db).get_for_user(access.actor.id)
    if row is not None and row.successful_run_id is not None:
        raise PortfolioReadOnlyError()
    return access


async def require_admin(
    user: CurrentUser = Depends(require_onboarded_user),
) -> CurrentUser:
    if user.role is not AuthRole.ADMIN:
        raise AdminRequiredError()
    return user


@lru_cache(maxsize=1)
def get_agent_registry() -> AgentRegistry:
    return default_registry()


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


async def get_durable_context(
    access: PortfolioAccess = Depends(require_session_owner_or_admin),
    db: AsyncSession = Depends(get_db_session),
) -> DurableAuthorizationContext:
    """Bind a request-scoped portfolio access decision to local durable IDs."""

    actor = access.actor
    if actor is None:
        return DurableAuthorizationContext.from_access(access)
    if (
        access.session.owner_user_id is not None
        and access.session.owner_user_id == actor.id
        and actor.role is AuthRole.USER
    ):
        # /me is the approved JIT repair boundary. Do not take an
        # entitlement row lock here: the request may continue into provider
        # or model work. The short binding transaction acquires it immediately
        # before durable portfolio mutation.
        row = await PortfolioEntitlementRepository(db).get_for_user(actor.id)
        if row is None or row.portfolio_session_id != access.session.id:
            from oryxenai.auth.errors import EntitlementBindingConflictError

            raise EntitlementBindingConflictError()
    return DurableAuthorizationContext.from_access(access)


async def get_pipeline_durable_context(
    access: PortfolioAccess = Depends(require_pipeline_session),
    db: AsyncSession = Depends(get_db_session),
) -> DurableAuthorizationContext | None:
    """Return owner bindings when attached, or explicit v0 detached context."""
    actor = access.actor
    if actor is None:
        return None
    if actor.role is AuthRole.USER:
        row = await PortfolioEntitlementRepository(db).get_for_user(actor.id)
        if row is None or row.portfolio_session_id != access.session.id:
            from oryxenai.auth.errors import EntitlementBindingConflictError

            raise EntitlementBindingConflictError()
    return DurableAuthorizationContext.from_access(access)


async def require_mutable_portfolio(
    access: PortfolioAccess = Depends(require_session_owner_or_admin),
    db: AsyncSession = Depends(get_db_session),
) -> PortfolioAccess:
    """Guard every product mutation after aggregate ownership is established."""

    actor = access.actor
    if actor is None:
        return access
    if actor.role is AuthRole.ADMIN:
        return access
    if actor.entitlement is not None and actor.entitlement.read_only:
        raise PortfolioReadOnlyError()
    row = await PortfolioEntitlementRepository(db).get_for_user(actor.id)
    if row is not None and row.successful_run_id is not None:
        raise PortfolioReadOnlyError()
    return access


def get_run_repo(db: AsyncSession = Depends(get_db_session)) -> AgentRunRepository:
    return AgentRunRepository(db)


def get_executor(
    registry: AgentRegistry = Depends(get_agent_registry),
    session_repo: PortfolioSessionRepository = Depends(get_session_repo),
    run_repo: AgentRunRepository = Depends(get_run_repo),
    context: DurableAuthorizationContext = Depends(get_durable_context),
) -> AgentExecutor:
    """Build an executor bound to the per-request session and repositories."""
    return AgentExecutor(registry, session_repo, run_repo, context)


def get_mock_runner(
    registry: AgentRegistry = Depends(get_agent_registry),
    executor: AgentExecutor = Depends(get_executor),
) -> MockRunner:
    return MockRunner(registry, executor)


def get_discovery_service(
    db: AsyncSession = Depends(get_db_session),
    registry: AgentRegistry = Depends(get_agent_registry),
    context: DurableAuthorizationContext | None = Depends(get_pipeline_durable_context),
) -> DiscoveryService:
    """Build a Discovery service bound to the request transaction."""
    return DiscoveryService(DiscoveryRepository(db), JobService(db, context), registry)


def get_content_architect_service(
    db: AsyncSession = Depends(get_db_session),
    registry: AgentRegistry = Depends(get_agent_registry),
    context: DurableAuthorizationContext | None = Depends(get_pipeline_durable_context),
) -> ContentArchitectService:
    """Build a Content Architect service bound to the request transaction."""
    return ContentArchitectService(
        ContentArchitectRepository(db), JobService(db, context), registry
    )


def get_visual_design_director_service(
    db: AsyncSession = Depends(get_db_session),
    registry: AgentRegistry = Depends(get_agent_registry),
    context: DurableAuthorizationContext | None = Depends(get_pipeline_durable_context),
) -> VisualDesignDirectorService:
    """Build a Visual Design Director service bound to the request transaction."""
    return VisualDesignDirectorService(
        VisualDesignDirectorRepository(db), JobService(db, context), registry
    )


def get_build_preparation_service(
    db: AsyncSession = Depends(get_db_session),
    context: DurableAuthorizationContext | None = Depends(get_pipeline_durable_context),
) -> BuildPreparationService:
    return BuildPreparationService(BuildPreparationRepository(db), JobService(db, context))


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
    context: DurableAuthorizationContext = Depends(get_durable_context),
) -> CodeGeneratorService:
    return CodeGeneratorService(
        CodeGeneratorRepository(db), JobService(db, context), request.app.state.settings
    )
