"""Session endpoints — create, list, and retrieve portfolio sessions."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from oryxenai.api.dependencies import (
    get_session_repo,
    require_onboarded_user,
    require_session_owner_or_admin,
)
from oryxenai.api.errors import ValidationError
from oryxenai.auth.authorization import PortfolioAccess
from oryxenai.auth.domain import AuthRole, CurrentUser
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository

router = APIRouter(prefix="/sessions", tags=["sessions"])

MAX_SESSION_NAME = 200


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None


class SessionResponse(BaseModel):
    id: str
    name: str
    status: str
    current_state: dict[str, object] = Field(default_factory=dict)
    revision: int
    created_at: str
    updated_at: str


def _to_response(session: PortfolioSession) -> SessionResponse:
    return SessionResponse(
        id=str(session.id),
        name=session.name,
        status=session.status,
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
    body: CreateSessionRequest,
    _user: CurrentUser = Depends(require_onboarded_user),
    repo: PortfolioSessionRepository = Depends(get_session_repo),
) -> SessionResponse:
    name = body.name or "Untitled session"
    if len(name) > MAX_SESSION_NAME:
        raise ValidationError(f"Session name exceeds {MAX_SESSION_NAME} characters.")
    session = await repo.create_owned(_user.id, name=name)
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
    access: PortfolioAccess = Depends(require_session_owner_or_admin),
) -> SessionResponse:
    return _to_response(access.session)
