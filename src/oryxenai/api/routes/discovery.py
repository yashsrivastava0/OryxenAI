"""HTTP API for the Explorer chat flow: start, answers, revise, state, approve."""

from __future__ import annotations

import asyncio
from typing import Any, NoReturn

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from oryxenai.agents.discovery.document_extract import (
    DocumentExtractionError,
    extract_document,
)
from oryxenai.agents.discovery.schemas import DiscoveryAnswer
from oryxenai.agents.discovery.service import DiscoveryOperationError, DiscoveryService
from oryxenai.api.dependencies import (
    get_discovery_service,
    get_pipeline_user,
    require_pipeline_mutable,
    require_pipeline_session,
)
from oryxenai.api.errors import AppError
from oryxenai.auth.authorization import PortfolioAccess

router = APIRouter(prefix="/sessions/{session_id}/discovery", tags=["discovery"])
document_router = APIRouter(prefix="/discovery-documents", tags=["discovery"])


@document_router.post("/extract")
async def extract_discovery_document(
    request: Request,
    filename: str,
    _user: object = Depends(get_pipeline_user),
) -> dict[str, Any]:
    """Extract text for the intake composer; persist only when Explorer starts."""
    limits = request.app.state.settings.discovery
    semaphore = getattr(request.app.state, "discovery_document_semaphore", None)
    if semaphore is None:
        semaphore = asyncio.Semaphore(1)
        request.app.state.discovery_document_semaphore = semaphore
    data = bytearray()
    async with semaphore:
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > limits.max_upload_bytes:
                raise AppError(
                    "The selected file exceeds the upload size limit.",
                    code="DISCOVERY_DOCUMENT_TOO_LARGE",
                    status_code=413,
                )
        try:
            name, extracted, page_count, warnings = await run_in_threadpool(
                extract_document,
                filename,
                bytes(data),
                max_chars=limits.max_input_chars,
                max_bytes=limits.max_upload_bytes,
                max_pdf_pages=limits.max_pdf_pages,
                artifacts_path=limits.ocr_artifacts_path,
                pdf_timeout_seconds=limits.pdf_timeout_seconds,
                engine=limits.pdf_engine,
                light_ocr=limits.light_ocr,
            )
        except DocumentExtractionError as exc:
            status_code = 413 if "too much text" in str(exc).lower() else 400
            raise AppError(
                str(exc), code="DISCOVERY_DOCUMENT_INVALID", status_code=status_code
            ) from exc
    return {
        "name": name,
        "text": extracted,
        "characters": len(extracted),
        "page_count": page_count,
        "warnings": warnings,
    }


class StartRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    message: str = ""
    document_text: str = ""
    document_name: str = ""
    goal: str = ""
    source_text: str = ""
    model_profile: str | None = None


class AnswersRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    complete: bool = False
    continue_with_current_information: bool = False
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
                source_text=body.source_text,
                document_name=body.document_name,
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
                continue_with_current_information=body.continue_with_current_information,
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


@router.post("/stop", response_model=DiscoveryStateResponse)
async def stop_discovery(
    session_id: str,
    access: PortfolioAccess = Depends(require_pipeline_session),
    _mutable: PortfolioAccess = Depends(require_pipeline_mutable),
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryStateResponse:
    """Stop the active Explorer job without deleting the user's intake."""
    try:
        return DiscoveryStateResponse(**await service.stop(access.session.id))
    except DiscoveryOperationError as exc:
        _translate(exc)
