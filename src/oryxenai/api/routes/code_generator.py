"""HTTP API for the Code Generator ("Studio"): state, start, stop, preview grants, versions."""

from __future__ import annotations

from typing import Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from oryxenai.agents.code_generator.service import (
    CodeGeneratorOperationError,
    CodeGeneratorService,
)
from oryxenai.api.dependencies import (
    get_code_generator_service,
    require_pipeline_mutable,
    require_pipeline_session,
)
from oryxenai.api.errors import AppError, ValidationError
from oryxenai.auth.authorization import PortfolioAccess

router = APIRouter(prefix="/sessions/{session_id}/code-generator", tags=["code-generator"])


class CodeGeneratorStateResponse(BaseModel):
    session_id: str
    session_revision: int
    code_generator: dict[str, Any]
    versions: list[dict[str, Any]] = Field(default_factory=list)
    chat: list[dict[str, Any]] = Field(default_factory=list)
    jobs: list[dict[str, Any]] = Field(default_factory=list)


def _translate(exc: CodeGeneratorOperationError) -> NoReturn:
    raise AppError(
        exc.message, code=exc.code, status_code=exc.status_code, details=exc.details
    ) from exc


def _uuid(value: str, label: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValidationError(f"Invalid {label} format.") from exc


@router.get("", response_model=CodeGeneratorStateResponse)
async def get_code_generator_state(
    session_id: str,
    access: PortfolioAccess = Depends(require_pipeline_session),
    service: CodeGeneratorService = Depends(get_code_generator_service),
) -> CodeGeneratorStateResponse:
    try:
        return CodeGeneratorStateResponse(**await service.get_state(access.session.id))
    except CodeGeneratorOperationError as exc:
        _translate(exc)


@router.post(
    "/start",
    response_model=CodeGeneratorStateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_code_generator(
    session_id: str,
    access: PortfolioAccess = Depends(require_pipeline_session),
    _mutable: PortfolioAccess = Depends(require_pipeline_mutable),
    service: CodeGeneratorService = Depends(get_code_generator_service),
) -> CodeGeneratorStateResponse:
    try:
        return CodeGeneratorStateResponse(**await service.start(access.session.id))
    except CodeGeneratorOperationError as exc:
        _translate(exc)


@router.post("/stop", response_model=CodeGeneratorStateResponse)
async def stop_code_generator(
    session_id: str,
    access: PortfolioAccess = Depends(require_pipeline_session),
    _mutable: PortfolioAccess = Depends(require_pipeline_mutable),
    service: CodeGeneratorService = Depends(get_code_generator_service),
) -> CodeGeneratorStateResponse:
    try:
        return CodeGeneratorStateResponse(**await service.stop(access.session.id))
    except CodeGeneratorOperationError as exc:
        _translate(exc)


@router.get("/preview-grant")
async def get_preview_grant(
    session_id: str,
    version_id: str | None = Query(default=None),
    access: PortfolioAccess = Depends(require_pipeline_session),
    service: CodeGeneratorService = Depends(get_code_generator_service),
) -> dict[str, Any]:
    """A short-lived signed preview URL (a read: nothing is stored or changed)."""
    target = _uuid(version_id, "version ID") if version_id else None
    try:
        return await service.mint_preview(access.session.id, target)
    except CodeGeneratorOperationError as exc:
        _translate(exc)


@router.get("/versions/{version_id}")
async def get_code_generator_version(
    session_id: str,
    version_id: str,
    include_html: bool = Query(default=False),
    access: PortfolioAccess = Depends(require_pipeline_session),
    service: CodeGeneratorService = Depends(get_code_generator_service),
) -> dict[str, Any]:
    try:
        return await service.get_version(
            access.session.id, _uuid(version_id, "version ID"), include_html=include_html
        )
    except CodeGeneratorOperationError as exc:
        _translate(exc)
