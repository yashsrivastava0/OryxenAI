from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.development_planner import (
    SitePlanValidationError,
    validate_site_plan,
)
from oryxenai.agents.code_generator.development_schemas import SitePlan, WorkUnit


def _projections() -> dict[str, dict[str, object]]:
    return {
        "site/contract.json": {
            "routes": [{"route_id": "home", "path": "/"}],
            "public_content": [{"route_id": "home", "sections": [{"section_id": "hero"}]}],
            "criteria": [{"criterion_id": "criterion:home:0", "route_id": "home"}],
        }
    }


def _plan() -> SitePlan:
    return SitePlan.model_validate(
        {
            "plan_id": "plan-home",
            "routes": [
                {
                    "route_id": "home",
                    "path": "/",
                    "section_ids": ["hero"],
                    "responsive_outcome": "stacked mobile layout",
                    "reduced_motion_outcome": "static equivalent",
                    "interaction_outcome": "keyboard accessible nav",
                    "composition": {
                        "hierarchy": "headline before evidence",
                        "layout_strategy": "text-led asymmetry",
                        "visual_anchor": "evidence panel",
                        "evidence_treatment": "inline proof",
                        "section_transitions": "measured spacing",
                    },
                    "responsive_behavior": {
                        "mobile_strategy": "stack content",
                        "breakpoint_strategy": "collapse at a readable measure",
                        "overflow_strategy": "wrap controls",
                        "touch_target_strategy": "large targets",
                    },
                }
            ],
            "creative_thesis": {
                "thesis": "evidence-first engineering",
                "distinction": "text-led proof rather than dashboard cards",
                "narrative_arc": "positioning to evidence",
                "visual_tension": "quiet type with precise accents",
            },
            "visual_system": {
                "typography": "confident display and readable body",
                "color_strategy": "one accent for evidence",
                "spacing_rhythm": "generous editorial pacing",
                "surface_treatment": "flat borders",
                "density_strategy": "calm information density",
                "motion_vocabulary": "subtle, optional reveal",
            },
            "shell": {
                "navigation": "single anchor navigation",
                "main_landmark": "one main landmark per route",
                "footer_strategy": "quiet closing contact",
                "focus_treatment": "visible focus outline",
                "route_transition": "none required",
            },
            "shared_component_contracts": [
                {
                    "component_id": "evidence-panel",
                    "purpose": "frame approved evidence",
                    "visual_role": "quiet contrast surface",
                    "expected_exports": ["EvidencePanel"],
                    "accessibility_contract": "semantic content container",
                }
            ],
            "interactions": [
                {
                    "interaction_id": "nav-focus",
                    "route_id": "home",
                    "trigger": "keyboard focus",
                    "outcome": "visible navigation focus",
                    "keyboard_behavior": "native anchor behavior",
                    "reduced_motion_behavior": "no motion needed",
                }
            ],
            "acceptance_coverage": [
                {
                    "criterion_id": "criterion:home:0",
                    "route_id": "home",
                    "expected_outcome": "evidence-first hierarchy is visible",
                    "source_marker": "data-criterion-id",
                }
            ],
            "work_graph": {
                "units": [
                    {
                        "unit_id": "foundation",
                        "kind": "foundation",
                        "owns_paths": ["src/tokens.ts"],
                    },
                    {
                        "unit_id": "route-home",
                        "kind": "route",
                        "route_id": "home",
                        "section_ids": ["hero"],
                        "owns_paths": ["src/routes/home.tsx"],
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


def test_site_plan_accepts_exact_contract_coverage() -> None:
    assert validate_site_plan(_plan(), _projections()).plan_id == "plan-home"


def test_site_plan_rejects_overlapping_future_file_ownership() -> None:
    plan = _plan()
    duplicate = plan.model_copy(deep=True)
    duplicate.work_graph.units[1].owns_paths = ["src/tokens.ts"]
    with pytest.raises(SitePlanValidationError, match="disjoint"):
        validate_site_plan(duplicate, _projections())


def test_site_plan_rejects_route_path_drift() -> None:
    plan = _plan()
    plan.routes[0].path = "/different"
    with pytest.raises(SitePlanValidationError, match="invalid or mismatched"):
        validate_site_plan(plan, _projections())


def test_site_plan_rejects_route_coverage_drift() -> None:
    plan = _plan()
    plan.routes = []
    with pytest.raises(SitePlanValidationError, match="exact admitted route"):
        validate_site_plan(plan, _projections())


def test_site_plan_rejects_section_coverage_drift() -> None:
    plan = _plan()
    plan.routes[0].section_ids = []
    with pytest.raises(SitePlanValidationError, match="exact admitted sections"):
        validate_site_plan(plan, _projections())


def test_site_plan_rejects_missing_experience_outcome() -> None:
    plan = _plan()
    plan.routes[0].responsive_outcome = ""
    with pytest.raises(SitePlanValidationError, match="explicit"):
        validate_site_plan(plan, _projections())


def test_site_plan_rejects_missing_route_work_unit() -> None:
    plan = _plan()
    plan.work_graph.units = [unit for unit in plan.work_graph.units if unit.kind != "route"]
    plan.work_graph.units[-1].depends_on = ["foundation"]
    with pytest.raises(SitePlanValidationError, match="exactly one route work"):
        validate_site_plan(plan, _projections())


def test_site_plan_rejects_work_graph_cycle() -> None:
    plan = _plan()
    plan.work_graph.units[0].depends_on = ["integrate"]
    with pytest.raises(SitePlanValidationError, match="acyclic"):
        validate_site_plan(plan, _projections())


def test_site_plan_accepts_split_route_batches_with_composition() -> None:
    plan = _plan()
    plan.routes[0].section_ids = ["hero", "project"]
    projections = _projections()
    projections["site/contract.json"]["public_content"][0]["sections"].append(
        {"section_id": "project"}
    )
    plan.work_graph.units = [
        WorkUnit.model_validate({"unit_id": "foundation", "kind": "foundation"}),
        WorkUnit.model_validate(
            {
                "kind": "route_batch",
                "route_id": "home",
                "section_ids": ["hero"],
                "unit_id": "route-home-hero",
                "depends_on": ["foundation"],
            }
        ),
        WorkUnit.model_validate(
            {
                "kind": "route_batch",
                "route_id": "home",
                "section_ids": ["project"],
                "unit_id": "route-home-project",
                "depends_on": ["foundation"],
            }
        ),
        WorkUnit.model_validate(
            {
                "unit_id": "compose-home",
                "kind": "route_compose",
                "route_id": "home",
                "depends_on": ["route-home-hero", "route-home-project"],
            }
        ),
        WorkUnit.model_validate(
            {
                "unit_id": "integrate",
                "kind": "integration",
                "depends_on": [
                    "foundation",
                    "route-home-hero",
                    "route-home-project",
                    "compose-home",
                ],
                "terminal": True,
            }
        ),
    ]
    assert validate_site_plan(plan, projections).plan_id == "plan-home"
