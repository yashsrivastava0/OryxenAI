from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from tests.unit.agents.code_generator.test_v4_contracts import _blueprint

from oryxenai.agents.code_generator.core.design_realization import compile_design_realization
from oryxenai.agents.code_generator.core.development_schemas import (
    ExecutionBindingV2,
    ImagePolicySnapshotV1,
    ResourcePlacementV4,
    RoutePlan,
    SitePlan,
)
from oryxenai.agents.code_generator.core.image_policy import (
    ImagePolicyError,
    build_image_policy_snapshot,
    required_image_placements,
)
from oryxenai.agents.code_generator.core.layout_recipe_catalogue import (
    compile_layout_recipe_css,
    layout_recipe_context,
)
from oryxenai.agents.code_generator.core.path_policy import semantic_segment
from oryxenai.agents.code_generator.core.portfolio_export import (
    _generation_report,
    build_image_evidence,
)
from oryxenai.core.settings import Settings


def _placement(slot_id: str, route_id: str = "home") -> ResourcePlacementV4:
    return ResourcePlacementV4(
        resource_slot_id=slot_id,
        route_id=route_id,
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
    assert policy.minimum_visible_images == 2
    assert policy.preferred_visible_images == 2
    assert policy.require_primary_route_image is True
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
    settings = Settings()
    settings.code_generator_development = settings.code_generator_development.model_copy(
        update={"minimum_visible_images": 1, "require_primary_route_image": True}
    )
    policy = build_image_policy_snapshot(settings, plan=plan)
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


def _single_slot_plan() -> SitePlan:
    """A brief with exactly one approved image slot (F01 regression fixture)."""

    blueprint = _blueprint().model_copy(update={"resource_placements": [_placement("slot-only")]})
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
            resource_slot_id="slot-only",
            route_id="home",
            category="editorial_photo",
            purpose="supporting image",
            resolution_type="deferred_materialized",
            local_paths=["resources/images/slot-only.jpg"],
        )
    ]
    return SitePlan(
        plan_id="single-slot-plan",
        routes=[route],
        experience_blueprint=blueprint,
        execution_bindings=bindings,
    )


def test_image_policy_clamps_infeasible_minimum_to_available_slot_count() -> None:
    """F01: one approved slot with a configured minimum above one is feasible."""

    plan = _single_slot_plan()
    settings = Settings()
    assert settings.code_generator_development.minimum_visible_images > 1

    policy = build_image_policy_snapshot(settings, plan=plan)

    assert policy.approved_image_slot_ids == ["slot-only"]
    assert policy.minimum_visible_images == 1
    assert policy.preferred_visible_images == 1
    # No valid planner response could satisfy an unclamped minimum here; the
    # clamped snapshot must be satisfiable by the actual approved scope.
    selected = required_image_placements(plan.experience_blueprint.resource_placements, policy)
    assert [item.resource_slot_id for item in selected] == ["slot-only"]


def test_required_image_placements_span_multiple_routes() -> None:
    """F02: a site-wide minimum spread across two routes selects both."""

    placements = [_placement("slot-home", "home"), _placement("slot-case", "case-study")]
    policy = ImagePolicySnapshotV1(
        minimum_visible_images=2,
        preferred_visible_images=2,
        require_primary_route_image=False,
        approved_image_slot_ids=["slot-home", "slot-case"],
        primary_route_id="home",
        text_only_exemption=False,
    )

    selected = required_image_placements(placements, policy)

    assert {item.resource_slot_id for item in selected} == {"slot-home", "slot-case"}
    assert {item.route_id for item in selected} == {"home", "case-study"}


def test_required_image_placements_does_not_invent_a_home_requirement() -> None:
    """F02: images only on a case-study route still satisfy a site-wide floor."""

    placements = [
        _placement("slot-case-1", "case-study"),
        _placement("slot-case-2", "case-study"),
    ]
    policy = ImagePolicySnapshotV1(
        minimum_visible_images=2,
        preferred_visible_images=2,
        require_primary_route_image=False,
        approved_image_slot_ids=["slot-case-1", "slot-case-2"],
        primary_route_id="home",
        text_only_exemption=False,
    )

    selected = required_image_placements(placements, policy)

    assert {item.route_id for item in selected} == {"case-study"}


def test_required_image_placements_counts_a_repeated_slot_once() -> None:
    """Referencing the same approved slot twice still counts once toward the floor."""

    placements = [
        _placement("slot-home", "home"),
        _placement("slot-home", "home"),
    ]
    policy = ImagePolicySnapshotV1(
        minimum_visible_images=1,
        preferred_visible_images=1,
        require_primary_route_image=False,
        approved_image_slot_ids=["slot-home"],
        primary_route_id="home",
        text_only_exemption=False,
    )

    selected = required_image_placements(placements, policy)

    assert len(selected) == 1


def test_required_image_placements_raises_when_site_minimum_is_infeasible() -> None:
    """An unclamped, infeasible policy is a contract failure, not an empty result."""

    placements = [_placement("slot-home", "home")]
    policy = ImagePolicySnapshotV1(
        minimum_visible_images=2,
        preferred_visible_images=2,
        require_primary_route_image=False,
        approved_image_slot_ids=["slot-home"],
        primary_route_id="home",
        text_only_exemption=False,
    )

    with pytest.raises(ImagePolicyError) as exc_info:
        required_image_placements(placements, policy)
    assert exc_info.value.code == "IMAGE_POLICY_SITE_PLACEMENT_MINIMUM_MISSING"


def test_design_realization_obligations_span_multiple_routes() -> None:
    """F02: design realization checks each route for its own required image."""

    base = _blueprint()
    case_study_shell = base.route_shells[0].model_copy(
        update={"route_id": "case-study", "storage_key": "case-study"}
    )
    case_study_region = base.section_regions[0].model_copy(
        update={
            "region_id": "region:case-study:hero",
            "route_id": "case-study",
            "owner_id": "owner:case-study:hero",
        }
    )
    case_study_move = base.distinctive_moves[0].model_copy(
        update={
            "move_id": "move:case-study-rail",
            "route_id": "case-study",
            "region_id": "region:case-study:hero",
        }
    )
    blueprint = base.model_copy(
        update={
            "route_shells": [*base.route_shells, case_study_shell],
            "section_regions": [*base.section_regions, case_study_region],
            "distinctive_moves": [*base.distinctive_moves, case_study_move],
            "resource_placements": [
                _placement("slot-home", "home"),
                _placement("slot-case", "case-study"),
            ],
        }
    )
    policy = ImagePolicySnapshotV1(
        minimum_visible_images=2,
        preferred_visible_images=2,
        require_primary_route_image=False,
        approved_image_slot_ids=["slot-home", "slot-case"],
        primary_route_id="home",
        text_only_exemption=False,
    )

    home_contract = compile_design_realization(
        blueprint, route_id="home", section_order=["hero"], image_policy=policy
    )
    case_study_contract = compile_design_realization(
        blueprint, route_id="case-study", section_order=["hero"], image_policy=policy
    )

    assert [item.resource_slot_id for item in home_contract.image_obligations] == ["slot-home"]
    assert [item.resource_slot_id for item in case_study_contract.image_obligations] == [
        "slot-case"
    ]


def test_final_source_validation_checks_each_required_route_independently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F02: a satisfied home image must not mask a missing case-study image."""

    import oryxenai.agents.code_generator.core.final_source_validation as fsv_module

    blueprint = _blueprint().model_copy(
        update={
            "resource_placements": [
                _placement("slot-home", "home"),
                _placement("slot-case", "case-study"),
            ]
        }
    )
    plan = SimpleNamespace(experience_blueprint=blueprint, acceptance_coverage=[], interactions=[])
    home_key = semantic_segment("home")
    case_key = semantic_segment("case-study")
    routes = [
        {"route_id": "home", "path": "/", "storage_key": "home", "section_sequence": ["hero"]},
        {
            "route_id": "case-study",
            "path": "/case-study",
            "storage_key": "case-study",
            "section_sequence": ["hero"],
        },
    ]
    projections = {
        "site/contract.json": {"routes": routes, "public_content": [], "facts": []},
        "design/visual-direction.json": {"global": {"must_preserve": []}},
        "execution/contract.json": {
            "slots": [
                {
                    "resource_slot_id": "slot-home",
                    "route_id": "home",
                    "category": "editorial_photo",
                },
                {
                    "resource_slot_id": "slot-case",
                    "route_id": "case-study",
                    "category": "editorial_photo",
                },
            ]
        },
        "generated/resource-assets.json": {
            "image_assets": [
                {
                    "resource_slot_id": "slot-home",
                    "category": "editorial_photo",
                    "sources": [{"path": "resources/images/slot-home.jpg"}],
                },
                {
                    "resource_slot_id": "slot-case",
                    "category": "editorial_photo",
                    "sources": [{"path": "resources/images/slot-case.jpg"}],
                },
            ]
        },
    }
    image_policy = ImagePolicySnapshotV1(
        minimum_visible_images=2,
        preferred_visible_images=2,
        require_primary_route_image=False,
        approved_image_slot_ids=["slot-home", "slot-case"],
        primary_route_id="home",
        text_only_exemption=False,
    )
    repo = tmp_path / "repo"
    (repo / "src" / "routes" / home_key).mkdir(parents=True)
    (repo / "src" / "routes" / case_key).mkdir(parents=True)
    (repo / "src" / "routes" / home_key / "index.tsx").write_text(
        '<LocalImage resourceId="slot-home" />\n', encoding="utf-8"
    )
    # case-study's route deliberately does NOT reference its approved slot.
    (repo / "src" / "routes" / case_key / "index.tsx").write_text(
        "<div>No image here.</div>\n", encoding="utf-8"
    )
    (repo / "src" / "generated").mkdir(parents=True)
    (repo / "src" / "generated" / "route-registry.ts").write_text(
        'export const ROUTES = {"home":"/","case-study":"/case-study"};\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(fsv_module, "validate_repository", lambda *args, **kwargs: [])
    monkeypatch.setattr(fsv_module, "audit_typescript_source", lambda *args, **kwargs: [])
    diagnostics = fsv_module.validate_final_source(
        repo,
        plan=plan,
        projections=projections,
        allowed_packages=set(),
        public_text=set(),
        image_policy=image_policy,
    )

    by_route = {item.route_id: item for item in diagnostics if item.symbol == "slot-case"}
    assert "case-study" in by_route
    assert by_route["case-study"].code == "SOURCE_ROUTE_IMAGE_MINIMUM_MISSING"
    assert not any(item.symbol == "slot-home" for item in diagnostics)
