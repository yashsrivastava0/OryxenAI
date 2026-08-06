"""Application service for the durable Discovery workflow."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, NoReturn
from uuid import UUID, uuid4

from pydantic import ValidationError as PydanticValidationError

from oryxenai.agents.discovery.ids import (
    answer_snapshot_hash,
    brief_hash,
    conflict_id,
    fact_id,
    operation_idempotency_key,
    question_id,
    source_snapshot_id,
)
from oryxenai.agents.discovery.preprocessing import (
    compute_source_hash,
    normalize_url,
    preprocess_text,
)
from oryxenai.agents.discovery.schemas import (
    AnswerMode,
    BriefEditRecord,
    DiscoveryAnalysisResult,
    DiscoveryAnswer,
    DiscoveryBrief,
    DiscoveryIntake,
    DiscoveryProductConstraints,
    DiscoveryQuestion,
    DiscoveryStatus,
    ResumeSource,
)
from oryxenai.agents.discovery.state import (
    apply_answer_edit,
    apply_answers_in_progress,
    apply_approval,
    apply_brief_edit,
    apply_brief_queued,
    apply_questions_queued,
    apply_source_edit,
)
from oryxenai.agents.discovery.validators import validate_answers, validate_call_b_result
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.discovery import DiscoveryRepository
from oryxenai.jobs.service import JobService


class DiscoveryOperationError(Exception):
    """Safe, transport-neutral error raised by the Discovery service."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 409,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def assign_stable_analysis_ids(analysis: DiscoveryAnalysisResult) -> DiscoveryAnalysisResult:
    """Replace model-provided local identifiers with deterministic app IDs."""
    data = analysis.model_dump(mode="json")
    facts = data.get("facts") or data.get("fact_candidates") or []
    fact_map: dict[str, str] = {}
    for fact in facts:
        old = str(fact.get("local_key", ""))
        value = fact.get("normalized_value")
        if value is None:
            value = fact.get("value")
        refs = [str(item.get("source_id", "")) for item in fact.get("evidence", [])]
        fact_map[old] = fact_id(
            str(fact.get("category", "other")),
            str(fact.get("field", "")),
            value,
            refs,
        )

    conflict_map: dict[str, str] = {}
    for conflict in data["conflicts"]:
        old = str(conflict.get("local_key", ""))
        alternatives = [str(item.get("value")) for item in conflict.get("alternatives", [])]
        conflict_map[old] = conflict_id(str(conflict.get("field", "")), alternatives)

    for fact in facts:
        fact["local_key"] = fact_map.get(str(fact.get("local_key", "")), fact["local_key"])
    for conflict in data["conflicts"]:
        old = str(conflict.get("local_key", ""))
        conflict["local_key"] = conflict_map.get(old, old)

    for question in data["questions"]:
        old = str(question.get("local_key", ""))
        related = [
            fact_map.get(str(key), str(key)) for key in question.get("related_fact_keys", [])
        ]
        conflicts = [
            conflict_map.get(str(key), str(key))
            for key in question.get("resolves_conflict_keys", [])
        ]
        question["related_fact_keys"] = related
        question["resolves_conflict_keys"] = conflicts
        question["local_key"] = question_id(
            str(question.get("category", "other")),
            related + conflicts + [old],
            1,
        )

    _remap_references(data, fact_map, conflict_map)
    return DiscoveryAnalysisResult.model_validate(data)


def _remap_references(
    value: Any,
    fact_map: dict[str, str],
    conflict_map: dict[str, str],
    key: str = "",
) -> None:
    """Recursively remap fact/conflict IDs in every reference position.

    Covers all v2 reference fields (fact_ids, supporting_fact_ids,
    basis_fact_ids, related_fact_ids, must_use_fact_ids, evidence_to_preserve,
    related_fact_keys, resolves_conflict_keys, ...) by remapping any string
    that matches a known old identifier, regardless of the containing key.
    """
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            if isinstance(child_value, str):
                if child_key in {"fact_key", "conflict_key"}:
                    value[child_key] = fact_map.get(child_value, child_value)
                else:
                    value[child_key] = _remap_string_references(child_value, fact_map, conflict_map)
            else:
                _remap_references(child_value, fact_map, conflict_map, child_key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            if isinstance(item, str):
                value[index] = _remap_string_references(item, fact_map, conflict_map)
            else:
                _remap_references(item, fact_map, conflict_map)


def _remap_string_references(
    text: str,
    fact_map: dict[str, str],
    conflict_map: dict[str, str],
) -> str:
    """Remap a string that is either a bare ID or a whitespace-separated ID list."""
    if not text:
        return text
    if text in fact_map:
        return fact_map[text]
    if text in conflict_map:
        return conflict_map[text]
    parts = text.split()
    if any(part in fact_map or part in conflict_map for part in parts):
        return " ".join(fact_map.get(part, conflict_map.get(part, part)) for part in parts)
    return text


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge two dicts, preserving unedited nested brief fields."""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class DiscoveryService:
    """Coordinates Discovery state, immutable inputs, runs, and jobs."""

    def __init__(
        self,
        repository: DiscoveryRepository,
        job_service: JobService,
        agent_registry: Any | None = None,
    ) -> None:
        self._repository = repository
        self._job_service = job_service
        self._agent_registry = agent_registry

        from oryxenai.core.settings import get_settings

        self._config = get_settings().discovery

    async def process_intake(
        self,
        session_id: UUID,
        intake: DiscoveryIntake,
        *,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        session = await self._require_session(session_id)
        if expected_revision is not None and session.revision != expected_revision:
            self._revision_conflict(expected_revision, session.revision)

        if len(intake.links) > self._config.max_links:
            raise DiscoveryOperationError(
                "DISCOVERY_INPUT_INVALID",
                f"At most {self._config.max_links} links are allowed.",
                status_code=400,
            )

        normalized = self._preprocess_intake(intake)
        source_values = {
            "main_prompt": normalized.main_prompt or "",
            "resume_text": normalized.resume_text or "",
            "links": [link.model_dump(mode="json") for link in normalized.links],
        }
        source_hash = compute_source_hash(json.dumps(source_values, sort_keys=True))
        current = await self._repository.get_discovery_state(session_id)
        if current.source_snapshot_hash == source_hash:
            return await self.get_discovery_state(session_id)

        revision = (
            max(
                current.source_revision,
                await self._repository.get_latest_source_revision(session_id),
            )
            + 1
        )
        normalized = normalized.model_copy(update={"source_revision": revision})
        source_id = source_snapshot_id(str(session_id), source_hash)

        metadata: dict[str, object] = {
            "output_language": normalized.output_language,
            "resume_source": normalized.resume_source.value,
            "links": [link.model_dump(mode="json") for link in normalized.links],
            "product_constraints": normalized.product_constraints.model_dump(mode="json"),
        }
        await self._repository.save_source(
            session_id,
            "main_prompt",
            normalized.main_prompt or "",
            compute_source_hash(normalized.main_prompt or ""),
            revision,
            language=normalized.output_language,
            metadata=metadata,
        )
        await self._repository.save_source(
            session_id,
            "resume_text",
            normalized.resume_text or "",
            compute_source_hash(normalized.resume_text or ""),
            revision,
            language=normalized.output_language,
            metadata={"resume_source": normalized.resume_source.value},
        )
        await self._repository.save_source(
            session_id,
            "links",
            json.dumps(metadata["links"], sort_keys=True),
            compute_source_hash(json.dumps(metadata["links"], sort_keys=True)),
            revision,
            language=normalized.output_language,
            metadata={},
        )

        state = apply_source_edit(current)
        state.source_revision = revision
        state.source_snapshot_id = source_id
        state.source_snapshot_hash = source_hash
        updated = await self._repository.save_discovery_state(
            session_id,
            state,
            session.revision if expected_revision is None else expected_revision,
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_discovery_state(session_id)

    async def enqueue_questions(
        self,
        session_id: UUID,
        *,
        expected_revision: int,
        idempotency_key: str | None = None,
        request_id: str = "",
    ) -> dict[str, Any]:
        session = await self._require_session(session_id)
        self._check_revision(session.revision, expected_revision)
        state = await self._repository.get_discovery_state(session_id)
        if state.status in {DiscoveryStatus.QUESTIONS_QUEUED, DiscoveryStatus.QUESTIONS_RUNNING}:
            return await self._operation_response(session_id, session.revision, state, "questions")
        if state.status is not DiscoveryStatus.INPUT_READY:
            self._not_ready("questions", state.status.value)

        intake = await self._load_intake_snapshot(session_id, state.source_revision)
        key = idempotency_key or self._idempotency_key(
            session_id, "prepare_questions", state.source_snapshot_hash or "", ""
        )
        existing_run = await self._repository.find_run_by_idempotency(session_id, key)
        if existing_run is not None:
            existing_hash = existing_run.input_payload.get("source_snapshot_hash")
            if existing_hash != state.source_snapshot_hash:
                raise DiscoveryOperationError(
                    "DISCOVERY_REVISION_CONFLICT",
                    "The idempotency key is already associated with a different source revision.",
                    details={"idempotency_key_reused": True},
                )
            job = await self._job_service.find_idempotent(f"discovery:{session_id}", key)
            return {
                "session_id": str(session_id),
                "session_revision": session.revision,
                "job_id": str(job.id) if job else None,
                "run_id": str(existing_run.id),
                "status": job.status if job else existing_run.status,
            }

        run = AgentRun(
            id=uuid4(),
            portfolio_session_id=session_id,
            agent_key="discovery",
            status="pending",
            input_payload={
                "operation": "prepare_questions",
                "intake": intake.model_dump(mode="json"),
                "source_revision": state.source_revision,
                "source_snapshot_hash": state.source_snapshot_hash,
            },
            state_before=dict(session.current_state),
            idempotency_key=key,
        )
        await self._repository.create_run(run)
        job = await self._job_service.enqueue(
            "discovery.prepare_questions",
            {
                "portfolio_session_id": str(session_id),
                "agent_run_id": str(run.id),
                "expected_session_revision": session.revision + 1,
                "expected_source_revision": state.source_revision,
                "request_id": request_id,
            },
            idempotency_scope=f"discovery:{session_id}",
            idempotency_key=key,
        )
        queued = apply_questions_queued(state, str(run.id), str(job.id))
        updated = await self._repository.save_discovery_state(session_id, queued, session.revision)
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return {
            "session_id": str(session_id),
            "session_revision": updated.revision,
            "job_id": str(job.id),
            "run_id": str(run.id),
            "status": job.status,
        }

    async def save_answers(
        self,
        session_id: UUID,
        answers: list[DiscoveryAnswer],
        *,
        question_version: int,
        complete: bool,
        expected_revision: int,
    ) -> dict[str, Any]:
        session = await self._require_session(session_id)
        self._check_revision(session.revision, expected_revision)
        state = await self._repository.get_discovery_state(session_id)
        if question_version != state.questions.version:
            raise DiscoveryOperationError(
                "DISCOVERY_QUESTIONS_STALE",
                "The question set has changed. Reload the current questions before saving answers.",
                details={"expected_question_version": state.questions.version},
            )
        if state.status not in {
            DiscoveryStatus.QUESTIONS_READY,
            DiscoveryStatus.ANSWERS_IN_PROGRESS,
            DiscoveryStatus.ANSWERS_READY,
            DiscoveryStatus.BRIEF_QUEUED,
            DiscoveryStatus.BRIEF_RUNNING,
            DiscoveryStatus.BRIEF_REVIEW,
            DiscoveryStatus.APPROVED,
        }:
            self._not_ready("answers", state.status.value)

        question_map = {question.local_key: question for question in state.questions.items}
        answer_map: dict[str, DiscoveryAnswer] = {}
        for answer in answers:
            question = question_map.get(answer.question_id)
            if question is None:
                raise DiscoveryOperationError(
                    "DISCOVERY_INPUT_INVALID",
                    f"Answer references unknown question '{answer.question_id}'.",
                    status_code=400,
                )
            self._validate_answer_mode(question, answer)
            if answer.question_id in answer_map:
                raise DiscoveryOperationError(
                    "DISCOVERY_INPUT_INVALID",
                    f"Question '{answer.question_id}' was answered more than once.",
                    status_code=400,
                )
            answer_map[answer.question_id] = answer.model_copy(
                update={"answer_revision": state.answers.revision + 1}
            )

        validation = validate_answers(
            {key: value.model_dump(mode="json") for key, value in answer_map.items()},
            state.questions.items,
            self._config,
        )
        if not validation.is_valid:
            raise DiscoveryOperationError(
                "DISCOVERY_INPUT_INVALID",
                "One or more answers are invalid.",
                status_code=400,
                details={"errors": validation.errors},
            )
        if complete:
            self._validate_complete_answers(answer_map, state.questions.items)

        if state.status in {DiscoveryStatus.BRIEF_REVIEW, DiscoveryStatus.APPROVED}:
            next_state = apply_answer_edit(state)
            if not complete:
                next_state = apply_answers_in_progress(next_state)
        elif state.status in {DiscoveryStatus.QUESTIONS_READY, DiscoveryStatus.ANSWERS_READY}:
            next_state = apply_answers_in_progress(state)
            if complete:
                next_state.status = DiscoveryStatus.ANSWERS_READY
        elif state.status == DiscoveryStatus.ANSWERS_IN_PROGRESS:
            next_state = state.model_copy(deep=True)
            if complete:
                next_state.status = DiscoveryStatus.ANSWERS_READY
        else:
            # BRIEF_QUEUED / BRIEF_RUNNING — documented mid-flight allowance.
            # The durable worker rejects the in-flight brief result via its
            # source/answer revision check, so the answers save is safe.
            next_state = state.model_copy(deep=True)
            next_state.status = (
                DiscoveryStatus.ANSWERS_READY if complete else DiscoveryStatus.ANSWERS_IN_PROGRESS
            )
        next_state.answers.revision += 1
        next_state.answers.question_version = question_version
        next_state.answers.items = answer_map
        next_state.brief.generated_from_answer_revision = None
        next_state.brief.approved = None

        updated = await self._repository.save_discovery_state(
            session_id, next_state, session.revision
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_discovery_state(session_id)

    async def enqueue_brief(
        self,
        session_id: UUID,
        *,
        expected_revision: int,
        idempotency_key: str | None = None,
        request_id: str = "",
    ) -> dict[str, Any]:
        session = await self._require_session(session_id)
        self._check_revision(session.revision, expected_revision)
        state = await self._repository.get_discovery_state(session_id)
        if state.status in {DiscoveryStatus.BRIEF_QUEUED, DiscoveryStatus.BRIEF_RUNNING}:
            return await self._operation_response(session_id, session.revision, state, "brief")
        if state.status not in {DiscoveryStatus.ANSWERS_READY, DiscoveryStatus.BRIEF_REVIEW}:
            self._not_ready("brief", state.status.value)
        analysis_run_id = state.questions.run_id
        if not analysis_run_id:
            raise DiscoveryOperationError(
                "DISCOVERY_NOT_READY", "A completed question analysis is required first."
            )
        analysis_run = await self._repository.get_run(UUID(analysis_run_id))
        if analysis_run is None or not analysis_run.output_payload:
            raise DiscoveryOperationError(
                "DISCOVERY_NOT_READY", "The question analysis result is unavailable."
            )

        answers_json = {
            key: value.model_dump(mode="json") for key, value in state.answers.items.items()
        }
        answer_hash = answer_snapshot_hash(answers_json)
        key = idempotency_key or self._idempotency_key(
            session_id,
            "build_brief",
            state.source_snapshot_hash or "",
            answer_hash,
        )
        existing_run = await self._repository.find_run_by_idempotency(session_id, key)
        if existing_run is not None:
            if existing_run.input_payload.get("answer_snapshot_hash") != answer_hash:
                raise DiscoveryOperationError(
                    "DISCOVERY_REVISION_CONFLICT",
                    "The idempotency key is already associated with different answers.",
                    details={"idempotency_key_reused": True},
                )
            job = await self._job_service.find_idempotent(f"discovery:{session_id}", key)
            return {
                "session_id": str(session_id),
                "session_revision": session.revision,
                "job_id": str(job.id) if job else None,
                "run_id": str(existing_run.id) if existing_run else None,
                "status": job.status if job else "pending",
            }

        intake = await self._load_intake_snapshot(session_id, state.source_revision)
        run = AgentRun(
            id=uuid4(),
            portfolio_session_id=session_id,
            agent_key="discovery",
            status="pending",
            input_payload={
                "operation": "build_brief",
                "intake": intake.model_dump(mode="json"),
                "analysis_run_id": analysis_run_id,
                "answers": answers_json,
                "source_revision": state.source_revision,
                "answer_revision": state.answers.revision,
                "answer_snapshot_hash": answer_hash,
            },
            state_before=dict(session.current_state),
            idempotency_key=key,
        )
        await self._repository.create_run(run)
        job = await self._job_service.enqueue(
            "discovery.build_brief",
            {
                "portfolio_session_id": str(session_id),
                "agent_run_id": str(run.id),
                "analysis_run_id": analysis_run_id,
                "expected_session_revision": session.revision + 1,
                "expected_source_revision": state.source_revision,
                "expected_answer_revision": state.answers.revision,
                "request_id": request_id,
            },
            idempotency_scope=f"discovery:{session_id}",
            idempotency_key=key,
        )
        queued = apply_brief_queued(state, str(run.id), str(job.id))
        updated = await self._repository.save_discovery_state(session_id, queued, session.revision)
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return {
            "session_id": str(session_id),
            "session_revision": updated.revision,
            "job_id": str(job.id),
            "run_id": str(run.id),
            "status": job.status,
        }

    async def edit_brief(
        self,
        session_id: UUID,
        edits: dict[str, Any],
        *,
        expected_revision: int,
        editor_identity: str | None = None,
    ) -> dict[str, Any]:
        session = await self._require_session(session_id)
        self._check_revision(session.revision, expected_revision)
        state = await self._repository.get_discovery_state(session_id)
        if state.status not in {DiscoveryStatus.BRIEF_REVIEW, DiscoveryStatus.APPROVED}:
            self._not_ready("brief edit", state.status.value)
        if state.brief.draft is None:
            raise DiscoveryOperationError(
                "DISCOVERY_BRIEF_STALE", "There is no editable brief draft."
            )

        unknown = set(edits) - set(DiscoveryBrief.model_fields)
        if unknown:
            raise DiscoveryOperationError(
                "DISCOVERY_INPUT_INVALID",
                "The brief edit contains unsupported fields.",
                status_code=400,
                details={"fields": sorted(unknown)},
            )
        old_dump = state.brief.draft.model_dump(mode="json")
        merged = _deep_merge(old_dump, edits)
        try:
            draft = DiscoveryBrief.model_validate(merged)
        except PydanticValidationError as exc:
            raise DiscoveryOperationError(
                "DISCOVERY_INPUT_INVALID",
                "The brief edit is invalid.",
                status_code=400,
                details={"errors": exc.errors(include_url=False)},
            ) from exc

        next_state = apply_brief_edit(state)
        next_state.brief.draft = draft
        now = datetime.now(UTC).isoformat()
        for field, value in edits.items():
            previous = old_dump.get(field)
            if previous != value:
                next_state.brief.edit_history.append(
                    BriefEditRecord(
                        field=field,
                        previous_value=previous,
                        new_value=draft.model_dump(mode="json").get(field),
                        edited_at=now,
                        editor_identity=editor_identity,
                    )
                )
        updated = await self._repository.save_discovery_state(
            session_id, next_state, session.revision
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_discovery_state(session_id)

    async def approve_brief(
        self,
        session_id: UUID,
        *,
        expected_revision: int,
        session_identity: str | None = None,
    ) -> dict[str, Any]:
        session = await self._require_session(session_id)
        self._check_revision(session.revision, expected_revision)
        state = await self._repository.get_discovery_state(session_id)
        if state.status is DiscoveryStatus.APPROVED and state.brief.approved is not None:
            return await self.get_discovery_state(session_id)
        if state.status is not DiscoveryStatus.BRIEF_REVIEW or state.brief.draft is None:
            self._not_ready("approval", state.status.value)
        draft = state.brief.draft
        if state.brief.generated_from_source_revision != state.source_revision or (
            state.brief.generated_from_answer_revision != state.answers.revision
        ):
            raise DiscoveryOperationError(
                "DISCOVERY_APPROVAL_INVALIDATED",
                "This brief is based on an older source or answer revision.",
            )

        analysis_run_id = state.questions.run_id
        analysis = (
            await self._repository.get_run(UUID(analysis_run_id)) if analysis_run_id else None
        )
        analysis_output = (analysis.output_payload or {}).get("analysis", {}) if analysis else {}
        try:
            parsed_analysis = DiscoveryAnalysisResult.model_validate(analysis_output)
            fact_ids = {fact.local_key for fact in parsed_analysis.facts}
            project_ids = {project.title for project in parsed_analysis.normalized_profile.projects}
            validation = validate_call_b_result(
                draft,
                fact_ids,
                project_ids,
                self._config,
            )
        except PydanticValidationError as exc:
            raise DiscoveryOperationError(
                "DISCOVERY_BRIEF_STALE", "The brief can no longer be validated."
            ) from exc
        if not validation.is_valid:
            raise DiscoveryOperationError(
                "DISCOVERY_BRIEF_STALE",
                "The brief contains unsupported or stale references.",
                details={"errors": validation.errors},
            )

        approved = apply_approval(
            state,
            {
                "session_identity": session_identity,
                "run_provenance": {
                    "analysis_run_id": analysis_run_id,
                    "brief_run_id": state.brief.run_id,
                    "brief_hash": brief_hash(draft),
                },
            },
        )
        updated = await self._repository.save_discovery_state(
            session_id, approved, session.revision
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_discovery_state(session_id)

    async def get_discovery_state(self, session_id: UUID) -> dict[str, Any]:
        session = await self._require_session(session_id)
        state = await self._repository.get_discovery_state(session_id)
        intake: dict[str, Any] | None = None
        if state.source_revision:
            try:
                intake = (
                    await self._load_intake_snapshot(session_id, state.source_revision)
                ).model_dump(mode="json")
            except (LookupError, PydanticValidationError, ValueError):
                intake = None
        analysis: dict[str, Any] | None = None
        if state.questions.run_id:
            run = await self._repository.get_run(UUID(state.questions.run_id))
            if run and run.output_payload:
                raw = run.output_payload.get("analysis")
                if isinstance(raw, dict):
                    analysis = self._safe_analysis(raw)

        jobs: list[dict[str, Any]] = []
        for job_id in (state.questions.job_id, state.brief.job_id):
            if job_id:
                try:
                    job = await self._job_service.get(UUID(job_id))
                except Exception:
                    job = None
                if job is not None:
                    jobs.append(
                        {
                            "id": str(job.id),
                            "kind": job.job_kind,
                            "status": job.status,
                            "attempt": job.attempt,
                            "error": job.error_payload,
                        }
                    )
        return {
            "session_id": str(session_id),
            "session_revision": session.revision,
            "discovery": state.model_dump(mode="json"),
            "intake": intake,
            "analysis": analysis,
            "jobs": jobs,
        }

    async def _operation_response(
        self,
        session_id: UUID,
        session_revision: int,
        state: Any,
        operation: str,
    ) -> dict[str, Any]:
        job_id = state.questions.job_id if operation == "questions" else state.brief.job_id
        run_id = state.questions.run_id if operation == "questions" else state.brief.run_id
        job = await self._job_service.get(UUID(job_id)) if job_id else None
        return {
            "session_id": str(session_id),
            "session_revision": session_revision,
            "job_id": job_id,
            "run_id": run_id,
            "status": job.status if job else state.status.value,
        }

    async def _require_session(self, session_id: UUID) -> Any:
        session = await self._repository.get_session(session_id)
        if session is None:
            raise DiscoveryOperationError(
                "SESSION_NOT_FOUND", "Portfolio session was not found.", status_code=404
            )
        return session

    def _preprocess_intake(self, intake: DiscoveryIntake) -> DiscoveryIntake:
        if intake.main_prompt and len(intake.main_prompt) > self._config.max_main_prompt_chars:
            raise DiscoveryOperationError(
                "DISCOVERY_SOURCE_TOO_LARGE",
                "The main prompt exceeds the configured limit.",
                status_code=422,
            )
        if intake.resume_text and len(intake.resume_text) > self._config.max_resume_chars * 2:
            raise DiscoveryOperationError(
                "DISCOVERY_SOURCE_TOO_LARGE",
                "The resume text exceeds the configured input limit.",
                status_code=422,
            )
        prompt, _ = preprocess_text(intake.main_prompt or "", self._config.max_main_prompt_chars)
        resume, _ = preprocess_text(intake.resume_text or "", self._config.max_resume_chars)
        seen: set[str] = set()
        links = []
        for link in intake.links:
            url = normalize_url(str(link.url))
            if url in seen:
                continue
            seen.add(url)
            links.append(link.model_copy(update={"url": url}))
        return intake.model_copy(
            update={"main_prompt": prompt, "resume_text": resume, "links": links}
        )

    async def _load_intake_snapshot(self, session_id: UUID, revision: int) -> DiscoveryIntake:
        sources = await self._repository.get_sources_at_revision(session_id, revision)
        by_kind = {source.source_kind: source for source in sources}
        main = by_kind.get("main_prompt")
        resume = by_kind.get("resume_text")
        links_source = by_kind.get("links")
        metadata = dict(main.source_metadata) if main is not None else {}
        try:
            links = json.loads(links_source.content) if links_source else []
        except json.JSONDecodeError:
            links = []
        constraints = metadata.get("product_constraints", {})
        if not isinstance(constraints, dict):
            constraints = {}
        return DiscoveryIntake(
            main_prompt=main.content if main else None,
            resume_text=resume.content if resume and resume.content else None,
            resume_source=ResumeSource(str(metadata.get("resume_source", "none"))),
            links=links,
            output_language=str(metadata.get("output_language", "en")),
            product_constraints=DiscoveryProductConstraints.model_validate(constraints),
            source_revision=revision,
        )

    def _validate_answer_mode(self, question: DiscoveryQuestion, answer: DiscoveryAnswer) -> None:
        if answer.mode is AnswerMode.AUTO and not question.allows_auto:
            raise DiscoveryOperationError(
                "DISCOVERY_INPUT_INVALID",
                f"Automatic selection is not allowed for '{question.local_key}'.",
                status_code=400,
            )
        if answer.mode is AnswerMode.SKIPPED and not question.allows_skip:
            raise DiscoveryOperationError(
                "DISCOVERY_INPUT_INVALID",
                f"Question '{question.local_key}' cannot be skipped.",
                status_code=400,
            )
        if question.kind.value == "single_select" and answer.mode is AnswerMode.ANSWERED:
            valid = {option.id for option in question.options}
            if answer.value not in valid:
                raise DiscoveryOperationError(
                    "DISCOVERY_INPUT_INVALID",
                    f"Answer for '{question.local_key}' is not one of its options.",
                    status_code=400,
                )
        if question.kind.value == "multi_select" and answer.mode is AnswerMode.ANSWERED:
            valid = {option.id for option in question.options}
            if not isinstance(answer.value, list) or not set(answer.value).issubset(valid):
                raise DiscoveryOperationError(
                    "DISCOVERY_INPUT_INVALID",
                    f"Answer for '{question.local_key}' contains an invalid option.",
                    status_code=400,
                )

    def _validate_complete_answers(
        self,
        answers: dict[str, DiscoveryAnswer],
        questions: list[DiscoveryQuestion],
    ) -> None:
        missing = [
            question.local_key
            for question in questions
            if question.required and question.local_key not in answers and not question.allows_skip
        ]
        if missing:
            raise DiscoveryOperationError(
                "DISCOVERY_INPUT_INVALID",
                "Required questions still need an answer or an allowed skip.",
                status_code=400,
                details={"question_ids": missing},
            )

    def _idempotency_key(
        self,
        session_id: UUID,
        operation: str,
        source_hash: str,
        answer_hash: str,
    ) -> str:
        from oryxenai.agents.discovery.prompt_builder import get_prompt_version
        from oryxenai.core.settings import get_settings

        profile = get_settings().models.get_profile("discovery")
        model_profile = f"{profile.provider}:{profile.model}" if profile else "discovery"
        return operation_idempotency_key(
            str(session_id),
            operation,
            source_hash,
            answer_hash,
            get_prompt_version(operation),
            model_profile,
        )

    def _safe_analysis(self, raw: dict[str, Any]) -> dict[str, Any]:
        safe = json.loads(json.dumps(raw, default=str))
        facts = safe.get("facts") or safe.get("fact_candidates", [])
        for fact in facts:
            for evidence in fact.get("evidence", []):
                excerpt = evidence.get("evidence_excerpt")
                if isinstance(excerpt, str):
                    evidence["evidence_excerpt"] = excerpt[:160]
        return {
            "source_assessment": safe.get("source_assessment", {}),
            "profile_overview": safe.get("profile_overview", {}),
            "normalized_profile": safe.get("normalized_profile", {}),
            "facts": facts,
            "conflicts": safe.get("conflicts", []),
            "uncertainties": safe.get("uncertainties", []),
            "input_warnings": safe.get("input_warnings", []),
        }

    def _check_revision(self, actual: int, expected: int) -> None:
        if actual != expected:
            self._revision_conflict(expected, actual)

    def _revision_conflict(self, expected: int, actual: int) -> NoReturn:
        raise DiscoveryOperationError(
            "DISCOVERY_REVISION_CONFLICT",
            "The session changed while this request was being processed. Reload and try again.",
            details={"expected_revision": expected, "actual_revision": actual},
        )

    def _not_ready(self, operation: str, status: str) -> NoReturn:
        raise DiscoveryOperationError(
            "DISCOVERY_NOT_READY",
            f"Discovery is not ready to {operation} from state '{status}'.",
            details={"status": status},
        )
