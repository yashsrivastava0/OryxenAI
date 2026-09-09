from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from tests.unit.agents.code_generator.test_v4_contracts import _blueprint

from oryxenai.agents.code_generator.core.design_realization import compile_design_realization
from oryxenai.agents.code_generator.core.development_schemas import (
    ExecutionBindingV2,
    ResourcePlacementV4,
    RoutePlan,
    SitePlan,
)
from oryxenai.agents.code_generator.core.image_policy import build_image_policy_snapshot
from oryxenai.agents.code_generator.core.layout_recipe_catalogue import (
    compile_layout_recipe_css,
    layout_recipe_context,
)
from oryxenai.agents.code_generator.core.portfolio_export import (
    _generation_report,
    build_image_evidence,
)
from oryxenai.core.settings import Settings


def _placement(slot_id: str) -> ResourcePlacementV4:
    return ResourcePlacementV4(
        resource_slot_id=slot_id,
        route_id="home",
        section_id="hero",
        element_marker=f'data-resource-slot="{slot_id}"',
        element_selector=f'[data-resource-slot="{slot_id}"]',
        alt_policy="decorative",
        fit="cover",
        loading="eager",
        responsive_behavior="Keep the media bounded below the approved copy.",
        sizes="(max-width: 48rem) 100vw, 40vw",
        aspect_ratio_min=1.2,
        aspect_ratio_max=1.8,
    )


def _image_plan() -> SitePlan:
    blueprint = _blueprint().model_copy(
        update={"resource_placements": [_placement("slot-hero"), _placement("slot-detail")]}
    )
    route = RoutePlan(
        route_id="home",
        path="/",
        section_ids=["hero"],
        responsive_outcome="stack on mobile",
        reduced_motion_outcome="static equivalent",
        interaction_outcome="keyboard accessible",
        storage_key="home",
    )
    bindings = [
        ExecutionBindingV2(
            resource_slot_id=slot_id,
            route_id="home",
            category="editorial_photo",
            purpose="supporting image",
            resolution_type="deferred_materialized",
            local_paths=[f"resources/images/{slot_id}.jpg"],
        )
        for slot_id in ("slot-hero", "slot-detail")
    ]
    return SitePlan(
        plan_id="image-plan",
        routes=[route],
        experience_blueprint=blueprint,
        execution_bindings=bindings,
    )


def test_image_policy_is_snapshot_hashed_and_primary_route_scoped() -> None:
    plan = _image_plan()
    policy = build_image_policy_snapshot(Settings(), plan=plan)

    assert policy.text_only_exemption is False
    assert policy.approved_image_slot_ids == ["slot-detail", "slot-hero"]
    assert policy.primary_route_id == "home"
    assert policy.minimum_visible_images == 1
    assert policy.preferred_visible_images == 2
    assert policy.policy_hash
    assert policy.model_validate(policy.model_dump(mode="json")).policy_hash == policy.policy_hash


def test_text_only_policy_is_honest_when_no_image_slots_are_admitted() -> None:
    blueprint = _blueprint()
    plan = SitePlan(
        plan_id="text-plan",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero"],
                responsive_outcome="stack",
                reduced_motion_outcome="static",
                interaction_outcome="keyboard",
            )
        ],
        experience_blueprint=blueprint,
        execution_bindings=[],
    )

    policy = build_image_policy_snapshot(Settings(), plan=plan)

    assert policy.text_only_exemption is True
    assert policy.approved_image_slot_ids == []
    assert policy.minimum_visible_images == 0
    assert policy.require_primary_route_image is False


def test_layout_catalogue_emits_all_three_marker_bound_recipe_floors() -> None:
    regions = [
        SimpleNamespace(
            region_id=f"region-{recipe}",
            route_id="home",
            section_id=recipe,
            region_selector=f'[data-region-id="region-{recipe}"]',
            layout_recipe=recipe,
            gap=SimpleNamespace(value=2, unit="rem"),
        )
        for recipe in ("text-with-supporting-media", "work-detail-list", "timeline-list")
    ]

    css = compile_layout_recipe_css(regions)
    context = layout_recipe_context(regions)

    assert len(context) == 3
    assert all(item["required_marker"] in css for item in context)
    assert "minmax(0, 1fr)" in css
    assert "border-block-start" in css
    assert "border-inline-start" in css
    assert "@media (max-width: 767px)" in css


def test_design_realization_adds_independent_primary_image_obligation() -> None:
    plan = _image_plan()
    policy = build_image_policy_snapshot(Settings(), plan=plan)
    contract = compile_design_realization(
        plan.experience_blueprint,
        route_id="home",
        section_order=["hero"],
        image_policy=policy,
    )

    assert [item.resource_slot_id for item in contract.image_obligations] == ["slot-hero"]
    assert all(item.policy_required for item in contract.image_obligations)


def test_image_evidence_separates_source_reference_from_browser_verification(
    tmp_path: Path,
) -> None:
    plan = _image_plan()
    repo = tmp_path / "repo"
    route_dir = repo / "src" / "routes" / "home"
    route_dir.mkdir(parents=True)
    (route_dir / "Home.tsx").write_text('<LocalImage resourceId="slot-hero" />\n', encoding="utf-8")
    run_root = tmp_path / "run"
    (run_root / "ledger").mkdir(parents=True)
    (run_root / "ledger" / "projections.json").write_text(
        json.dumps(
            {
                "generated/resource-assets.json": {
                    "image_assets": [
                        {
                            "resource_slot_id": "slot-hero",
                            "category": "editorial_photo",
                            "sources": [{"path": "resources/images/slot-hero.jpg"}],
                        },
                        {
                            "resource_slot_id": "slot-detail",
                            "category": "editorial_photo",
                            "sources": [{"path": "resources/images/slot-detail.jpg"}],
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    evidence = build_image_evidence(
        repo_dir=repo,
        run_root=run_root,
        plan=plan,
        runtime_evidence=[
            {
                "resource_slot_id": "slot-hero",
                "route_id": "home",
                "section_id": "hero",
                "decoded_in_browser": True,
                "visible_in_browser": True,
            }
        ],
    )
    by_slot = {item["resource_slot_id"]: item for item in evidence["entries"]}

    assert evidence["planned_count"] == 2
    assert evidence["referenced_count"] == 1
    assert evidence["decoded_count"] == 1
    assert evidence["visible_count"] == 1
    assert by_slot["slot-hero"]["browser_evidence_state"] == "verified"
    assert by_slot["slot-detail"]["browser_evidence_state"] == "not_run"
    assert by_slot["slot-detail"]["decoded_in_browser"] is None
    assert evidence["browser_evidence_complete"] is False


def test_failure_report_surfaces_actual_pipeline_issue() -> None:
    report = _generation_report(
        {
            "issues": [{"code": "SOURCE_REPAIR_EXHAUSTED", "message": "repair budget spent"}],
            "terminal_failure": {
                "terminal_code": "SOURCE_REPAIR_EXHAUSTED",
                "safe_user_summary": "repair budget spent",
            },
        }
    )

    assert "Primary failure: `SOURCE_REPAIR_EXHAUSTED`" in report
    assert "Recorded pipeline issues: `1`" in report
    assert "repair budget spent" in report
