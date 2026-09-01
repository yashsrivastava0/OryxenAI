"""Canonical database projections consumed by Build Preparation.

The session API and the worker must agree on exactly which approved upstream
snapshots a Build Preparation run used.  This module is the single boundary
for that composition: it strips private Content Architect fields, preserves
the Visual Design Director handoff, applies deterministic visual normalization,
and stamps the resulting source reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from oryxenai.agents.build_preparation.compiler import build_source_ref
from oryxenai.agents.build_preparation.schemas import BuildPreparationSourceRef
from oryxenai.agents.build_preparation.validators import (
    validate_content_visual_identity_consistency,
)
from oryxenai.agents.build_preparation.visual_input import normalize_visual_input


def _dump(value: Any) -> Any:
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="json")
    if isinstance(value, dict):
        return dict(value)
    return value


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _dump_list(value: Any) -> list[Any]:
    return [_dump(item) for item in value] if isinstance(value, list) else []


def _publication_status(value: Any) -> str:
    status = _field(value, "publication_status", "")
    return str(getattr(status, "value", status) or "")


@dataclass(frozen=True)
class BuildPreparationInputs:
    """Immutable compact input pair for one Build Preparation run."""

    content_architect: dict[str, Any]
    visual_design_director: dict[str, Any]
    source_ref: BuildPreparationSourceRef


class BuildPreparationInputIntegrator:
    """Compose approved Content Architect and Visual Design Director inputs."""

    def __init__(self, settings: Any) -> None:
        self._settings = settings

    @staticmethod
    def content_projection(state: Any) -> dict[str, Any]:
        """Return the public Content Architect projection only."""
        claim_grounding = [
            _dump(claim)
            for claim in _dump_list(_field(state, "claim_grounding", []))
            if _publication_status(claim) == "approved"
        ]
        return {
            "approved": _dump(_field(state, "approved", None)) or {},
            "site_story_strategy": _dump(_field(state, "site_story_strategy", {})) or {},
            "decision_basis": _dump_list(_field(state, "decision_basis", [])),
            "route_plan": _dump_list(_field(state, "route_plan", [])),
            "page_content_packs": [
                {**dict(pack), "internal_notes": {}}
                for pack in _dump_list(_field(state, "page_content_packs", []))
                if isinstance(pack, dict)
            ],
            "claim_grounding": claim_grounding,
            "public_content_manifest": _dump(_field(state, "public_content_manifest", {})) or {},
            "visual_director_handoff": _dump(_field(state, "visual_director_handoff", {})) or {},
        }

    @staticmethod
    def visual_projection(state: Any) -> dict[str, Any]:
        """Return the Visual Design Director projection used downstream."""
        return {
            "approved": _dump(_field(state, "approved", None)) or {},
            "visual_language": _dump(_field(state, "visual_language", {})) or {},
            "shared_visual_systems": _dump(_field(state, "shared_visual_systems", {})) or {},
            "navigation_direction": _dump(_field(state, "navigation_direction", {})) or {},
            "motion_system": _dump(_field(state, "motion_system", {})) or {},
            "interaction_system": _dump(_field(state, "interaction_system", {})) or {},
            "accessibility_and_performance": _dump(
                _field(state, "accessibility_and_performance", {})
            )
            or {},
            "must_preserve": _dump_list(_field(state, "must_preserve", [])),
            "must_not_fabricate": _dump_list(_field(state, "must_not_fabricate", [])),
            "resource_policy": _dump(_field(state, "resource_policy", {})) or {},
            "compiler_handoff": _dump(_field(state, "compiler_handoff", {})) or {},
            "pages": _dump_list(_field(state, "pages", [])),
            "asset_briefs": _dump_list(_field(state, "asset_briefs", [])),
            "resource_candidates": _dump_list(_field(state, "resource_candidates", [])),
        }

    def compose(
        self,
        content_architect: Any,
        visual_design_director: Any,
        *,
        content_architect_session_revision: int = 0,
        visual_design_director_session_revision: int = 0,
    ) -> BuildPreparationInputs:
        content = self.content_projection(content_architect)
        visual = self.visual_projection(visual_design_director)
        config = self._settings.build_preparation
        normalized = normalize_visual_input(
            content,
            visual,
            image_target=int(config.editorial_image_budget),
            image_maximum=int(config.editorial_image_maximum),
            component_target=int(config.visual_component_budget),
            component_maximum=int(config.visual_component_maximum),
            enabled=bool(config.auto_derive_visual_resources),
        )
        validate_content_visual_identity_consistency(content, normalized.visual)
        return BuildPreparationInputs(
            content_architect=content,
            visual_design_director=normalized.visual,
            source_ref=build_source_ref(
                content,
                normalized.visual,
                content_architect_session_revision=content_architect_session_revision,
                visual_design_director_session_revision=visual_design_director_session_revision,
            ),
        )
