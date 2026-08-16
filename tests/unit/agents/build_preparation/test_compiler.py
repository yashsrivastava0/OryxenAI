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
    assert {need.source_id for need in result.resource_needs} == {
        "editorial-hero-image",
        "hero-photo",
        "hero-card",
    }
    editorial = next(
        need for need in result.resource_needs if need.source_id == "editorial-hero-image"
    )
    assert editorial.required_for_handoff is False
    assert "custom text-led composition" in editorial.fallback
    assert result.model_calls == 0
    assert result.source_ref.content_architect_content_hash == "ca-hash"
    assert result.source_ref.visual_design_director_direction_hash == "vdd-hash"
    assert [event.event_id for event in result.events][-1] == "stage_0_complete"


def test_stage0_uses_content_architect_route_identity_over_visual_echoes() -> None:
    content, visual = _inputs()
    content["route_plan"] = [
        {
            "route_id": "home",
            "path": "/",
            "title": "Arjun | Software Engineer",
            "purpose": "Introduce the professional profile and selected work.",
            "publication_status": "approved",
        }
    ]
    visual["pages"][0].update({"path": "/drifted-path", "purpose": "A stale visual-only purpose."})

    result = compile_stage0(content, visual)

    assert result.routes[0].path == "/"
    assert result.routes[0].title == "Arjun | Software Engineer"
    assert result.routes[0].purpose == "Introduce the professional profile and selected work."


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


def test_stage0_marks_critical_optional_external_asset_as_required_for_handoff() -> None:
    content, visual = _inputs()
    visual["asset_briefs"][0]["importance"] = "critical"
    result = compile_stage0(content, visual)
    hero = next(need for need in result.resource_needs if need.source_id == "hero-photo")
    assert hero.required_for_handoff is True


def test_stage0_rejects_approved_user_media_without_an_honest_fallback() -> None:
    content, visual = _inputs()
    visual["asset_briefs"][0].update(
        {"source_policy": "approved_user_media", "fallback_strategy": ""}
    )
    with pytest.raises(BuildPreparationValidationError, match="honest local fallback"):
        compile_stage0(content, visual)


def test_stage0_drops_routes_ca_marked_pending_with_status_diagnostic() -> None:
    content, visual = _inputs()
    # Content Architect marks the only route pending; VDD page stays approved.
    content["route_plan"] = [{"route_id": "home", "path": "/", "publication_status": "pending"}]
    result = compile_stage0(content, visual)
    assert result.routes == []
    assert any(
        "publication_status='pending'" in warning and "did not approve it" in warning
        for warning in result.warnings
    )
    scope_compiled = next(event for event in result.events if event.event_id == "scope_compiled")
    assert scope_compiled.details["dropped_routes"] == [
        {"route_id": "home", "publication_status": "pending"}
    ]
