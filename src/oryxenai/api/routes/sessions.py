"""Session endpoints — create, list, and retrieve portfolio sessions."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from oryxenai.api.dependencies import (
    get_db_session,
    get_pipeline_user,
    get_session_repo,
    is_detached_pipeline,
    require_detached_pipeline_mode,
    require_onboarded_user,
    require_pipeline_session,
)
from oryxenai.api.errors import PipelineRestartCleanupError, SessionNotFoundError, ValidationError
from oryxenai.auth.authorization import PortfolioAccess
from oryxenai.auth.domain import AuthRole, CurrentUser
from oryxenai.auth.entitlements import PortfolioEntitlementRepository
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.runtime.pipeline_reset import PipelineResetError, PipelineResetService

router = APIRouter(prefix="/sessions", tags=["sessions"])

MAX_SESSION_NAME = 200


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None


class RestartSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replacement_session_id: str


class SessionResponse(BaseModel):
    id: str
    name: str
    status: str
    session_mode: str
    current_state: dict[str, object] = Field(default_factory=dict)
    revision: int
    created_at: str
    updated_at: str


def _to_response(session: PortfolioSession) -> SessionResponse:
    return SessionResponse(
        id=str(session.id),
        name=session.name,
        status=session.status,
        session_mode=getattr(session, "session_mode", "legacy"),
        current_state=session.current_state,
        revision=session.revision,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


def _validate_limit(limit: int) -> int:
    if not 1 <= limit <= 100:
        raise ValidationError("Limit must be between 1 and 100.", details={"field": "limit"})
    return limit


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    request: Request,
    body: CreateSessionRequest,
    _user: CurrentUser | None = Depends(get_pipeline_user),
    repo: PortfolioSessionRepository = Depends(get_session_repo),
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    name = body.name or "Untitled session"
    if len(name) > MAX_SESSION_NAME:
        raise ValidationError(f"Session name exceeds {MAX_SESSION_NAME} characters.")
    if is_detached_pipeline(request):
        session = await repo.create_detached(name=name)
    elif _user is None:
        from oryxenai.auth.errors import AuthRequiredError

        raise AuthRequiredError()
    elif _user.role is AuthRole.ADMIN:
        session = await repo.create_owned(_user.id, name=name)
    else:
        session = await PortfolioEntitlementRepository(db).get_or_create_session(
            user_id=_user.id, name=name
        )
    return _to_response(session)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    limit: int = 20,
    user: CurrentUser = Depends(require_onboarded_user),
    repo: PortfolioSessionRepository = Depends(get_session_repo),
) -> list[SessionResponse]:
    limit = _validate_limit(limit)
    if user.role is AuthRole.ADMIN:
        sessions = await repo.list_recent_for_admin(limit=limit)
    else:
        sessions = await repo.list_owned_recent(user.id, limit=limit)
    return [_to_response(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    access: PortfolioAccess = Depends(require_pipeline_session),
) -> SessionResponse:
    return _to_response(access.session)


@router.post("/{session_id}/restart", response_model=SessionResponse)
async def restart_session(
    request: Request,
    session_id: str,
    body: RestartSessionRequest,
    _mode: None = Depends(require_detached_pipeline_mode),
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    try:
        old_id = UUID(session_id)
        replacement_id = UUID(body.replacement_session_id)
    except ValueError as exc:
        raise ValidationError("Session IDs must be valid UUIDs.") from exc
    service = PipelineResetService(
        db,
        settings=request.app.state.settings,
        artifact_store=getattr(request.app.state, "artifact_store", None),
        preview_storage=getattr(request.app.state, "preview_storage", None),
        auth_admin_provider=getattr(request.app.state, "auth_admin_provider", None),
    )
    try:
        return _to_response(await service.restart(old_id, replacement_id))
    except PipelineResetError as exc:
        raise PipelineRestartCleanupError() from exc
    except LookupError as exc:
        raise SessionNotFoundError(session_id) from exc
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
