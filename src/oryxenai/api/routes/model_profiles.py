"""Safe model-profile metadata for the developer UI."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from oryxenai.agents.shared.model_router import ModelRouter
from oryxenai.agents.shared.model_runtime import safe_preflight_error
from oryxenai.agents.shared.providers.errors import ProviderConfigError
from oryxenai.api.dependencies import require_admin, require_detached_pipeline_mode
from oryxenai.api.errors import AppError

router = APIRouter(
    prefix="/model-profiles",
    tags=["model-profiles"],
    dependencies=[Depends(require_admin)],
)

pipeline_router = APIRouter(
    prefix="/pipeline/model-profiles",
    tags=["pipeline-model-profiles"],
    dependencies=[Depends(require_detached_pipeline_mode)],
)


class ModelProfileOptionResponse(BaseModel):
    """Non-secret profile metadata; credentials and endpoints stay server-side."""

    id: str
    label: str
    provider: str
    model: str
    is_default: bool


@router.get("", response_model=list[ModelProfileOptionResponse])
async def list_model_profiles(request: Request) -> list[ModelProfileOptionResponse]:
    settings = request.app.state.settings
    return [
        ModelProfileOptionResponse(**option.as_dict())
        for option in ModelRouter(settings.models).public_options()
    ]


class PipelineProfileOptionResponse(BaseModel):
    id: str
    label: str
    is_default: bool


class PipelineProfileListResponse(BaseModel):
    default_model_profile: str = ""
    options: list[PipelineProfileOptionResponse]


class PipelineProfilePreflightRequest(BaseModel):
    model_profile: str = ""


@pipeline_router.get("", response_model=PipelineProfileListResponse)
async def list_pipeline_model_profiles(request: Request) -> PipelineProfileListResponse:
    options = ModelRouter(request.app.state.settings.models).public_options()
    return PipelineProfileListResponse(
        default_model_profile="",
        options=[
            PipelineProfileOptionResponse(
                id=option.id,
                label=option.label,
                is_default=option.is_default,
            )
            for option in options
        ],
    )


@pipeline_router.post("/preflight", response_model=dict[str, Any])
async def preflight_pipeline_model_profile(
    request: Request,
    body: PipelineProfilePreflightRequest,
) -> dict[str, Any]:
    try:
        receipt = await request.app.state.model_runtime.preflight(
            [
                "discovery",
                "content_architect",
                "visual_design_director",
                "build_preparation",
            ],
            body.model_profile,
        )
        return dict(receipt)
    except ProviderConfigError as exc:
        raise AppError(str(exc), code="MODEL_PROFILE_INVALID", status_code=400) from exc
    except Exception as exc:
        code, message = safe_preflight_error(exc)
        raise AppError(message, code=code, status_code=503) from exc
