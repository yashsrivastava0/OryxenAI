from __future__ import annotations

from oryxenai.agents.code_generator.core.development_schemas import (
    CandidateIdentity,
    InteractionContract,
    RoutePlan,
    SitePlan,
    VerificationProfile,
    WorkGraph,
)
from oryxenai.agents.code_generator.core.verification_plan import derive_verification_plan


def test_interaction_journeys_use_literal_markers_and_assert_external_links() -> None:
    identity = CandidateIdentity(
        input_receipt_hash="input",
        site_plan_hash="plan",
        work_graph_hash="graph",
        source_checkpoint_hash="checkpoint",
        source_manifest_hash="manifest",
        scaffold_toolchain_profile_hash="toolchain",
        verification_profile_hash="verification",
    )
    plan = SitePlan(
        plan_id="plan",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=[],
                responsive_outcome="desktop and mobile",
                reduced_motion_outcome="safe",
                interaction_outcome="keyboard safe",
            )
        ],
        work_graph=WorkGraph(units=[]),
        interactions=[
            InteractionContract(
                interaction_id="interaction:home:projects",
                route_id="home",
                trigger="click",
                outcome="scroll to projects",
                keyboard_behavior="Enter",
                reduced_motion_behavior="safe",
                target="#featured-projects",
                accessible_name="Projects",
            ),
            InteractionContract(
                interaction_id="interaction:home:linkedin",
                route_id="home",
                trigger="click",
                outcome="open approved profile",
                keyboard_behavior="Enter",
                reduced_motion_behavior="safe",
                target="",
                accessible_name="Connect on LinkedIn",
            ),
        ],
    )
    profile = VerificationProfile(profile_id="test")
    result = derive_verification_plan(
        identity=identity,
        plan=plan,
        projections={
            "site/contract.json": {
                "routes": [{"route_id": "home", "path": "/"}],
                "public_content": [],
                "public_content_manifest": {"nav": []},
            }
        },
        profile=profile,
    )

    journeys = {journey.journey_id: journey for journey in result.runtime_journeys}
    projects = journeys["interaction:interaction:home:projects"].steps[1]
    linkedin = journeys["interaction:interaction:home:linkedin"].steps[1]
    assert projects.action == "click"
    assert projects.target == '[data-interaction-id="interaction:home:projects"]'
    assert linkedin.action == "assert_link"
    assert linkedin.target == '[data-interaction-id="interaction:home:linkedin"]'


def test_default_runtime_profile_keeps_interactions_out_of_route_smoke() -> None:
    identity = CandidateIdentity(
        input_receipt_hash="input",
        site_plan_hash="plan",
        work_graph_hash="graph",
        source_checkpoint_hash="checkpoint",
        source_manifest_hash="manifest",
        scaffold_toolchain_profile_hash="toolchain",
        verification_profile_hash="verification",
    )
    plan = SitePlan(
        plan_id="plan",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=[],
                responsive_outcome="desktop and mobile",
                reduced_motion_outcome="safe",
                interaction_outcome="keyboard safe",
            )
        ],
        work_graph=WorkGraph(units=[]),
        interactions=[
            InteractionContract(
                interaction_id="interaction:home:projects",
                route_id="home",
                trigger="click",
                outcome="scroll to projects",
                keyboard_behavior="Enter",
                reduced_motion_behavior="safe",
            )
        ],
    )
    result = derive_verification_plan(
        identity=identity,
        plan=plan,
        projections={
            "site/contract.json": {
                "routes": [{"route_id": "home", "path": "/"}],
                "public_content": [],
                "public_content_manifest": {"nav": []},
            }
        },
        profile=VerificationProfile(
            profile_id="smoke",
            runtime_check_ids=["runtime.routes", "runtime.assets"],
        ),
    )
    assert all(not item.journey_id.startswith("interaction:") for item in result.runtime_journeys)
