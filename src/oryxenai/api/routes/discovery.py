"""HTTP API for the durable Discovery intake, questions, brief, and approval flow."""

from __future__ import annotations

from typing import Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from oryxenai.agents.discovery.schemas import DiscoveryAnswer, DiscoveryIntake
from oryxenai.agents.discovery.service import DiscoveryOperationError, DiscoveryService
from oryxenai.api.dependencies import get_discovery_service
from oryxenai.api.errors import AppError, ValidationError

router = APIRouter(prefix="/sessions/{session_id}/discovery", tags=["discovery"])


class IntakeRequest(DiscoveryIntake):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(default=0, ge=0)


class EnqueueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=0)
    idempotency_key: str | None = Field(default=None, max_length=256)


class AnswersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=0)
    question_version: int = Field(ge=0)
    complete: bool = False
    answers: list[DiscoveryAnswer] = Field(default_factory=list, max_length=30)


class BriefEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=0)
    edits: dict[str, Any] = Field(default_factory=dict, max_length=30)
    editor_identity: str | None = Field(default=None, max_length=128)


class ApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=0)
    session_identity: str | None = Field(default=None, max_length=128)


class DiscoveryStateResponse(BaseModel):
    session_id: str
    session_revision: int
    discovery: dict[str, Any]
    intake: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    jobs: list[dict[str, Any]] = Field(default_factory=list)


class DiscoveryOperationResponse(BaseModel):
    session_id: str
    session_revision: int
    job_id: str | None = None
    run_id: str | None = None
    status: str
    discovery: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    jobs: list[dict[str, Any]] = Field(default_factory=list)


def _session_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValidationError(f"Invalid session ID format: '{value}'") from exc


def _translate(exc: DiscoveryOperationError) -> NoReturn:
    raise AppError(
        exc.message,
        code=exc.code,
        status_code=exc.status_code,
        details=exc.details,
    ) from exc


def _state_response(data: dict[str, Any]) -> DiscoveryStateResponse:
    return DiscoveryStateResponse(**data)


@router.get("", response_model=DiscoveryStateResponse)
async def get_discovery_state(
    session_id: str,
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryStateResponse:
    try:
        return _state_response(await service.get_discovery_state(_session_uuid(session_id)))
    except DiscoveryOperationError as exc:
        _translate(exc)


@router.put("/input", response_model=DiscoveryStateResponse)
async def update_discovery_input(
    session_id: str,
    body: IntakeRequest,
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryStateResponse:
    intake = DiscoveryIntake.model_validate(body.model_dump(exclude={"expected_revision"}))
    try:
        return _state_response(
            await service.process_intake(
                _session_uuid(session_id), intake, expected_revision=body.expected_revision
            )
        )
    except DiscoveryOperationError as exc:
        _translate(exc)


@router.post(
    "/questions",
    response_model=DiscoveryOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_questions(
    session_id: str,
    body: EnqueueRequest,
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryOperationResponse:
    try:
        return DiscoveryOperationResponse(
            **await service.enqueue_questions(
                _session_uuid(session_id),
                expected_revision=body.expected_revision,
                idempotency_key=body.idempotency_key,
            )
        )
    except DiscoveryOperationError as exc:
        _translate(exc)


@router.put("/answers", response_model=DiscoveryStateResponse)
async def save_discovery_answers(
    session_id: str,
    body: AnswersRequest,
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryStateResponse:
    try:
        return _state_response(
            await service.save_answers(
                _session_uuid(session_id),
                body.answers,
                question_version=body.question_version,
                complete=body.complete,
                expected_revision=body.expected_revision,
            )
        )
    except DiscoveryOperationError as exc:
        _translate(exc)


@router.post(
    "/brief",
    response_model=DiscoveryOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_brief(
    session_id: str,
    body: EnqueueRequest,
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryOperationResponse:
    try:
        return DiscoveryOperationResponse(
            **await service.enqueue_brief(
                _session_uuid(session_id),
                expected_revision=body.expected_revision,
                idempotency_key=body.idempotency_key,
            )
        )
    except DiscoveryOperationError as exc:
        _translate(exc)


@router.patch("/brief", response_model=DiscoveryStateResponse)
async def edit_discovery_brief(
    session_id: str,
    body: BriefEditRequest,
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryStateResponse:
    try:
        return _state_response(
            await service.edit_brief(
                _session_uuid(session_id),
                body.edits,
                expected_revision=body.expected_revision,
                editor_identity=body.editor_identity,
            )
        )
    except DiscoveryOperationError as exc:
        _translate(exc)


@router.post("/approve", response_model=DiscoveryStateResponse)
async def approve_discovery_brief(
    session_id: str,
    body: ApproveRequest,
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryStateResponse:
    try:
        return _state_response(
            await service.approve_brief(
                _session_uuid(session_id),
                expected_revision=body.expected_revision,
                session_identity=body.session_identity,
            )
        )
    except DiscoveryOperationError as exc:
        _translate(exc)
