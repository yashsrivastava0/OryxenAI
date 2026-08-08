"""Unit tests for VisualDesignDirectorAgent's adaptive 1-3 call orchestration."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from oryxenai.agents.discovery.schemas import StructuredModelResult
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.agents.visual_design_director.agent import (
    VisualDesignDirectorAgent,
    VisualDesignDirectorModelOutputError,
)


class _FakeModelClient:
    """Returns a canned payload per operation, regardless of the prompt."""

    def __init__(self, payloads: dict[str, dict[str, Any]]) -> None:
        self._payloads = payloads
        self.calls: list[str] = []
        self.requests: list[dict[str, Any]] = []

    async def complete(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError

    async def generate_structured(
        self, *, operation: str, input_payload: dict[str, Any], **kwargs: Any
    ) -> StructuredModelResult:
        self.calls.append(operation)
        self.requests.append({"operation": operation, "input_payload": input_payload})
        return StructuredModelResult(
            parsed_output=self._payloads[operation],
            response_id=f"fake-{operation}",
            model="fake-model",
            usage={"prompt_tokens": 1, "completion_tokens": 1},
            finish_reason="stop",
            latency_ms=1.0,
        )


def _route(route_id: str, *, publication_status: str = "approved") -> dict[str, Any]:
    return {
        "route_id": route_id,
        "path": f"/{route_id}",
        "purpose": "p",
        "publication_status": publication_status,
    }


def _scene(scene_id: str, route_id: str) -> dict[str, Any]:
    return {
        "scene_id": scene_id,
        "route_id": route_id,
        "responsive_behavior": "stacks on mobile",
    }


def _page(route_id: str) -> dict[str, Any]:
    return {
        "route_id": route_id,
        "path": f"/{route_id}",
        "scenes": [_scene(f"{route_id}_scene", route_id)],
    }


def _language_payload(
    *,
    pages_included: bool,
    integration_needed: bool = False,
    route_ids: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "mode": "VISUAL_LANGUAGE_AND_PAGES" if pages_included else "VISUAL_LANGUAGE_ONLY",
        "pages_included": pages_included,
        "integration_needed": integration_needed,
        "visual_language": {"creative_thesis": "x"},
        "shared_visual_systems": {"card_treatment": "flat"},
    }
    if pages_included:
        payload["pages"] = [_page(route_id) for route_id in (route_ids or ["r0"])]
    return payload


def _pages_payload(route_ids: list[str], *, integration_needed: bool = False) -> dict[str, Any]:
    return {
        "mode": "PAGES_READY",
        "pages_included": True,
        "integration_needed": integration_needed,
        "pages": [_page(route_id) for route_id in route_ids],
    }


def _integrate_payload(route_ids: list[str]) -> dict[str, Any]:
    return {
        "mode": "INTEGRATED",
        "pages_included": True,
        "pages": [_page(route_id) for route_id in route_ids],
        "compiler_handoff": {"shared_systems": "typography"},
    }


def _context(
    route_count: int,
    *,
    route_plan: list[dict[str, Any]] | None = None,
    **agent_input_overrides: Any,
) -> Any:
    resolved_route_plan = (
        route_plan if route_plan is not None else [_route(f"r{i}") for i in range(route_count)]
    )
    agent_input: dict[str, Any] = {
        "operation": "build",
        "intake": {
            "content_architect_content_hash": "hash1",
            "content_architect_session_revision": 1,
            "presentation_mode": "single_page" if route_count == 1 else "multi_page",
            "route_plan": resolved_route_plan,
        },
        "preferences": {},
        "prior_output": {},
        "revision_request": "",
    }
    agent_input.update(agent_input_overrides)
    return build_context(
        portfolio_session_id=uuid4(),
        agent_key=AgentKey.VISUAL_DESIGN_DIRECTOR,
        current_state={},
        agent_input=agent_input,
    )


async def test_single_page_stops_after_one_call():
    client = _FakeModelClient({"establish_visual_language": _language_payload(pages_included=True)})
    agent = VisualDesignDirectorAgent(model_client=client)

    result = await agent.run(_context(route_count=1))

    assert client.calls == ["establish_visual_language"]
    assert result.output["stages_run"] == ["establish_visual_language"]
    assert result.output["pages"]


async def test_hybrid_calls_direct_page_experience_when_pages_deferred():
    route_ids = ["r0", "r1"]
    client = _FakeModelClient(
        {
            "establish_visual_language": _language_payload(pages_included=False),
            "direct_page_experience": _pages_payload(route_ids),
        }
    )
    agent = VisualDesignDirectorAgent(model_client=client)

    result = await agent.run(_context(route_count=2))

    assert client.calls == ["establish_visual_language", "direct_page_experience"]
    assert result.output["stages_run"] == [
        "establish_visual_language",
        "direct_page_experience",
    ]
    assert len(result.output["pages"]) == 2


async def test_integration_pass_runs_when_route_count_exceeds_threshold():
    route_ids = ["r0", "r1", "r2"]
    client = _FakeModelClient(
        {
            "establish_visual_language": _language_payload(pages_included=False),
            "direct_page_experience": _pages_payload(route_ids),
            "integrate_site_experience": _integrate_payload(route_ids),
        }
    )
    agent = VisualDesignDirectorAgent(model_client=client)

    result = await agent.run(_context(route_count=3))

    assert client.calls == [
        "establish_visual_language",
        "direct_page_experience",
        "integrate_site_experience",
    ]
    assert result.output["stages_run"] == [
        "establish_visual_language",
        "direct_page_experience",
        "integrate_site_experience",
    ]
    assert result.output["compiler_handoff"]["shared_systems"] == "typography"


async def test_integration_pass_runs_when_explicitly_flagged_at_two_routes():
    route_ids = ["r0", "r1"]
    client = _FakeModelClient(
        {
            "establish_visual_language": _language_payload(
                pages_included=True, integration_needed=True, route_ids=route_ids
            ),
            "integrate_site_experience": _integrate_payload(route_ids),
        }
    )
    agent = VisualDesignDirectorAgent(model_client=client)

    await agent.run(_context(route_count=2))

    assert client.calls == ["establish_visual_language", "integrate_site_experience"]


async def test_single_route_never_triggers_integration_even_if_flagged():
    """Regression guard for the explicit len(route_plan) > 1 integration guard
    in agent.py — nothing to reconcile against with a single route, even if a
    stage mistakenly sets integration_needed=True."""
    client = _FakeModelClient(
        {
            "establish_visual_language": _language_payload(
                pages_included=True, integration_needed=True, route_ids=["r0"]
            )
        }
    )
    agent = VisualDesignDirectorAgent(model_client=client)

    await agent.run(_context(route_count=1))

    assert client.calls == ["establish_visual_language"]


async def test_invalid_model_output_raises_visual_design_director_error():
    client = _FakeModelClient({"establish_visual_language": {"mode": "PAGES_READY"}})
    agent = VisualDesignDirectorAgent(model_client=client)

    with pytest.raises(VisualDesignDirectorModelOutputError):
        await agent.run(_context(route_count=1))


async def test_blocked_route_referenced_in_pages_is_rejected():
    """A blocked Content Architect route must never surface in visual output
    (hard reject) — direct mirror of Content Architect's own blocked-content
    backstop, applied one stage down the pipeline."""
    payload = _language_payload(pages_included=True, route_ids=["r0"])
    client = _FakeModelClient({"establish_visual_language": payload})
    agent = VisualDesignDirectorAgent(model_client=client)

    context = _context(route_count=1, route_plan=[_route("r0", publication_status="blocked")])

    with pytest.raises(VisualDesignDirectorModelOutputError):
        await agent.run(context)


async def test_pages_truncated_to_configured_max():
    """A page count longer than max_pages is truncated, never rejected —
    mirrors ContentArchitectAgent's own route_plan truncation precedent.

    agent._config is the process-wide cached settings singleton (shared
    across every VisualDesignDirectorAgent instance in this test session),
    so mutating it here must be restored — otherwise this leaks into every
    later test in the file.
    """
    route_ids = ["r0", "r1"]
    client = _FakeModelClient(
        {"establish_visual_language": _language_payload(pages_included=True, route_ids=route_ids)}
    )
    agent = VisualDesignDirectorAgent(model_client=client)
    original_max_pages = agent._config.max_pages
    agent._config.max_pages = 1
    try:
        result = await agent.run(_context(route_count=2))
    finally:
        agent._config.max_pages = original_max_pages

    assert client.calls == ["establish_visual_language"]
    assert len(result.output["pages"]) == 1


async def test_resource_catalogue_shortlist_identical_across_stages():
    """The shortlist is computed once before stage 1 and reused unchanged —
    a resource_id picked in an earlier stage must stay valid for a later
    stage's validator."""
    route_ids = ["r0", "r1", "r2"]
    client = _FakeModelClient(
        {
            "establish_visual_language": _language_payload(pages_included=False),
            "direct_page_experience": _pages_payload(route_ids),
            "integrate_site_experience": _integrate_payload(route_ids),
        }
    )
    agent = VisualDesignDirectorAgent(model_client=client)

    await agent.run(_context(route_count=3))

    shortlists = [
        request["input_payload"]["resource_catalogue_shortlist"] for request in client.requests
    ]
    assert shortlists[0] == shortlists[1] == shortlists[2]
    assert shortlists[0]


async def test_revision_forwards_prior_output_and_revision_request():
    client = _FakeModelClient({"establish_visual_language": _language_payload(pages_included=True)})
    agent = VisualDesignDirectorAgent(model_client=client)

    await agent.run(
        _context(
            route_count=1,
            prior_output={"visual_language": {"creative_thesis": "old"}},
            revision_request="Use a lighter palette",
        )
    )

    sent = client.requests[0]["input_payload"]
    assert sent["revision_request"] == "Use a lighter palette"
    assert sent["prior_output"]["visual_language"]["creative_thesis"] == "old"


async def test_pending_route_page_is_stamped_not_compilable():
    """A page for a pending route keeps full scene content but is
    deterministically marked not compilable — never trusting the model's
    own narrative claims about deferral/compilability (the bug a live
    review caught: the model can produce full page content while its own
    prose still claims the route was deferred)."""
    client = _FakeModelClient(
        {"establish_visual_language": _language_payload(pages_included=True, route_ids=["r0"])}
    )
    agent = VisualDesignDirectorAgent(model_client=client)

    result = await agent.run(
        _context(route_count=1, route_plan=[_route("r0", publication_status="pending")])
    )

    page = result.output["pages"][0]
    assert page["publication_status"] == "pending"
    assert page["compilable"] is False
    assert result.output["compiler_handoff"]["pages_compilable"] == {"r0": False}


async def test_approved_route_page_is_stamped_compilable():
    client = _FakeModelClient(
        {"establish_visual_language": _language_payload(pages_included=True, route_ids=["r0"])}
    )
    agent = VisualDesignDirectorAgent(model_client=client)

    result = await agent.run(
        _context(route_count=1, route_plan=[_route("r0", publication_status="approved")])
    )

    page = result.output["pages"][0]
    assert page["publication_status"] == "approved"
    assert page["compilable"] is True
    assert result.output["compiler_handoff"]["pages_compilable"] == {"r0": True}


async def test_mixed_publication_status_stamped_independently_per_page():
    route_ids = ["r0", "r1", "r2"]
    client = _FakeModelClient(
        {
            "establish_visual_language": _language_payload(pages_included=False),
            "direct_page_experience": _pages_payload(route_ids),
            "integrate_site_experience": _integrate_payload(route_ids),
        }
    )
    agent = VisualDesignDirectorAgent(model_client=client)

    result = await agent.run(
        _context(
            route_count=3,
            route_plan=[
                _route("r0", publication_status="approved"),
                _route("r1", publication_status="pending"),
                _route("r2", publication_status="approved"),
            ],
        )
    )

    compilable_by_route = {page["route_id"]: page["compilable"] for page in result.output["pages"]}
    assert compilable_by_route == {"r0": True, "r1": False, "r2": True}


async def test_meta_operation_reflects_final_stage_not_stage_one():
    """Regression guard for the exact bug a live review caught: meta.operation
    must never stay stuck on stage 1's operation once a later stage actually
    ran — agent.py owns this deterministically rather than trusting whatever
    the model wrote into meta."""
    route_ids = ["r0", "r1"]
    client = _FakeModelClient(
        {
            "establish_visual_language": _language_payload(pages_included=False),
            "direct_page_experience": _pages_payload(route_ids),
        }
    )
    agent = VisualDesignDirectorAgent(model_client=client, profile_name="visual_design_director")

    result = await agent.run(_context(route_count=2))

    assert result.output["meta"]["final_operation"] == "direct_page_experience"
    assert result.output["meta"]["stages_run"] == [
        "establish_visual_language",
        "direct_page_experience",
    ]
    assert result.output["meta"]["model_profile"] == "visual_design_director"
    assert result.output["meta"]["prompt_version"] == result.prompt_version


async def test_stage_two_user_summary_supersedes_stale_deferral_claim():
    """The exact scenario a live review caught: stage 1 correctly says pages
    are deferred; stage 2 then actually produces them. The final
    user_summary must describe what was actually produced, not repeat
    stage 1's now-stale deferral claim."""
    route_ids = ["r0"]
    stage_one_payload = _language_payload(pages_included=False)
    stage_one_payload["user_summary"] = "Route direction is deferred; not yet produced."
    stage_two_payload = _pages_payload(route_ids)
    stage_two_payload["user_summary"] = "The home page direction is complete and ready for review."
    client = _FakeModelClient(
        {
            "establish_visual_language": stage_one_payload,
            "direct_page_experience": stage_two_payload,
        }
    )
    agent = VisualDesignDirectorAgent(model_client=client)

    result = await agent.run(_context(route_count=1))

    assert (
        result.output["user_summary"] == "The home page direction is complete and ready for review."
    )


async def test_resource_candidates_stamped_with_catalogue_provenance():
    payload = _language_payload(pages_included=True, route_ids=["r0"])
    payload["resource_candidates"] = [
        {"resource_id": "hero_asymmetric_text_dominant", "why_it_matches": "text-led hero"}
    ]
    client = _FakeModelClient({"establish_visual_language": payload})
    agent = VisualDesignDirectorAgent(model_client=client)

    result = await agent.run(_context(route_count=1))

    candidate = result.output["resource_candidates"][0]
    assert candidate["resource_id"] == "hero_asymmetric_text_dominant"
    assert candidate["category"] == "hero_pattern"
    assert candidate["lookup_status"] == "verified"
    assert candidate["resource_library_version"]
