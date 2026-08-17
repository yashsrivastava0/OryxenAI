"""Trusted derivation of the bounded text/DOM verification plan."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from oryxenai.agents.code_generator.core.development_schemas import (
    CandidateIdentity,
    SitePlan,
    VerificationJourney,
    VerificationPlan,
    VerificationProfile,
    VerificationStep,
)


def build_verification_profile(settings: Any) -> VerificationProfile:
    config = getattr(settings, "code_generator_verification", None)
    viewports = getattr(config, "viewport_profiles", None) if config is not None else None
    if not viewports:
        viewports = {
            "mobile": {"width": 390, "height": 844},
            "tablet": {"width": 768, "height": 1024},
            "desktop": {"width": 1440, "height": 900},
        }
    return VerificationProfile(
        profile_id=str(getattr(config, "profile_id", "code-generator-verification-v1")),
        source_check_ids=list(
            getattr(
                config, "source_check_ids", ["source.paths", "source.coverage", "source.policy"]
            )
        ),
        build_check_ids=list(
            getattr(
                config,
                "build_check_ids",
                ["build.install", "build.typecheck", "build.production", "build.closure"],
            )
        ),
        runtime_check_ids=list(
            getattr(
                config,
                "runtime_check_ids",
                [
                    "runtime.routes",
                    "runtime.navigation",
                    "runtime.assets",
                    "runtime.accessibility",
                ],
            )
        ),
        browser_name=str(getattr(config, "browser_name", "chromium")),
        browser_executable=str(getattr(config, "browser_executable", "") or ""),
        viewport_profiles={str(key): dict(value) for key, value in viewports.items()},
        build_command=[
            str(item) for item in getattr(config, "build_command", ["npm", "run", "build"])
        ],
        typecheck_command=[
            str(item) for item in getattr(config, "typecheck_command", ["npm", "run", "typecheck"])
        ],
    )


def derive_verification_plan(
    *,
    identity: CandidateIdentity,
    plan: SitePlan,
    projections: dict[str, dict[str, Any]],
    profile: VerificationProfile,
) -> VerificationPlan:
    site = projections.get("site/contract.json", {})
    routes = [item for item in site.get("routes", []) if isinstance(item, dict)]
    content_by_route = {
        str(item.get("route_id", "")): item
        for item in site.get("public_content", [])
        if isinstance(item, dict)
    }
    journeys: list[VerificationJourney] = []
    check_ids = [*profile.source_check_ids, *profile.build_check_ids, *profile.runtime_check_ids]
    for route in routes:
        route_id = str(route.get("route_id", ""))
        path = str(route.get("path", "/"))
        content = content_by_route.get(route_id, {})
        expected_ids = [
            str(section.get("section_id", ""))
            for section in content.get("sections", [])
            if isinstance(section, dict) and section.get("section_id")
        ]
        expected_text = _content_strings(content)
        journey_id = f"direct:{route_id}"
        journeys.append(
            VerificationJourney(
                journey_id=journey_id,
                route_id=route_id,
                start_path=path,
                viewport_profile=_viewport_for_route(plan, route_id),
                steps=[
                    VerificationStep(
                        step_id=f"{journey_id}:load",
                        action="load",
                        expected_url=path,
                        expected_content_ids=expected_ids,
                        expected_text=expected_text,
                    ),
                    VerificationStep(
                        step_id=f"{journey_id}:overflow",
                        action="assert_overflow",
                    ),
                    VerificationStep(
                        step_id=f"{journey_id}:main",
                        action="assert_accessible",
                        target="main",
                    ),
                ],
            )
        )
    nav = site.get("public_content_manifest", {}).get("nav", [])
    nav_steps: list[VerificationStep] = []
    for index, item in enumerate(nav if isinstance(nav, list) else []):
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("target", ""))
        target_route = next(
            (route for route in routes if str(route.get("route_id", "")) == target_id), None
        )
        if target_route is None:
            continue
        target_path = str(target_route.get("path", "/"))
        nav_steps.append(
            VerificationStep(
                step_id=f"navigation:{index}",
                action="navigate",
                target=f'[data-navigation-target="{target_id}"]',
                expected_url=target_path,
            )
        )
    if nav_steps:
        journeys.append(
            VerificationJourney(
                journey_id="navigation:all-edges",
                start_path=str(routes[0].get("path", "/")) if routes else "/",
                viewport_profile="desktop",
                steps=[
                    VerificationStep(step_id="navigation:start", action="load"),
                    *nav_steps,
                    VerificationStep(step_id="navigation:back", action="back"),
                    VerificationStep(step_id="navigation:forward", action="forward"),
                ],
            )
        )
    journeys.append(
        VerificationJourney(
            journey_id="unknown-route",
            start_path="/__oryxenai_unknown_route__",
            viewport_profile="desktop",
            steps=[
                VerificationStep(
                    step_id="unknown-route:load",
                    action="load",
                    expected_url="/__oryxenai_unknown_route__",
                    expected_text=["Page not found"],
                )
            ],
        )
    )
    # Interaction journeys remain available for an explicitly requested
    # interaction check, but are not generated by the default smoke profile.
    # This keeps Playwright focused on route/asset health instead of turning
    # every interaction into a separate browser session.
    if not profile.runtime_check_ids or "runtime.interactions" in profile.runtime_check_ids:
        interactions = plan.interactions
    else:
        interactions = []
    for interaction in interactions:
        interaction_data = (
            interaction.model_dump(mode="json")
            if hasattr(interaction, "model_dump")
            else interaction
        )
        if not isinstance(interaction_data, dict):
            continue
        interaction_id = str(interaction_data.get("interaction_id", ""))
        route_id = str(interaction_data.get("route_id", ""))
        route = next((item for item in routes if str(item.get("route_id", "")) == route_id), {})
        if not interaction_id or not route:
            continue
        trigger = str(interaction_data.get("trigger", "click")).casefold()
        planned_url = str(interaction_data.get("expected_url", ""))
        interaction_target = str(interaction_data.get("target", "")).strip()
        is_css_selector = bool(
            interaction_target
            and (
                interaction_target[0] in "[#."
                or re.fullmatch(r"[A-Za-z][A-Za-z0-9-]*", interaction_target)
            )
        )
        # A blank expected URL is common for approved external links because
        # the planner intentionally does not duplicate the trusted URL
        # ledger.  Prose/blank targets are still link interactions; assert
        # their local href and accessible name without navigating outbound.
        is_external_link = urlsplit(planned_url).scheme in {"http", "https"} or (
            not planned_url and not is_css_selector
        )
        action = (
            "assert_link"
            if is_external_link
            else "focus"
            if "focus" in trigger
            else "press"
            if "key" in trigger
            else "click"
        )
        selector = _interaction_selector(interaction_data, interaction_id)
        # Only same-app path expectations are enforceable in the offline
        # runtime: external destinations and "#anchor" scrolls cannot be
        # asserted as page.url paths.
        enforceable_url = planned_url if planned_url.startswith("/") else ""
        journey_id = f"interaction:{interaction_id}"
        journeys.append(
            VerificationJourney(
                journey_id=journey_id,
                route_id=route_id,
                start_path=str(route.get("path", "/")),
                viewport_profile=_viewport_for_route(plan, route_id),
                steps=[
                    VerificationStep(step_id=f"{journey_id}:load", action="load"),
                    VerificationStep(
                        step_id=f"{journey_id}:action",
                        action=action,  # type: ignore[arg-type]
                        target=selector,
                        expected_outcome=str(interaction_data.get("outcome", "")),
                        expected_url=enforceable_url,
                        expected_accessible_name=str(interaction_data.get("accessible_name", "")),
                    ),
                ],
            )
        )
    resources = projections.get("resources/ledger.json", {})
    expected_resources = [
        str(path)
        for receipt in resources.get("receipts", [])
        if isinstance(receipt, dict)
        for material in receipt.get("materialized_files", [])
        if isinstance(material, dict)
        for path in [material.get("local_path", "")]
        if path
    ]
    return VerificationPlan(
        based_on_candidate_identity=identity.identity_hash,
        source_checks=list(profile.source_check_ids),
        build_checks=list(profile.build_check_ids),
        runtime_journeys=journeys,
        expected_local_resources=sorted(set(expected_resources)),
        expected_check_ids=sorted(set(check_ids + [journey.journey_id for journey in journeys])),
    )


def _interaction_selector(interaction_data: dict[str, Any], interaction_id: str) -> str:
    """Anchor every interaction journey on its literal contract marker.

    ``target`` is planner prose, not an authority to select a different DOM
    node.  Using it for a journey can click a section wrapper (for example
    ``#featured-projects``) instead of the approved interactive anchor.
    """

    return f'[data-interaction-id="{interaction_id}"]'


def _content_strings(content: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for section in content.get("sections", []):
        if not isinstance(section, dict):
            continue
        for value in (
            section.get("content", {}).values() if isinstance(section.get("content"), dict) else []
        ):
            if isinstance(value, str) and value.strip():
                values.append(" ".join(value.split()))
    return values


def _viewport_for_route(plan: SitePlan, route_id: str) -> str:
    for route in plan.routes:
        if route.route_id == route_id:
            value = f"{route.responsive_outcome} {route.responsive_behavior}".casefold()
            if "mobile" in value or "narrow" in value:
                return "mobile"
    return "desktop"
