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
from oryxenai.agents.shared.model_cache import (
    StructuredResultCache,
    generate_with_cache,
    prompt_cache_context,
)
from oryxenai.core.logging import get_logger
from oryxenai.core.settings import get_settings

logger = get_logger("oryxenai.agents.discovery")

_QUESTIONS_OPERATIONS = {"understand_and_question", "prepare_questions"}
_BRIEF_OPERATIONS = {"build_or_revise_brief", "build_brief"}
_MATERIAL_HEADING_MARKERS = (
    "professional summary",
    "professional experience",
    "work experience",
    "education",
    "certifications",
    "core skills",
    "technical skills",
    "selected projects",
    "employment history",
)


class DiscoveryModelOutputError(Exception):
    """Raised when the model output fails the output contract."""

    def __init__(self, operation: str, errors: list[str]) -> None:
        self.operation = operation
        self.errors = errors
        super().__init__(f"Discovery {operation} output failed validation: {'; '.join(errors[:5])}")


class DiscoveryAgent(Agent):
    """Discovery agent that uses an injected ModelClient."""

    key = AgentKey.DISCOVERY

    def __init__(
        self,
        model_client: ModelClient,
        profile_name: str = "",
        *,
        result_cache: StructuredResultCache | None = None,
        profile_fingerprint: str = "",
    ) -> None:
        if model_client is None:
            raise ValueError("DiscoveryAgent requires a model client")
        self._model_client = model_client
        self._config = get_settings().discovery
        self._profile_name = profile_name
        self._result_cache = result_cache
        self._profile_fingerprint = profile_fingerprint

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

        def validate(parsed: dict[str, Any]) -> None:
            validation = validate_questions_output(parsed, self._config.max_questions)
            if not validation.is_valid:
                raise DiscoveryModelOutputError("understand_and_question", validation.errors)

        result = await generate_with_cache(
            client=self._model_client,
            result_cache=self._result_cache,
            agent_key=self.key.value,
            operation="understand_and_question",
            system_prompt=system_prompt,
            instructions=task_prompt,
            input_payload=source_packet,
            output_model=QuestionSetOutput,
            model_profile=self._profile_name,
            profile_fingerprint=self._profile_fingerprint,
            request_context=prompt_cache_context(
                self.key.value, "understand_and_question", manifest
            ),
            strict_schema=False,
            validator=validate,
        )

        parsed = _parsed_output(result)

        mode = OperationMode(parsed.get("mode", OperationMode.ASK_QUESTIONS.value))
        questions = parsed.get("questions") or []
        if mode is OperationMode.NEEDS_DETAILS and not questions and _has_material(intake):
            # A substantive resume/document paired with NEEDS_DETAILS is a
            # contradictory but transport-valid model response. Reusing it
            # from the durable cache would otherwise leave the UI with no
            # actionable question forever. A small deterministic fallback
            # preserves the cost saving and keeps the conversation moving.
            logger.warning(
                "understand_and_question returned NEEDS_DETAILS for substantive material; "
                "using deterministic question fallback"
            )
            mode = OperationMode.ASK_QUESTIONS
            questions = _fallback_questions()
            parsed["assistant_message"] = (
                "I have enough material to work from. Two quick choices will help me position "
                "the portfolio accurately."
            )
        logger.info("understand_and_question mode=%s questions=%d", mode.value, len(questions))
        for question in questions:
            options = question.get("options") if isinstance(question, dict) else None
            if isinstance(options, list) and len(options) > 3:
                logger.warning(
                    "understand_and_question question %r returned %d options (frontend caps at 3)",
                    question.get("id", ""),
                    len(options),
                )

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

        def validate(parsed: dict[str, Any]) -> None:
            validation = validate_brief_output(parsed)
            if not validation.is_valid:
                raise DiscoveryModelOutputError("build_or_revise_brief", validation.errors)

        result = await generate_with_cache(
            client=self._model_client,
            result_cache=self._result_cache,
            agent_key=self.key.value,
            operation="build_or_revise_brief",
            system_prompt=system_prompt,
            instructions=task_prompt,
            input_payload=source_packet,
            output_model=BriefOutput,
            model_profile=self._profile_name,
            profile_fingerprint=self._profile_fingerprint,
            request_context=prompt_cache_context(self.key.value, "build_or_revise_brief", manifest),
            strict_schema=False,
            validator=validate,
        )

        parsed = _parsed_output(result)

        logger.info(
            "build_or_revise_brief produced %d chars of markdown",
            len(parsed.get("brief_markdown", "")),
        )

        profile = dict(parsed.get("profile", {}) or {})
        projects = profile.get("projects")
        if isinstance(projects, list) and len(projects) > self._config.max_projects:
            profile["projects"] = projects[: self._config.max_projects]

        return AgentResult(
            output={
                "operation": "build_or_revise_brief",
                "mode": OperationMode.BRIEF_READY.value,
                "assistant_message": str(parsed.get("assistant_message", "") or ""),
                "brief_title": str(parsed.get("brief_title", "") or ""),
                "brief_markdown": str(parsed.get("brief_markdown", "") or ""),
                "user_summary": str(parsed.get("user_summary", "") or ""),
                "profile": profile,
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


def _has_material(intake: dict[str, Any]) -> bool:
    """Recognize clearly substantive source material without another model call."""

    document_text = str(intake.get("document_text", "") or "").strip()
    if len(document_text) >= 240:
        return True
    message = str(intake.get("message", "") or "").strip().casefold()
    if len(message) >= 2400:
        return True
    if len(message) < 800:
        return False
    marker_count = sum(marker in message for marker in _MATERIAL_HEADING_MARKERS)
    return marker_count >= 2


def _fallback_questions() -> list[dict[str, Any]]:
    """Return the minimum useful interaction for a contradictory model mode."""

    return [
        {
            "id": "portfolio_priority",
            "text": "Which kind of opportunity should this portfolio prioritize first?",
            "kind": "text",
            "options": [],
            "reason": "sets the portfolio's positioning and call to action",
            "allow_skip": True,
            "allow_auto": False,
        },
        {
            "id": "signature_proof",
            "text": "Which project or accomplishment should be the main proof point on the portfolio?",
            "kind": "text",
            "options": [],
            "reason": "determines the strongest story for the case-study section",
            "allow_skip": True,
            "allow_auto": False,
        },
    ]


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
        "telemetry": result.telemetry,
        "cache": result.cache_metadata,
    }
