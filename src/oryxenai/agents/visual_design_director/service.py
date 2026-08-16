"""Application service for the Visual Design Director workflow.

Single-job flow: start (compact approved Content Architect snapshot +
preferences) -> visual_design_director.build (up to 3 internal model calls)
-> review -> revise (optional, re-runs build) -> approve. Requires Content
Architect to be APPROVED before starting, and rejects any further operation
once Content Architect's approved content hash no longer matches the
snapshot this run was grounded in. Mirrors
agents/content_architect/service.py exactly, one stage down the pipeline.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, NoReturn
from uuid import UUID, uuid4

from oryxenai.agents.content_architect.schemas import ContentArchitectState, ContentArchitectStatus
from oryxenai.agents.visual_design_director.schemas import (
    VisualDesignDirectorIntake,
    VisualDesignDirectorPreferences,
    VisualDesignDirectorSourceRef,
    VisualDesignDirectorState,
    VisualDesignDirectorStatus,
)
from oryxenai.agents.visual_design_director.state import (
    apply_approval,
    apply_revision_requested,
    apply_start,
)
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.visual_design_director import VisualDesignDirectorRepository
from oryxenai.jobs.service import JobService

_BUILD_KIND = "visual_design_director.build"


def compute_route_publication_hash(route_plan: list[dict[str, Any]]) -> str:
    """Deterministic hash of route_id -> publication_status pairs.

    Content Architect's own content_hash is computed only from
    page_content_packs/public_content_manifest — never from route_plan's
    publication_status — so a route flipping between pending/approved/
    blocked with no other content change would otherwise go undetected by
    Visual Design Director's staleness check. Checked independently of
    content_architect_content_hash for exactly that reason.
    """
    pairs = sorted(
        (
            str(route.get("route_id", "") or ""),
            str(route.get("publication_status", "approved") or "approved"),
        )
        for route in route_plan
        if isinstance(route, dict) and route.get("route_id")
    )
    combined = json.dumps(pairs, sort_keys=True)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def compute_content_architect_visual_input_hash(
    content_architect: ContentArchitectState,
) -> str:
    """Fingerprint every approved Content Architect field consumed by VDD.

    ``ContentArchitectApproval.content_hash`` intentionally covers only the
    public page packs and manifest. VDD also consumes the story strategy,
    route intent, media availability, handoff/privacy boundaries, and the
    complete route plan. Keeping a second projection hash here prevents those
    changes from silently leaving an old visual direction looking current.
    """
    projection = {
        "approved_content_hash": (
            content_architect.approved.content_hash if content_architect.approved else ""
        ),
        "site_story_strategy": content_architect.site_story_strategy,
        "route_plan": [route.model_dump(mode="json") for route in content_architect.route_plan],
        "page_content_packs": [
            _strip_internal_notes(pack.model_dump(mode="json"))
            for pack in content_architect.page_content_packs
        ],
        "public_content_manifest": content_architect.public_content_manifest,
        "media_status": content_architect.media_status,
        "visual_director_handoff": content_architect.visual_director_handoff,
        "privacy_and_confidentiality": content_architect.privacy_and_confidentiality,
    }
    combined = json.dumps(projection, sort_keys=True, default=str)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _strip_internal_notes(pack: dict[str, Any]) -> dict[str, Any]:
    """Drop Content Architect's internal-only QA notes before they become
    part of Visual Design Director's own persisted intake snapshot.

    Content Architect's README is explicit that internal_notes is "the ONLY
    place review/QA reasoning may live" and "must never leak" into
    visitor-facing output — Visual Design Director's prompts never read
    this field, so carrying it forward duplicates upstream data with no
    functional purpose, contrary to this project's compact-projection
    principle (see AGENTS.md).
    """
    stripped = dict(pack)
    stripped["internal_notes"] = {}
    return stripped


class VisualDesignDirectorOperationError(Exception):
    """Safe, transport-neutral error raised by the Visual Design Director service."""

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


class VisualDesignDirectorService:
    """Coordinates Visual Design Director state, runs, and jobs."""

    def __init__(
        self,
        repository: VisualDesignDirectorRepository,
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
        """Snapshot the approved Content Architect result and enqueue the build job."""
        session = await self._require_session(session_id)
        state = await self._repository.get_visual_design_director_state(session_id)

        if state.status not in {
            VisualDesignDirectorStatus.NOT_STARTED,
            VisualDesignDirectorStatus.NEEDS_ATTENTION,
        }:
            return await self.get_visual_design_director_state(session_id)

        content_architect = await self._repository.get_content_architect_snapshot(session_id)
        if (
            content_architect.status is not ContentArchitectStatus.APPROVED
            or content_architect.approved is None
        ):
            raise VisualDesignDirectorOperationError(
                "VISUAL_DESIGN_DIRECTOR_CONTENT_ARCHITECT_NOT_APPROVED",
                "Content Architect must be approved before Visual Design Director can start.",
                details={"content_architect_status": content_architect.status.value},
            )

        # A model/provider choice made earlier in the session applies for
        # the whole session — if none is explicitly given here, inherit the
        # choice already recorded on the approved Content Architect run
        # rather than asking the user to pick twice. Falls back to the
        # literal default profile name (never blank) so the persisted state
        # always records which profile actually ran, for debugging and
        # reproducibility.
        resolved_profile = (
            model_profile or content_architect.model_profile or "visual_design_director"
        )

        all_route_plan_dump = [
            route.model_dump(mode="json") for route in content_architect.route_plan
        ]
        public_route_ids = {
            str(route["route_id"])
            for route in all_route_plan_dump
            if route.get("route_id") and route.get("publication_status") == "approved"
        }
        # The approved Content Architect public scope is the only route graph
        # Visual Design Director is allowed to turn into public direction.
        # Pending routes stay in CA review state and source fingerprints, but
        # never become VDD pages that would violate pack-v2 exact-set equality.
        route_plan_dump = [
            route
            for route in all_route_plan_dump
            if str(route.get("route_id", "") or "") in public_route_ids
        ]
        intake = VisualDesignDirectorIntake(
            content_architect_content_hash=content_architect.approved.content_hash,
            content_architect_session_revision=session.revision,
            presentation_mode=str(
                (content_architect.site_story_strategy or {}).get("presentation_mode", "") or ""
            ),
            site_story_strategy=content_architect.site_story_strategy,
            route_plan=route_plan_dump,
            page_content_packs=[
                _strip_internal_notes(pack.model_dump(mode="json"))
                for pack in content_architect.page_content_packs
                if pack.route_id in public_route_ids
            ],
            public_content_manifest=content_architect.public_content_manifest,
            media_status=content_architect.media_status,
            visual_director_handoff=content_architect.visual_director_handoff,
            privacy_and_confidentiality=list(content_architect.privacy_and_confidentiality),
        )
        prefs = VisualDesignDirectorPreferences(**(preferences or {}))
        source_ref = VisualDesignDirectorSourceRef(
            content_architect_content_hash=content_architect.approved.content_hash,
            content_architect_visual_input_hash=compute_content_architect_visual_input_hash(
                content_architect
            ),
            content_architect_session_revision=session.revision,
            route_publication_hash=compute_route_publication_hash(all_route_plan_dump),
            snapshotted_at=datetime.now(UTC).isoformat(),
        )

        intake_payload = intake.model_dump(mode="json")
        prefs_payload = prefs.model_dump(mode="json")
        retry_nonce = (
            state.attempt if state.status is VisualDesignDirectorStatus.NEEDS_ATTENTION else 0
        )
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
            agent_key="visual_design_director",
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
            idempotency_scope=f"visual_design_director:{session_id}",
            idempotency_key=key,
        )

        running = apply_start(state, source_ref=source_ref, intake=intake, preferences=prefs)
        running.model_profile = resolved_profile
        running.run_id = str(run.id)
        running.job_id = str(job.id)
        running.attempt = 0
        running.max_attempts = self._settings.worker_retry.max_attempts
        updated = await self._repository.save_visual_design_director_state(
            session_id, running, session.revision
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_visual_design_director_state(session_id)

    async def revise(
        self,
        session_id: UUID,
        revision_request: str,
        *,
        request_id: str = "",
    ) -> dict[str, Any]:
        """Re-run the build pipeline with a natural-language revision request."""
        session = await self._require_session(session_id)
        state = await self._repository.get_visual_design_director_state(session_id)
        if state.status is not VisualDesignDirectorStatus.DESIGN_REVIEW:
            self._not_ready("revise", state.status.value)
        revision_request = (revision_request or "").strip()
        if not revision_request:
            raise VisualDesignDirectorOperationError(
                "VISUAL_DESIGN_DIRECTOR_NOT_READY", "revision_request is required.", status_code=409
            )
        content_architect = await self._repository.get_content_architect_snapshot(session_id)
        self._check_content_architect_not_stale(content_architect, state)

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
            agent_key="visual_design_director",
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
            idempotency_scope=f"visual_design_director:{session_id}",
            idempotency_key=key,
        )

        running = apply_revision_requested(state, str(run.id), str(job.id), revision_request)
        running.attempt = 0
        updated = await self._repository.save_visual_design_director_state(
            session_id, running, session.revision
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_visual_design_director_state(session_id)

    async def approve(self, session_id: UUID) -> dict[str, Any]:
        """Approve the reviewed visual direction."""
        session = await self._require_session(session_id)
        state = await self._repository.get_visual_design_director_state(session_id)
        if state.status is VisualDesignDirectorStatus.APPROVED:
            return await self.get_visual_design_director_state(session_id)
        if state.status is not VisualDesignDirectorStatus.DESIGN_REVIEW:
            self._not_ready("approve", state.status.value)

        pages_payload = [page.model_dump(mode="json") for page in state.pages]
        asset_briefs_payload = [asset.model_dump(mode="json") for asset in state.asset_briefs]
        visual_direction_hash = _visual_direction_hash(
            pages_payload,
            state.visual_language,
            state.shared_visual_systems,
            asset_briefs_payload,
            navigation_direction=state.navigation_direction,
            motion_system=state.motion_system,
            interaction_system=state.interaction_system,
            accessibility_and_performance=state.accessibility_and_performance,
            resource_candidates=[
                resource.model_dump(mode="json") for resource in state.resource_candidates
            ],
            must_preserve=state.must_preserve,
            must_not_fabricate=state.must_not_fabricate,
            compiler_handoff=state.compiler_handoff,
        )
        approved = apply_approval(state, visual_direction_hash)
        updated = await self._repository.save_visual_design_director_state(
            session_id, approved, session.revision
        )
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_visual_design_director_state(session_id)

    async def get_visual_design_director_state(self, session_id: UUID) -> dict[str, Any]:
        session = await self._require_session(session_id)
        state = await self._repository.get_visual_design_director_state(session_id)

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

        visual_design_director = state.model_dump(mode="json")
        visual_design_director["elapsed_seconds"] = _elapsed_seconds(state.started_at)
        visual_design_director["attempt"] = state.attempt
        visual_design_director["max_attempts"] = state.max_attempts
        return {
            "session_id": str(session_id),
            "session_revision": session.revision,
            "visual_design_director": visual_design_director,
            "jobs": jobs,
        }

    def _authoritative_output(self, state: VisualDesignDirectorState) -> dict[str, Any]:
        return {
            "visual_language": state.visual_language,
            "shared_visual_systems": state.shared_visual_systems,
            "navigation_direction": state.navigation_direction,
            "motion_system": state.motion_system,
            "interaction_system": state.interaction_system,
            "pages": [page.model_dump(mode="json") for page in state.pages],
            "asset_briefs": [asset.model_dump(mode="json") for asset in state.asset_briefs],
            "resource_candidates": [
                resource.model_dump(mode="json") for resource in state.resource_candidates
            ],
            "compiler_handoff": state.compiler_handoff,
        }

    def _check_content_architect_not_stale(
        self, content_architect: ContentArchitectState, state: VisualDesignDirectorState
    ) -> None:
        current_hash = content_architect.approved.content_hash if content_architect.approved else ""
        current_route_publication_hash = compute_route_publication_hash(
            [route.model_dump(mode="json") for route in content_architect.route_plan]
        )
        current_visual_input_hash = compute_content_architect_visual_input_hash(content_architect)
        if (
            current_hash != state.source_ref.content_architect_content_hash
            or current_route_publication_hash != state.source_ref.route_publication_hash
            or (
                state.source_ref.content_architect_visual_input_hash
                and current_visual_input_hash
                != state.source_ref.content_architect_visual_input_hash
            )
        ):
            raise VisualDesignDirectorOperationError(
                "VISUAL_DESIGN_DIRECTOR_STALE_SOURCE",
                "Content Architect has changed since this Visual Design Director run started. "
                "Start a fresh Visual Design Director run.",
                details={
                    "expected_content_architect_content_hash": (
                        state.source_ref.content_architect_content_hash
                    ),
                    "actual_content_architect_content_hash": current_hash,
                    "expected_route_publication_hash": state.source_ref.route_publication_hash,
                    "actual_route_publication_hash": current_route_publication_hash,
                    "expected_content_architect_visual_input_hash": (
                        state.source_ref.content_architect_visual_input_hash
                    ),
                    "actual_content_architect_visual_input_hash": current_visual_input_hash,
                },
            )

    async def _require_session(self, session_id: UUID) -> Any:
        session = await self._repository.get_session(session_id)
        if session is None:
            raise VisualDesignDirectorOperationError(
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
        raise VisualDesignDirectorOperationError(
            "VISUAL_DESIGN_DIRECTOR_REVISION_CONFLICT",
            "The session changed while this request was being processed. Reload and try again.",
            details={"expected_revision": expected, "actual_revision": actual},
        )

    def _not_ready(self, operation: str, status: str) -> NoReturn:
        raise VisualDesignDirectorOperationError(
            "VISUAL_DESIGN_DIRECTOR_NOT_READY",
            f"Visual Design Director is not ready to {operation} from state '{status}'.",
            details={"status": status},
        )


def _visual_direction_hash(
    pages: Any,
    visual_language: Any,
    shared_visual_systems: Any,
    asset_briefs: Any,
    *,
    navigation_direction: Any = None,
    motion_system: Any = None,
    interaction_system: Any = None,
    accessibility_and_performance: Any = None,
    resource_candidates: Any = None,
    must_preserve: Any = None,
    must_not_fabricate: Any = None,
    compiler_handoff: Any = None,
) -> str:
    """Hash the complete approved visual contract.

    The original approval hash covered only pages, visual language, shared
    systems, and asset briefs. That allowed a change to navigation, motion,
    accessibility, resource choices, or compiler handoff to leave an approval
    looking current. The optional keyword fields preserve compatibility with
    older callers/tests while making new approvals sensitive to every
    compiler-relevant VDD field.
    """
    combined = json.dumps(
        {
            "pages": pages,
            "visual_language": visual_language,
            "shared_visual_systems": shared_visual_systems,
            "asset_briefs": asset_briefs,
            "navigation_direction": navigation_direction,
            "motion_system": motion_system,
            "interaction_system": interaction_system,
            "accessibility_and_performance": accessibility_and_performance,
            "resource_candidates": resource_candidates,
            "must_preserve": must_preserve,
            "must_not_fabricate": must_not_fabricate,
            "compiler_handoff": compiler_handoff,
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
