from __future__ import annotations

import pytest

from oryxenai.agents.build_preparation.compiler import compile_stage0
from oryxenai.agents.build_preparation.validators import BuildPreparationValidationError


def _inputs() -> tuple[dict[str, object], dict[str, object]]:
    content = {
        "approved": {"content_hash": "ca-hash"},
        "route_plan": [{"route_id": "home", "path": "/", "publication_status": "approved"}],
        "page_content_packs": [],
        "public_content_manifest": {},
    }
    visual = {
        "approved": {"visual_direction_hash": "vdd-hash"},
        "pages": [
            {
                "route_id": "home",
                "path": "/",
                "purpose": "Single-page portfolio home",
                "publication_status": "approved",
                "compilable": True,
                "asset_briefs": ["hero-photo"],
                "resource_candidates": ["hero-card"],
                "scenes": [
                    {
                        "scene_id": "hero",
                        "asset_requirements": ["hero-photo"],
                        "resource_candidates": ["hero-card"],
                    }
                ],
            }
        ],
        "asset_briefs": [
            {
                "asset_id": "hero-photo",
                "purpose": "Human-centered hero image",
                "asset_type": "photo",
                "source_status": "needs_acquisition",
                "source_policy": "optional_external_acquisition",
                "importance": "optional",
                "subject": "person at work",
                "mood": "calm",
                "fallback_strategy": "Use typography-only hero.",
            }
        ],
        "resource_candidates": [
            {
                "resource_id": "hero-card",
                "category": "component",
                "why_it_matches": "Supports a focused hero treatment.",
                "possible_use": "Hero content card",
                "priority": "optional",
                "fallback": "Implement a plain bordered card.",
            }
        ],
    }
    return content, visual


def test_stage0_compiles_routes_and_resource_needs_without_model_calls() -> None:
    content, visual = _inputs()
    result = compile_stage0(content, visual)

    assert [route.route_id for route in result.routes] == ["home"]
    assert {need.source_id for need in result.resource_needs} == {"hero-photo", "hero-card"}
    assert result.model_calls == 0
    assert result.source_ref.content_architect_content_hash == "ca-hash"
    assert result.source_ref.visual_design_director_direction_hash == "vdd-hash"
    assert [event.event_id for event in result.events][-1] == "stage_0_complete"


def test_stage0_excludes_non_public_routes_with_warning() -> None:
    content, visual = _inputs()
    visual["pages"] = [dict(visual["pages"][0], publication_status="pending")]
    result = compile_stage0(content, visual)
    assert result.routes == []
    assert result.resource_needs == []
    assert any("Excluded route" in warning for warning in result.warnings)


def test_stage0_rejects_dangling_structured_references() -> None:
    content, visual = _inputs()
    page = visual["pages"][0]
    page["scenes"][0]["resource_candidates"] = ["missing"]
    with pytest.raises(BuildPreparationValidationError, match="unknown resource"):
        compile_stage0(content, visual)


def test_stage0_scope_hash_is_deterministic() -> None:
    content, visual = _inputs()
    assert compile_stage0(content, visual).scope_hash == compile_stage0(content, visual).scope_hash
