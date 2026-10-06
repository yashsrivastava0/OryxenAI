"""Explorer's two model operations and server-owned output normalization."""

from __future__ import annotations

from typing import Any

from oryxenai.agents.discovery.dossier import as_text_list, profile_from_dossier
from oryxenai.agents.discovery.drafts import BriefOutput, QuestionSetOutput
from oryxenai.agents.discovery.normalize import normalize_brief, normalize_questions
from oryxenai.agents.discovery.palette import PALETTE_GAP_ID, add_palette_question
from oryxenai.agents.discovery.prompt_builder import build_instructions
from oryxenai.agents.discovery.schemas import (
    QuestionHistoryEvent,
    SourceDocument,
    StructuredModelResult,
)
from oryxenai.agents.discovery.sources import documents_from_intake
from oryxenai.agents.shared.contracts import Agent, AgentContext, AgentKey, AgentResult, ModelClient
from oryxenai.agents.shared.model_cache import (
    StructuredResultCache,
    generate_with_cache,
    prompt_cache_context,
)
from oryxenai.agents.shared.providers.errors import ModelOutputInvalidError
from oryxenai.core.logging import get_logger
from oryxenai.core.settings import get_settings

logger = get_logger("oryxenai.agents.discovery")
_QUESTIONS_OPERATIONS = {"understand_and_question", "prepare_questions"}
_BRIEF_OPERATIONS = {"build_or_revise_brief", "build_brief"}


class DiscoveryModelOutputError(Exception):
    """An output contains no recoverable Explorer content."""

    def __init__(self, operation: str, errors: list[str]) -> None:
        self.operation = operation
        self.errors = errors
        super().__init__(f"Explorer {operation} output failed validation: {'; '.join(errors[:5])}")


class DiscoveryAgent(Agent):
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
            return await self._questions(context)
        if operation in _BRIEF_OPERATIONS:
            return await self._brief(context)
        raise ValueError(f"Unknown Explorer operation: {operation}")

    async def _questions(self, context: AgentContext) -> AgentResult:
        packet, _documents, events = _packet(context.agent_input)
        system, instructions, version, manifest = build_instructions(
            "understand_and_question", packet
        )
        request_context = prompt_cache_context(
            self.key.value, "understand_and_question", manifest, context
        )
        request_context["stream"] = True
        closed = {event.gap_id for event in events if event.gap_id and event.status != "pending"}
        unresolved_questions: list[str] = []

        def validate(parsed: dict[str, Any]) -> None:
            output, errors = normalize_questions(
                parsed, self._config.max_questions, closed_gap_ids=closed
            )
            if output is None:
                raw_questions = parsed.get("questions")
                for item in raw_questions if isinstance(raw_questions, list) else []:
                    question_text = (
                        str(item.get("text") or item.get("question") or "").strip()
                        if isinstance(item, dict)
                        else str(item).strip()
                    )
                    if question_text and question_text not in unresolved_questions:
                        unresolved_questions.append(question_text)
                if not unresolved_questions:
                    unresolved_questions.append("Clarify missing resume details or portfolio goals")
                raise DiscoveryModelOutputError("understand_and_question", errors)

        try:
            result = await generate_with_cache(
                client=self._model_client,
                result_cache=self._result_cache,
                agent_key=self.key.value,
                operation="understand_and_question",
                system_prompt=system,
                instructions=instructions,
                input_payload=packet,
                output_model=QuestionSetOutput,
                model_profile=self._profile_name,
                profile_fingerprint=self._profile_fingerprint,
                request_context=request_context,
                strict_schema=False,
                validator=validate,
            )
        except (DiscoveryModelOutputError, ModelOutputInvalidError):
            if not unresolved_questions:
                raise
            # The model client's bounded recovery has been exhausted. Preserve
            # the open gaps for the brief instead of showing a broken card.
            fallback_output = add_palette_question(
                {
                    "mode": "READY_FOR_BRIEF",
                    "assistant_message": "I can draft your brief from what you shared and mark uncertain details for review.",
                    "questions": [],
                },
                already_answered=any(
                    event.gap_id == PALETTE_GAP_ID and event.status == "answered"
                    for event in events
                ),
            )
            return AgentResult(
                output={
                    "operation": "understand_and_question",
                    **fallback_output,
                    "memory_update": {"unresolved_question_gaps": unresolved_questions[:3]},
                },
                prompt_version=version,
                model_metadata={"question_recovery_exhausted": True, "prompt_modules": manifest},
            )
        output, errors = normalize_questions(
            result.parsed_output, self._config.max_questions, closed_gap_ids=closed
        )
        if output is None:
            raise DiscoveryModelOutputError("understand_and_question", errors)
        output = add_palette_question(
            output,
            already_answered=any(
                event.gap_id == PALETTE_GAP_ID and event.status == "answered" for event in events
            ),
        )
        logger.info(
            "model_stage engine=discovery operation=understand_and_question run=%s "
            "latency_ms=%.0f cache_hit=%s mode=%s questions=%d",
            context.run_id,
            result.latency_ms,
            bool(result.cache_metadata.get("cache_hit")),
            output["mode"],
            len(output["questions"]),
        )
        return AgentResult(
            output={"operation": "understand_and_question", **output, "memory_update": {}},
            prompt_version=version,
            model_metadata=_metadata(result, manifest),
        )

    async def _brief(self, context: AgentContext) -> AgentResult:
        packet, documents, events = _packet(context.agent_input)
        unresolved_gaps = packet.get("unresolved_question_gaps") or []
        revision_request = str(context.agent_input.get("revision_request", "") or "")
        packet.update(
            existing_brief=str(context.agent_input.get("existing_brief", "") or ""),
            revision_request=revision_request,
        )
        system, instructions, version, manifest = build_instructions(
            "build_or_revise_brief", packet
        )
        request_context = prompt_cache_context(
            self.key.value, "build_or_revise_brief", manifest, context
        )
        request_context["stream"] = True

        def normalize(parsed: dict[str, Any]) -> dict[str, Any]:
            if unresolved_gaps:
                parsed = {
                    **parsed,
                    "open_items": list(
                        dict.fromkeys([*as_text_list(parsed.get("open_items")), *unresolved_gaps])
                    ),
                }
            output, errors = normalize_brief(
                parsed,
                documents=documents,
                question_events=[event for event in events if event.gap_id != PALETTE_GAP_ID],
                goal_text=str(context.agent_input.get("intake", {}).get("goal", "") or ""),
            )
            if output is None:
                raise DiscoveryModelOutputError("build_or_revise_brief", errors)
            return output

        result = await generate_with_cache(
            client=self._model_client,
            result_cache=None if revision_request.strip() else self._result_cache,
            agent_key=self.key.value,
            operation="build_or_revise_brief",
            system_prompt=system,
            instructions=instructions,
            input_payload=packet,
            output_model=BriefOutput,
            model_profile=self._profile_name,
            profile_fingerprint=self._profile_fingerprint,
            request_context=request_context,
            strict_schema=False,
            validator=lambda parsed: _validate_brief(parsed, normalize),
        )
        output = normalize(result.parsed_output)
        dossier = output["dossier"]
        profile = profile_from_dossier(dossier)
        logger.info(
            "model_stage engine=discovery operation=build_or_revise_brief run=%s "
            "latency_ms=%.0f cache_hit=%s output_chars=%d",
            context.run_id,
            result.latency_ms,
            bool(result.cache_metadata.get("cache_hit")),
            len(output["brief_markdown"]),
        )
        return AgentResult(
            output={
                "operation": "build_or_revise_brief",
                **output,
                "dossier": dossier.model_dump(mode="json"),
                "profile": profile.model_dump(mode="json"),
                "memory_update": {},
            },
            prompt_version=version,
            model_metadata=_metadata(result, manifest),
        )


def _packet(
    agent_input: dict[str, Any],
) -> tuple[dict[str, Any], list[SourceDocument], list[QuestionHistoryEvent]]:
    intake = agent_input.get("intake", {})
    if not isinstance(intake, dict):
        intake = {}
    raw_documents = agent_input.get("source_documents")
    documents = (
        [SourceDocument.model_validate(item) for item in raw_documents]
        if isinstance(raw_documents, list)
        else documents_from_intake(intake)
    )
    raw_events = agent_input.get("question_events", [])
    events = (
        [QuestionHistoryEvent.model_validate(item) for item in raw_events]
        if isinstance(raw_events, list)
        else []
    )
    packet: dict[str, Any] = {
        "goal": str(intake.get("goal", "") or "")
        if not any(document.source_kind == "user_intent" for document in documents)
        else "",
        # Answers travel once, in question_history; their per-answer source
        # snapshots exist for the review UI and would only repeat them here.
        "sources": [
            {"kind": document.source_kind, "label": document.label, "text": document.original_text}
            for document in documents
            if document.source_kind != "user_answer"
        ],
        "question_history": [
            {
                "question": event.question,
                "answer": event.answer,
                "status": event.status,
                "gap_id": event.gap_id,
            }
            for event in events
            if event.gap_id != PALETTE_GAP_ID
        ],
    }
    prior_memory = agent_input.get("prior_memory")
    if isinstance(prior_memory, dict):
        unresolved = prior_memory.get("unresolved_question_gaps")
        if isinstance(unresolved, list):
            packet["unresolved_question_gaps"] = [
                str(item).strip() for item in unresolved[:3] if str(item).strip()
            ]
    return packet, documents, events


def _metadata(result: StructuredModelResult, manifest: dict[str, str]) -> dict[str, Any]:
    return {
        "provider": str(result.telemetry.get("provider", "") or ""),
        "model": result.model,
        "response_id": result.response_id,
        "usage": result.usage,
        "latency_ms": result.latency_ms,
        "finish_reason": result.finish_reason,
        "prompt_modules": manifest,
        "telemetry": result.telemetry,
        "cache": result.cache_metadata,
    }


def _validate_brief(parsed: dict[str, Any], normalize: Any) -> None:
    normalize(parsed)
