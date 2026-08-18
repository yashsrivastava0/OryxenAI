from __future__ import annotations

import pytest

from oryxenai.agents.build_preparation.compiler import compile_stage0
from oryxenai.agents.build_preparation.validators import BuildPreparationValidationError
from oryxenai.agents.build_preparation.visual_input import normalize_visual_input


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


def _enriched_content() -> dict[str, object]:
    return {
        "approved": {"content_hash": "ca-enriched"},
        "route_plan": [
            {
                "route_id": "home",
                "path": "/",
                "publication_status": "approved",
                "section_sequence": [
                    "home:hero",
                    "home:capabilities",
                    "home:experience",
                    "home:selected-work",
                    "home:connect",
                ],
            }
        ],
        "page_content_packs": [
            {
                "route_id": "home",
                "sections": [
                    {"section_id": "home:hero", "content": {"headline": "Build systems."}},
                    {
                        "section_id": "home:capabilities",
                        "content": {"heading": "Capabilities", "items": ["APIs", "Delivery"]},
                    },
                    {
                        "section_id": "home:experience",
                        "content": {"heading": "Experience", "entries": ["One", "Two"]},
                    },
                    {
                        "section_id": "home:selected-work",
                        "content": {"heading": "Selected work", "projects": ["One", "Two"]},
                    },
                    {"section_id": "home:connect", "content": {"heading": "Connect"}},
                ],
            }
        ],
        "site_story_strategy": {
            "positioning": "Backend and platform engineer building dependable APIs and delivery systems."
        },
    }


def test_missing_vdd_derives_deterministic_visual_direction_and_roles() -> None:
    content = _enriched_content()
    first = normalize_visual_input(content, {})
    second = normalize_visual_input(content, {})

    assert first.mode == "assumed_from_content"
    assert first.assumption_hash == second.assumption_hash
    assert len(first.visual["asset_briefs"]) == 5
    assert (
        len(
            [
                item
                for item in first.visual["resource_candidates"]
                if item["category"] == "visual_component"
            ]
        )
        == 3
    )
    result = compile_stage0(content, {})
    assert result.visual_input_mode == "assumed_from_content"
    assert result.assumption_hash
    assert {need.section_ids[0] for need in result.resource_needs if need.section_ids} >= {
        "home:hero",
        "home:selected-work",
    }


def test_partial_vdd_merges_roles_but_preserves_explicit_prohibition() -> None:
    content = _enriched_content()
    visual = {
        "approved": {"visual_direction_hash": "vdd-partial"},
        "must_not_fabricate": ["No stock imagery or external photos."],
        "pages": [{"route_id": "home", "publication_status": "approved", "scenes": []}],
        "asset_briefs": [],
        "resource_candidates": [],
    }

    normalized = normalize_visual_input(content, visual)
    assert normalized.mode == "merged_vdd_assumptions"
    assert normalized.visual["asset_briefs"] == []
    assert len(normalized.visual["resource_candidates"]) == 3
    result = compile_stage0(content, visual)
    assert not any(need.category == "editorial_photo" for need in result.resource_needs)
    assert any(need.category == "visual_component" for need in result.resource_needs)


def test_component_roles_are_distinct_and_route_aware() -> None:
    normalized = normalize_visual_input(_enriched_content(), {})
    roles = [
        item
        for item in normalized.visual["resource_candidates"]
        if item["category"] == "visual_component"
    ]
    assert {item["interaction_role"] for item in roles} == {
        "capability-grouping",
        "experience-timeline",
        "selected-work-detail",
    }
    assert {item["where_it_may_help"].split(" / ")[0] for item in roles} == {"home"}


def test_component_budget_does_not_create_roles_for_static_sections() -> None:
    content, visual = _enriched_content(), {}
    for section in content["page_content_packs"][0]["sections"]:
        section["content"] = {"heading": section["section_id"]}

    normalized = normalize_visual_input(
        content,
        visual,
        component_target=4,
        component_maximum=6,
    )

    assert [
        item
        for item in normalized.visual["resource_candidates"]
        if item["category"] == "visual_component"
    ] == []


def test_stage0_compiles_routes_and_resource_needs_without_model_calls() -> None:
    content, visual = _inputs()
    result = compile_stage0(content, visual)

    assert [route.route_id for route in result.routes] == ["home"]
    assert {need.source_id for need in result.resource_needs} == {
        "hero-photo",
        "hero-card",
    }
    assert (
        next(
            need for need in result.resource_needs if need.source_id == "hero-photo"
        ).required_for_handoff
        is True
    )
    assert (
        next(
            need for need in result.resource_needs if need.source_id == "hero-card"
        ).required_for_handoff
        is True
    )
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
