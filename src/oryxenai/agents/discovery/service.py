"""Application service for Explorer source collection, interview, and review.

The service persists immutable text snapshots, schedules one contextual question
batch, and requires approval of the resulting brief.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, NoReturn
from uuid import UUID, uuid4

from oryxenai.agents.discovery.palette import (
    PALETTE_GAP_ID,
    PALETTE_TO_THEME,
    WORK_GAP_ID,
    atlas_work_answer,
    atlas_work_question,
    palette_answer,
    palette_question,
)
from oryxenai.agents.discovery.schemas import (
    AnswerMode,
    DiscoveryAnswer,
    DiscoveryIntake,
    DiscoveryQuestion,
    DiscoveryState,
    DiscoveryStatus,
    QuestionAnswerRevision,
    QuestionHistoryEvent,
    QuestionKind,
    SourceDocument,
)
from oryxenai.agents.discovery.sources import (
    create_source_document,
    document_from_answer,
)
from oryxenai.agents.discovery.state import (
    apply_answers_in_progress,
    apply_approval,
    apply_brief_running,
    apply_needs_attention,
    apply_start,
)
from oryxenai.agents.shared.agent_output import public_discovery_outputs
from oryxenai.agents.shared.job_status import public_job_status
from oryxenai.agents.shared.model_router import ModelRouter
from oryxenai.agents.shared.observability import frontend_cache_receipt
from oryxenai.auth.authorization import durable_snapshot_for_session
from oryxenai.core.logging import get_logger
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.discovery import DiscoveryRepository
from oryxenai.jobs.contracts import JobStatus
from oryxenai.jobs.service import JobService

logger = get_logger("oryxenai.agents.discovery.service")


class DiscoveryOperationError(Exception):
    """Safe, transport-neutral error raised by the Explorer service."""

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


class DiscoveryService:
    """Coordinates Explorer state, runs, and jobs."""

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

        self._settings = get_settings()

    async def start(
        self,
        session_id: UUID,
        message: str,
        document_text: str,
        goal: str,
        *,
        source_text: str = "",
        document_name: str = "",
        model_profile: str = "",
        request_id: str = "",
    ) -> dict[str, Any]:
        """Store the raw input and enqueue the understand_and_question job.

        Restarting from NEEDS_INPUT lets the user add more material without
        discarding the source snapshots already collected.
        """
        session = await self._require_session(session_id)
        state = await self._repository.get_discovery_state(session_id)

        state = await self._recover_failed_question_job(state)
        if (
            sum(len(value or "") for value in (message, document_text, goal, source_text))
            > self._settings.discovery.max_input_chars
        ):
            raise DiscoveryOperationError(
                "DISCOVERY_INPUT_TOO_LARGE",
                "The supplied material is too long. Shorten it and try again.",
                status_code=413,
            )

        if state.status not in {
            DiscoveryStatus.NOT_STARTED,
            DiscoveryStatus.QUESTIONS_READY,
            DiscoveryStatus.NEEDS_INPUT,
            DiscoveryStatus.NEEDS_ATTENTION,
        }:
            return await self.get_discovery_state(session_id)

        resolved_profile = self._resolve_model_profile(model_profile, state.model_profile)
        policy_snapshot = self._current_routing_policy_snapshot()

        submitted = DiscoveryIntake(
            message=message,
            document_text=document_text,
            document_name=document_name,
            goal=goal,
            source_text=source_text,
        )
        intake, added_documents = _merge_intake(state.intake, submitted)
        source_documents = [*state.source_documents, *added_documents]
        intake_payload = intake.model_dump(mode="json")
        # A browser retry can arrive after the first job has already finished
        # but before the client received its response.  The deterministic
        # idempotency key intentionally identifies that exact request, so
        # return the persisted result instead of attempting a duplicate
        # AgentRun insert (and, more importantly, another model call).
        if (
            state.status in {DiscoveryStatus.QUESTIONS_READY, DiscoveryStatus.NEEDS_INPUT}
            and state.operation_a.run_id
            and state.intake == intake
            and state.model_profile == resolved_profile
        ):
            return await self.get_discovery_state(session_id)
        retry_nonce: int | str
        if state.status is DiscoveryStatus.NEEDS_ATTENTION:
            # ``attempt`` is the worker's per-job delivery counter and resets
            # to one every time a user explicitly retries a failed run.  It
            # therefore cannot identify a new logical retry on its own: a
            # second manual retry would recreate the previous AgentRun's
            # idempotency key and hit ``ux_agent_runs_idempotency``.  The
            # previous Operation A run id advances whenever a retry is
            # accepted, so use it as the stable nonce for this retry variant.
            # Keep the numeric fallback for legacy/corrupt state with no run
            # identity rather than making an otherwise recoverable retry
            # fail during key construction.
            retry_nonce = (
                state.operation_a.run_id or state.brief.run_id or f"attempt-{state.attempt}"
            )
        elif state.status is DiscoveryStatus.QUESTIONS_READY:
            retry_nonce = state.attempt + 1
        else:
            retry_nonce = 0
        key = self._idempotency_key(
            session_id,
            "understand_and_question",
            intake_payload,
            {},
            memory=state.memory,
            question_events=[event.model_dump(mode="json") for event in state.question_events],
            retry_nonce=retry_nonce,
        )

        run = AgentRun(
            id=uuid4(),
            agent_key="discovery",
            status="pending",
            input_payload={
                "operation": "understand_and_question",
                "intake": intake_payload,
                "source_documents": [doc.model_dump(mode="json") for doc in source_documents],
                "answers": {
                    qid: answer.model_dump(mode="json")
                    for qid, answer in state.answers.items.items()
                },
                "question_events": [
                    event.model_dump(mode="json") for event in state.question_events
                ],
                "prior_memory": state.memory,
                "model_profile": resolved_profile,
                "input_classification": "personal",
                "routing_policy_snapshot": policy_snapshot,
            },
            state_before=dict(session.current_state),
            idempotency_key=key,
            **durable_snapshot_for_session(self._job_service.authorization_context, session_id),
        )
        await self._repository.create_run(run)
        job = await self._job_service.enqueue(
            "discovery.understand_and_question",
            {
                "portfolio_session_id": str(session_id),
                "agent_run_id": str(run.id),
                "expected_session_revision": session.revision + 1,
                "request_id": request_id,
            },
            idempotency_scope=f"discovery:{session_id}",
            idempotency_key=key,
            max_attempts=self._settings.worker_retry.agent_job_max_attempts,
        )

        queued = apply_start(state)
        queued.intake = intake
        queued.source_documents = source_documents
        queued.model_profile = resolved_profile
        queued.routing_policy_version = str(policy_snapshot["version"])
        queued.routing_policy_fingerprint = str(policy_snapshot["fingerprint"])
        queued.operation_a.run_id = str(run.id)
        queued.operation_a.job_id = str(job.id)
        queued.attempt = 0
        queued.max_attempts = self._settings.worker_retry.agent_job_max_attempts
        updated = await self._repository.save_discovery_state(session_id, queued, session.revision)
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_discovery_state(session_id)

    async def save_answers(
        self,
        session_id: UUID,
        answers: list[DiscoveryAnswer],
        *,
        complete: bool,
        continue_with_current_information: bool = False,
        request_id: str = "",
    ) -> dict[str, Any]:
        """Save answers and prepare the brief when the batch is complete."""
        session = await self._require_session(session_id)
        state = await self._repository.get_discovery_state(session_id)
        state = await self._recover_failed_question_job(state)
        state = _refresh_open_palette(state)
        if state.status not in {
            DiscoveryStatus.QUESTIONS_READY,
            DiscoveryStatus.ANSWERS_IN_PROGRESS,
            DiscoveryStatus.NEEDS_ATTENTION,
        }:
            self._not_ready("save answers", state.status.value)

        active_questions = {item.id: item for item in state.operation_a.items}
        seen_question_ids: set[str] = set()
        for answer in answers:
            if len(str(answer.value or "")) > self._settings.discovery.max_answer_chars:
                raise DiscoveryOperationError(
                    "DISCOVERY_ANSWER_TOO_LARGE",
                    "An answer is too long. Shorten it and try again.",
                    status_code=413,
                )
            question_id = answer.question_id
            if not question_id or question_id not in active_questions:
                raise DiscoveryOperationError(
                    "DISCOVERY_INVALID_ANSWER",
                    "Answer refers to a question outside the current round.",
                    status_code=400,
                )
            if question_id in seen_question_ids:
                raise DiscoveryOperationError(
                    "DISCOVERY_INVALID_ANSWER",
                    "Submit each question at most once per request.",
                    status_code=400,
                )
            seen_question_ids.add(question_id)
            if answer.mode is AnswerMode.ANSWERED and not _has_answer_value(answer.value):
                raise DiscoveryOperationError(
                    "DISCOVERY_INVALID_ANSWER",
                    "An answered question needs a response; use Skip instead.",
                    status_code=400,
                )
            question = active_questions[question_id]
            if question.kind is QuestionKind.PALETTE_SELECT:
                if answer.mode is not AnswerMode.ANSWERED or palette_answer(answer.value) is None:
                    raise DiscoveryOperationError(
                        "DISCOVERY_INVALID_ANSWER",
                        "Choose one of the visual palettes before continuing.",
                        status_code=400,
                    )
                continue
            if question.kind is QuestionKind.WORK_DETAIL:
                if answer.mode is AnswerMode.ANSWERED and atlas_work_answer(answer.value) is None:
                    raise DiscoveryOperationError(
                        "DISCOVERY_INVALID_ANSWER",
                        "Share project details or choose the illustrative concept option.",
                        status_code=400,
                    )
                continue
            if answer.mode is AnswerMode.ANSWERED and not (
                isinstance(answer.value, str)
                or (question.kind is QuestionKind.MULTI_SELECT and isinstance(answer.value, list))
            ):
                raise DiscoveryOperationError(
                    "DISCOVERY_INVALID_ANSWER",
                    "Answer must be text or selected options from the current question.",
                    status_code=400,
                )
            if answer.mode is AnswerMode.ANSWERED and isinstance(answer.value, list):
                option_ids = {option.id for option in question.options}
                selected = answer.value
                if (
                    question.kind is not QuestionKind.MULTI_SELECT
                    or any(not isinstance(item, str) or item not in option_ids for item in selected)
                    or len(set(selected)) != len(selected)
                ):
                    raise DiscoveryOperationError(
                        "DISCOVERY_INVALID_ANSWER",
                        "Selected options must be unique choices from the current question.",
                        status_code=400,
                    )

        answer_map: dict[str, DiscoveryAnswer] = dict(state.answers.items)
        answer_documents: list[SourceDocument] = []
        question_events = [event.model_copy(deep=True) for event in state.question_events]
        next_theme_id = state.selected_theme_id
        allow_illustrative_work = state.allow_illustrative_work
        for answer in answers:
            if answer.question_id:
                previous = answer_map.get(answer.question_id)
                answer_map[answer.question_id] = answer
                question = active_questions[answer.question_id]
                if question.kind is QuestionKind.PALETTE_SELECT:
                    palette_choice = palette_answer(answer.value)
                    assert palette_choice is not None
                    next_theme_id = PALETTE_TO_THEME[palette_choice[0]]
                    if next_theme_id != "cobalt-atlas/v2":
                        allow_illustrative_work = False
                elif question.kind is QuestionKind.WORK_DETAIL:
                    work_choice = atlas_work_answer(answer.value)
                    allow_illustrative_work = bool(work_choice and work_choice[1])
                event = next(
                    (item for item in question_events if item.question_id == answer.question_id),
                    None,
                )
                if event is not None:
                    changed = previous != answer or event.status == "pending"
                    if answer.mode is AnswerMode.SKIPPED:
                        event.status = "skipped"
                        event.answer = ""
                        event.answer_source_refs = []
                        if changed:
                            event.answer_history.append(
                                QuestionAnswerRevision(
                                    revision=len(event.answer_history) + 1,
                                    status="skipped",
                                    recorded_at=datetime.now(UTC).isoformat(),
                                )
                            )
                    else:
                        answer_text = _answer_text(answer.value, question)
                        event.status = "answered"
                        event.answer = answer_text
                        if changed:
                            event.answer_source_refs = []
                            if question.kind is QuestionKind.PALETTE_SELECT:
                                answer_document = None
                            elif question.kind is QuestionKind.WORK_DETAIL:
                                work_answer = atlas_work_answer(answer.value)
                                answer_document = (
                                    document_from_answer(answer.question_id, work_answer[0])
                                    if work_answer and work_answer[0]
                                    else None
                                )
                            else:
                                answer_document = document_from_answer(
                                    answer.question_id, answer_text
                                )
                            if answer_document is not None:
                                answer_documents.append(answer_document)
                                event.answer_source_refs = [
                                    span.id for span in answer_document.spans
                                ]
                            event.answer_history.append(
                                QuestionAnswerRevision(
                                    revision=len(event.answer_history) + 1,
                                    status="answered",
                                    answer=answer_text,
                                    source_refs=event.answer_source_refs,
                                    recorded_at=datetime.now(UTC).isoformat(),
                                )
                            )
        next_state = state.model_copy(deep=True)
        if state.status in {DiscoveryStatus.QUESTIONS_READY, DiscoveryStatus.NEEDS_ATTENTION}:
            next_state = apply_answers_in_progress(state)
        next_state.answers.revision += 1
        next_state.answers.items = answer_map
        next_state.selected_theme_id = next_theme_id
        next_state.allow_illustrative_work = allow_illustrative_work
        next_state.question_events = question_events
        next_state.source_documents.extend(answer_documents)
        next_state.latest_error = None

        # The visual choice is last in the original round. Add one optional,
        # server-authored work question before scheduling the brief.
        if next_theme_id == "cobalt-atlas/v2" and not any(
            item.gap_id == WORK_GAP_ID for item in next_state.operation_a.items
        ):
            work_question = atlas_work_question(f"{next_state.operation_a.run_id}:atlas-work")
            next_state.operation_a.items.append(work_question)
            next_state.question_events.append(
                QuestionHistoryEvent(
                    question_id=work_question.id,
                    gap_id=work_question.gap_id,
                    question=work_question.text,
                    status="pending",
                )
            )
            complete = False

        operation = ""
        if complete:
            if any(
                item.gap_id == WORK_GAP_ID and item.id not in next_state.answers.items
                for item in next_state.operation_a.items
            ):
                raise DiscoveryOperationError(
                    "DISCOVERY_WORK_CHOICE_REQUIRED",
                    "Answer or skip the optional work question before continuing.",
                )
            if (
                any(
                    question.kind is QuestionKind.PALETTE_SELECT
                    for question in active_questions.values()
                )
                and not next_state.selected_theme_id
            ):
                raise DiscoveryOperationError(
                    "DISCOVERY_PALETTE_REQUIRED",
                    "Choose a color direction before preparing the brief.",
                    status_code=409,
                )
            # A fresh user action may follow a routing change. Snapshot the
            # route used by this new job rather than replaying the old one.
            policy_snapshot = self._current_routing_policy_snapshot()
            next_state.routing_policy_version = str(policy_snapshot["version"])
            next_state.routing_policy_fingerprint = str(policy_snapshot["fingerprint"])
            answered_ids = {answer.question_id for answer in answers if answer.question_id}
            for event in next_state.question_events:
                if event.status == "pending" and event.question_id not in answered_ids:
                    event.status = "continued_without_answer"
            operation = "build_or_revise_brief"

        if operation:
            retry_nonce: int | str = 0
            if state.status is DiscoveryStatus.NEEDS_ATTENTION:
                retry_nonce = (
                    state.brief.run_id or state.operation_a.run_id or f"attempt-{state.attempt}"
                )
            run, job = await self._enqueue_followup_run(
                session_id,
                session,
                next_state,
                operation,
                request_id=request_id,
                retry_nonce=retry_nonce,
                revision_request=(
                    state.brief.revision_request
                    if state.status is DiscoveryStatus.NEEDS_ATTENTION and state.brief.markdown
                    else ""
                ),
            )
            if operation == "build_or_revise_brief":
                next_state = apply_brief_running(next_state, str(run.id), str(job.id))
            else:
                next_state = apply_start(next_state)
                next_state.operation_a.run_id = str(run.id)
                next_state.operation_a.job_id = str(job.id)
            next_state.attempt = 0

        updated = await self._repository.save_discovery_state(
            session_id, next_state, session.revision
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_discovery_state(session_id)

    async def _recover_failed_question_job(self, state: DiscoveryState) -> DiscoveryState:
        """A failed legacy job may leave its question state marked as queued."""
        if state.status not in {
            DiscoveryStatus.QUESTIONS_QUEUED,
            DiscoveryStatus.QUESTIONS_RUNNING,
        }:
            return state
        if not state.operation_a.job_id:
            return state
        job = await self._job_service.get(UUID(state.operation_a.job_id))
        if job is None or job.status not in {JobStatus.FAILED.value, JobStatus.CANCELLED.value}:
            return state
        return apply_needs_attention(
            state,
            {
                "code": "DISCOVERY_JOB_FAILED",
                "message": "Explorer can be retried with the saved answers.",
                "retryable": False,
            },
        )

    async def _enqueue_followup_run(
        self,
        session_id: UUID,
        session: Any,
        state: Any,
        operation: str,
        *,
        request_id: str,
        retry_nonce: int | str,
        revision_delta: int = 1,
        revision_request: str = "",
    ) -> tuple[AgentRun, Any]:
        answers = {
            qid: answer.model_dump(mode="json") for qid, answer in state.answers.items.items()
        }
        intake = state.intake.model_dump(mode="json")
        key = self._idempotency_key(
            session_id,
            operation,
            intake,
            answers,
            memory=state.memory,
            question_events=[event.model_dump(mode="json") for event in state.question_events],
            existing_brief=state.brief.markdown,
            revision_request=revision_request,
            retry_nonce=retry_nonce,
        )
        routing_snapshot = {
            "version": state.routing_policy_version,
            "fingerprint": state.routing_policy_fingerprint,
        }
        run = AgentRun(
            id=uuid4(),
            agent_key="discovery",
            status="pending",
            input_payload={
                "operation": operation,
                "intake": intake,
                "source_documents": [
                    document.model_dump(mode="json") for document in state.source_documents
                ],
                "answers": answers,
                "question_events": [
                    event.model_dump(mode="json") for event in state.question_events
                ],
                "prior_memory": state.memory,
                "existing_brief": state.brief.markdown,
                "revision_request": revision_request,
                "model_profile": state.model_profile,
                "input_classification": "personal",
                "routing_policy_snapshot": routing_snapshot,
            },
            state_before=dict(session.current_state),
            idempotency_key=key,
            **durable_snapshot_for_session(self._job_service.authorization_context, session_id),
        )
        await self._repository.create_run(run)
        job = await self._job_service.enqueue(
            f"discovery.{operation}",
            {
                "portfolio_session_id": str(session_id),
                "agent_run_id": str(run.id),
                "expected_session_revision": session.revision + revision_delta,
                "request_id": request_id,
            },
            idempotency_scope=f"discovery:{session_id}",
            idempotency_key=key,
            max_attempts=self._settings.worker_retry.agent_job_max_attempts,
        )
        return run, job

    async def revise_brief(
        self,
        session_id: UUID,
        revision_request: str,
        *,
        request_id: str = "",
    ) -> dict[str, Any]:
        """Re-run Operation B with a natural-language revision request.

        Allowed only while a brief is under review. The state returns to
        BRIEF_RUNNING and then back to BRIEF_REVIEW when the run succeeds.
        """
        session = await self._require_session(session_id)
        state = await self._repository.get_discovery_state(session_id)
        if (
            state.status
            not in {
                DiscoveryStatus.BRIEF_REVIEW,
                DiscoveryStatus.NEEDS_ATTENTION,
            }
            or not state.brief.markdown.strip()
        ):
            self._not_ready("revise", state.status.value)
        revision_request = (revision_request or "").strip()
        if not revision_request:
            raise DiscoveryOperationError(
                "DISCOVERY_NOT_READY", "revision_request is required.", status_code=409
            )
        policy_snapshot = self._current_routing_policy_snapshot()

        key = self._idempotency_key(
            session_id,
            "build_or_revise_brief",
            state.intake.model_dump(mode="json"),
            {qid: answer.model_dump(mode="json") for qid, answer in state.answers.items.items()},
            memory=state.memory,
            question_events=[event.model_dump(mode="json") for event in state.question_events],
            existing_brief=state.brief.markdown,
            revision_request=revision_request,
            retry_nonce=state.attempt,
        )
        run = AgentRun(
            id=uuid4(),
            agent_key="discovery",
            status="pending",
            input_payload={
                "operation": "build_or_revise_brief",
                "intake": state.intake.model_dump(mode="json"),
                "source_documents": [
                    document.model_dump(mode="json") for document in state.source_documents
                ],
                "answers": {
                    qid: answer.model_dump(mode="json")
                    for qid, answer in state.answers.items.items()
                },
                "question_events": [
                    event.model_dump(mode="json") for event in state.question_events
                ],
                "prior_memory": state.memory,
                "existing_brief": state.brief.markdown,
                "revision_request": revision_request,
                "model_profile": state.model_profile,
                "input_classification": "personal",
                "routing_policy_snapshot": policy_snapshot,
            },
            state_before=dict(session.current_state),
            idempotency_key=key,
            **durable_snapshot_for_session(self._job_service.authorization_context, session_id),
        )
        await self._repository.create_run(run)
        job = await self._job_service.enqueue(
            "discovery.build_or_revise_brief",
            {
                "portfolio_session_id": str(session_id),
                "agent_run_id": str(run.id),
                "expected_session_revision": session.revision + 1,
                "request_id": request_id,
            },
            idempotency_scope=f"discovery:{session_id}",
            idempotency_key=key,
            max_attempts=self._settings.worker_retry.agent_job_max_attempts,
        )

        running = apply_brief_running(state, str(run.id), str(job.id))
        running.brief.revision_request = revision_request
        running.routing_policy_version = str(policy_snapshot["version"])
        running.routing_policy_fingerprint = str(policy_snapshot["fingerprint"])
        running.attempt = 0
        updated = await self._repository.save_discovery_state(session_id, running, session.revision)
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_discovery_state(session_id)

    async def approve_brief(self, session_id: UUID) -> dict[str, Any]:
        """Approve the reviewed brief."""
        session = await self._require_session(session_id)
        state = await self._repository.get_discovery_state(session_id)
        if state.status is DiscoveryStatus.APPROVED:
            return await self.get_discovery_state(session_id)
        if state.status is not DiscoveryStatus.BRIEF_REVIEW or not state.brief.markdown.strip():
            self._not_ready("approve", state.status.value)

        brief_hash = _brief_hash(
            state.brief.markdown,
            state.dossier,
            title=state.brief.title,
            user_summary=state.brief.user_summary,
            profile=state.brief.profile.model_dump(mode="json"),
            open_items=state.brief.open_items,
            selected_theme_id=state.selected_theme_id,
            allow_illustrative_work=state.allow_illustrative_work,
        )
        approved = apply_approval(state, brief_hash)
        updated = await self._repository.save_discovery_state(
            session_id, approved, session.revision
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_discovery_state(session_id)

    async def stop(self, session_id: UUID) -> dict[str, Any]:
        """Stop the active Explorer operation and preserve the intake.

        Cancellation is deliberately recoverable: the session enters the
        existing ``needs_attention`` state so the user can retry from the
        preserved input, while the durable job becomes terminal and cannot be
        resurrected by a late worker completion.
        """
        session = await self._require_session(session_id)
        state = await self._repository.get_discovery_state(session_id)
        if state.status in {
            DiscoveryStatus.QUESTIONS_QUEUED,
            DiscoveryStatus.QUESTIONS_RUNNING,
        }:
            job_id = state.operation_a.job_id
            run_id = state.operation_a.run_id
            operation = "understand_and_question"
        elif state.status is DiscoveryStatus.BRIEF_RUNNING:
            job_id = state.brief.job_id
            run_id = state.brief.run_id
            operation = "build_or_revise_brief"
        else:
            return await self.get_discovery_state(session_id)

        error = {
            "code": "JOB_CANCELLED",
            "message": "Explorer was stopped. Your input is preserved and can be retried.",
            "retryable": False,
            "operation": operation,
        }
        if job_id:
            try:
                await self._job_service.cancel(UUID(job_id))
            except (TypeError, ValueError):
                logger.warning("discovery stop found malformed job id session_id=%s", session_id)
        stopped = apply_needs_attention(state, error)
        updated = await self._repository.save_discovery_state(session_id, stopped, session.revision)
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        if run_id:
            try:
                await self._repository.mark_run_cancelled(UUID(run_id), error)
            except (TypeError, ValueError):
                logger.warning("discovery stop found malformed run id session_id=%s", session_id)
        return await self.get_discovery_state(session_id)

    async def get_discovery_state(self, session_id: UUID) -> dict[str, Any]:
        session = await self._require_session(session_id)
        state = await self._repository.get_discovery_state(session_id)
        state = _refresh_open_palette(state)

        jobs: list[dict[str, Any]] = []
        for job_id in (state.operation_a.job_id, state.brief.job_id):
            if job_id:
                try:
                    job = await self._job_service.get(UUID(job_id))
                except Exception:
                    job = None
                if job is not None:
                    jobs.append(public_job_status(job))

        discovery = state.model_dump(mode="json")
        discovery["elapsed_seconds"] = _elapsed_seconds(state.started_at)
        discovery["attempt"] = state.attempt
        discovery["max_attempts"] = state.max_attempts
        discovery["agent_output"] = await public_discovery_outputs(
            getattr(self._repository, "get_run", None),
            questions_run_id=state.operation_a.run_id,
            brief_run_id=state.brief.run_id,
        )
        run_id = state.brief.run_id or state.operation_a.run_id
        if run_id:
            try:
                run = await self._repository.get_run(UUID(run_id))
            except Exception:
                run = None
            if run is not None and run.status == "succeeded":
                receipt = frontend_cache_receipt(run.model_metadata, run_id=run_id)
                if receipt:
                    discovery["cache_receipt"] = receipt
        return {
            "session_id": str(session_id),
            "session_revision": session.revision,
            "discovery": discovery,
            "jobs": jobs,
        }

    def _resolve_model_profile(self, requested: str, sticky: str) -> str:
        """Validate a requested model-profile override against model config.

        An empty request keeps whatever the session already committed to
        (sticky, set once at the first successful start()). Unknown,
        unselectable, or conflicting requests fail explicitly.
        """
        router = ModelRouter(self._settings.models)
        if not requested:
            return sticky
        if not router.is_selectable(requested):
            raise DiscoveryOperationError(
                "MODEL_PROFILE_NOT_SELECTABLE",
                "The requested model profile is not available for this pipeline.",
                status_code=400,
                details={"model_profile": requested},
            )
        if sticky and requested != sticky:
            raise DiscoveryOperationError(
                "MODEL_PROFILE_LOCKED",
                "The model profile is locked after Explorer starts. Restart the pipeline to change it.",
                status_code=409,
            )
        return requested

    def _current_routing_policy_snapshot(self) -> dict[str, Any]:
        from oryxenai.agents.shared.model_runtime import get_model_runtime

        return get_model_runtime(self._settings.models).router.policy_snapshot()

    async def _require_session(self, session_id: UUID) -> Any:
        session = await self._repository.get_session(session_id)
        if session is None:
            raise DiscoveryOperationError(
                "SESSION_NOT_FOUND", "Portfolio session was not found.", status_code=404
            )
        return session

    def _idempotency_key(
        self,
        session_id: UUID,
        operation: str,
        intake: dict[str, Any],
        answers: dict[str, Any],
        *,
        memory: dict[str, Any] | None = None,
        question_events: list[dict[str, Any]] | None = None,
        existing_brief: str = "",
        revision_request: str = "",
        retry_nonce: int | str = 0,
    ) -> str:
        combined = json.dumps(
            {
                "session": str(session_id),
                "operation": operation,
                "intake": intake,
                "answers": answers,
                "memory": memory or {},
                "question_events": question_events or [],
                "existing_brief": existing_brief,
                "revision_request": revision_request,
                "retry": retry_nonce,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def _revision_conflict(self, expected: int, actual: int) -> NoReturn:
        raise DiscoveryOperationError(
            "DISCOVERY_REVISION_CONFLICT",
            "The session changed while this request was being processed. Reload and try again.",
            details={"expected_revision": expected, "actual_revision": actual},
        )

    def _not_ready(self, operation: str, status: str) -> NoReturn:
        raise DiscoveryOperationError(
            "DISCOVERY_NOT_READY",
            f"Explorer is not ready to {operation} from state '{status}'.",
            details={"status": status},
        )


def _refresh_open_palette(state: DiscoveryState) -> DiscoveryState:
    """Show current server-owned choices in interviews saved before a theme release."""
    if state.status not in {
        DiscoveryStatus.QUESTIONS_READY,
        DiscoveryStatus.ANSWERS_IN_PROGRESS,
        DiscoveryStatus.NEEDS_INPUT,
        DiscoveryStatus.NEEDS_ATTENTION,
    }:
        return state
    current = palette_question()
    revised: list[DiscoveryQuestion] = []
    changed = False
    for item in state.operation_a.items:
        if (
            item.kind is QuestionKind.PALETTE_SELECT
            and item.gap_id == PALETTE_GAP_ID
            and item.id not in state.answers.items
        ):
            replacement = current.model_copy(update={"id": item.id})
            revised.append(replacement)
            changed = changed or replacement != item
        else:
            revised.append(item)
    if not changed:
        return state
    refreshed = state.model_copy(deep=True)
    refreshed.operation_a.items = revised
    return refreshed


def _brief_hash(
    markdown: str,
    dossier: Any | None = None,
    *,
    title: str = "",
    user_summary: str = "",
    profile: dict[str, Any] | None = None,
    open_items: list[str] | None = None,
    selected_theme_id: str = "",
    allow_illustrative_work: bool = False,
) -> str:
    payload = {
        "title": title,
        "markdown": markdown,
        "user_summary": user_summary,
        "profile": profile or {},
        "open_items": open_items or [],
        "dossier": dossier.model_dump(mode="json") if dossier is not None else None,
    }
    if selected_theme_id:
        payload["selected_theme_id"] = selected_theme_id
    if allow_illustrative_work:
        payload["allow_illustrative_work"] = True
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _merge_intake(
    previous: DiscoveryIntake,
    submitted: DiscoveryIntake,
) -> tuple[DiscoveryIntake, list[SourceDocument]]:
    """Append genuinely new material while making browser retries idempotent."""

    combined = previous.model_copy(deep=True)
    new_documents: list[SourceDocument] = []
    fields = (
        ("source_text", "Pasted source material", "user_provided", True),
        ("document_text", "Attached document", "user_provided", True),
        ("message", "Your notes", "user_provided", True),
        ("goal", "Portfolio goal", "user_intent", False),
    )
    for field, label, source_kind, append in fields:
        previous_text = str(getattr(previous, field, "") or "")
        submitted_text = str(getattr(submitted, field, "") or "")
        if not submitted_text.strip():
            continue
        if submitted_text == previous_text:
            continue
        if previous_text and submitted_text.startswith(previous_text):
            addition = submitted_text[len(previous_text) :]
        else:
            addition = submitted_text
        if not addition:
            continue
        if append:
            if previous_text and submitted_text.startswith(previous_text):
                merged_text = submitted_text
            else:
                merged_text = f"{previous_text}\n\n{addition}" if previous_text else addition
            setattr(combined, field, merged_text)
            if field == "document_text":
                combined.document_name = submitted.document_name or previous.document_name
        else:
            setattr(combined, field, submitted_text)
        if field == "document_text" and submitted.document_name:
            label = f"Attached document: {submitted.document_name}"
        new_documents.append(create_source_document(addition, label=label, source_kind=source_kind))
    return combined, new_documents


def _has_answer_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list | dict):
        return bool(value)
    return True


def _answer_text(value: Any, question: DiscoveryQuestion) -> str:
    """Record the user's selected label rather than an opaque model option ID."""
    if question.kind is QuestionKind.PALETTE_SELECT:
        selected = palette_answer(value)
        if selected is not None:
            label = next(option.label for option in question.options if option.id == selected[0])
            return f"{label}. {selected[1]}" if selected[1] else label
    if question.kind is QuestionKind.WORK_DETAIL:
        work_selected = atlas_work_answer(value)
        if work_selected is not None:
            details, allowed = work_selected
            return (
                f"{details} | Illustrative concept allowed"
                if details and allowed
                else "Illustrative concept allowed"
                if allowed
                else details
            )
    if question.kind is QuestionKind.BOOLEAN and isinstance(value, str):
        return {"true": "Yes", "false": "No"}.get(value, value)
    if question.kind in {QuestionKind.SINGLE_SELECT, QuestionKind.MULTI_SELECT}:
        option_labels = {option.id: option.label for option in question.options}
        if isinstance(value, str):
            return option_labels.get(value, value)
        if isinstance(value, list):
            return ", ".join(
                option_labels.get(item, item) if isinstance(item, str) else str(item)
                for item in value
            )
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _elapsed_seconds(started_at: str | None) -> float | None:
    if not started_at:
        return None
    try:
        started = datetime.fromisoformat(started_at)
    except ValueError:
        return None
    return max(0.0, (datetime.now(UTC) - started).total_seconds())
