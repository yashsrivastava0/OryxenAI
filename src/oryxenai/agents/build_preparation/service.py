"""Application service for the durable Build Preparation pipeline."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any, NoReturn
from uuid import UUID, uuid4

from oryxenai.agents.build_preparation.compiler import build_source_ref
from oryxenai.agents.build_preparation.schemas import (
    BuildPreparationSourceRef,
    BuildPreparationStatus,
)
from oryxenai.agents.build_preparation.state import apply_start, reset_for_regeneration
from oryxenai.agents.content_architect.schemas import ContentArchitectStatus
from oryxenai.agents.visual_design_director.schemas import VisualDesignDirectorStatus
from oryxenai.core.settings import get_settings
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.build_preparation import BuildPreparationRepository
from oryxenai.jobs.service import JobService
from oryxenai.storage.artifacts import (
    ArtifactStorageError,
    ArtifactStore,
    create_artifact_store,
    is_expired,
)

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
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self._repository = repository
        self._job_service = job_service
        self._artifact_store = artifact_store
        self._settings = get_settings()

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

        ca_payload = self._content_projection(content_architect)
        vdd_payload = self._visual_projection(visual_design_director)
        source_ref = build_source_ref(
            ca_payload,
            vdd_payload,
            content_architect_session_revision=session.revision,
            visual_design_director_session_revision=session.revision,
        )
        resolved_profile = model_profile or state.model_profile or "build_preparation"
        key = self._idempotency_key(session_id, source_ref, resolved_profile, state.attempt)
        run = AgentRun(
            id=uuid4(),
            portfolio_session_id=session_id,
            agent_key=_AGENT_KEY,
            status="pending",
            input_payload={
                "operation": "build",
                "model_profile": resolved_profile,
                "max_routes": self._settings.build_preparation.max_routes,
                "live_model": self._settings.build_preparation.reasoning_enabled,
                "live_providers": self._settings.build_preparation.reasoning_enabled,
                "output_dir": self._settings.build_preparation.fixture_output_dir,
                "artifact_upload": True,
                "debug_mirror": self._settings.build_preparation.debug_mirror_enabled,
                "bundle_expires_at": (
                    datetime.now(UTC)
                    + timedelta(days=max(1, self._settings.build_preparation.bundle_ttl_days))
                ).isoformat(),
                "integration_route_threshold": self._settings.build_preparation.integration_route_threshold,
                "source_ref": source_ref.model_dump(mode="json"),
                "content_architect": ca_payload,
                "visual_design_director": vdd_payload,
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
            if (
                content_architect.approved is not None
                and visual_design_director.approved is not None
            ):
                current_source_ref = build_source_ref(
                    self._content_projection(content_architect),
                    self._visual_projection(visual_design_director),
                )
                upstream_stale = (
                    current_source_ref.visual_design_director_direction_hash
                    != state.source_ref.visual_design_director_direction_hash
                    or current_source_ref.input_projection_hash
                    != state.source_ref.input_projection_hash
                ) and state.status is not BuildPreparationStatus.NOT_STARTED
                if upstream_stale:
                    stale_reasons.append("approved_upstream_changed")
                stale = upstream_stale
        except Exception:
            current_source_ref = None

        if state.package is not None:
            if is_expired(
                state.package.artifact or _empty_artifact_reference(state.package.expires_at)
            ):
                stale = True
                stale_reasons.append("artifact_expired")
            reference = state.package.artifact
            if reference is not None and reference.provider != "memory":
                try:
                    store = self._artifact_store or create_artifact_store(self._settings)
                    stored = await store.head(reference)
                    if stored is None:
                        stale = True
                        stale_reasons.append("artifact_missing")
                    elif (
                        stored.sha256 != reference.sha256
                        or stored.size_bytes != reference.size_bytes
                    ):
                        stale = True
                        stale_reasons.append("artifact_changed")
                except ArtifactStorageError:
                    stale = True
                    stale_reasons.append("artifact_unavailable")

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
        payload = state.model_dump(mode="json")
        payload["elapsed_seconds"] = _elapsed_seconds(state.started_at)
        payload["stale"] = stale
        payload["stale_reasons"] = list(dict.fromkeys(stale_reasons))
        if current_source_ref is not None:
            payload["current_source_ref"] = current_source_ref.model_dump(mode="json")
        return {
            "session_id": str(session_id),
            "session_revision": session.revision,
            "build_preparation": payload,
            "jobs": jobs,
        }

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
    def _content_projection(state: Any) -> dict[str, Any]:
        return {
            "approved": state.approved.model_dump(mode="json") if state.approved else {},
            "route_plan": [route.model_dump(mode="json") for route in state.route_plan],
            "page_content_packs": [
                {**pack.model_dump(mode="json"), "internal_notes": {}}
                for pack in state.page_content_packs
            ],
            "public_content_manifest": state.public_content_manifest,
        }

    @staticmethod
    def _visual_projection(state: Any) -> dict[str, Any]:
        return {
            "approved": state.approved.model_dump(mode="json") if state.approved else {},
            "pages": [page.model_dump(mode="json") for page in state.pages],
            "asset_briefs": [asset.model_dump(mode="json") for asset in state.asset_briefs],
            "resource_candidates": [
                resource.model_dump(mode="json") for resource in state.resource_candidates
            ],
        }

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


def _empty_artifact_reference(expires_at: str) -> Any:
    """Provide a non-persisted reference so expiry uses one parser."""
    from oryxenai.storage.artifacts import ArtifactReference

    return ArtifactReference(
        provider="memory",
        key="expiry-only",
        sha256="0" * 64,
        size_bytes=0,
        expires_at=expires_at,
    )
