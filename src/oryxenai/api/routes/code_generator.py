"""Production session API for Code Generator."""

from __future__ import annotations

from typing import Any, NoReturn

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field

from oryxenai.agents.code_generator.service import (
    CodeGeneratorOperationError,
    CodeGeneratorService,
)
from oryxenai.api.dependencies import (
    get_code_generator_service,
    require_mutable_portfolio,
    require_session_owner_or_admin,
)
from oryxenai.api.errors import AppError
from oryxenai.auth.authorization import PortfolioAccess

router = APIRouter(prefix="/sessions/{session_id}/code-generator", tags=["code-generator"])


class StartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CodeGeneratorStateResponse(BaseModel):
    session_id: str
    session_revision: int
    code_generator: dict[str, Any]
    jobs: list[dict[str, Any]] = Field(default_factory=list)


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
    access: PortfolioAccess = Depends(require_session_owner_or_admin),
    service: CodeGeneratorService = Depends(get_code_generator_service),
) -> CodeGeneratorStateResponse:
    try:
        return CodeGeneratorStateResponse(**await service.get_state(access.session.id))
    except CodeGeneratorOperationError as exc:
        _translate(exc)


@router.post(
    "/start", response_model=CodeGeneratorStateResponse, status_code=status.HTTP_202_ACCEPTED
)
async def start_code_generator(
    session_id: str,
    request: Request,
    _body: StartRequest,
    access: PortfolioAccess = Depends(require_session_owner_or_admin),
    _mutable: PortfolioAccess = Depends(require_mutable_portfolio),
    service: CodeGeneratorService = Depends(get_code_generator_service),
) -> CodeGeneratorStateResponse:
    try:
        return CodeGeneratorStateResponse(
            **await service.start(
                access.session.id,
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
    access: PortfolioAccess = Depends(require_session_owner_or_admin),
    _mutable: PortfolioAccess = Depends(require_mutable_portfolio),
    service: CodeGeneratorService = Depends(get_code_generator_service),
) -> CodeGeneratorStateResponse:
    try:
        return CodeGeneratorStateResponse(
            **await service.regenerate(
                access.session.id,
                idempotency_key=request.headers.get("Idempotency-Key", ""),
            )
        )
    except CodeGeneratorOperationError as exc:
        _translate(exc)


@router.post(
    "/retry",
    response_model=CodeGeneratorStateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_code_generator(
    session_id: str,
    request: Request,
    _body: StartRequest | None = None,
    access: PortfolioAccess = Depends(require_session_owner_or_admin),
    _mutable: PortfolioAccess = Depends(require_mutable_portfolio),
    service: CodeGeneratorService = Depends(get_code_generator_service),
) -> CodeGeneratorStateResponse:
    try:
        return CodeGeneratorStateResponse(
            **await service.retry(
                access.session.id,
                idempotency_key=request.headers.get("Idempotency-Key", ""),
            )
        )
    except CodeGeneratorOperationError as exc:
        _translate(exc)
