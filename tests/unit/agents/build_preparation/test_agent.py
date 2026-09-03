from __future__ import annotations

from uuid import uuid4

import pytest

from oryxenai.agents.build_preparation.agent import (
    BuildPreparationAgent,
    BuildPreparationModelOutputError,
)
from oryxenai.agents.build_preparation.validators import BuildPreparationValidationError
from oryxenai.agents.discovery.schemas import StructuredModelResult
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.core.settings import Settings


def _agent_input() -> dict[str, object]:
    return {
        "visual_design_director": {
            "approved": {"visual_direction_hash": "visual-hash"},
            "pages": [{"route_id": "home", "publication_status": "approved", "scenes": []}],
            "asset_briefs": [],
            "resource_candidates": [],
        },
        "content_architect": {
            "route_plan": [{"route_id": "home", "path": "/", "publication_status": "approved"}],
            "page_content_packs": [{"route_id": "home", "sections": [{"section_id": "hero"}]}],
        },
        "max_routes": 12,
    }


def _context(agent_input: dict[str, object]) -> object:
    return build_context(
        portfolio_session_id=uuid4(),
        agent_key=AgentKey.BUILD_PREPARATION,
        current_state={},
        agent_input=agent_input,
    )


@pytest.mark.asyncio
async def test_offline_run_produces_both_briefs_with_zero_model_calls() -> None:
    agent = BuildPreparationAgent(settings=Settings(), live_model=False, live_providers=False)
    result = await agent.run(_context(_agent_input()))

    assert result.output["model_calls"] == 0
    assert result.output["routes"][0]["route_id"] == "home"
    assert result.output["content_brief_markdown"].startswith("# Content & Narrative Brief")
    assert '"navigation_contract": {' in result.output["content_brief_markdown"]
    assert "The navigation_contract above is the complete, closed set" in result.output["content_brief_markdown"]
    assert "authority" in result.output["visual_brief_markdown"].lower()
    assert '"purpose":' in result.output["visual_brief_markdown"]
    assert '"guidance":' in result.output["visual_brief_markdown"]


@pytest.mark.asyncio
async def test_live_mode_requires_a_model_client() -> None:
    agent = BuildPreparationAgent(
        model_client=None, settings=Settings(), live_model=True, live_providers=False
    )
    with pytest.raises(BuildPreparationModelOutputError, match="Live mode requires"):
        await agent.run(_context(_agent_input()))


class _FakeModelClient:
    def __init__(self, parsed_output: dict[str, object]) -> None:
        self._parsed_output = parsed_output

    async def generate_structured(self, **kwargs: object) -> StructuredModelResult:
        return StructuredModelResult(parsed_output=self._parsed_output, model="fake-model")


@pytest.mark.asyncio
async def test_live_run_rejects_a_candidate_index_the_model_was_not_given() -> None:
    agent = BuildPreparationAgent(
        model_client=_FakeModelClient(
            {
                "visual_brief_prose": "## Design language\n\nClear and editorial.",
                "resource_guidance": [{"need_id": "does-not-exist", "primary_candidate_index": 0}],
            }
        ),
        settings=Settings(),
        live_model=True,
        live_providers=False,
    )
    with pytest.raises(BuildPreparationValidationError):
        await agent.run(_context(_agent_input()))


@pytest.mark.asyncio
async def test_live_run_accepts_a_valid_model_response() -> None:
    agent = BuildPreparationAgent(
        model_client=_FakeModelClient(
            {
                "visual_brief_prose": "## Design language\n\nClear and editorial.\n\n"
                "Code Generator has final authority to adapt this brief.",
                "resource_guidance": [],
                "component_guidance": [],
                "seo_suggestions": {"home": "A concise portfolio home page."},
            }
        ),
        settings=Settings(),
        live_model=True,
        live_providers=False,
    )
    result = await agent.run(_context(_agent_input()))

    assert result.output["model_calls"] == 1
    assert "concise portfolio home page" in result.output["content_brief_markdown"]
    assert "Clear and editorial" in result.output["visual_brief_markdown"]
