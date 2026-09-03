"""Build Preparation session API and detached Phase 2 harness API."""

from __future__ import annotations

import json
from typing import Any, NoReturn, cast

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from oryxenai.agents.build_preparation.fixture import FixturePreparationError, run_fixture
from oryxenai.agents.build_preparation.fixture_runs import (
    FixtureRunConflictError,
    FixtureRunManager,
    FixtureRunNotFoundError,
)
from oryxenai.agents.build_preparation.service import (
    BuildPreparationOperationError,
    BuildPreparationService,
)
from oryxenai.api.dependencies import (
    get_build_preparation_service,
    require_admin,
    require_pipeline_mutable,
    require_pipeline_session,
)
from oryxenai.api.errors import AppError
from oryxenai.auth.authorization import PortfolioAccess
from oryxenai.core.logging import get_request_id

router = APIRouter(prefix="/sessions/{session_id}/build-preparation", tags=["build-preparation"])
fixture_router = APIRouter(
    prefix="/build-preparation/fixture",
    tags=["build-preparation-fixture"],
    dependencies=[Depends(require_admin)],
)
detached_fixture_router = APIRouter(
    prefix="/build-preparation/fixture",
    tags=["build-preparation-fixture"],
)


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


def _translate(exc: BuildPreparationOperationError) -> NoReturn:
    raise AppError(
        exc.message,
        code=exc.code,
        status_code=exc.status_code,
        details=exc.details,
    ) from exc


def _fixture_enabled(request: Request) -> None:
    settings = request.app.state.settings
    if not settings.is_dev_ui_enabled or not settings.build_preparation.fixture_enabled:
        raise AppError(
            "The temporary Build Preparation fixture is disabled.",
            code="FIXTURE_DISABLED",
            status_code=404,
        )


def _fixture_inputs(
    request: Request, body: FixtureRunRequest | None
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Validate the two fixture payload forms before starting work."""
    settings = request.app.state.settings
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
    return override, content_architect_override


def _fixture_manager(request: Request) -> FixtureRunManager:
    return cast(FixtureRunManager, request.app.state.fixture_run_manager)


@router.get("", response_model=BuildPreparationStateResponse)
async def get_build_preparation_state(
    session_id: str,
    access: PortfolioAccess = Depends(require_pipeline_session),
    service: BuildPreparationService = Depends(get_build_preparation_service),
) -> BuildPreparationStateResponse:
    try:
        return BuildPreparationStateResponse(**await service.get_state(access.session.id))
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
    access: PortfolioAccess = Depends(require_pipeline_session),
    _mutable: PortfolioAccess = Depends(require_pipeline_mutable),
    service: BuildPreparationService = Depends(get_build_preparation_service),
) -> BuildPreparationStateResponse:
    try:
        return BuildPreparationStateResponse(
            **await service.start(
                access.session.id,
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
    access: PortfolioAccess = Depends(require_pipeline_session),
    _mutable: PortfolioAccess = Depends(require_pipeline_mutable),
    service: BuildPreparationService = Depends(get_build_preparation_service),
) -> BuildPreparationStateResponse:
    try:
        return BuildPreparationStateResponse(
            **await service.regenerate(
                access.session.id,
                model_profile=(body.model_profile if body else None) or "",
                request_id=get_request_id() or "",
            )
        )
    except BuildPreparationOperationError as exc:
        _translate(exc)


@router.get("/download")
async def download_build_preparation_brief(
    session_id: str,
    doc: str = "content",
    access: PortfolioAccess = Depends(require_pipeline_session),
    service: BuildPreparationService = Depends(get_build_preparation_service),
) -> Response:
    doc = "visual" if doc == "visual" else "content"
    try:
        data, content_type = await service.download_brief(access.session.id, doc)
    except BuildPreparationOperationError as exc:
        _translate(exc)
    filename_stem = "visual-and-build-brief" if doc == "visual" else "content-and-narrative-brief"
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename_stem}-{str(access.session.id)[:8]}.md"'
            )
        },
    )


@fixture_router.post("/run")
@detached_fixture_router.post("/run")
async def run_build_preparation_fixture(
    request: Request,
    body: FixtureRunRequest | None = None,
) -> dict[str, Any]:
    _fixture_enabled(request)
    settings = request.app.state.settings
    override, content_architect_override = _fixture_inputs(request, body)
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


@fixture_router.get("/preflight")
@detached_fixture_router.get("/preflight")
async def get_build_preparation_fixture_preflight(request: Request) -> dict[str, Any]:
    _fixture_enabled(request)
    return _fixture_manager(request).preflight()


@fixture_router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
@detached_fixture_router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def start_build_preparation_fixture_run(
    request: Request,
    body: FixtureRunRequest | None = None,
) -> dict[str, Any]:
    _fixture_enabled(request)
    override, content_architect_override = _fixture_inputs(request, body)
    try:
        return await _fixture_manager(request).start(
            visual_design_director=override,
            content_architect=content_architect_override,
            live_model=body.live_model if body else False,
            live_providers=body.live_providers if body else False,
            model_profile=(body.model_profile if body else None) or "",
        )
    except FixtureRunConflictError as exc:
        raise AppError(
            "A Build Preparation fixture run is already in progress.",
            code="FIXTURE_RUN_IN_PROGRESS",
            status_code=409,
        ) from exc


@fixture_router.get("/runs/{run_id}")
@detached_fixture_router.get("/runs/{run_id}")
async def get_build_preparation_fixture_run(request: Request, run_id: str) -> dict[str, Any]:
    _fixture_enabled(request)
    try:
        return await _fixture_manager(request).get(run_id)
    except FixtureRunNotFoundError as exc:
        raise AppError(
            "The requested Build Preparation fixture run was not found.",
            code="FIXTURE_RUN_NOT_FOUND",
            status_code=404,
        ) from exc


@fixture_router.get("/runs/{run_id}/download")
@detached_fixture_router.get("/runs/{run_id}/download")
async def download_build_preparation_fixture_run(
    request: Request, run_id: str, doc: str = "content"
) -> FileResponse:
    _fixture_enabled(request)
    doc = "visual" if doc == "visual" else "content"
    try:
        brief_path = await _fixture_manager(request).download_path(run_id, doc)
    except FixtureRunNotFoundError as exc:
        raise AppError(
            "The requested Build Preparation fixture brief was not found.",
            code="FIXTURE_RUN_BRIEF_NOT_FOUND",
            status_code=404,
        ) from exc
    filename_stem = "visual-and-build-brief" if doc == "visual" else "content-and-narrative-brief"
    return FileResponse(
        brief_path,
        media_type="text/markdown",
        filename=f"{filename_stem}-{run_id[:8]}.md",
    )
