"""Build Preparation session API and detached Phase 2 harness API."""

from __future__ import annotations

import json
from typing import Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field

from oryxenai.agents.build_preparation.fixture import FixturePreparationError, run_fixture
from oryxenai.agents.build_preparation.service import (
    BuildPreparationOperationError,
    BuildPreparationService,
)
from oryxenai.api.dependencies import get_build_preparation_service
from oryxenai.api.errors import AppError, ValidationError
from oryxenai.core.logging import get_request_id

router = APIRouter(prefix="/sessions/{session_id}/build-preparation", tags=["build-preparation"])
fixture_router = APIRouter(prefix="/build-preparation/fixture", tags=["build-preparation-fixture"])


class StartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_profile: str | None = None


class BuildPreparationStateResponse(BaseModel):
    session_id: str
    session_revision: int
    build_preparation: dict[str, Any]
    jobs: list[dict[str, Any]] = Field(default_factory=list)


class FixtureRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: dict[str, Any] | None = None
    output_json: str | None = None
    content_architect: dict[str, Any] | None = None
    content_architect_json: str | None = None
    live_model: bool = False
    live_providers: bool = False
    model_profile: str | None = None


def _session_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValidationError(f"Invalid session ID format: '{value}'") from exc


def _translate(exc: BuildPreparationOperationError) -> NoReturn:
    raise AppError(
        exc.message,
        code=exc.code,
        status_code=exc.status_code,
        details=exc.details,
    ) from exc


@router.get("", response_model=BuildPreparationStateResponse)
async def get_build_preparation_state(
    session_id: str,
    service: BuildPreparationService = Depends(get_build_preparation_service),
) -> BuildPreparationStateResponse:
    try:
        return BuildPreparationStateResponse(**await service.get_state(_session_uuid(session_id)))
    except BuildPreparationOperationError as exc:
        _translate(exc)


@router.post(
    "/start",
    response_model=BuildPreparationStateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_build_preparation(
    session_id: str,
    body: StartRequest,
    service: BuildPreparationService = Depends(get_build_preparation_service),
) -> BuildPreparationStateResponse:
    try:
        return BuildPreparationStateResponse(
            **await service.start(
                _session_uuid(session_id),
                model_profile=body.model_profile or "",
                request_id=get_request_id() or "",
            )
        )
    except BuildPreparationOperationError as exc:
        _translate(exc)


@router.post(
    "/regenerate",
    response_model=BuildPreparationStateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def regenerate_build_preparation(
    session_id: str,
    body: StartRequest | None = None,
    service: BuildPreparationService = Depends(get_build_preparation_service),
) -> BuildPreparationStateResponse:
    try:
        return BuildPreparationStateResponse(
            **await service.regenerate(
                _session_uuid(session_id),
                model_profile=(body.model_profile if body else None) or "",
                request_id=get_request_id() or "",
            )
        )
    except BuildPreparationOperationError as exc:
        _translate(exc)


@fixture_router.post("/run")
async def run_build_preparation_fixture(
    request: Request,
    body: FixtureRunRequest | None = None,
) -> dict[str, Any]:
    settings = request.app.state.settings
    if not settings.is_dev_ui_enabled or not settings.build_preparation.fixture_enabled:
        raise AppError(
            "The temporary Build Preparation fixture is disabled.",
            code="FIXTURE_DISABLED",
            status_code=404,
        )
    override: dict[str, Any] | None = None
    if body is not None and body.output is not None and body.output_json is not None:
        raise AppError(
            "Provide either output or output_json, not both.",
            code="FIXTURE_INPUT_AMBIGUOUS",
            status_code=422,
        )
    if body is not None and body.output_json is not None:
        if len(body.output_json.encode("utf-8")) > settings.api.max_input_bytes:
            raise AppError(
                "The fixture output is too large.",
                code="FIXTURE_INPUT_TOO_LARGE",
                status_code=413,
            )
        try:
            parsed = json.loads(body.output_json)
        except json.JSONDecodeError as exc:
            raise AppError(
                "The pasted fixture output is not valid JSON.",
                code="FIXTURE_INPUT_INVALID",
                status_code=422,
            ) from exc
        if not isinstance(parsed, dict):
            raise AppError(
                "The fixture output must be a JSON object.",
                code="FIXTURE_INPUT_INVALID",
                status_code=422,
            )
        override = parsed
    elif body is not None and body.output is not None:
        override = body.output
    content_architect_override: dict[str, Any] | None = None
    if (
        body is not None
        and body.content_architect is not None
        and body.content_architect_json is not None
    ):
        raise AppError(
            "Provide either content_architect or content_architect_json, not both.",
            code="FIXTURE_INPUT_AMBIGUOUS",
            status_code=422,
        )
    if body is not None and body.content_architect_json is not None:
        if len(body.content_architect_json.encode("utf-8")) > settings.api.max_input_bytes:
            raise AppError(
                "The Content Architect fixture output is too large.",
                code="FIXTURE_INPUT_TOO_LARGE",
                status_code=413,
            )
        try:
            parsed_content_architect = json.loads(body.content_architect_json)
        except json.JSONDecodeError as exc:
            raise AppError(
                "The pasted Content Architect output is not valid JSON.",
                code="FIXTURE_INPUT_INVALID",
                status_code=422,
            ) from exc
        if not isinstance(parsed_content_architect, dict):
            raise AppError(
                "The Content Architect fixture output must be a JSON object.",
                code="FIXTURE_INPUT_INVALID",
                status_code=422,
            )
        content_architect_override = parsed_content_architect
    elif body is not None and body.content_architect is not None:
        content_architect_override = body.content_architect
    try:
        return await run_fixture(
            settings,
            raw_override=override,
            content_architect_override=content_architect_override,
            live_model=body.live_model if body else False,
            live_providers=body.live_providers if body else False,
            model_profile=(body.model_profile if body else None) or "",
        )
    except FixturePreparationError as exc:
        raise AppError(
            exc.message,
            code=exc.code,
            status_code=422,
            details=exc.details,
        ) from exc
