"""Unit tests for DiscoveryAgent's own post-validation processing."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from oryxenai.agents.discovery.agent import DiscoveryAgent, _packet
from oryxenai.agents.discovery.normalize import normalize_brief, normalize_questions
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


def test_model_packet_is_stable_across_new_source_ids():
    intake = {
        "message": "Build my portfolio",
        "document_text": "I designed a PostgreSQL queue.",
        "goal": "Find engineering work",
    }
    first, first_documents, _ = _packet({"intake": intake})
    second, second_documents, _ = _packet({"intake": intake})
    assert first == second
    assert first_documents[0].id != second_documents[0].id


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
    payload["questions"][0]["text"] = "Choose a focus"
    payload["questions"][1]["text"] = "Choose an audience"
    normalized, errors = normalize_questions(payload)
    assert errors == []
    assert normalized is not None
    assert [option["id"] for option in normalized["questions"][0]["options"]] == ["0", "1", "2"]
    assert normalized["questions"][1]["kind"] == "text"
    assert normalized["questions"][1]["options"] == []


def test_dossier_normalization_preserves_claims_and_repairs_references():
    payload = {
        "brief_markdown": "# Brief\n\nA useful brief.",
        "dossier": {
            "facts": [{"id": "fact-1", "statement": "Built a service"}],
            "projects": [{"id": "project-1", "name": "Service", "fact_ids": ["fact-1", "absent"]}],
        },
    }
    normalized, errors = normalize_brief(payload, documents=[], question_events=[])
    assert errors == []
    assert normalized is not None
    dossier = normalized["dossier"]
    assert dossier.facts[0].statement == "Built a service"
    assert dossier.projects[0].fact_ids == ["fact-1"]
    assert dossier.source_coverage == []


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
