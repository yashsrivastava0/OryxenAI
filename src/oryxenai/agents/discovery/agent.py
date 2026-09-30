"""Discovery agent for source-grounded intake, clarification, and briefing.

Each durable job makes one model call. A completed question batch proceeds to
the brief, without another interview round.

The legacy operation names prepare_questions / build_brief are accepted as
aliases so persisted in-flight run payloads keep working. Input is preserved
as submitted; output and source-reference consistency are checked by
validators.py.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from oryxenai.agents.discovery.prompt_builder import build_instructions
from oryxenai.agents.discovery.schemas import (
    BriefOutput,
    DiscoveryDossier,
    EducationEntry,
    ExperienceEntry,
    OperationMode,
    ProjectEntry,
    QuestionHistoryEvent,
    QuestionSetOutput,
    SourceDocument,
    StructuredModelResult,
    StructuredProfile,
)
from oryxenai.agents.discovery.sources import source_segments_for_model
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
        documents = _source_documents_from(context.agent_input, intake)
        question_events = _question_events_from(context.agent_input)
        source_packet = {
            "goal": _unindexed_goal(intake, documents),
            "source_documents": source_segments_for_model(documents),
            "answers": context.agent_input.get("answers", {}),
            "question_history": [event.model_dump(mode="json") for event in question_events],
            "prior_memory": context.agent_input.get("prior_memory", {}),
        }

        system_prompt, task_prompt, version, manifest = build_instructions(
            operation="understand_and_question",
            source_packet=source_packet,
        )

        def validate(parsed: dict[str, Any]) -> None:
            closed_gaps = {
                event.gap_id
                for event in question_events
                if event.gap_id and event.status != "pending"
            }
            questions = parsed.get("questions")
            if isinstance(questions, list):
                for question in questions:
                    if not isinstance(question, dict) or question.get("gap_id"):
                        continue
                    normalized_text = " ".join(str(question.get("text", "")).casefold().split())
                    question["gap_id"] = (
                        "gap_" + hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()[:16]
                    )
            validation = validate_questions_output(
                parsed,
                self._config.max_questions,
                closed_gap_ids=closed_gaps,
            )
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
                self.key.value, "understand_and_question", manifest, context
            ),
            strict_schema=False,
            validator=validate,
        )

        parsed = _parsed_output(result)
        _normalize_question_choices(parsed)

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
        documents = _source_documents_from(context.agent_input, intake)
        question_events = _question_events_from(context.agent_input)
        answers = context.agent_input.get("answers", {})
        source_packet = {
            "goal": _unindexed_goal(intake, documents),
            "source_documents": source_segments_for_model(documents),
            "answers": answers,
            "question_history": [event.model_dump(mode="json") for event in question_events],
            "prior_memory": context.agent_input.get("prior_memory", {}),
            "existing_brief": str(context.agent_input.get("existing_brief", "") or ""),
            "revision_request": str(context.agent_input.get("revision_request", "") or ""),
        }

        system_prompt, task_prompt, version, manifest = build_instructions(
            operation="build_or_revise_brief",
            source_packet=source_packet,
        )

        def validate(parsed: dict[str, Any]) -> None:
            _normalize_dossier_links(parsed)
            _normalize_dossier_lineage(parsed, documents, question_events)
            validation = validate_brief_output(parsed, documents)
            if not validation.is_valid:
                logger.warning(
                    "Discovery brief validation rejected response count=%d categories=%s",
                    len(validation.errors),
                    [re.sub(r"'[^']*'", "'<id>'", error) for error in validation.errors[:12]],
                )
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
            request_context=prompt_cache_context(
                self.key.value, "build_or_revise_brief", manifest, context
            ),
            strict_schema=False,
            validator=validate,
        )

        parsed = _parsed_output(result)

        logger.info(
            "build_or_revise_brief produced %d chars of markdown",
            len(parsed.get("brief_markdown", "")),
        )

        dossier = DiscoveryDossier.model_validate(parsed["dossier"])
        profile = _profile_from_dossier(dossier)

        return AgentResult(
            output={
                "operation": "build_or_revise_brief",
                "mode": OperationMode.BRIEF_READY.value,
                "assistant_message": str(parsed.get("assistant_message", "") or ""),
                "brief_title": str(parsed.get("brief_title", "") or ""),
                "brief_markdown": str(parsed.get("brief_markdown", "") or ""),
                "user_summary": str(parsed.get("user_summary", "") or ""),
                "profile": profile.model_dump(mode="json"),
                "dossier": dossier.model_dump(mode="json"),
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
            "source_text": str(raw.get("source_text", "") or ""),
        }


def _parsed_output(result: StructuredModelResult) -> dict[str, Any]:
    if isinstance(result, StructuredModelResult):
        return result.parsed_output
    return dict(result.parsed_output)


def _normalize_question_choices(parsed: dict[str, Any]) -> None:
    """Keep exactly three suggestions, or use free text when fewer are usable."""
    questions = parsed.get("questions")
    if not isinstance(questions, list):
        return
    for question in questions:
        if not isinstance(question, dict):
            continue
        if question.get("kind") not in {"single_select", "multi_select"}:
            continue
        options = question.get("options")
        if not isinstance(options, list):
            continue
        if len(options) < 3:
            question["kind"] = "text"
            question["options"] = []
        elif len(options) > 3:
            question["options"] = options[:3]


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


def _source_documents_from(
    agent_input: dict[str, Any], intake: dict[str, Any]
) -> list[SourceDocument]:
    raw_documents = agent_input.get("source_documents", [])
    if isinstance(raw_documents, list) and (raw_documents or "source_documents" in agent_input):
        return [SourceDocument.model_validate(item) for item in raw_documents]
    from oryxenai.agents.discovery.sources import documents_from_intake

    return documents_from_intake(intake)


def _question_events_from(agent_input: dict[str, Any]) -> list[QuestionHistoryEvent]:
    raw_events = agent_input.get("question_events", [])
    if not isinstance(raw_events, list):
        return []
    return [QuestionHistoryEvent.model_validate(item) for item in raw_events]


def _unindexed_goal(intake: dict[str, Any], documents: list[SourceDocument]) -> str:
    if any(document.source_kind == "user_intent" for document in documents):
        return ""
    return str(intake.get("goal", "") or "")


def _normalize_dossier_lineage(
    parsed: dict[str, Any],
    documents: list[SourceDocument],
    question_events: list[QuestionHistoryEvent],
) -> None:
    """Set immutable provenance metadata from server-held snapshots, never model guesses."""

    raw_dossier = parsed.get("dossier")
    if not isinstance(raw_dossier, dict):
        return
    lineage = raw_dossier.get("lineage")
    if not isinstance(lineage, dict):
        lineage = {}
        raw_dossier["lineage"] = lineage
    lineage.update(
        {
            "version": 1,
            "schema_version": "DiscoveryDossier/v1",
            "provenance_status": "source_indexed" if documents else "unverified_legacy",
            "source_document_ids": [document.id for document in documents],
            "source_hashes": [document.sha256 for document in documents],
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    raw_dossier["contract_version"] = "DiscoveryDossier/v1"
    if not raw_dossier.get("id"):
        raw_dossier["id"] = f"dossier_{uuid4().hex}"
    raw_dossier["question_events"] = [event.model_dump(mode="json") for event in question_events]
    canonical = json.dumps(
        {key: value for key, value in raw_dossier.items() if key != "lineage"},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    lineage["payload_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_dossier_links(parsed: dict[str, Any]) -> None:
    """Repair mechanical cross-links without changing the model's claims."""
    dossier = parsed.get("dossier")
    if not isinstance(dossier, dict):
        return
    facts = dossier.get("facts")
    coverage = dossier.get("source_coverage")
    if not isinstance(facts, list) or not isinstance(coverage, list):
        return
    fact_refs: dict[str, list[str]] = {}
    span_facts: dict[str, list[str]] = {}
    for fact in facts:
        if not isinstance(fact, dict) or not isinstance(fact.get("id"), str):
            continue
        refs = fact.get("source_refs")
        if not isinstance(refs, list):
            continue
        fact_id = fact["id"]
        fact_refs[fact_id] = [ref for ref in refs if isinstance(ref, str)]
        for ref in fact_refs[fact_id]:
            span_facts.setdefault(ref, []).append(fact_id)
    for key in ("roles", "projects", "other_evidence"):
        entities = dossier.get(key)
        if not isinstance(entities, list):
            continue
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            ids = entity.get("fact_ids")
            refs = entity.get("source_refs")
            if not isinstance(ids, list) or not isinstance(refs, list):
                continue
            entity["source_refs"] = list(
                dict.fromkeys(
                    [*refs, *(ref for fact_id in ids for ref in fact_refs.get(fact_id, []))]
                )
            )
    for item in coverage:
        if not isinstance(item, dict):
            continue
        span_id = item.get("span_id")
        if not isinstance(span_id, str):
            continue
        cited = span_facts.get(span_id, [])
        if cited:
            item["disposition"] = "fact"
            item["fact_ids"] = list(dict.fromkeys(cited))
        elif item.get("disposition") == "fact":
            # The model labeled this passage as factual but supplied no
            # supported fact. Keep it visible as an open source item rather
            # than dropping the passage or asserting an ungrounded claim.
            item["disposition"] = "reference_context"
            item["fact_ids"] = []
            open_items = dossier.setdefault("open_items", [])
            if isinstance(open_items, list) and not any(
                isinstance(open_item, dict) and span_id in open_item.get("source_refs", [])
                for open_item in open_items
            ):
                open_items.append(
                    {
                        "id": f"open_source_{hashlib.sha256(span_id.encode()).hexdigest()[:12]}",
                        "detail": "A supplied passage needs review before it is used as a factual claim.",
                        "importance": "context",
                        "status": "open",
                        "source_refs": [span_id],
                    }
                )


def _profile_from_dossier(dossier: DiscoveryDossier) -> StructuredProfile:
    """Project only source-linked dossier facts into the legacy CA profile shape."""

    facts_by_id = {fact.id: fact for fact in dossier.facts}
    experience = [
        ExperienceEntry(
            organization=role.organization,
            role=role.role,
            dates=role.dates,
            highlights=[
                _qualified_fact(facts_by_id[fact_id])
                for fact_id in role.fact_ids
                if fact_id in facts_by_id
            ]
            or role.details,
        )
        for role in dossier.roles
    ]
    projects = [
        ProjectEntry(
            name=project.name,
            summary=project.problem,
            contribution=project.personal_contribution,
            tech=project.tools,
            link=project.links[0] if project.links else "",
        )
        for project in dossier.projects
    ]
    education: list[EducationEntry] = []
    skills: list[str] = []
    languages: list[str] = []
    for evidence in dossier.other_evidence:
        category = evidence.category.casefold()
        value = evidence.title or evidence.detail
        if category in {"education", "certification"}:
            education.append(
                EducationEntry(
                    institution=evidence.title if category == "education" else "",
                    credential=evidence.detail or evidence.title,
                )
            )
        elif category in {"skill", "tool", "technology"} and value:
            skills.append(value)
        elif category in {"language", "spoken_language"} and value:
            languages.append(value)
    private_omitted = [
        restriction.instruction
        for restriction in dossier.restrictions
        if restriction.disposition.casefold() in {"omit", "generalize", "restricted"}
        and restriction.instruction
    ]
    return StructuredProfile(
        name=dossier.subject.name,
        current_title=dossier.subject.current_title,
        location=dossier.subject.location,
        links=dossier.subject.links,
        experience=experience,
        education=education,
        projects=projects,
        skills=list(dict.fromkeys(skills)),
        spoken_languages=list(dict.fromkeys(languages)),
        private_omitted=private_omitted,
    )


def _qualified_fact(fact: Any) -> str:
    statement = str(fact.statement)
    if fact.ownership.value == "team":
        return f"Team contribution: {statement}"
    if fact.ownership.value == "unknown":
        return f"Attribution not specified: {statement}"
    return statement
