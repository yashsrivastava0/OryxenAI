"""Safe model-profile metadata for the developer UI."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from oryxenai.agents.shared.model_router import ModelRouter

router = APIRouter(prefix="/model-profiles", tags=["model-profiles"])


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
