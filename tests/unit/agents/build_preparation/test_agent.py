from __future__ import annotations

import pytest

from oryxenai.agents.build_preparation.agent import (
    BuildPreparationAgent,
    BuildPreparationModelOutputError,
)
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.core.settings import Settings


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


@pytest.mark.asyncio
async def test_live_phase_requires_model_client_instead_of_using_offline_fallback() -> None:
    context = build_context(
        portfolio_session_id=__import__("uuid").uuid4(),
        agent_key=AgentKey.BUILD_PREPARATION,
        current_state={},
        agent_input={
            "operation": "build",
            "live_model": True,
            "live_providers": False,
            "visual_design_director": {
                "approved": {"visual_direction_hash": "visual-hash"},
                "source_ref": {"content_architect_content_hash": "content-hash"},
                "pages": [{"route_id": "home", "publication_status": "approved", "scenes": []}],
                "asset_briefs": [],
                "resource_candidates": [],
            },
            "content_architect": {
                "page_content_packs": [{"route_id": "home", "sections": [{"section_id": "hero"}]}]
            },
        },
    )

    with pytest.raises(BuildPreparationModelOutputError, match="live Build Preparation model"):
        await BuildPreparationAgent(
            model_client=None,
            live_model=True,
            live_providers=False,
            settings=Settings(),
        ).run(context)
