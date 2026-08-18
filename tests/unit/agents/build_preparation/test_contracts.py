from __future__ import annotations

import pytest

from oryxenai.agents.build_preparation.agent import _normalize_selection_ids
from oryxenai.agents.build_preparation.contracts import (
    PACK_VERSION,
    PackContractError,
    compile_v2_projections,
)
from oryxenai.agents.build_preparation.execution import compile_execution_contract
from oryxenai.agents.build_preparation.schemas import (
    FetchedResource,
    ResourceNeed,
    ResourceQuery,
    ResourceSelection,
    RouteScope,
    Stage1QueryPlan,
    Stage2SelectionPlan,
)
from oryxenai.agents.build_preparation.validators import (
    BuildPreparationValidationError,
    validate_query_plan,
    validate_selection_plan,
)


def test_query_plan_must_cover_every_stage0_need() -> None:
    with pytest.raises(BuildPreparationValidationError, match="every Stage 0 need"):
        validate_query_plan(Stage1QueryPlan(), {"need-1"})


def test_selection_plan_is_closed_over_candidates_and_needs() -> None:
    query_plan = Stage1QueryPlan(
        queries=[ResourceQuery(need_id="need-1", kind="custom", fallback="Build it locally.")]
    )
    assert query_plan.queries[0].need_id == "need-1"
    with pytest.raises(BuildPreparationValidationError, match="every Stage 0 need"):
        validate_selection_plan(Stage2SelectionPlan(), {"need-1"}, [])

    plan = Stage2SelectionPlan(
        selections=[ResourceSelection(need_id="need-1", fallback="Build it locally.")]
    )
    assert validate_selection_plan(plan, {"need-1"}, []) == plan


def test_selection_alternates_must_be_returned_and_distinct_from_primary() -> None:
    candidates = [
        FetchedResource(
            resource_id="candidate-1",
            need_id="need-1",
            kind="component",
            provider="shadcn",
            provider_asset_id="accordion",
            title="Accordion",
            license="MIT",
            license_reference="https://example.test/license",
        )
    ]
    with pytest.raises(BuildPreparationValidationError, match="alternate resource"):
        validate_selection_plan(
            Stage2SelectionPlan(
                selections=[
                    ResourceSelection(
                        need_id="need-1",
                        selected_resource_id="candidate-1",
                        alternate_resource_ids=["candidate-2"],
                    )
                ]
            ),
            {"need-1"},
            candidates,
        )

    with pytest.raises(BuildPreparationValidationError, match="own alternate"):
        validate_selection_plan(
            Stage2SelectionPlan(
                selections=[
                    ResourceSelection(
                        need_id="need-1",
                        selected_resource_id="candidate-1",
                        alternate_resource_ids=["candidate-1"],
                    )
                ]
            ),
            {"need-1"},
            candidates,
        )


def test_model_selection_ids_are_discarded_when_not_in_provider_closed_set() -> None:
    plan, warnings = _normalize_selection_ids(
        Stage2SelectionPlan(
            selections=[
                ResourceSelection(
                    need_id="need-1",
                    selected_resource_id="invented-resource",
                    alternate_resource_ids=["also-invented", "candidate-1"],
                )
            ]
        ),
        [
            FetchedResource(
                resource_id="candidate-1",
                need_id="need-1",
                kind="component",
                provider="shadcn",
            )
        ],
        [ResourceNeed(need_id="need-1", kind="resource", source_id="component")],
    )

    selection = plan.selections[0]
    assert selection.selected_resource_id is None
    assert selection.alternate_resource_ids == ["candidate-1"]
    assert selection.fallback
    assert any("invented-resource" in warning for warning in warnings)


def test_required_visual_without_real_material_is_an_execution_gap() -> None:
    need = ResourceNeed(
        need_id="need-image",
        kind="asset",
        source_id="editorial-image-1",
        category="editorial_photo",
        route_ids=["home"],
        required_for_handoff=True,
    )
    contract, recipes, slots, gaps = compile_execution_contract(
        routes=[RouteScope(route_id="home", path="/")],
        needs=[need],
        materialized_resources=[],
        site={"routes": [{"route_id": "home", "section_sequence": []}]},
        visual={},
        target={"allowed_dependencies": []},
    )
    gap_slot_ids = {gap.slot_id for gap in gaps}
    assert all(recipe.slot_id not in gap_slot_ids for recipe in recipes)
    assert len(gaps) == 1
    assert any(
        slot.resource_slot_id in gap_slot_ids and slot.resolution.resolution_type == "execution_gap"
        for slot in slots
    )
    assert contract["execution_gaps"][0]["code"] == "VDD_EXECUTION_GAP"


def test_component_target_is_advisory_and_never_creates_quota_gaps() -> None:
    contract, recipes, slots, gaps = compile_execution_contract(
        routes=[RouteScope(route_id="home", path="/")],
        needs=[],
        materialized_resources=[],
        site={"routes": [{"route_id": "home", "section_sequence": []}]},
        visual={"global": {"resource_policy": {"component_target_count": 4}}},
        target={"allowed_dependencies": []},
    )

    assert recipes
    assert slots
    assert gaps == []
    assert contract["execution_gaps"] == []


def _approved_content() -> dict[str, object]:
    return {
        "approved": {"content_hash": "content-hash"},
        "route_plan": [
            {
                "route_id": "home",
                "path": "/",
                "publication_status": "approved",
                "section_sequence": ["hero"],
            }
        ],
        "page_content_packs": [
            {
                "route_id": "home",
                "sections": [
                    {
                        "section_id": "hero",
                        "claim_ids": ["fact-1"],
                        "content": {"headline": "Evidence"},
                    }
                ],
            }
        ],
        "claim_grounding": [
            {
                "claim_id": "fact-1",
                "statement": "A grounded fact.",
                "source_reference": "fixture",
                "evidence_status": "verified",
            }
        ],
        "visual_director_handoff": {"offline": True},
        "site_story_strategy": {"composition": "adaptable"},
    }


def _approved_visual() -> dict[str, object]:
    return {
        "approved": {"visual_direction_hash": "visual-hash"},
        "pages": [
            {
                "route_id": "home",
                "path": "/",
                "publication_status": "approved",
                "compilable": True,
                "acceptance_criteria": ["Keep the evidence hierarchy."],
            }
        ],
    }


def test_pack_v2_compiles_authoritative_route_content_and_visual_direction() -> None:
    projections = compile_v2_projections(
        content_architect=_approved_content(),
        visual_design_director=_approved_visual(),
        source_ref={"input_projection_hash": "projection-hash"},
        target_contract={"target_id": "react-vite-v1"},
        max_routes=12,
    )
    assert projections["site"]["pack_version"] == PACK_VERSION
    assert projections["site"]["routes"][0]["files"]["content"].startswith("routes/home-")
    assert projections["visual"]["routes"][0]["route_id"] == "home"
    assert projections["site"]["runtime_requirements"][0]["runtime_id"]
    assert projections["site"]["freedoms"][0]["freedom_id"]


def test_pack_v2_rejects_missing_compilable_visual_route() -> None:
    with pytest.raises(PackContractError, match="must match exactly"):
        compile_v2_projections(
            content_architect=_approved_content(),
            visual_design_director={
                "approved": {"visual_direction_hash": "visual-hash"},
                "pages": [],
            },
            source_ref={"input_projection_hash": "projection-hash"},
            target_contract={"target_id": "react-vite-v1"},
            max_routes=12,
        )


def test_pack_v2_rejects_all_pending_routes_with_status_details() -> None:
    content = _approved_content()
    content["route_plan"] = [
        {"route_id": "home", "path": "/", "publication_status": "pending"},
        {"route_id": "about", "path": "/about", "publication_status": "blocked"},
    ]
    with pytest.raises(PackContractError, match="No approved public") as exc_info:
        compile_v2_projections(
            content_architect=content,
            visual_design_director=_approved_visual(),
            source_ref={"input_projection_hash": "projection-hash"},
            target_contract={"target_id": "react-vite-v1"},
            max_routes=12,
        )
    assert exc_info.value.code == "BUILD_PACK_V2_CONTENT_ROUTES_NONE_APPROVED"
    assert exc_info.value.details["route_count"] == 2
    assert exc_info.value.details["route_statuses"] == {
        "home": "pending",
        "about": "blocked",
    }


def test_pack_v2_rejects_empty_route_plan() -> None:
    content = _approved_content()
    content["route_plan"] = []
    with pytest.raises(
        PackContractError, match="Approved Content Architect routes are required"
    ) as exc_info:
        compile_v2_projections(
            content_architect=content,
            visual_design_director=_approved_visual(),
            source_ref={"input_projection_hash": "projection-hash"},
            target_contract={"target_id": "react-vite-v1"},
            max_routes=12,
        )
    assert exc_info.value.code == "BUILD_PACK_V2_CONTENT_ROUTES_EMPTY"


def test_pack_v2_accepts_approved_subset_when_pending_ca_drafts_are_absent_from_vdd() -> None:
    """Pending CA routes stay in review; they never become public VDD pages."""
    content = _approved_content()
    content["route_plan"].append(
        {
            "route_id": "case-study-draft",
            "path": "/case-study-draft",
            "publication_status": "pending",
            "section_sequence": ["summary"],
        }
    )
    content["page_content_packs"].append(
        {
            "route_id": "case-study-draft",
            "sections": [
                {
                    "section_id": "summary",
                    "claim_ids": [],
                    "content": {"headline": "Awaiting permission"},
                }
            ],
        }
    )
    content["claim_grounding"].append(
        {
            "claim_id": "draft-fact",
            "statement": "A restricted implementation detail.",
            "source_reference": "private review",
            "evidence_status": "verified",
            "publication_status": "pending",
        }
    )

    projections = compile_v2_projections(
        content_architect=content,
        visual_design_director=_approved_visual(),
        source_ref={"input_projection_hash": "projection-hash"},
        target_contract={"target_id": "react-vite-v1"},
        max_routes=12,
    )

    assert [route["route_id"] for route in projections["site"]["routes"]] == ["home"]
    assert [route["route_id"] for route in projections["visual"]["routes"]] == ["home"]
    assert [fact["fact_id"] for fact in projections["site"]["facts"]] == ["fact-1"]


def test_pack_v2_rejects_pending_ca_draft_reintroduced_by_visual_direction() -> None:
    content = _approved_content()
    content["route_plan"].append(
        {
            "route_id": "case-study-draft",
            "path": "/case-study-draft",
            "publication_status": "pending",
        }
    )
    visual = _approved_visual()
    visual["pages"].append(
        {
            "route_id": "case-study-draft",
            "path": "/case-study-draft",
            "publication_status": "approved",
            "compilable": True,
        }
    )

    with pytest.raises(PackContractError) as exc_info:
        compile_v2_projections(
            content_architect=content,
            visual_design_director=visual,
            source_ref={"input_projection_hash": "projection-hash"},
            target_contract={"target_id": "react-vite-v1"},
            max_routes=12,
        )

    assert exc_info.value.code == "BUILD_PACK_V2_VDD_ROUTE_UNKNOWN"
