"""Feature-gated standalone Code Generator developer API."""

from __future__ import annotations

from typing import Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from oryxenai.agents.code_generator.core.development_input import DevelopmentInputError
from oryxenai.agents.code_generator.core.development_schemas import (
    BuildPreparationRunRequest,
    FixtureRunRequest,
)
from oryxenai.agents.code_generator.core.development_service import (
    CodeGeneratorDevelopmentService,
    DevelopmentRunError,
)
from oryxenai.api.dependencies import get_code_generator_development_service
from oryxenai.api.errors import AppError

router = APIRouter(prefix="/development/code-generator", tags=["code-generator-development"])


def _run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise AppError(
            "Invalid development run ID.", code="RUN_ID_INVALID", status_code=422
        ) from exc


def _error(exc: DevelopmentRunError | DevelopmentInputError) -> NoReturn:
    raise AppError(
        exc.message,
        code=exc.code,
        status_code=getattr(exc, "status_code", 422),
        details=getattr(exc, "details", {}),
    ) from exc


@router.get("/fixtures")
async def fixtures(
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    return {"fixtures": service.fixtures()}


@router.get("/readiness")
async def readiness(
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    """Non-secret prerequisites for an honest standalone developer workflow."""

    return service.readiness()


@router.post("/provider-preflight")
async def provider_preflight(
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    """Verify the configured provider request contract without portfolio data."""

    try:
        return await service.provider_preflight()
    except DevelopmentRunError as exc:
        _error(exc)


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def create_fixture_run(
    request: Request,
    body: FixtureRunRequest,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return (
            await service.create_fixture(
                body.fixture_id, idempotency_key=request.headers.get("Idempotency-Key", "")
            )
        ).model_dump(mode="json")
    except (DevelopmentRunError, DevelopmentInputError) as exc:
        _error(exc)


@router.get("/build-preparation-packs")
async def build_preparation_packs(
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    """Newest-first local Build Preparation debug-mirror packs."""

    return {"packs": service.build_preparation_packs()}


@router.post("/runs/from-build-preparation", status_code=status.HTTP_202_ACCEPTED)
async def create_build_preparation_run(
    request: Request,
    body: BuildPreparationRunRequest,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return (
            await service.create_from_build_preparation(
                body.pack, idempotency_key=request.headers.get("Idempotency-Key", "")
            )
        ).model_dump(mode="json")
    except (DevelopmentRunError, DevelopmentInputError) as exc:
        _error(exc)


@router.post("/runs/upload", status_code=status.HTTP_202_ACCEPTED)
async def create_upload_run(
    request: Request,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    filename = request.headers.get("X-Upload-Filename", "")
    mime_type = request.headers.get("content-type", "")
    try:
        limit = int(request.app.state.settings.code_generator_development.max_upload_bytes)
        content_length = request.headers.get("content-length", "")
        if content_length.isdigit() and int(content_length) > limit:
            raise DevelopmentInputError(
                "UPLOAD_TOO_LARGE", "The uploaded ZIP exceeds the configured size limit."
            )
        chunks: list[bytes] = []
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > limit:
                raise DevelopmentInputError(
                    "UPLOAD_TOO_LARGE", "The uploaded ZIP exceeds the configured size limit."
                )
            chunks.append(chunk)
        data = b"".join(chunks)
        return (
            await service.create_upload(
                filename=filename,
                mime_type=mime_type,
                data=data,
                idempotency_key=request.headers.get("Idempotency-Key", ""),
            )
        ).model_dump(mode="json")
    except (DevelopmentRunError, DevelopmentInputError) as exc:
        _error(exc)


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return (await service.get(_run_id(run_id))).model_dump(mode="json")
    except DevelopmentRunError as exc:
        _error(exc)


@router.get("/runs/{run_id}/events")
async def get_events(
    run_id: str,
    after: int = 0,
    limit: int = 50,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        events = await service.events(_run_id(run_id), after=after, limit=limit)
        return {"events": [event.model_dump(mode="json") for event in events]}
    except DevelopmentRunError as exc:
        _error(exc)


@router.get("/runs/{run_id}/plan")
async def get_plan(
    run_id: str,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return await service.plan(_run_id(run_id))
    except DevelopmentRunError as exc:
        _error(exc)


@router.post("/runs/{run_id}/acquire", status_code=status.HTTP_202_ACCEPTED)
async def acquire_run(
    request: Request,
    run_id: str,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return (
            await service.acquire(
                _run_id(run_id), idempotency_key=request.headers.get("Idempotency-Key", "")
            )
        ).model_dump(mode="json")
    except DevelopmentRunError as exc:
        _error(exc)


@router.get("/runs/{run_id}/acquisition")
async def get_acquisition(
    run_id: str,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return await service.acquisition(_run_id(run_id))
    except DevelopmentRunError as exc:
        _error(exc)


@router.get("/runs/{run_id}/dependencies")
async def get_dependencies(
    run_id: str,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return await service.dependencies(_run_id(run_id))
    except DevelopmentRunError as exc:
        _error(exc)


@router.get("/runs/{run_id}/plan-deltas")
async def get_plan_deltas(
    run_id: str,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return await service.plan_deltas(_run_id(run_id))
    except DevelopmentRunError as exc:
        _error(exc)


@router.post("/runs/{run_id}/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_run(
    request: Request,
    run_id: str,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return (
            await service.generate(
                _run_id(run_id), idempotency_key=request.headers.get("Idempotency-Key", "")
            )
        ).model_dump(mode="json")
    except DevelopmentRunError as exc:
        _error(exc)


@router.get("/runs/{run_id}/generation")
async def get_generation(
    run_id: str,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return await service.generation(_run_id(run_id))
    except DevelopmentRunError as exc:
        _error(exc)


@router.post("/runs/{run_id}/verify", status_code=status.HTTP_202_ACCEPTED)
async def verify_run(
    request: Request,
    run_id: str,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return (
            await service.verify(
                _run_id(run_id), idempotency_key=request.headers.get("Idempotency-Key", "")
            )
        ).model_dump(mode="json")
    except DevelopmentRunError as exc:
        _error(exc)


@router.get("/runs/{run_id}/verification")
async def get_verification(
    run_id: str,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return await service.verification(_run_id(run_id))
    except DevelopmentRunError as exc:
        _error(exc)


@router.get("/runs/{run_id}/preview")
async def get_preview(
    run_id: str,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return await service.preview(_run_id(run_id))
    except DevelopmentRunError as exc:
        _error(exc)


@router.get("/runs/{run_id}/source-manifest")
async def get_source_manifest(
    run_id: str,
    service: CodeGeneratorDevelopmentService = Depends(get_code_generator_development_service),
) -> dict[str, Any]:
    try:
        return await service.source_manifest(_run_id(run_id))
    except DevelopmentRunError as exc:
        _error(exc)
