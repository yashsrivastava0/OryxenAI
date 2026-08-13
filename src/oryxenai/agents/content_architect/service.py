"""Application service for the Content Architect workflow.

Single-job flow: start (compact approved Discovery snapshot + preferences)
-> content_architect.build (up to 3 internal model calls) -> review -> revise
(optional, re-runs build) -> approve. Requires Discovery to be APPROVED
before starting, and rejects any further operation once Discovery's approved
brief hash no longer matches the snapshot this run was grounded in.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, NoReturn
from uuid import UUID, uuid4

from oryxenai.agents.content_architect.schemas import (
    ContentArchitectIntake,
    ContentArchitectPreferences,
    ContentArchitectSourceRef,
    ContentArchitectState,
    ContentArchitectStatus,
)
from oryxenai.agents.content_architect.state import (
    NoPublishableRoutesError,
    apply_approval,
    apply_revision_requested,
    apply_start,
)
from oryxenai.agents.discovery.schemas import DiscoveryState, DiscoveryStatus
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.content_architect import ContentArchitectRepository
from oryxenai.jobs.service import JobService

_BUILD_KIND = "content_architect.build"


class ContentArchitectOperationError(Exception):
    """Safe, transport-neutral error raised by the Content Architect service."""

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


class ContentArchitectService:
    """Coordinates Content Architect state, runs, and jobs."""

    def __init__(
        self,
        repository: ContentArchitectRepository,
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
        preferences: dict[str, Any],
        *,
        model_profile: str = "",
        request_id: str = "",
    ) -> dict[str, Any]:
        """Snapshot the approved Discovery result and enqueue the build job."""
        session = await self._require_session(session_id)
        state = await self._repository.get_content_architect_state(session_id)

        if state.status not in {
            ContentArchitectStatus.NOT_STARTED,
            ContentArchitectStatus.NEEDS_ATTENTION,
        }:
            return await self.get_content_architect_state(session_id)

        discovery = await self._repository.get_discovery_snapshot(session_id)
        if discovery.status is not DiscoveryStatus.APPROVED or discovery.brief.approved is None:
            raise ContentArchitectOperationError(
                "CONTENT_ARCHITECT_DISCOVERY_NOT_APPROVED",
                "Discovery must be approved before Content Architect can start.",
                details={"discovery_status": discovery.status.value},
            )

        # A model/provider choice made on the home page applies for the whole
        # session — if none is explicitly given here, inherit the choice
        # already recorded on the approved Discovery run rather than asking
        # the user to pick twice.
        resolved_profile = model_profile or discovery.model_profile

        intake = ContentArchitectIntake(
            approved_brief_title=discovery.brief.title,
            user_summary=discovery.brief.user_summary,
            profile=discovery.brief.profile.model_dump(mode="json"),
            open_items=list(discovery.brief.open_items),
            discovery_brief_hash=discovery.brief.approved.brief_hash,
            discovery_session_revision=session.revision,
        )
        prefs = ContentArchitectPreferences(**(preferences or {}))
        source_ref = ContentArchitectSourceRef(
            discovery_brief_hash=discovery.brief.approved.brief_hash,
            discovery_session_revision=session.revision,
            snapshotted_at=datetime.now(UTC).isoformat(),
        )

        intake_payload = intake.model_dump(mode="json")
        prefs_payload = prefs.model_dump(mode="json")
        retry_nonce = state.attempt if state.status is ContentArchitectStatus.NEEDS_ATTENTION else 0
        key = self._idempotency_key(
            session_id,
            "build",
            intake_payload,
            prefs_payload,
            prior_output={},
            revision_request="",
            source_ref=source_ref.model_dump(mode="json"),
            retry_nonce=retry_nonce,
        )

        run = AgentRun(
            id=uuid4(),
            portfolio_session_id=session_id,
            agent_key="content_architect",
            status="pending",
            input_payload={
                "operation": "build",
                "intake": intake_payload,
                "preferences": prefs_payload,
                "prior_output": {},
                "revision_request": "",
                "model_profile": resolved_profile,
            },
            state_before=dict(session.current_state),
            idempotency_key=key,
        )
        await self._repository.create_run(run)
        job = await self._job_service.enqueue(
            _BUILD_KIND,
            {
                "portfolio_session_id": str(session_id),
                "agent_run_id": str(run.id),
                "expected_session_revision": session.revision + 1,
                "request_id": request_id,
            },
            idempotency_scope=f"content_architect:{session_id}",
            idempotency_key=key,
        )

        running = apply_start(state, source_ref=source_ref, intake=intake, preferences=prefs)
        running.model_profile = resolved_profile
        running.run_id = str(run.id)
        running.job_id = str(job.id)
        running.attempt = 0
        running.max_attempts = self._settings.worker_retry.max_attempts
        updated = await self._repository.save_content_architect_state(
            session_id, running, session.revision
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_content_architect_state(session_id)

    async def revise(
        self,
        session_id: UUID,
        revision_request: str,
        *,
        request_id: str = "",
    ) -> dict[str, Any]:
        """Re-run the build pipeline with a natural-language revision request."""
        session = await self._require_session(session_id)
        state = await self._repository.get_content_architect_state(session_id)
        if state.status is not ContentArchitectStatus.CONTENT_REVIEW:
            self._not_ready("revise", state.status.value)
        revision_request = (revision_request or "").strip()
        if not revision_request:
            raise ContentArchitectOperationError(
                "CONTENT_ARCHITECT_NOT_READY", "revision_request is required.", status_code=409
            )
        discovery = await self._repository.get_discovery_snapshot(session_id)
        self._check_discovery_not_stale(discovery, state)

        prior_output = self._authoritative_output(state)
        intake_payload = state.intake.model_dump(mode="json")
        prefs_payload = state.preferences.model_dump(mode="json")
        key = self._idempotency_key(
            session_id,
            "build",
            intake_payload,
            prefs_payload,
            prior_output=prior_output,
            revision_request=revision_request,
            source_ref=state.source_ref.model_dump(mode="json"),
            retry_nonce=state.attempt,
        )
        run = AgentRun(
            id=uuid4(),
            portfolio_session_id=session_id,
            agent_key="content_architect",
            status="pending",
            input_payload={
                "operation": "build",
                "intake": intake_payload,
                "preferences": prefs_payload,
                "prior_output": prior_output,
                "revision_request": revision_request,
                "model_profile": state.model_profile,
            },
            state_before=dict(session.current_state),
            idempotency_key=key,
        )
        await self._repository.create_run(run)
        job = await self._job_service.enqueue(
            _BUILD_KIND,
            {
                "portfolio_session_id": str(session_id),
                "agent_run_id": str(run.id),
                "expected_session_revision": session.revision + 1,
                "request_id": request_id,
            },
            idempotency_scope=f"content_architect:{session_id}",
            idempotency_key=key,
        )

        running = apply_revision_requested(state, str(run.id), str(job.id), revision_request)
        running.attempt = 0
        updated = await self._repository.save_content_architect_state(
            session_id, running, session.revision
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_content_architect_state(session_id)

    async def approve(self, session_id: UUID) -> dict[str, Any]:
        """Approve the reviewed content."""
        session = await self._require_session(session_id)
        state = await self._repository.get_content_architect_state(session_id)
        if state.status is ContentArchitectStatus.APPROVED:
            return await self.get_content_architect_state(session_id)
        if state.status is not ContentArchitectStatus.CONTENT_REVIEW:
            self._not_ready("approve", state.status.value)

        packs_payload = [pack.model_dump(mode="json") for pack in state.page_content_packs]
        content_hash = _content_hash(packs_payload, state.public_content_manifest)
        try:
            approved = apply_approval(state, content_hash)
        except NoPublishableRoutesError as exc:
            raise ContentArchitectOperationError(
                "CONTENT_ARCHITECT_NO_PUBLISHABLE_ROUTES",
                "Cannot approve: no publishable routes. Revise/re-run Content "
                "Architect so at least one route has publication_status 'approved'.",
                details={
                    "route_count": exc.route_count,
                    "route_statuses": exc.route_statuses,
                },
            ) from exc
        updated = await self._repository.save_content_architect_state(
            session_id, approved, session.revision
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_content_architect_state(session_id)

    async def get_content_architect_state(self, session_id: UUID) -> dict[str, Any]:
        session = await self._require_session(session_id)
        state = await self._repository.get_content_architect_state(session_id)

        jobs: list[dict[str, Any]] = []
        if state.job_id:
            try:
                job = await self._job_service.get(UUID(state.job_id))
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

        content_architect = state.model_dump(mode="json")
        content_architect["elapsed_seconds"] = _elapsed_seconds(state.started_at)
        content_architect["attempt"] = state.attempt
        content_architect["max_attempts"] = state.max_attempts
        return {
            "session_id": str(session_id),
            "session_revision": session.revision,
            "content_architect": content_architect,
            "jobs": jobs,
        }

    def _authoritative_output(self, state: ContentArchitectState) -> dict[str, Any]:
        return {
            "site_story_strategy": state.site_story_strategy,
            "decision_basis": [d.model_dump(mode="json") for d in state.decision_basis],
            "route_plan": [route.model_dump(mode="json") for route in state.route_plan],
            "page_content_packs": [
                pack.model_dump(mode="json") for pack in state.page_content_packs
            ],
            "public_content_manifest": state.public_content_manifest,
            "claim_grounding": [claim.model_dump(mode="json") for claim in state.claim_grounding],
            "visual_director_handoff": state.visual_director_handoff,
        }

    def _check_discovery_not_stale(
        self, discovery: DiscoveryState, state: ContentArchitectState
    ) -> None:
        current_hash = discovery.brief.approved.brief_hash if discovery.brief.approved else ""
        if current_hash != state.source_ref.discovery_brief_hash:
            raise ContentArchitectOperationError(
                "CONTENT_ARCHITECT_STALE_SOURCE",
                "Discovery has changed since this Content Architect run started. "
                "Start a fresh Content Architect run.",
                details={
                    "expected_discovery_brief_hash": state.source_ref.discovery_brief_hash,
                    "actual_discovery_brief_hash": current_hash,
                },
            )

    async def _require_session(self, session_id: UUID) -> Any:
        session = await self._repository.get_session(session_id)
        if session is None:
            raise ContentArchitectOperationError(
                "SESSION_NOT_FOUND", "Portfolio session was not found.", status_code=404
            )
        return session

    def _idempotency_key(
        self,
        session_id: UUID,
        operation: str,
        intake: dict[str, Any],
        preferences: dict[str, Any],
        *,
        prior_output: dict[str, Any] | None = None,
        revision_request: str = "",
        source_ref: dict[str, Any] | None = None,
        retry_nonce: int = 0,
    ) -> str:
        combined = json.dumps(
            {
                "session": str(session_id),
                "operation": operation,
                "intake": intake,
                "preferences": preferences,
                "prior_output": prior_output or {},
                "revision_request": revision_request,
                "source_ref": source_ref or {},
                "retry": retry_nonce,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def _revision_conflict(self, expected: int, actual: int) -> NoReturn:
        raise ContentArchitectOperationError(
            "CONTENT_ARCHITECT_REVISION_CONFLICT",
            "The session changed while this request was being processed. Reload and try again.",
            details={"expected_revision": expected, "actual_revision": actual},
        )

    def _not_ready(self, operation: str, status: str) -> NoReturn:
        raise ContentArchitectOperationError(
            "CONTENT_ARCHITECT_NOT_READY",
            f"Content Architect is not ready to {operation} from state '{status}'.",
            details={"status": status},
        )


def _content_hash(page_content_packs: Any, public_content_manifest: Any) -> str:
    combined = json.dumps(
        {
            "page_content_packs": page_content_packs,
            "public_content_manifest": public_content_manifest,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _elapsed_seconds(started_at: str | None) -> float | None:
    if not started_at:
        return None
    try:
        started = datetime.fromisoformat(started_at)
    except ValueError:
        return None
    return max(0.0, (datetime.now(UTC) - started).total_seconds())
