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
from tests.unit.agents.content_architect.helpers import (
    claim,
    integrate_payload,
    pages_payload,
    plan_payload,
    valid_page,
)


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
    client = _FakeModelClient({"plan_content": plan_payload()})
    agent = ContentArchitectAgent(model_client=client)

    result = await agent.run(_context())

    assert client.calls == ["plan_content"]
    assert result.output["stages_run"] == ["plan_content"]
    assert len(result.output["page_content"]["systems_practice"]["pillars"]) == 4


async def test_full_dossier_reaches_planning_and_deferred_writing():
    dossier = {
        "facts": [{"id": "fact:last", "statement": "Led the final project"}],
        "projects": [{"id": "project:last", "name": "Final project"}],
        "restrictions": [{"id": "restriction:client", "instruction": "Omit client name"}],
    }
    client = _FakeModelClient(
        {
            "plan_content": plan_payload(content_included=False),
            "write_pages": pages_payload(),
        }
    )
    agent = ContentArchitectAgent(model_client=client)
    context = _context()
    context.agent_input["intake"]["dossier"] = dossier
    context.agent_input["intake"]["profile"] = {"name": "Duplicate profile"}

    result = await agent.run(context)

    assert client.calls == ["plan_content", "write_pages"]
    assert result.output["stages_run"] == ["plan_content", "write_pages"]
    assert all(packet["dossier"] == dossier for packet in client.packets)
    assert all(packet["profile"] == {} for packet in client.packets)


async def test_deferred_writer_summary_describes_finished_page():
    pages = pages_payload()
    pages["user_summary"] = "Your finished page leads with the strongest grounded work."
    client = _FakeModelClient(
        {"plan_content": plan_payload(content_included=False), "write_pages": pages}
    )

    result = await ContentArchitectAgent(model_client=client).run(_context())

    assert result.output["user_summary"] == pages["user_summary"]


async def test_writer_refreshes_claim_field_paths():
    plan = plan_payload(content_included=False)
    plan["claim_grounding"] = [claim("claim:a")]
    pages = pages_payload()
    pages["claim_grounding"] = [
        claim("claim:a", field_paths=["systems_practice.pillars[0].description"])
    ]
    client = _FakeModelClient({"plan_content": plan, "write_pages": pages})
    agent = ContentArchitectAgent(model_client=client)

    result = await agent.run(_context())

    assert result.output["claim_grounding"][0]["field_paths"] == [
        "systems_practice.pillars[0].description"
    ]


def test_dossier_backed_content_requires_complete_coverage():
    dossier = {
        "contract_version": "DiscoveryDossier/v1",
        "facts": [{"id": "fact:last"}],
        "projects": [{"id": "project:last"}],
    }
    valid_ledger = [
        {
            "source_id": "fact/fact:last",
            "disposition": "used",
            "field_paths": ["hero.intro"],
        },
        {
            "source_id": "project/project:last",
            "disposition": "retained_internally",
            "reason": "The source lacks enough project context for public copy.",
        },
    ]
    kwargs: dict[str, Any] = {
        "page_content": valid_page(),
        "claim_grounding": [],
        "dossier": dossier,
    }

    assert not _approval_readiness_errors(**kwargs, coverage_ledger=valid_ledger)
    assert any(
        "missing dossier items" in error
        for error in _approval_readiness_errors(**kwargs, coverage_ledger=valid_ledger[:1])
    )
    legacy = [{**valid_ledger[0], "disposition": "published"}, valid_ledger[1]]
    assert any(
        "invalid disposition" in error
        for error in _approval_readiness_errors(**kwargs, coverage_ledger=legacy)
    )


async def test_integration_pass_runs_when_explicitly_flagged():
    client = _FakeModelClient(
        {
            "plan_content": plan_payload(integration_needed=True),
            "integrate_content": integrate_payload(),
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


async def test_wrong_pillar_count_gets_one_bounded_corrective_pass():
    short = valid_page()
    short["systems_practice"]["pillars"] = short["systems_practice"]["pillars"][:3]
    plan = plan_payload()
    plan["page_content"] = short
    client = _FakeModelClient({"plan_content": plan, "integrate_content": integrate_payload()})
    agent = ContentArchitectAgent(model_client=client)

    result = await agent.run(_context())

    assert client.calls == ["plan_content", "integrate_content"]
    assert len(result.output["page_content"]["systems_practice"]["pillars"]) == 4


async def test_pending_claim_bound_to_public_field_gets_one_bounded_corrective_pass():
    plan = plan_payload()
    plan["claim_grounding"] = [
        claim(
            "claim:credentials",
            publication_status="pending",
            field_paths=["hero.intro"],
        )
    ]
    repaired = integrate_payload()
    repaired["claim_grounding"] = [claim("claim:credentials", publication_status="pending")]
    client = _FakeModelClient({"plan_content": plan, "integrate_content": repaired})
    agent = ContentArchitectAgent(model_client=client)

    result = await agent.run(_context())

    assert client.calls == ["plan_content", "integrate_content"]
    assert result.output["claim_grounding"][0]["field_paths"] == []


async def test_unresolved_public_scope_never_reaches_review_output():
    plan = plan_payload()
    plan["claim_grounding"] = [
        claim("claim:credentials", publication_status="pending", field_paths=["hero.intro"])
    ]
    still_invalid = integrate_payload()
    still_invalid["claim_grounding"] = plan["claim_grounding"]
    client = _FakeModelClient({"plan_content": plan, "integrate_content": still_invalid})
    agent = ContentArchitectAgent(model_client=client)

    with pytest.raises(ContentArchitectModelOutputError, match="approval_readiness"):
        await agent.run(_context())

    assert client.calls == ["plan_content", "integrate_content"]


async def test_blocked_claim_bound_to_public_field_is_rejected():
    """A blocked claim must never be reachable from page copy (hard reject).

    Regression guard for a real live-model failure: an unresolved item got
    public copy despite an explicit restriction.
    """
    payload = plan_payload()
    payload["claim_grounding"] = [
        claim("claim:nda", publication_status="blocked", field_paths=["hero.intro"])
    ]
    client = _FakeModelClient({"plan_content": payload})
    agent = ContentArchitectAgent(model_client=client)

    with pytest.raises(ContentArchitectModelOutputError):
        await agent.run(_context())


async def test_internal_note_key_leaked_into_page_content_is_rejected():
    """Internal review notes must live in internal_notes, never in page copy."""
    payload = plan_payload()
    payload["page_content"]["hero"]["status_note"] = "Ownership pending confirmation."
    client = _FakeModelClient({"plan_content": payload})
    agent = ContentArchitectAgent(model_client=client)

    with pytest.raises(ContentArchitectModelOutputError):
        await agent.run(_context())


async def test_stray_page_keys_are_dropped_not_fatal():
    payload = plan_payload()
    payload["page_content"]["hero"]["tagline_note"] = "ignored"
    client = _FakeModelClient({"plan_content": payload})
    agent = ContentArchitectAgent(model_client=client)

    result = await agent.run(_context())

    assert "tagline_note" not in result.output["page_content"]["hero"]
