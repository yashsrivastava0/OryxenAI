"""Public projections that exclude fields outside the active workflows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from oryxenai.agents.content_architect.schemas import (
    ContentArchitectIntake,
    ContentArchitectOutput,
    ContentArchitectPreferences,
    ContentArchitectSourceRef,
    ContentArchitectState,
)
from oryxenai.agents.discovery.schemas import DiscoveryState


def _fields(value: object, model: type[Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {key: item for key, item in value.items() if key in model.model_fields}


def project_session_state(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    projected: dict[str, Any] = {}
    if "discovery" in value:
        projected["discovery"] = _fields(value["discovery"], DiscoveryState)
    if "content_architect" in value:
        raw = _fields(value["content_architect"], ContentArchitectState)
        for key, model in (
            ("intake", ContentArchitectIntake),
            ("preferences", ContentArchitectPreferences),
            ("source_ref", ContentArchitectSourceRef),
        ):
            if key in raw:
                raw[key] = _fields(raw[key], model)
        projected["content_architect"] = raw
    raw_agents = value.get("agents")
    if isinstance(raw_agents, Mapping):
        agents: dict[str, Any] = {}
        for key, item in raw_agents.items():
            if key == "discovery":
                agents[key] = item
            elif key == "content_architect":
                agents[key] = _fields(item, ContentArchitectOutput)
        if agents:
            projected["agents"] = agents
    return projected


def project_agent_output(agent_key: str, value: object) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    if agent_key == "content_architect":
        return _fields(value, ContentArchitectOutput)
    return dict(value)


def project_agent_input(agent_key: str, value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    if agent_key != "content_architect":
        return dict(value)
    allowed = {
        "operation",
        "intake",
        "preferences",
        "prior_output",
        "revision_request",
        "model_profile",
        "input_classification",
        "routing_policy_snapshot",
    }
    projected = {key: item for key, item in value.items() if key in allowed}
    if "intake" in projected:
        projected["intake"] = _fields(projected["intake"], ContentArchitectIntake)
    if "preferences" in projected:
        projected["preferences"] = _fields(projected["preferences"], ContentArchitectPreferences)
    if "prior_output" in projected:
        projected["prior_output"] = _fields(projected["prior_output"], ContentArchitectOutput)
    return projected
