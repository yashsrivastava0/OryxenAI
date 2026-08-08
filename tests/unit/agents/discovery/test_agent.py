"""Unit tests for DiscoveryAgent's own post-validation processing."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from oryxenai.agents.discovery.agent import DiscoveryAgent
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


async def test_build_or_revise_brief_truncates_projects_over_the_configured_max():
    """A resume can legitimately list more projects than max_projects.

    Truncating (not rejecting) means one good generation is never thrown
    away and retried against a condition that can only fail again the same
    way — profile.projects reflects real facts about the source material,
    not a random model mistake. See validators.py::validate_brief_output.
    """
    agent = DiscoveryAgent(model_client=_FakeModelClient(_brief_payload(project_count=12)))
    agent._config.max_projects = 5

    result = await agent.run(_context())

    projects = result.output["profile"]["projects"]
    assert len(projects) == 5
    assert [p["name"] for p in projects] == [f"Project {i}" for i in range(5)]


async def test_build_or_revise_brief_keeps_projects_under_the_max_untouched():
    agent = DiscoveryAgent(model_client=_FakeModelClient(_brief_payload(project_count=3)))
    agent._config.max_projects = 5

    result = await agent.run(_context())

    assert len(result.output["profile"]["projects"]) == 3
