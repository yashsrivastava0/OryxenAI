"""Unit tests for DiscoveryAgent's own post-validation processing."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from oryxenai.agents.discovery.agent import (
    DiscoveryAgent,
    _normalize_dossier_links,
    _normalize_question_choices,
)
from oryxenai.agents.discovery.schemas import StructuredModelResult
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey


class _FakeModelClient:
    """Returns a fixed structured result regardless of the prompt."""

    def __init__(self, parsed_output: dict[str, Any]) -> None:
        self._parsed_output = parsed_output

    async def complete(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError

    async def generate_structured(self, **kwargs: Any) -> StructuredModelResult:
        return StructuredModelResult(
            parsed_output=self._parsed_output,
            response_id="fake-response-id",
            model="fake-model",
            usage={"prompt_tokens": 1, "completion_tokens": 1},
            finish_reason="stop",
            latency_ms=1.0,
        )


def test_question_choices_are_three_or_free_text():
    payload = {
        "questions": [
            {
                "kind": "single_select",
                "options": [{"id": str(i), "label": str(i)} for i in range(9)],
            },
            {"kind": "multi_select", "options": [{"id": "only", "label": "Only"}]},
        ]
    }
    _normalize_question_choices(payload)
    assert [option["id"] for option in payload["questions"][0]["options"]] == ["0", "1", "2"]
    assert payload["questions"][1]["kind"] == "text"
    assert payload["questions"][1]["options"] == []


def test_dossier_link_normalization_preserves_claims_and_repairs_references():
    payload = {
        "dossier": {
            "facts": [{"id": "fact-1", "statement": "Built a service", "source_refs": ["span-1"]}],
            "projects": [{"id": "project-1", "fact_ids": ["fact-1"], "source_refs": []}],
            "source_coverage": [
                {"span_id": "span-1", "disposition": "reference_context", "fact_ids": []},
                {"span_id": "span-2", "disposition": "fact", "fact_ids": []},
            ],
        }
    }
    _normalize_dossier_links(payload)
    dossier = payload["dossier"]
    assert dossier["facts"][0]["statement"] == "Built a service"
    assert dossier["projects"][0]["source_refs"] == ["span-1"]
    assert dossier["source_coverage"][0]["disposition"] == "fact"
    assert dossier["source_coverage"][0]["fact_ids"] == ["fact-1"]
    assert dossier["source_coverage"][1]["disposition"] == "reference_context"
    assert dossier["open_items"][0]["source_refs"] == ["span-2"]


def _brief_payload(project_count: int) -> dict[str, Any]:
    return {
        "mode": "BRIEF_READY",
        "assistant_message": "Review the brief.",
        "brief_title": "Portfolio Discovery Brief",
        "brief_markdown": "# Portfolio Discovery Brief\n\nContent.",
        "user_summary": "A short summary.",
        "profile": {
            "name": "Test User",
            "projects": [{"name": f"Project {i}"} for i in range(project_count)],
        },
        "dossier": {
            "projects": [
                {"id": f"project-{i}", "name": f"Project {i}"} for i in range(project_count)
            ]
        },
        "open_items": [],
        "memory_update": {},
    }


def _context() -> Any:
    return build_context(
        portfolio_session_id=uuid4(),
        agent_key=AgentKey.DISCOVERY,
        current_state={},
        agent_input={"operation": "build_or_revise_brief", "intake": {}, "answers": {}},
    )


def _questions_context(message: str) -> Any:
    return build_context(
        portfolio_session_id=uuid4(),
        agent_key=AgentKey.DISCOVERY,
        current_state={},
        agent_input={
            "operation": "understand_and_question",
            "intake": {"message": message, "document_text": "", "goal": ""},
            "prior_memory": {},
        },
    )


async def test_build_or_revise_brief_preserves_projects_over_the_configured_max():
    """Preserve the full project inventory even when it exceeds old config."""
    agent = DiscoveryAgent(model_client=_FakeModelClient(_brief_payload(project_count=12)))
    agent._config.max_projects = 5

    result = await agent.run(_context())

    projects = result.output["profile"]["projects"]
    assert len(projects) == 12
    assert [p["name"] for p in projects] == [f"Project {i}" for i in range(12)]


async def test_build_or_revise_brief_keeps_projects_under_the_max_untouched():
    agent = DiscoveryAgent(model_client=_FakeModelClient(_brief_payload(project_count=3)))
    agent._config.max_projects = 5

    result = await agent.run(_context())

    assert len(result.output["profile"]["projects"]) == 3


async def test_needs_details_does_not_invent_questions_for_supplied_material():
    """A model may ask the user for more detail without a synthetic fallback."""
    resume = "\n".join(
        [
            "# Professional Summary",
            "Senior engineer building reliable platforms.",
            "## Professional Experience",
            "Led production systems and mentored engineers.",
            "## Core Skills",
            "Python, SQL, and cloud architecture.",
        ]
        + ["Additional factual project detail."] * 80
    )
    agent = DiscoveryAgent(
        model_client=_FakeModelClient(
            {
                "mode": "NEEDS_DETAILS",
                "assistant_message": "Please provide more details.",
                "questions": [],
                "memory_update": {},
            }
        )
    )

    result = await agent.run(_questions_context(resume))

    assert result.output["mode"] == "NEEDS_DETAILS"
    assert result.output["questions"] == []


async def test_needs_details_mode_is_preserved_for_long_unstructured_material():
    """Long source does not justify generic, invented questions."""
    agent = DiscoveryAgent(
        model_client=_FakeModelClient(
            {
                "mode": "NEEDS_DETAILS",
                "assistant_message": "Please provide more details.",
                "questions": [],
                "memory_update": {},
            }
        )
    )

    result = await agent.run(_questions_context("Experience detail. " * 180))

    assert result.output["mode"] == "NEEDS_DETAILS"
    assert result.output["questions"] == []
