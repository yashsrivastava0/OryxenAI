"""Application service for the durable Build Preparation pipeline."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, NoReturn
from uuid import UUID, uuid4

from oryxenai.agents.build_preparation.input_integrator import (
    BuildPreparationInputIntegrator,
)
from oryxenai.agents.build_preparation.schemas import (
    BuildPreparationSourceRef,
    BuildPreparationStatus,
)
from oryxenai.agents.build_preparation.state import apply_start, reset_for_regeneration
from oryxenai.agents.content_architect.schemas import ContentArchitectStatus
from oryxenai.agents.shared.observability import frontend_cache_receipt
from oryxenai.agents.visual_design_director.schemas import VisualDesignDirectorStatus
from oryxenai.auth.authorization import durable_snapshot_for_session
from oryxenai.core.settings import get_settings
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.build_preparation import BuildPreparationRepository
from oryxenai.jobs.service import JobService

_BUILD_KIND = "build_preparation.prepare"
_AGENT_KEY = "build_preparation"


class BuildPreparationOperationError(Exception):
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


class BuildPreparationService:
    def __init__(
        self,
        repository: BuildPreparationRepository,
        job_service: JobService,
    ) -> None:
        self._repository = repository
        self._job_service = job_service
        self._settings = get_settings()
        self._input_integrator = BuildPreparationInputIntegrator(self._settings)

    async def start(
        self,
        session_id: UUID,
        *,
        model_profile: str = "",
        request_id: str = "",
    ) -> dict[str, Any]:
        session = await self._require_session(session_id)
        state = await self._repository.get_state(session_id)
        if state.status is BuildPreparationStatus.RUNNING:
            return await self.get_state(session_id)
        if state.status is BuildPreparationStatus.READY:
            self._not_ready("start", state.status.value, "Use regenerate for a ready run.")

        content_architect = await self._repository.get_content_architect_snapshot(session_id)
        visual_design_director = await self._repository.get_visual_design_director_snapshot(
            session_id
        )
        self._require_approved_upstream(content_architect, visual_design_director)

        inputs = self._input_integrator.compose(
            content_architect,
            visual_design_director,
            content_architect_session_revision=session.revision,
            visual_design_director_session_revision=session.revision,
        )
        ca_payload = inputs.content_architect
        vdd_payload = inputs.visual_design_director
        source_ref = inputs.source_ref
        sticky_profile = visual_design_director.model_profile
        if model_profile and model_profile != sticky_profile:
            raise BuildPreparationOperationError(
                "MODEL_PROFILE_LOCKED",
                "Build Preparation must use the model profile selected in Discovery.",
            )
        resolved_profile = sticky_profile
        key = self._idempotency_key(session_id, source_ref, resolved_profile, state.attempt)
        run = AgentRun(
            id=uuid4(),
            agent_key=_AGENT_KEY,
            status="pending",
            input_payload={
                "model_profile": resolved_profile,
                "max_routes": self._settings.build_preparation.max_routes,
                "live_model": self._settings.build_preparation.reasoning_enabled,
                "live_providers": self._settings.build_preparation.reasoning_enabled,
                "output_dir": self._settings.build_preparation.session_staging_root,
                "debug_mirror": self._settings.build_preparation.debug_mirror_enabled,
                "source_ref": source_ref.model_dump(mode="json"),
                "content_architect": ca_payload,
                "visual_design_director": vdd_payload,
                "auto_derive_visual_resources": self._settings.build_preparation.auto_derive_visual_resources,
            },
            state_before=dict(session.current_state),
            idempotency_key=key,
            **durable_snapshot_for_session(self._job_service.authorization_context, session_id),
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
            idempotency_scope=f"{_AGENT_KEY}:{session_id}",
            idempotency_key=key,
            max_attempts=self._settings.worker_retry.max_attempts,
        )

        running = apply_start(
            state,
            source_ref=source_ref,
            model_profile=resolved_profile,
            max_attempts=self._settings.worker_retry.max_attempts,
        )
        running.run_id = str(run.id)
        running.job_id = str(job.id)
        running.attempt = 0
        updated = await self._repository.save_state(session_id, running, session.revision)
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.get_state(session_id)

    async def regenerate(
        self,
        session_id: UUID,
        *,
        model_profile: str = "",
        request_id: str = "",
    ) -> dict[str, Any]:
        session = await self._require_session(session_id)
        state = await self._repository.get_state(session_id)
        if state.status is BuildPreparationStatus.RUNNING:
            return await self.get_state(session_id)
        reset = reset_for_regeneration(state)
        updated = await self._repository.save_state(session_id, reset, session.revision)
        if updated is None:
            self._revision_conflict(session.revision, session.revision + 1)
        return await self.start(
            session_id,
            model_profile=model_profile or state.model_profile,
            request_id=request_id,
        )

    async def get_state(self, session_id: UUID) -> dict[str, Any]:
        session = await self._require_session(session_id)
        state = await self._repository.get_state(session_id)
        stale = False
        stale_reasons: list[str] = []
        current_source_ref: BuildPreparationSourceRef | None = None
        try:
            content_architect = await self._repository.get_content_architect_snapshot(session_id)
            visual_design_director = await self._repository.get_visual_design_director_snapshot(
                session_id
            )
            has_approved_inputs = (
                content_architect.approved is not None
                and visual_design_director.approved is not None
            )
            if has_approved_inputs:
                current_source_ref = self._input_integrator.compose(
                    content_architect,
                    visual_design_director,
                ).source_ref
                upstream_stale = (
                    current_source_ref.visual_design_director_direction_hash
                    != state.source_ref.visual_design_director_direction_hash
                    or current_source_ref.input_projection_hash
                    != state.source_ref.input_projection_hash
                ) and state.status is not BuildPreparationStatus.NOT_STARTED
                if upstream_stale:
                    stale_reasons.append("approved_upstream_changed")
                stale = upstream_stale
            elif state.status is not BuildPreparationStatus.NOT_STARTED and (
                state.source_ref.input_projection_hash or state.content_brief_markdown
            ):
                stale = True
                stale_reasons.append("approved_upstream_unavailable")
        except Exception:
            current_source_ref = None

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
                        "execution_lane": getattr(job, "execution_lane", None),
                        "attempt": job.attempt,
                        "error": job.error_payload,
                    }
                )
        payload = state.model_dump(mode="json")
        payload["elapsed_seconds"] = _elapsed_seconds(state.started_at)
        payload["stale"] = stale
        payload["stale_reasons"] = list(dict.fromkeys(stale_reasons))
        if current_source_ref is not None:
            payload["current_source_ref"] = current_source_ref.model_dump(mode="json")
        if state.run_id:
            try:
                run = await self._repository.get_run(UUID(state.run_id))
            except Exception:
                run = None
            if run is not None and run.status == "succeeded":
                receipt = frontend_cache_receipt(run.model_metadata, run_id=state.run_id)
                if receipt:
                    payload["cache_receipt"] = receipt
        return {
            "session_id": str(session_id),
            "session_revision": session.revision,
            "build_preparation": payload,
            "jobs": jobs,
        }

    async def download_brief(self, session_id: UUID, doc: str = "content") -> tuple[bytes, str]:
        """Return one of the two Markdown briefs as UTF-8 bytes."""
        state_response = await self.get_state(session_id)
        payload = state_response["build_preparation"]
        if bool(payload.get("stale")):
            raise BuildPreparationOperationError(
                "BUILD_PREPARATION_BRIEF_STALE",
                "The Build Preparation briefs are stale. Regenerate them before downloading.",
                details={"stale_reasons": payload.get("stale_reasons", [])},
            )
        field = "visual_brief_markdown" if doc == "visual" else "content_brief_markdown"
        markdown = str(payload.get(field, "") or "")
        if not markdown:
            raise BuildPreparationOperationError(
                "BUILD_PREPARATION_BRIEF_NOT_READY",
                "Build Preparation has not produced this brief yet.",
            )
        return markdown.encode("utf-8"), "text/markdown; charset=utf-8"

    async def _require_session(self, session_id: UUID) -> Any:
        session = await self._repository.get_session(session_id)
        if session is None:
            raise BuildPreparationOperationError(
                "SESSION_NOT_FOUND", "Portfolio session was not found.", status_code=404
            )
        return session

    def _require_approved_upstream(
        self, content_architect: Any, visual_design_director: Any
    ) -> None:
        if (
            content_architect.status is not ContentArchitectStatus.APPROVED
            or content_architect.approved is None
        ):
            raise BuildPreparationOperationError(
                "BUILD_PREPARATION_CONTENT_ARCHITECT_NOT_APPROVED",
                "Content Architect must be approved before Build Preparation can start.",
                details={"content_architect_status": content_architect.status.value},
            )
        if (
            visual_design_director.status is not VisualDesignDirectorStatus.APPROVED
            or visual_design_director.approved is None
        ):
            raise BuildPreparationOperationError(
                "BUILD_PREPARATION_VISUAL_DESIGN_DIRECTOR_NOT_APPROVED",
                "Visual Design Director must be approved before Build Preparation can start.",
                details={"visual_design_director_status": visual_design_director.status.value},
            )

    @staticmethod
    def _idempotency_key(
        session_id: UUID,
        source_ref: BuildPreparationSourceRef,
        model_profile: str,
        attempt: int,
    ) -> str:
        value = json.dumps(
            {
                "session_id": str(session_id),
                "source_ref": source_ref.model_dump(mode="json"),
                "model_profile": model_profile,
                "attempt": attempt,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _revision_conflict(expected: int, actual: int) -> NoReturn:
        raise BuildPreparationOperationError(
            "BUILD_PREPARATION_REVISION_CONFLICT",
            "The session changed while Build Preparation was starting. Reload and try again.",
            details={"expected_revision": expected, "actual_revision": actual},
        )

    @staticmethod
    def _not_ready(operation: str, status: str, message: str = "") -> NoReturn:
        raise BuildPreparationOperationError(
            "BUILD_PREPARATION_NOT_READY",
            message or f"Build Preparation is not ready to {operation} from state '{status}'.",
            details={"status": status},
        )


def _elapsed_seconds(started_at: str | None) -> float | None:
    if not started_at:
        return None
    try:
        started = datetime.fromisoformat(started_at)
    except ValueError:
        return None
    return max(0.0, (datetime.now(UTC) - started).total_seconds())
