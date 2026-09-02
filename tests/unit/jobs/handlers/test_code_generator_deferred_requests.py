from __future__ import annotations

from oryxenai.agents.code_generator.core.development_schemas import SitePlan
from oryxenai.jobs.handlers.code_generator import _build_deferred_requests


def _plan() -> SitePlan:
    return SitePlan.model_validate(
        {
            "plan_id": "plan-home",
            "routes": [
                {
                    "route_id": "home",
                    "path": "/",
                    "section_ids": ["hero", "project"],
                    "responsive_outcome": "stack on mobile",
                    "reduced_motion_outcome": "static equivalent",
                    "interaction_outcome": "keyboard accessible",
                    "composition": {
                        "hierarchy": "headline before evidence",
                        "layout_strategy": "text-led asymmetry",
                        "visual_anchor": "evidence panel",
                    },
                    "responsive_behavior": {
                        "mobile_strategy": "stack sections",
                        "breakpoint_strategy": "collapse at readable measure",
                        "overflow_strategy": "wrap controls",
                        "touch_target_strategy": "large targets",
                    },
                }
            ],
            "creative_thesis": {
                "thesis": "evidence-first systems",
                "distinction": "proof-led rather than card-led",
                "narrative_arc": "positioning to evidence",
            },
            "visual_system": {
                "typography": "confident display and calm body",
                "color_strategy": "single evidence accent",
                "spacing_rhythm": "editorial pauses",
                "motion_vocabulary": "subtle optional reveals",
            },
            "shell": {
                "navigation": "semantic anchor navigation",
                "main_landmark": "one main landmark",
                "focus_treatment": "visible focus ring",
            },
            "shared_component_contracts": [],
            "interactions": [],
            "acceptance_coverage": [
                {
                    "criterion_id": "criterion:home:0",
                    "route_id": "home",
                    "expected_outcome": "evidence-first hierarchy",
                    "source_marker": "data-criterion-id",
                }
            ],
            "resource_slots": [],
            "work_graph": {
                "units": [
                    {"unit_id": "foundation", "kind": "foundation"},
                    {
                        "unit_id": "route-home",
                        "kind": "route",
                        "route_id": "home",
                        "section_ids": ["hero", "project"],
                        "depends_on": ["foundation"],
                    },
                    {
                        "unit_id": "integrate",
                        "kind": "integration",
                        "depends_on": ["foundation", "route-home"],
                        "terminal": True,
                    },
                ]
            },
        }
    )


def _execution_projection(*slots: dict) -> dict:
    return {"execution/contract.json": {"slots": list(slots)}}


def _deferred_slot(**overrides) -> dict:
    slot = {
        "resource_slot_id": "slot-hero-image",
        "category": "photo",
        "route_id": "home",
        "section_ids": ["hero"],
        "component_placement": "hero background image",
        "required": True,
        "resolution": {
            "resolution_type": "deferred_materialized",
            "resource_id": "resource-pexels-1",
            "provider": "pexels",
            "provider_asset_id": "1",
            "source_reference": "https://www.pexels.com/photo/1",
            "license": "Pexels License",
            "license_reference": "https://www.pexels.com/license/",
            "local_paths": ["resources/images/resource-pexels-1.jpg"],
            "import_path": "./resources/images/resource-pexels-1.jpg",
            "rationale": "hero background image",
        },
    }
    slot.update(overrides)
    return slot


def test_deferred_slot_becomes_a_pinned_request_with_no_search_needed() -> None:
    plan = _plan()
    projections = _execution_projection(_deferred_slot())

    requests, candidates = _build_deferred_requests(plan, projections, "input-hash", "plan-hash")

    assert len(requests) == 1
    request = requests[0]
    assert request.request_id == "deferred-slot-hero-image"
    assert request.category == "image"
    assert request.placement.route_id == "home"
    assert request.placement.section_id == "hero"
    assert request.requiredness == "required"
    assert request.source_constraints.allowed_source_kinds == ["pexels"]
    assert request.affected_work_unit_ids == ["route-home"]

    assert set(candidates) == {"deferred-slot-hero-image"}
    candidate = candidates["deferred-slot-hero-image"]
    assert candidate.candidate_id == "1"
    assert candidate.provider_key == "pexels"
    assert candidate.provider_resource_id == "1"
    assert candidate.category == "image"
    assert candidate.canonical_source == "https://www.pexels.com/photo/1"
    assert candidate.licence == "Pexels License"


def test_component_category_maps_and_dependencies_become_metadata() -> None:
    plan = _plan()
    slot = _deferred_slot(
        resource_slot_id="slot-project-card",
        category="component",
        section_ids=["project"],
        required=False,
        resolution={
            "resolution_type": "deferred_materialized",
            "resource_id": "resource-magicui-card",
            "provider": "magicui",
            "provider_asset_id": "magic-card",
            "source_reference": "https://magicui.design/r/magic-card.json",
            "license": "MIT",
            "local_paths": [
                "resources/components/magicui/resource-magicui-card/source/magic-card.tsx"
            ],
            "dependencies": ["motion"],
            "expected_exports": ["MagicCard"],
        },
    )
    projections = _execution_projection(slot)

    requests, candidates = _build_deferred_requests(plan, projections, "input-hash", "plan-hash")

    assert requests[0].category == "component_source"
    assert requests[0].requiredness == "preferred"
    assert requests[0].technical_constraints.required_exports == ["MagicCard"]
    candidate = candidates["deferred-slot-project-card"]
    assert candidate.category == "component_source"
    assert candidate.dependency_metadata == {"motion": []}


def test_non_deferred_and_unsupported_category_slots_are_skipped() -> None:
    plan = _plan()
    projections = _execution_projection(
        _deferred_slot(
            resource_slot_id="slot-local",
            resolution={
                "resolution_type": "local_materialized",
                "resource_id": "resource-already-real",
                "local_paths": ["resources/images/resource-already-real.jpg"],
            },
        ),
        _deferred_slot(
            resource_slot_id="slot-diagram",
            category="diagram",
            resolution={
                "resolution_type": "deferred_materialized",
                "resource_id": "resource-diagram",
                "provider": "pexels",
                "provider_asset_id": "2",
                "local_paths": ["resources/images/resource-diagram.jpg"],
            },
        ),
    )

    requests, candidates = _build_deferred_requests(plan, projections, "input-hash", "plan-hash")

    assert requests == []
    assert candidates == {}
