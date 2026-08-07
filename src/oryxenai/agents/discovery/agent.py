"""Discovery agent — turns raw user input into questions and a portfolio brief.

Two model calls maximum:
  1. understand_and_question: user input -> interaction mode + questions (0..7)
  2. build_or_revise_brief: user input + answers + memory -> detailed brief

The legacy operation names prepare_questions / build_brief are accepted as
aliases so persisted in-flight run payloads keep working. Input is accepted
as-is (no input validation). The output contract is the only validation gate,
enforced by validators.py.
"""

from __future__ import annotations

from typing import Any

from oryxenai.agents.discovery.prompt_builder import build_instructions
from oryxenai.agents.discovery.schemas import (
    BriefOutput,
    OperationMode,
    QuestionSetOutput,
    StructuredModelResult,
)
from oryxenai.agents.discovery.validators import (
    validate_brief_output,
    validate_questions_output,
)
from oryxenai.agents.shared.contracts import Agent, AgentContext, AgentKey, AgentResult, ModelClient
from oryxenai.core.logging import get_logger
from oryxenai.core.settings import get_settings

logger = get_logger("oryxenai.agents.discovery")

_QUESTIONS_OPERATIONS = {"understand_and_question", "prepare_questions"}
_BRIEF_OPERATIONS = {"build_or_revise_brief", "build_brief"}


class DiscoveryModelOutputError(Exception):
    """Raised when the model output fails the output contract."""

    def __init__(self, operation: str, errors: list[str]) -> None:
        self.operation = operation
        self.errors = errors
        super().__init__(f"Discovery {operation} output failed validation: {'; '.join(errors[:5])}")


class DiscoveryAgent(Agent):
    """Discovery agent that uses an injected ModelClient."""

    key = AgentKey.DISCOVERY

    def __init__(self, model_client: ModelClient) -> None:
        if model_client is None:
            raise ValueError("DiscoveryAgent requires a model client")
        self._model_client = model_client
        self._config = get_settings().discovery

    async def run(self, context: AgentContext) -> AgentResult:
        operation = context.agent_input.get("operation", "understand_and_question")

        if operation in _QUESTIONS_OPERATIONS:
            return await self._run_understand_and_question(context)
        if operation in _BRIEF_OPERATIONS:
            return await self._run_build_or_revise_brief(context)
        raise ValueError(f"Unknown Discovery operation: {operation}")

    async def _run_understand_and_question(self, context: AgentContext) -> AgentResult:
        intake = self._intake_from(context.agent_input)
        source_packet = {
            "message": intake.get("message", ""),
            "document_text": intake.get("document_text", ""),
            "goal": intake.get("goal", ""),
            "prior_memory": context.agent_input.get("prior_memory", {}),
        }

        system_prompt, task_prompt, version, manifest = build_instructions(
            operation="understand_and_question",
            source_packet=source_packet,
        )

        result = await self._model_client.generate_structured(
            operation="understand_and_question",
            instructions=f"{system_prompt}\n\n{task_prompt}",
            input_payload=source_packet,
            output_model=QuestionSetOutput,
        )

        parsed = _parsed_output(result)
        validation = validate_questions_output(parsed, self._config.max_questions)
        if not validation.is_valid:
            raise DiscoveryModelOutputError("understand_and_question", validation.errors)

        mode = OperationMode(parsed.get("mode", OperationMode.ASK_QUESTIONS.value))
        questions = parsed.get("questions") or []
        logger.info("understand_and_question mode=%s questions=%d", mode.value, len(questions))

        return AgentResult(
            output={
                "operation": "understand_and_question",
                "mode": mode.value,
                "assistant_message": str(parsed.get("assistant_message", "") or ""),
                "questions": questions,
                "memory_update": parsed.get("memory_update", {}) or {},
            },
            prompt_version=version,
            model_metadata=_metadata(result, manifest),
        )

    async def _run_build_or_revise_brief(self, context: AgentContext) -> AgentResult:
        intake = self._intake_from(context.agent_input)
        answers = context.agent_input.get("answers", {})
        source_packet = {
            "message": intake.get("message", ""),
            "document_text": intake.get("document_text", ""),
            "goal": intake.get("goal", ""),
            "answers": answers,
            "prior_memory": context.agent_input.get("prior_memory", {}),
            "existing_brief": str(context.agent_input.get("existing_brief", "") or ""),
            "revision_request": str(context.agent_input.get("revision_request", "") or ""),
        }

        system_prompt, task_prompt, version, manifest = build_instructions(
            operation="build_or_revise_brief",
            source_packet=source_packet,
        )

        result = await self._model_client.generate_structured(
            operation="build_or_revise_brief",
            instructions=f"{system_prompt}\n\n{task_prompt}",
            input_payload=source_packet,
            output_model=BriefOutput,
        )

        parsed = _parsed_output(result)
        validation = validate_brief_output(parsed)
        if not validation.is_valid:
            raise DiscoveryModelOutputError("build_or_revise_brief", validation.errors)

        logger.info(
            "build_or_revise_brief produced %d chars of markdown",
            len(parsed.get("brief_markdown", "")),
        )

        return AgentResult(
            output={
                "operation": "build_or_revise_brief",
                "mode": OperationMode.BRIEF_READY.value,
                "assistant_message": str(parsed.get("assistant_message", "") or ""),
                "brief_title": str(parsed.get("brief_title", "") or ""),
                "brief_markdown": str(parsed.get("brief_markdown", "") or ""),
                "open_items": parsed.get("open_items", []) or [],
                "memory_update": parsed.get("memory_update", {}) or {},
            },
            prompt_version=version,
            model_metadata=_metadata(result, manifest),
        )

    @staticmethod
    def _intake_from(agent_input: dict[str, Any]) -> dict[str, Any]:
        raw = agent_input.get("intake", {})
        if not isinstance(raw, dict):
            return {}
        return {
            "message": str(raw.get("message", "") or ""),
            "document_text": str(raw.get("document_text", "") or ""),
            "goal": str(raw.get("goal", "") or ""),
        }


def _parsed_output(result: StructuredModelResult) -> dict[str, Any]:
    if isinstance(result, StructuredModelResult):
        return result.parsed_output
    return dict(result.parsed_output)


def _metadata(result: StructuredModelResult, manifest: dict[str, str]) -> dict[str, Any]:
    return {
        "provider": result.model,
        "model": result.model,
        "response_id": result.response_id,
        "usage": result.usage,
        "latency_ms": result.latency_ms,
        "finish_reason": result.finish_reason,
        "prompt_modules": manifest,
    }
