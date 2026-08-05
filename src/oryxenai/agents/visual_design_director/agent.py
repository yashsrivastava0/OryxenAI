"""Visual Design Director agent — deterministic mock implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from oryxenai.agents.shared.contracts import Agent, AgentContext, AgentKey, AgentResult
from oryxenai.agents.visual_design_director.schemas import (
    VisualDesignDirectorRequest,
    VisualDesignDirectorResponse,
)

_SAMPLE_DIR = Path(__file__).resolve().parent / "samples"


def _load_sample(filename: str) -> dict[str, Any]:
    path = _SAMPLE_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Sample file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


class VisualDesignDirectorAgent(Agent):
    """Deterministic mock Visual Design Director agent."""

    key = AgentKey.VISUAL_DESIGN_DIRECTOR

    async def run(self, context: AgentContext) -> AgentResult:
        VisualDesignDirectorRequest(**context.agent_input)
        raw = _load_sample("output.json")
        response = VisualDesignDirectorResponse(**raw)
        return AgentResult(
            output=response.model_dump(),
            prompt_version="0.0.0-mock",
            model_metadata={"provider": "mock", "agent": self.key.value},
        )
