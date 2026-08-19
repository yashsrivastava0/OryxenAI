"""Production session API for Code Generator."""

from __future__ import annotations

from typing import Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field

from oryxenai.agents.code_generator.service import (
    CodeGeneratorOperationError,
    CodeGeneratorService,
)
from oryxenai.api.dependencies import get_code_generator_service
from oryxenai.api.errors import AppError, ValidationError

router = APIRouter(prefix="/sessions/{session_id}/code-generator", tags=["code-generator"])


class StartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CodeGeneratorStateResponse(BaseModel):
    session_id: str
    session_revision: int
    code_generator: dict[str, Any]
    jobs: list[dict[str, Any]] = Field(default_factory=list)


def _session_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValidationError(f"Invalid session ID format: '{value}'") from exc


def _translate(exc: CodeGeneratorOperationError) -> NoReturn:
    raise AppError(
        exc.message,
        code=exc.code,
        status_code=exc.status_code,
        details=exc.details,
    ) from exc


@router.get("", response_model=CodeGeneratorStateResponse)
async def get_code_generator_state(
    session_id: str,
    service: CodeGeneratorService = Depends(get_code_generator_service),
) -> CodeGeneratorStateResponse:
    try:
        return CodeGeneratorStateResponse(**await service.get_state(_session_uuid(session_id)))
    except CodeGeneratorOperationError as exc:
        _translate(exc)


@router.post(
    "/start", response_model=CodeGeneratorStateResponse, status_code=status.HTTP_202_ACCEPTED
)
async def start_code_generator(
    session_id: str,
    request: Request,
    _body: StartRequest,
    service: CodeGeneratorService = Depends(get_code_generator_service),
) -> CodeGeneratorStateResponse:
    try:
        return CodeGeneratorStateResponse(
            **await service.start(
                _session_uuid(session_id),
                idempotency_key=request.headers.get("Idempotency-Key", ""),
            )
        )
    except CodeGeneratorOperationError as exc:
        _translate(exc)


@router.post(
    "/regenerate",
    response_model=CodeGeneratorStateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def regenerate_code_generator(
    session_id: str,
    request: Request,
    _body: StartRequest | None = None,
    service: CodeGeneratorService = Depends(get_code_generator_service),
) -> CodeGeneratorStateResponse:
    try:
        return CodeGeneratorStateResponse(
            **await service.regenerate(
                _session_uuid(session_id),
                idempotency_key=request.headers.get("Idempotency-Key", ""),
            )
        )
    except CodeGeneratorOperationError as exc:
        _translate(exc)
