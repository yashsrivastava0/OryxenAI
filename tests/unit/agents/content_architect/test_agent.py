"""Unit tests for ContentArchitectAgent's adaptive 1-3 call orchestration."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from oryxenai.agents.content_architect.agent import (
    ContentArchitectAgent,
    ContentArchitectModelOutputError,
    _approval_readiness_errors,
)
from oryxenai.agents.discovery.schemas import StructuredModelResult
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey


class _FakeModelClient:
    """Returns a canned payload per operation, regardless of the prompt."""

    def __init__(self, payloads: dict[str, dict[str, Any]]) -> None:
        self._payloads = payloads
        self.calls: list[str] = []
        self.packets: list[dict[str, Any]] = []

    async def complete(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError

    async def generate_structured(self, *, operation: str, **kwargs: Any) -> StructuredModelResult:
        self.calls.append(operation)
        self.packets.append(kwargs["input_payload"])
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
        "title": f"Route {route_id}",
        "purpose": "p",
        "section_sequence": ["hero"],
        "publication_status": publication_status,
    }


def _pack(route_id: str, *, claim_ids: list[str] | None = None) -> dict[str, Any]:
    return {
        "route_id": route_id,
        "sections": [
            {
                "section_id": "hero",
                "purpose": "p",
                "content": {"text": "x"},
                "claim_ids": claim_ids or [],
            }
        ],
        "internal_notes": {},
    }


def _plan_payload(
    *, content_included: bool, route_count: int = 1, integration_needed: bool = False
) -> dict[str, Any]:
    routes = [_route(f"r{i}") for i in range(route_count)]
    payload: dict[str, Any] = {
        "mode": "STRATEGY_AND_CONTENT" if content_included else "STRATEGY_ONLY",
        "content_included": content_included,
        "integration_needed": integration_needed,
        "site_story_strategy": {"positioning": "x"},
        "route_plan": routes,
        "claim_grounding": [],
    }
    if content_included:
        payload["page_content_packs"] = [_pack(r["route_id"]) for r in routes]
        payload["public_content_manifest"] = {"nav": []}
    return payload


def _pages_payload(route_count: int, *, integration_needed: bool = False) -> dict[str, Any]:
    return {
        "mode": "PAGES_READY",
        "content_included": False,
        "integration_needed": integration_needed,
        "page_content_packs": [_pack(f"r{i}") for i in range(route_count)],
        "public_content_manifest": {"nav": []},
    }


def _integrate_payload(route_count: int) -> dict[str, Any]:
    return {
        "mode": "INTEGRATED",
        "content_included": False,
        "page_content_packs": [_pack(f"r{i}") for i in range(route_count)],
        "public_content_manifest": {"nav": []},
    }


def _context() -> Any:
    return build_context(
        portfolio_session_id=uuid4(),
        agent_key=AgentKey.CONTENT_ARCHITECT,
        current_state={},
        agent_input={
            "operation": "build",
            "intake": {"approved_brief_title": "Test Brief"},
            "preferences": {},
            "prior_output": {},
            "revision_request": "",
        },
    )


async def test_single_page_stops_after_one_call():
    client = _FakeModelClient({"plan_content": _plan_payload(content_included=True, route_count=1)})
    agent = ContentArchitectAgent(model_client=client)

    result = await agent.run(_context())

    assert client.calls == ["plan_content"]
    assert result.output["stages_run"] == ["plan_content"]
    assert result.output["page_content_packs"]


async def test_full_dossier_reaches_planning_and_deferred_writing():
    dossier = {
        "facts": [{"id": "fact:last", "statement": "Led the final project"}],
        "projects": [{"id": "project:last", "name": "Final project"}],
        "restrictions": [{"id": "restriction:client", "instruction": "Omit client name"}],
    }
    client = _FakeModelClient(
        {
            "plan_content": _plan_payload(content_included=False),
            "write_pages": _pages_payload(route_count=1),
        }
    )
    agent = ContentArchitectAgent(model_client=client)
    context = _context()
    context.agent_input["intake"]["dossier"] = dossier

    await agent.run(context)

    assert client.calls == ["plan_content", "write_pages"]
    assert all(packet["dossier"] == dossier for packet in client.packets)


def test_dossier_backed_content_requires_one_page_and_complete_coverage():
    dossier = {
        "contract_version": "DiscoveryDossier/v1",
        "facts": [{"id": "fact:last"}],
        "projects": [{"id": "project:last"}],
    }
    route = _route("home")
    route["path"] = "/"
    pack = _pack("home")
    valid_ledger = [
        {
            "source_id": "fact/fact:last",
            "disposition": "published",
            "public_refs": ["home#hero"],
        },
        {
            "source_id": "project/project:last",
            "disposition": "internal",
            "reason": "The source lacks enough project context for public copy.",
        },
    ]
    kwargs = {
        "route_plan": [route],
        "claim_grounding": [],
        "page_content_packs": [pack],
        "public_content_manifest": {"nav": []},
        "dossier": dossier,
        "site_story_strategy": {"presentation_mode": "single_page"},
    }

    assert not _approval_readiness_errors(**kwargs, coverage_ledger=valid_ledger)
    assert any(
        "missing dossier items" in error
        for error in _approval_readiness_errors(**kwargs, coverage_ledger=valid_ledger[:1])
    )
    assert any(
        "one complete root-page route" in error
        for error in _approval_readiness_errors(
            **{**kwargs, "route_plan": [_route("home")]}, coverage_ledger=valid_ledger
        )
    )


async def test_multi_page_calls_write_pages_when_content_deferred():
    client = _FakeModelClient(
        {
            "plan_content": _plan_payload(content_included=False, route_count=2),
            "write_pages": _pages_payload(route_count=2),
        }
    )
    agent = ContentArchitectAgent(model_client=client)

    result = await agent.run(_context())

    assert client.calls == ["plan_content", "write_pages"]
    assert result.output["stages_run"] == ["plan_content", "write_pages"]
    assert len(result.output["page_content_packs"]) == 2


async def test_integration_pass_runs_when_route_count_exceeds_threshold():
    client = _FakeModelClient(
        {
            "plan_content": _plan_payload(content_included=False, route_count=3),
            "write_pages": _pages_payload(route_count=3),
            "integrate_content": _integrate_payload(route_count=3),
        }
    )
    agent = ContentArchitectAgent(model_client=client)

    result = await agent.run(_context())

    assert client.calls == ["plan_content", "write_pages", "integrate_content"]
    assert result.output["stages_run"] == ["plan_content", "write_pages", "integrate_content"]
    assert len(result.output["route_plan"]) == 3
    assert len(result.output["page_content_packs"]) == 3


async def test_integration_pass_runs_when_explicitly_flagged_even_for_small_route_count():
    client = _FakeModelClient(
        {
            "plan_content": _plan_payload(
                content_included=True, route_count=1, integration_needed=True
            ),
            "integrate_content": _integrate_payload(route_count=1),
        }
    )
    agent = ContentArchitectAgent(model_client=client)

    await agent.run(_context())

    assert client.calls == ["plan_content", "integrate_content"]


async def test_invalid_model_output_raises_content_architect_error():
    client = _FakeModelClient({"plan_content": {"mode": "PAGES_READY"}})
    agent = ContentArchitectAgent(model_client=client)

    with pytest.raises(ContentArchitectModelOutputError):
        await agent.run(_context())


async def test_pending_claim_in_approved_route_gets_one_bounded_corrective_pass():
    plan = _plan_payload(content_included=True)
    plan["claim_grounding"] = [
        {
            "claim_id": "claim:credentials",
            "statement": "A supplied credential",
            "source_reference": "profile.education",
            "evidence_status": "verified",
            "publication_status": "pending",
        }
    ]
    plan["page_content_packs"][0] = _pack("r0", claim_ids=["claim:credentials"])
    repaired = _integrate_payload(1)
    client = _FakeModelClient({"plan_content": plan, "integrate_content": repaired})
    agent = ContentArchitectAgent(model_client=client)

    result = await agent.run(_context())

    assert client.calls == ["plan_content", "integrate_content"]
    assert result.output["stages_run"] == ["plan_content", "integrate_content"]
    assert result.output["page_content_packs"][0]["sections"][0]["claim_ids"] == []


async def test_unresolved_public_scope_never_reaches_review_output():
    plan = _plan_payload(content_included=True)
    plan["claim_grounding"] = [
        {
            "claim_id": "claim:credentials",
            "statement": "A supplied credential",
            "source_reference": "profile.education",
            "evidence_status": "verified",
            "publication_status": "pending",
        }
    ]
    plan["page_content_packs"][0] = _pack("r0", claim_ids=["claim:credentials"])
    still_invalid = _integrate_payload(1)
    still_invalid["page_content_packs"][0] = _pack("r0", claim_ids=["claim:credentials"])
    client = _FakeModelClient({"plan_content": plan, "integrate_content": still_invalid})
    agent = ContentArchitectAgent(model_client=client)

    with pytest.raises(ContentArchitectModelOutputError, match="approval_readiness"):
        await agent.run(_context())

    assert client.calls == ["plan_content", "integrate_content"]


async def test_blocked_route_referenced_in_content_pack_is_rejected():
    """A blocked route must never surface in page_content_packs (hard reject).

    Regression guard for a real live-model failure: an unresolved project
    got a public route and a confident title despite being unverified.
    """
    payload = _plan_payload(content_included=True, route_count=1)
    payload["route_plan"][0]["publication_status"] = "blocked"
    client = _FakeModelClient({"plan_content": payload})
    agent = ContentArchitectAgent(model_client=client)

    with pytest.raises(ContentArchitectModelOutputError):
        await agent.run(_context())


async def test_internal_note_key_leaked_into_content_is_rejected():
    """Internal review notes must live in internal_notes, never in content.

    Regression guard for a real live-model failure: status_note/
    evidence_status/publication_check fields appeared inside visitor-facing
    public_content blocks.
    """
    payload = _plan_payload(content_included=True, route_count=1)
    payload["page_content_packs"][0]["sections"][0]["content"]["status_note"] = (
        "Ownership pending confirmation."
    )
    client = _FakeModelClient({"plan_content": payload})
    agent = ContentArchitectAgent(model_client=client)

    with pytest.raises(ContentArchitectModelOutputError):
        await agent.run(_context())


async def test_route_plan_over_configured_max_is_rejected_without_truncation():
    """A public route plan cannot silently lose content at the configured ceiling."""
    client = _FakeModelClient({"plan_content": _plan_payload(content_included=True, route_count=2)})
    agent = ContentArchitectAgent(model_client=client)
    agent._config.max_routes = 1

    with pytest.raises(ContentArchitectModelOutputError, match="not truncated"):
        await agent.run(_context())

    assert client.calls == ["plan_content"]
