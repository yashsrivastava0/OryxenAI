from __future__ import annotations

import pytest

from oryxenai.agents.build_preparation.agent import BuildPreparationAgent
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey


@pytest.mark.asyncio
async def test_agent_runs_stage0_without_model_client() -> None:
    visual = {
        "pages": [{"route_id": "home", "publication_status": "approved", "scenes": []}],
        "asset_briefs": [],
        "resource_candidates": [],
    }
    context = build_context(
        portfolio_session_id=__import__("uuid").uuid4(),
        agent_key=AgentKey.BUILD_PREPARATION,
        current_state={},
        agent_input={"visual_design_director": visual, "max_routes": 12},
    )
    result = await BuildPreparationAgent().run(context)
    assert result.output["stage"] == "stage_0"
    assert result.model_metadata["model_calls"] == 0
