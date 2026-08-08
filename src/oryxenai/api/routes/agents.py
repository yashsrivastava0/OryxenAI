"""Agents listing endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from oryxenai.agents.shared.registry import AgentRegistry
from oryxenai.api.dependencies import get_agent_registry

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentInfo(BaseModel):
    key: str
    name: str
    description: str
    mock: bool = True


@router.get("", response_model=list[AgentInfo])
async def list_agents(
    registry: AgentRegistry = Depends(get_agent_registry),
) -> list[AgentInfo]:
    """Return registered mock agents with minimal metadata."""
    info_map: dict[str, str] = {
        "discovery": "Gathers user intent and requirements.",
        "content_architect": "Turns an approved Discovery brief into final, grounded content and a route plan.",
        "visual_design_director": (
            "Turns an approved Content Architect output into a visual-experience "
            "direction: global visual language, per-route storyboards, scenes, "
            "motion/interaction system, and asset/resource intent."
        ),
        "code_generator": "Generates portfolio site source files.",
    }
    result: list[AgentInfo] = []
    for key in sorted(registry.list_keys(), key=lambda k: k.value):
        result.append(
            AgentInfo(
                key=key.value,
                name=key.value.replace("_", " ").title(),
                description=info_map.get(key.value, ""),
            )
        )
    return result
