"""HTTP API for the Content Architect flow: start, revise, state, approve."""

from __future__ import annotations

from typing import Any, NoReturn

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from oryxenai.agents.content_architect.service import (
    ContentArchitectOperationError,
    ContentArchitectService,
)
from oryxenai.api.dependencies import (
    get_content_architect_service,
    require_mutable_portfolio,
    require_session_owner_or_admin,
)
from oryxenai.api.errors import AppError
from oryxenai.auth.authorization import PortfolioAccess

router = APIRouter(prefix="/sessions/{session_id}/content-architect", tags=["content-architect"])


class StartRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    preferences: dict[str, Any] = Field(default_factory=dict)
    model_profile: str | None = None


class ReviseRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    revision_request: str


class ContentArchitectStateResponse(BaseModel):
    session_id: str
    session_revision: int
    content_architect: dict[str, Any]
    jobs: list[dict[str, Any]] = Field(default_factory=list)


def _translate(exc: ContentArchitectOperationError) -> NoReturn:
    raise AppError(
        exc.message,
        code=exc.code,
        status_code=exc.status_code,
        details=exc.details,
    ) from exc


@router.get("", response_model=ContentArchitectStateResponse)
async def get_content_architect_state(
    session_id: str,
    access: PortfolioAccess = Depends(require_session_owner_or_admin),
    service: ContentArchitectService = Depends(get_content_architect_service),
) -> ContentArchitectStateResponse:
    try:
        return ContentArchitectStateResponse(
            **await service.get_content_architect_state(access.session.id)
        )
    except ContentArchitectOperationError as exc:
        _translate(exc)


@router.post(
    "/start",
    response_model=ContentArchitectStateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_content_architect(
    session_id: str,
    body: StartRequest,
    access: PortfolioAccess = Depends(require_session_owner_or_admin),
    _mutable: PortfolioAccess = Depends(require_mutable_portfolio),
    service: ContentArchitectService = Depends(get_content_architect_service),
) -> ContentArchitectStateResponse:
    try:
        return ContentArchitectStateResponse(
            **await service.start(
                access.session.id,
                body.preferences,
                model_profile=body.model_profile or "",
            )
        )
    except ContentArchitectOperationError as exc:
        _translate(exc)


@router.post(
    "/revise",
    response_model=ContentArchitectStateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def revise_content_architect(
    session_id: str,
    body: ReviseRequest,
    access: PortfolioAccess = Depends(require_session_owner_or_admin),
    _mutable: PortfolioAccess = Depends(require_mutable_portfolio),
    service: ContentArchitectService = Depends(get_content_architect_service),
) -> ContentArchitectStateResponse:
    try:
        return ContentArchitectStateResponse(
            **await service.revise(access.session.id, body.revision_request)
        )
    except ContentArchitectOperationError as exc:
        _translate(exc)


@router.post("/approve", response_model=ContentArchitectStateResponse)
async def approve_content_architect(
    session_id: str,
    access: PortfolioAccess = Depends(require_session_owner_or_admin),
    _mutable: PortfolioAccess = Depends(require_mutable_portfolio),
    service: ContentArchitectService = Depends(get_content_architect_service),
) -> ContentArchitectStateResponse:
    try:
        return ContentArchitectStateResponse(**await service.approve(access.session.id))
    except ContentArchitectOperationError as exc:
        _translate(exc)
