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
    # No direct_source_url in this fixture -- falls back to source_reference.
    assert candidate.canonical_source == "https://www.pexels.com/photo/1"
    assert candidate.licence == "Pexels License"
    # ImageAdapter must fetch and optimize this one already-decided image,
    # not pre-generate a full responsive set on top of the local rendition
    # generation downstream already performs from a single file.
    assert candidate.technical_metadata == {"single_rendition_only": True}


def test_image_candidate_prefers_the_direct_fetch_url_over_the_page_url() -> None:
    plan = _plan()
    slot = _deferred_slot(
        resolution={
            **_deferred_slot()["resolution"],
            "direct_source_url": "https://images.pexels.com/photos/1/pexels-photo-1.jpeg",
        }
    )
    projections = _execution_projection(slot)

    _, candidates = _build_deferred_requests(plan, projections, "input-hash", "plan-hash")

    candidate = candidates["deferred-slot-hero-image"]
    # ImageAdapter's materialize() fetches canonical_source directly -- it
    # must never receive the human-readable Pexels page URL, which 404s as
    # an image download and isn't on the approved image-host allowlist.
    assert candidate.canonical_source == "https://images.pexels.com/photos/1/pexels-photo-1.jpeg"


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
    # ComponentSourceAdapter.materialize() only performs the registry-aware
    # fetch (parsing files[].content out of the item JSON) when this exact
    # metadata shape is present; otherwise it falls back to treating the
    # raw registry response bytes as if they were the component source,
    # which fails safety inspection on the registry JSON's own $schema URL.
    retrieval_candidate = candidate.technical_metadata["retrieval_candidate"]
    assert retrieval_candidate["provider"] == "magicui"
    assert retrieval_candidate["name"] == "magic-card"
    assert retrieval_candidate["item_url"] == "https://magicui.design/r/magic-card.json"
    assert retrieval_candidate["dependencies"] == ["motion"]
    # canonical_source stays the registry item URL for components -- the
    # registry-aware fetch path resolves it itself; only image/font
    # categories use canonical_source as a direct-download URL.
    assert candidate.canonical_source == "https://magicui.design/r/magic-card.json"


def test_font_candidate_carries_per_weight_direct_urls() -> None:
    plan = _plan()
    slot = _deferred_slot(
        resource_slot_id="slot-font",
        category="font",
        resolution={
            "resolution_type": "deferred_materialized",
            "resource_id": "resource-fontsource-1",
            "provider": "fontsource",
            "provider_asset_id": "space-grotesk",
            "source_reference": "https://api.fontsource.org/v1/fonts/space-grotesk",
            "license": "OFL-1.1",
            "local_paths": [
                "resources/fonts/resource-fontsource-1/400-normal.woff2",
                "resources/fonts/resource-fontsource-1/700-normal.woff2",
            ],
            "direct_source_urls": {
                "400-normal": "https://cdn.jsdelivr.net/fontsource/fonts/space-grotesk@latest/400-normal.woff2",
                "700-normal": "https://cdn.jsdelivr.net/fontsource/fonts/space-grotesk@latest/700-normal.woff2",
            },
        },
    )
    projections = _execution_projection(slot)

    _, candidates = _build_deferred_requests(plan, projections, "input-hash", "plan-hash")

    candidate = candidates["deferred-slot-font"]
    # FontAdapter.materialize() only fetches the real per-weight CDN files
    # when this exact key is present; otherwise it falls back to treating
    # the Fontsource metadata-API response as if it were font bytes, which
    # fails the WOFF/WOFF2 magic-byte check.
    assert candidate.technical_metadata["font_urls"] == {
        "400-normal": "https://cdn.jsdelivr.net/fontsource/fonts/space-grotesk@latest/400-normal.woff2",
        "700-normal": "https://cdn.jsdelivr.net/fontsource/fonts/space-grotesk@latest/700-normal.woff2",
    }


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
