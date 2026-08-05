"""Session endpoints — create, list, and retrieve portfolio sessions."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from oryxenai.api.dependencies import get_session_repo
from oryxenai.api.errors import SessionNotFoundError, ValidationError
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository

router = APIRouter(prefix="/sessions", tags=["sessions"])

MAX_SESSION_NAME = 200


class CreateSessionRequest(BaseModel):
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


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: CreateSessionRequest,
    repo: PortfolioSessionRepository = Depends(get_session_repo),
) -> SessionResponse:
    name = body.name or "Untitled session"
    if len(name) > MAX_SESSION_NAME:
        raise ValidationError(f"Session name exceeds {MAX_SESSION_NAME} characters.")
    session = await repo.create(name=name)
    return _to_response(session)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    limit: int = 20,
    repo: PortfolioSessionRepository = Depends(get_session_repo),
) -> list[SessionResponse]:
    sessions = await repo.list_recent(limit=limit)
    return [_to_response(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    repo: PortfolioSessionRepository = Depends(get_session_repo),
) -> SessionResponse:
    try:
        sid = UUID(session_id)
    except ValueError as exc:
        raise ValidationError(f"Invalid session ID format: '{session_id}'") from exc
    session = await repo.get_by_id(sid)
    if session is None:
        raise SessionNotFoundError(session_id)
    return _to_response(session)
