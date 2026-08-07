"""Application service for the Discovery workflow.

Simple linear flow: start (message + document + goal) -> Operation A
(understand_and_question) -> answers -> Operation B (build_or_revise_brief)
-> approve. Input is stored as-is; nothing is validated.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, NoReturn
from uuid import UUID, uuid4

from oryxenai.agents.discovery.schemas import (
    DiscoveryAnswer,
    DiscoveryIntake,
    DiscoveryStatus,
)
from oryxenai.agents.discovery.state import (
    apply_answers_in_progress,
    apply_approval,
    apply_brief_running,
    apply_start,
)
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


class DiscoveryService:
    """Coordinates Discovery state, runs, and jobs."""

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
        request_id: str = "",
    ) -> dict[str, Any]:
        """Store the raw input and enqueue the understand_and_question job.

        Restarting from QUESTIONS_READY (e.g. the user pastes more material
        after NEEDS_DETAILS) enqueues a fresh Operation A run.
        """
        session = await self._require_session(session_id)
        state = await self._repository.get_discovery_state(session_id)

        if state.status not in {
            DiscoveryStatus.NOT_STARTED,
            DiscoveryStatus.QUESTIONS_READY,
            DiscoveryStatus.NEEDS_ATTENTION,
        }:
            return await self.get_discovery_state(session_id)

        intake = DiscoveryIntake(message=message, document_text=document_text, goal=goal)
        intake_payload = intake.model_dump(mode="json")
        if state.status is DiscoveryStatus.NEEDS_ATTENTION:
            retry_nonce = state.attempt
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
            retry_nonce=retry_nonce,
        )

        run = AgentRun(
            id=uuid4(),
            portfolio_session_id=session_id,
            agent_key="discovery",
            status="pending",
            input_payload={
                "operation": "understand_and_question",
                "intake": intake_payload,
                "prior_memory": state.memory,
            },
            state_before=dict(session.current_state),
            idempotency_key=key,
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
        )

        queued = apply_start(state)
        queued.intake = intake
        queued.operation_a.run_id = str(run.id)
        queued.operation_a.job_id = str(job.id)
        queued.attempt = 0
        queued.max_attempts = self._settings.worker_retry.max_attempts
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
        request_id: str = "",
    ) -> dict[str, Any]:
        """Save answers; when complete, enqueue the brief job."""
        session = await self._require_session(session_id)
        state = await self._repository.get_discovery_state(session_id)
        if state.status not in {
            DiscoveryStatus.QUESTIONS_READY,
            DiscoveryStatus.ANSWERS_IN_PROGRESS,
            DiscoveryStatus.NEEDS_ATTENTION,
        }:
            self._not_ready("save answers", state.status.value)

        answer_map: dict[str, DiscoveryAnswer] = {}
        for answer in answers:
            if answer.question_id:
                answer_map[answer.question_id] = answer
        next_state = state.model_copy(deep=True)
        if state.status in {DiscoveryStatus.QUESTIONS_READY, DiscoveryStatus.NEEDS_ATTENTION}:
            next_state = apply_answers_in_progress(state)
        next_state.answers.revision += 1
        next_state.answers.items = answer_map
        next_state.latest_error = None

        if complete:
            retry_nonce = state.attempt if state.status is DiscoveryStatus.NEEDS_ATTENTION else 0
            key = self._idempotency_key(
                session_id,
                "build_or_revise_brief",
                next_state.intake.model_dump(mode="json"),
                {qid: answer.model_dump(mode="json") for qid, answer in answer_map.items()},
                memory=next_state.memory,
                existing_brief=next_state.brief.markdown,
                retry_nonce=retry_nonce,
            )
            run = AgentRun(
                id=uuid4(),
                portfolio_session_id=session_id,
                agent_key="discovery",
                status="pending",
                input_payload={
                    "operation": "build_or_revise_brief",
                    "intake": next_state.intake.model_dump(mode="json"),
                    "answers": {
                        qid: answer.model_dump(mode="json") for qid, answer in answer_map.items()
                    },
                    "prior_memory": next_state.memory,
                    "existing_brief": next_state.brief.markdown,
                    "revision_request": "",
                },
                state_before=dict(session.current_state),
                idempotency_key=key,
            )
            await self._repository.create_run(run)
            job = await self._job_service.enqueue(
                "discovery.build_or_revise_brief",
                {
                    "portfolio_session_id": str(session_id),
                    "agent_run_id": str(run.id),
                    "expected_session_revision": session.revision + 2,
                    "request_id": request_id,
                },
                idempotency_scope=f"discovery:{session_id}",
                idempotency_key=key,
            )
            next_state = apply_brief_running(next_state, str(run.id), str(job.id))
            next_state.attempt = 0

        updated = await self._repository.save_discovery_state(
            session_id, next_state, session.revision
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_discovery_state(session_id)

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
        if state.status is not DiscoveryStatus.BRIEF_REVIEW or not state.brief.markdown.strip():
            self._not_ready("revise", state.status.value)
        revision_request = (revision_request or "").strip()
        if not revision_request:
            raise DiscoveryOperationError(
                "DISCOVERY_NOT_READY", "revision_request is required.", status_code=409
            )

        key = self._idempotency_key(
            session_id,
            "build_or_revise_brief",
            state.intake.model_dump(mode="json"),
            {qid: answer.model_dump(mode="json") for qid, answer in state.answers.items.items()},
            memory=state.memory,
            existing_brief=state.brief.markdown,
            retry_nonce=state.attempt,
        )
        run = AgentRun(
            id=uuid4(),
            portfolio_session_id=session_id,
            agent_key="discovery",
            status="pending",
            input_payload={
                "operation": "build_or_revise_brief",
                "intake": state.intake.model_dump(mode="json"),
                "answers": {
                    qid: answer.model_dump(mode="json")
                    for qid, answer in state.answers.items.items()
                },
                "prior_memory": state.memory,
                "existing_brief": state.brief.markdown,
                "revision_request": revision_request,
            },
            state_before=dict(session.current_state),
            idempotency_key=key,
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
        )

        running = apply_brief_running(state, str(run.id), str(job.id))
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

        brief_hash = _brief_hash(state.brief.markdown)
        approved = apply_approval(state, brief_hash)
        updated = await self._repository.save_discovery_state(
            session_id, approved, session.revision
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_discovery_state(session_id)

    async def get_discovery_state(self, session_id: UUID) -> dict[str, Any]:
        session = await self._require_session(session_id)
        state = await self._repository.get_discovery_state(session_id)

        jobs: list[dict[str, Any]] = []
        for job_id in (state.operation_a.job_id, state.brief.job_id):
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

        discovery = state.model_dump(mode="json")
        discovery["elapsed_seconds"] = _elapsed_seconds(state.started_at)
        discovery["attempt"] = state.attempt
        discovery["max_attempts"] = state.max_attempts
        return {
            "session_id": str(session_id),
            "session_revision": session.revision,
            "discovery": discovery,
            "jobs": jobs,
        }

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
        existing_brief: str = "",
        retry_nonce: int = 0,
    ) -> str:
        combined = json.dumps(
            {
                "session": str(session_id),
                "operation": operation,
                "intake": intake,
                "answers": answers,
                "memory": memory or {},
                "existing_brief": existing_brief,
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
            f"Discovery is not ready to {operation} from state '{status}'.",
            details={"status": status},
        )


def _brief_hash(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def _elapsed_seconds(started_at: str | None) -> float | None:
    if not started_at:
        return None
    try:
        started = datetime.fromisoformat(started_at)
    except ValueError:
        return None
    return max(0.0, (datetime.now(UTC) - started).total_seconds())
