"""HTTP API for the Discovery chat flow: start, answers, revise, state, approve."""

from __future__ import annotations

from typing import Any, NoReturn

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from oryxenai.agents.discovery.schemas import DiscoveryAnswer
from oryxenai.agents.discovery.service import DiscoveryOperationError, DiscoveryService
from oryxenai.api.dependencies import (
    get_discovery_service,
    require_pipeline_mutable,
    require_pipeline_session,
)
from oryxenai.api.errors import AppError
from oryxenai.auth.authorization import PortfolioAccess

router = APIRouter(prefix="/sessions/{session_id}/discovery", tags=["discovery"])


class StartRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    message: str = ""
    document_text: str = ""
    goal: str = ""
    model_profile: str | None = None


class AnswersRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    complete: bool = False
    answers: list[DiscoveryAnswer] = Field(default_factory=list)


class ReviseRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    revision_request: str


class DiscoveryStateResponse(BaseModel):
    session_id: str
    session_revision: int
    discovery: dict[str, Any]
    jobs: list[dict[str, Any]] = Field(default_factory=list)


class DiscoveryOperationResponse(BaseModel):
    session_id: str
    session_revision: int
    job_id: str | None = None
    run_id: str | None = None
    status: str
    discovery: dict[str, Any] | None = None
    jobs: list[dict[str, Any]] = Field(default_factory=list)


def _translate(exc: DiscoveryOperationError) -> NoReturn:
    raise AppError(
        exc.message,
        code=exc.code,
        status_code=exc.status_code,
        details=exc.details,
    ) from exc


@router.get("", response_model=DiscoveryStateResponse)
async def get_discovery_state(
    session_id: str,
    access: PortfolioAccess = Depends(require_pipeline_session),
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryStateResponse:
    try:
        return DiscoveryStateResponse(**await service.get_discovery_state(access.session.id))
    except DiscoveryOperationError as exc:
        _translate(exc)


@router.post(
    "/start",
    response_model=DiscoveryStateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_discovery(
    session_id: str,
    body: StartRequest,
    access: PortfolioAccess = Depends(require_pipeline_session),
    _mutable: PortfolioAccess = Depends(require_pipeline_mutable),
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryStateResponse:
    try:
        return DiscoveryStateResponse(
            **await service.start(
                access.session.id,
                body.message,
                body.document_text,
                body.goal,
                model_profile=body.model_profile or "",
            )
        )
    except DiscoveryOperationError as exc:
        _translate(exc)


@router.put("/answers", response_model=DiscoveryStateResponse)
async def save_discovery_answers(
    session_id: str,
    body: AnswersRequest,
    access: PortfolioAccess = Depends(require_pipeline_session),
    _mutable: PortfolioAccess = Depends(require_pipeline_mutable),
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryStateResponse:
    try:
        return DiscoveryStateResponse(
            **await service.save_answers(
                access.session.id,
                body.answers,
                complete=body.complete,
            )
        )
    except DiscoveryOperationError as exc:
        _translate(exc)


@router.post(
    "/revise",
    response_model=DiscoveryStateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def revise_discovery_brief(
    session_id: str,
    body: ReviseRequest,
    access: PortfolioAccess = Depends(require_pipeline_session),
    _mutable: PortfolioAccess = Depends(require_pipeline_mutable),
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryStateResponse:
    try:
        return DiscoveryStateResponse(
            **await service.revise_brief(access.session.id, body.revision_request)
        )
    except DiscoveryOperationError as exc:
        _translate(exc)


@router.post("/approve", response_model=DiscoveryStateResponse)
async def approve_discovery_brief(
    session_id: str,
    access: PortfolioAccess = Depends(require_pipeline_session),
    _mutable: PortfolioAccess = Depends(require_pipeline_mutable),
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryStateResponse:
    try:
        return DiscoveryStateResponse(**await service.approve_brief(access.session.id))
    except DiscoveryOperationError as exc:
        _translate(exc)
