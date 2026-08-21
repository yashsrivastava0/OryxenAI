from __future__ import annotations

from pathlib import Path

import pytest

from oryxenai.agents.code_generator.core.development_schemas import (
    CandidateIdentity,
    InteractionContract,
    RoutePlan,
    SitePlan,
    VerificationProfile,
    WorkGraph,
)
from oryxenai.agents.code_generator.core.runtime_verifier import (
    RuntimeVerifier,
    _browser_environment,
    _validate_interaction_state,
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


def test_every_route_is_checked_at_all_configured_viewports_with_geometry() -> None:
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
                section_ids=["hero"],
                responsive_outcome="desktop and mobile",
                reduced_motion_outcome="safe",
                interaction_outcome="keyboard safe",
            )
        ],
    )
    profile = VerificationProfile(
        profile_id="geometry",
        viewport_profiles={
            "mobile": {"width": 390, "height": 844},
            "tablet": {"width": 768, "height": 1024},
            "desktop": {"width": 1440, "height": 900},
        },
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
        profile=profile,
    )
    direct = [item for item in result.runtime_journeys if item.journey_id.startswith("direct:")]

    assert {item.viewport_profile for item in direct} == {"mobile", "tablet", "desktop"}
    assert all(any(step.action == "assert_geometry" for step in item.steps) for item in direct)
    reduced = next(
        item for item in result.runtime_journeys if item.journey_id == "reduced-motion:home"
    )
    assert reduced.motion_profile == "reduce"
    assert any(step.action == "assert_geometry" for step in reduced.steps)


def test_runtime_verifier_translates_nested_preview_urls_to_application_paths() -> None:
    base = "http://127.0.0.1:4174/preview/session-abcdefghijklmnop/"

    assert RuntimeVerifier._application_path(base, base) == "/"
    assert RuntimeVerifier._application_path(f"{base}projects", base) == "/projects"


def test_browser_environment_uses_isolated_writable_directories(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

    environment = _browser_environment()

    assert environment["HOME"] == str(tmp_path / "oryxenai-browser" / "home")
    assert all(
        Path(environment[key]).is_dir()
        for key in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR")
    )


def test_runtime_verifier_accepts_a_bidirectional_toggle_when_state_changes() -> None:
    _validate_interaction_state(
        {"expanded": "false"},
        {"expanded": "true"},
        "Expands or collapses the section navigation.",
    )


def test_runtime_verifier_rejects_a_bidirectional_toggle_that_does_not_change_state() -> None:
    with pytest.raises(AssertionError, match="did not change"):
        _validate_interaction_state(
            {"expanded": "false"},
            {"expanded": "false"},
            "Expands or collapses the section navigation.",
        )
