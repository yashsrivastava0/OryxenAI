"""Code Generator agent — deterministic mock implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.schemas import (
    CodeGeneratorRequest,
    CodeGeneratorResponse,
)
from oryxenai.agents.shared.contracts import Agent, AgentContext, AgentKey, AgentResult

_SAMPLE_DIR = Path(__file__).resolve().parent / "samples"


def _load_sample(filename: str) -> dict[str, Any]:
    path = _SAMPLE_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Sample file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


class CodeGeneratorAgent(Agent):
    """Deterministic mock Code Generator agent."""

    key = AgentKey.CODE_GENERATOR

    async def run(self, context: AgentContext) -> AgentResult:
        CodeGeneratorRequest(**context.agent_input)
        raw = _load_sample("output.json")
        response = CodeGeneratorResponse(**raw)
        return AgentResult(
            output=response.model_dump(),
            prompt_version="0.0.0-mock",
            model_metadata={"provider": "mock", "agent": self.key.value},
        )
