"""Application service and worker-facing preparation operation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

from oryxenai.agents.content_architect.schemas import ContentArchitectStatus
from oryxenai.agents.visual_design_director.schemas import VisualDesignDirectorStatus
from oryxenai.build_preparation.bundle import BundleIntegrityError, create_bundle
from oryxenai.build_preparation.compiler import (
    BlueprintCompilationError,
    compile_blueprint,
    compile_context,
)
from oryxenai.build_preparation.fingerprints import (
    preparation_input_hash,
    projection_hash,
    source_fingerprints,
)
from oryxenai.build_preparation.resources import (
    catalogue_hash,
    deduplicate_entries,
    resolve_local_requirements,
    resolve_remote_requirements,
)
from oryxenai.build_preparation.schemas import (
    ArtifactObjectRef,
    BuildPreparationState,
    BuildPreparationStatus,
    SourceRef,
)
from oryxenai.build_preparation.storage import ArtifactStore, ArtifactStoreError, build_r2_store
from oryxenai.core.logging import get_logger
from oryxenai.core.settings import Settings, get_settings
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.agent_runs import AgentRunRepository
from oryxenai.db.repositories.content_architect import ContentArchitectRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.db.repositories.visual_design_director import VisualDesignDirectorRepository
from oryxenai.jobs.service import JobService

logger = get_logger("oryxenai.build_preparation")
BUILD_KIND = "build_preparation.prepare"


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


def load_target_contract() -> dict[str, Any]:
    path = (
        Path(__file__).resolve().parent / "resources" / "targets" / "react_vite_v1" / "target.json"
    )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("target contract must be an object")
        return cast(dict[str, Any], value)
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildPreparationOperationError(
            "TARGET_CONTRACT_INVALID", "The generated frontend target contract is invalid."
        ) from exc


def target_contract_hash() -> str:
    return hashlib.sha256(
        json.dumps(load_target_contract(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_policy_hash(settings: Settings) -> str:
    return projection_hash(
        settings.build_preparation.model_dump(mode="json"),
        settings.artifact_storage.model_dump(mode="json"),
        settings.resource_providers.model_dump(mode="json"),
        {"catalogue_hash": catalogue_hash()},
    )


def provider_availability() -> dict[str, bool]:
    return {"pexels": bool(os.environ.get("PEXELS_API_KEY", "").strip())}


def source_ref_for(content: Any, visual: Any, fingerprints: dict[str, str]) -> SourceRef:
    return SourceRef(
        discovery_brief_hash=str(getattr(content.source_ref, "discovery_brief_hash", "")),
        content_hash=str(content.approved.content_hash if content.approved else ""),
        visual_direction_hash=str(visual.approved.visual_direction_hash if visual.approved else ""),
        route_publication_hash=fingerprints["route_publication_hash"],
        discovery_projection_hash=fingerprints["discovery_projection_hash"],
        content_projection_hash=fingerprints["content_projection_hash"],
        visual_projection_hash=fingerprints["visual_projection_hash"],
        content_session_revision=int(getattr(content.source_ref, "discovery_session_revision", 0)),
        visual_session_revision=int(
            getattr(visual.source_ref, "content_architect_session_revision", 0)
        ),
        captured_at=datetime.now(UTC).isoformat(),
    )


def compute_current_input(
    content: Any, visual: Any, settings: Settings
) -> tuple[SourceRef, str, str, str]:
    content_dump = content.model_dump(mode="json")
    visual_dump = visual.model_dump(mode="json")
    fingerprints = source_fingerprints(content_dump, visual_dump)
    source = source_ref_for(content, visual, fingerprints)
    policy = build_policy_hash(settings)
    target_contract = load_target_contract()
    configured_target = settings.build_preparation.target_contract.strip()
    if configured_target and str(target_contract.get("target_id", "")) != configured_target:
        raise BuildPreparationOperationError(
            "TARGET_CONTRACT_MISMATCH",
            "The configured frontend target contract is unavailable.",
            details={"configured": configured_target},
        )
    target = target_contract_hash()
    return (
        source,
        preparation_input_hash(
            fingerprints,
            policy_hash=policy,
            target_contract_hash=target,
            provider_availability=provider_availability(),
        ),
        policy,
        target,
    )


def _store_for(settings: Settings, artifact_store: ArtifactStore | None) -> ArtifactStore:
    if artifact_store is not None:
        return artifact_store
    if settings.artifact_storage.provider == "memory":
        from oryxenai.build_preparation.storage import memory_artifact_store

        return memory_artifact_store()
    if settings.artifact_storage.provider not in {"r2_s3", "r2"}:
        raise ArtifactStoreError("unsupported artifact storage provider")
    return build_r2_store(
        settings.artifact_storage,
        ttl_days=settings.build_preparation.bundle_ttl_days,
    )


class BuildPreparationService:
    def __init__(
        self,
        db: Any,
        *,
        settings: Settings | None = None,
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self._db = db
        self._settings = settings or get_settings()
        self._store: ArtifactStore | None = artifact_store
        self._store_error = ""
        if self._store is None:
            try:
                self._store = _store_for(self._settings, None)
            except Exception as exc:
                logger.warning(
                    "artifact store unavailable provider=%s",
                    self._settings.artifact_storage.provider,
                )
                self._store_error = (
                    str(exc)
                    if isinstance(exc, ArtifactStoreError)
                    else "artifact storage is unavailable"
                )
        self._sessions = PortfolioSessionRepository(db)
        self._runs = AgentRunRepository(db)
        self._content = ContentArchitectRepository(db)
        self._visual = VisualDesignDirectorRepository(db)
        self._jobs = JobService(db)

    async def start(
        self, session_id: UUID, *, model_profile: str = "", request_id: str = ""
    ) -> dict[str, Any]:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise BuildPreparationOperationError(
                "SESSION_NOT_FOUND", "Portfolio session was not found.", status_code=404
            )
        content = await self._content.get_content_architect_state(session_id)
        visual = await self._visual.get_visual_design_director_state(session_id)
        if content.status is not ContentArchitectStatus.APPROVED or content.approved is None:
            raise BuildPreparationOperationError(
                "CONTENT_NOT_APPROVED",
                "Content Architect must be approved before Build Preparation can start.",
            )
        if visual.status is not VisualDesignDirectorStatus.APPROVED or visual.approved is None:
            raise BuildPreparationOperationError(
                "VISUAL_NOT_APPROVED",
                "Visual Design Director must be approved before Build Preparation can start.",
            )
        source, input_hash, policy_hash, target_hash = compute_current_input(
            content, visual, self._settings
        )
        current = BuildPreparationState.model_validate(
            session.current_state.get("build_preparation", {})
        )
        if current.status is BuildPreparationStatus.PREPARING:
            return await self.get_state(session_id)
        if (
            current.status is BuildPreparationStatus.READY
            and current.preparation_input_hash == input_hash
            and current.bundle_ref
        ):
            expiry = _parse_datetime(current.bundle_ref.expires_at)
            if self._store is not None and expiry > datetime.now(UTC) + timedelta(
                hours=self._settings.build_preparation.minimum_reuse_hours
            ):
                try:
                    verified = await self._store.head(current.bundle_ref.object_key)
                except ArtifactStoreError as exc:
                    raise BuildPreparationOperationError(
                        "ARTIFACT_STORE_UNAVAILABLE",
                        "Temporary artifact storage could not verify the existing pack.",
                        status_code=503,
                    ) from exc
                if verified is not None and verified.sha256 == current.bundle_ref.sha256:
                    return await self.get_state(session_id)

        if self._store is None:
            raise BuildPreparationOperationError(
                "ARTIFACT_STORAGE_NOT_CONFIGURED",
                "Temporary artifact storage is not configured for Build Preparation.",
                details={"provider": self._settings.artifact_storage.provider},
            )

        retry_nonce = (
            current.run_id
            if current.status
            in {BuildPreparationStatus.NEEDS_ATTENTION, BuildPreparationStatus.READY}
            else ""
        )
        key = hashlib.sha256(
            json.dumps(
                {
                    "session": str(session_id),
                    "input": input_hash,
                    "policy": policy_hash,
                    "target": target_hash,
                    "retry": retry_nonce,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        existing = await self._runs.find_by_idempotency(session_id, "build_preparation", key)
        if existing is not None and existing.status in {"pending", "running"}:
            return await self.get_state(session_id)
        run = AgentRun(
            id=uuid4(),
            portfolio_session_id=session_id,
            agent_key="build_preparation",
            status="pending",
            input_payload={
                "operation": "prepare",
                "source": source.model_dump(mode="json"),
                "input_hash": input_hash,
                "policy_hash": policy_hash,
                "target_contract_hash": target_hash,
                "model_profile": model_profile,
            },
            state_before=dict(session.current_state),
            idempotency_key=key,
        )
        await self._runs.create(run)
        job = await self._jobs.enqueue(
            BUILD_KIND,
            {
                "portfolio_session_id": str(session_id),
                "agent_run_id": str(run.id),
                "expected_session_revision": session.revision + 1,
                "request_id": request_id,
            },
            max_attempts=self._settings.worker_retry.max_attempts,
            idempotency_scope=f"build_preparation:{session_id}",
            idempotency_key=key,
        )
        next_state = BuildPreparationState(
            status=BuildPreparationStatus.PREPARING,
            preparation_id=str(uuid4()),
            model_profile=model_profile,
            run_id=str(run.id),
            job_id=str(job.id),
            max_attempts=self._settings.worker_retry.max_attempts,
            source_ref=source,
            preparation_input_hash=input_hash,
            policy_hash=policy_hash,
            target_contract_hash=target_hash,
            started_at=datetime.now(UTC).isoformat(),
        )
        await self._save_state(session_id, next_state, session.revision)
        return await self.get_state(session_id)

    async def get_state(self, session_id: UUID) -> dict[str, Any]:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise BuildPreparationOperationError(
                "SESSION_NOT_FOUND", "Portfolio session was not found.", status_code=404
            )
        state = BuildPreparationState.model_validate(
            session.current_state.get("build_preparation", {})
        )
        try:
            content = await self._content.get_content_architect_state(session_id)
            visual = await self._visual.get_visual_design_director_state(session_id)
            _, current_hash, policy, target = compute_current_input(content, visual, self._settings)
            reasons: list[str] = []
            if state.preparation_input_hash and state.preparation_input_hash != current_hash:
                reasons.append("upstream_or_policy_changed")
            if state.policy_hash and state.policy_hash != policy:
                reasons.append("policy_changed")
            if state.target_contract_hash and state.target_contract_hash != target:
                reasons.append("target_contract_changed")
            if state.bundle_ref and _parse_datetime(state.bundle_ref.expires_at) <= datetime.now(
                UTC
            ):
                reasons.append("bundle_expired")
            state.stale_reasons = sorted(set(reasons))
            state.stale = bool(reasons)
        except Exception:
            state.stale = True
            state.stale_reasons = ["unable_to_verify_current_sources"]
        jobs: list[dict[str, Any]] = []
        if state.job_id:
            job = await self._jobs.get(UUID(state.job_id))
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
        return {
            "session_id": str(session_id),
            "session_revision": session.revision,
            "build_preparation": payload,
            "jobs": jobs,
        }

    async def prepare_job(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        session_id = UUID(str(payload["portfolio_session_id"]))
        run_id = UUID(str(payload["agent_run_id"]))
        attempt = int(payload.get("attempt", 1))
        max_attempts = int(payload.get("max_attempts", self._settings.worker_retry.max_attempts))
        run = await self._runs.get_by_id(run_id)
        session = await self._sessions.get_by_id(session_id)
        if run is None or session is None:
            raise ValueError("Build Preparation run or session was not found")
        if run.status == "succeeded":
            return {
                "status": "succeeded",
                "run_id": str(run_id),
                "operation": "prepare",
                "reused": True,
            }
        await self._runs.mark_started(run_id)
        content = await self._content.get_content_architect_state(session_id)
        visual = await self._visual.get_visual_design_director_state(session_id)
        try:
            source, current_hash, policy_hash, target_hash = compute_current_input(
                content, visual, self._settings
            )
        except BuildPreparationOperationError as exc:
            return await self._fail(
                session_id,
                run_id,
                attempt,
                max_attempts,
                {"code": exc.code, "message": exc.message, "retryable": False},
            )
        expected_hash = str(run.input_payload.get("input_hash", ""))
        if expected_hash != current_hash:
            return await self._fail(
                session_id,
                run_id,
                attempt,
                max_attempts,
                {
                    "code": "BUILD_PREPARATION_STALE_SOURCE",
                    "message": "Approved Content or Visual Design changed while preparation was queued.",
                    "retryable": False,
                },
            )
        state = BuildPreparationState.model_validate(
            session.current_state.get("build_preparation", {})
        )
        state.attempt = attempt
        try:
            await self._save_state(session_id, state, session.revision)
        except BuildPreparationOperationError as exc:
            return await self._fail(
                session_id,
                run_id,
                attempt,
                max_attempts,
                {"code": exc.code, "message": exc.message, "retryable": True},
            )
        parent: Path | None = None
        try:
            blueprint, packets, warnings = compile_blueprint(
                content,
                visual,
                source=source,
                preparation_hash=current_hash,
                max_routes=self._settings.build_preparation.max_routes,
                target_contract_hash=target_hash,
            )
            manifest = resolve_local_requirements(
                blueprint.resource_requirements, pexels_available=provider_availability()["pexels"]
            )
            remote_entries, resource_files, provider_warnings = await resolve_remote_requirements(
                blueprint.resource_requirements,
                settings=self._settings,
                target_contract=load_target_contract(),
            )
            remote_requirement_ids = {
                requirement_id
                for entry in remote_entries
                for requirement_id in entry.requirement_ids
            }
            manifest.entries = [
                entry
                for entry in manifest.entries
                if not remote_requirement_ids.intersection(entry.requirement_ids)
            ] + remote_entries
            manifest.entries, manifest.deduplication = deduplicate_entries(manifest.entries)
            manifest.warnings = sorted(set(manifest.warnings + provider_warnings))
            manifest.policy_hash = policy_hash
            manifest.manifest_hash = hashlib.sha256(
                json.dumps(
                    manifest.model_dump(mode="json", exclude={"manifest_hash"}),
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            context = compile_context(
                blueprint, packets, manifest, target_contract=load_target_contract()
            )
            parent = Path(tempfile.mkdtemp(prefix="oryxenai-build-preparation-"))
            bundle, bundle_sha, bundle_size = create_bundle(
                blueprint,
                manifest,
                context,
                packets,
                target_contract=load_target_contract(),
                resource_files=resource_files,
                max_bundle_bytes=self._settings.build_preparation.max_bundle_bytes,
                workspace_dir=parent,
            )
            expires_at = datetime.now(UTC) + timedelta(
                days=self._settings.build_preparation.bundle_ttl_days
            )
            object_key = f"{self._settings.artifact_storage.prefix.rstrip('/')}/sessions/{session_id}/versions/{current_hash}/runs/{run_id}/bundle-{bundle_sha}.zip"
            if self._store is None:
                raise ArtifactStoreError(self._store_error or "artifact storage is not configured")
            stored = await self._store.put(
                object_key,
                bundle,
                expires_at=expires_at,
                metadata={"input-hash": current_hash, "schema-version": "1"},
            )
            final_session = await self._sessions.get_by_id(session_id)
            final_content = await self._content.get_content_architect_state(session_id)
            final_visual = await self._visual.get_visual_design_director_state(session_id)
            _, final_hash, _, _ = compute_current_input(final_content, final_visual, self._settings)
            if final_session is None or final_hash != current_hash:
                return await self._fail(
                    session_id,
                    run_id,
                    attempt,
                    max_attempts,
                    {
                        "code": "BUILD_PREPARATION_STALE_SOURCE",
                        "message": "Approved upstream artifacts changed during preparation.",
                        "retryable": False,
                    },
                )
            ref = ArtifactObjectRef(
                storage_profile=self._settings.artifact_storage.provider,
                bucket=self._settings.artifact_storage.bucket,
                object_key=stored.object_key,
                etag=stored.etag,
                sha256=stored.sha256,
                size_bytes=stored.size_bytes,
                content_type=stored.content_type,
                created_at=datetime.now(UTC).isoformat(),
                expires_at=stored.expires_at.isoformat(),
                last_verified_at=datetime.now(UTC).isoformat(),
            )
            ready = BuildPreparationState.model_validate(state.model_dump(mode="json"))
            ready.status = BuildPreparationStatus.READY
            ready.bundle_ref = ref
            ready.warnings = sorted(set(warnings + manifest.warnings + blueprint.warnings))
            ready.completed_at = datetime.now(UTC).isoformat()
            ready.latest_error = None
            await self._save_state(session_id, ready, final_session.revision)
            saved = await self._sessions.get_by_id(session_id)
            await self._runs.mark_succeeded(
                run_id,
                {
                    "status": "succeeded",
                    "bundle": ref.model_dump(mode="json"),
                    "blueprint_hash": blueprint.blueprint_hash,
                    "manifest_hash": manifest.manifest_hash,
                    "context_hash": context.context_hash,
                },
                dict(saved.current_state) if saved else {},
                model_metadata={"result_status": "succeeded"},
            )
            await self._db.commit()
            return {
                "status": "succeeded",
                "run_id": str(run_id),
                "operation": "prepare",
                "bundle_sha256": bundle_sha,
                "bundle_size": bundle_size,
            }
        except (BlueprintCompilationError, BundleIntegrityError) as exc:
            return await self._fail(
                session_id,
                run_id,
                attempt,
                max_attempts,
                {
                    "code": getattr(exc, "code", "BUILD_PREPARATION_INVALID"),
                    "message": str(exc),
                    "retryable": False,
                },
            )
        except ArtifactStoreError as exc:
            return await self._fail(
                session_id,
                run_id,
                attempt,
                max_attempts,
                {"code": "ARTIFACT_STORE_UNAVAILABLE", "message": str(exc), "retryable": True},
            )
        except Exception as exc:
            logger.warning("build preparation failed error=%s", type(exc).__name__)
            return await self._fail(
                session_id,
                run_id,
                attempt,
                max_attempts,
                {
                    "code": "BUILD_PREPARATION_FAILED",
                    "message": "Build Preparation failed safely.",
                    "retryable": False,
                },
            )
        finally:
            if parent is not None:
                shutil.rmtree(parent, ignore_errors=True)

    async def _fail(
        self, session_id: UUID, run_id: UUID, attempt: int, max_attempts: int, error: dict[str, Any]
    ) -> dict[str, Any]:
        session = await self._sessions.get_by_id(session_id)
        if session is not None and (not error.get("retryable") or attempt >= max_attempts):
            state = BuildPreparationState.model_validate(
                session.current_state.get("build_preparation", {})
            )
            state.status = BuildPreparationStatus.NEEDS_ATTENTION
            state.attempt = attempt
            state.latest_error = {
                "code": error.get("code", "BUILD_PREPARATION_FAILED"),
                "message": error.get("message", "Build Preparation failed safely."),
                "retryable": bool(error.get("retryable", False)),
            }
            await self._save_state(session_id, state, session.revision)
        await self._runs.mark_failed(run_id, error)
        await self._db.commit()
        return {"status": "failed", "run_id": str(run_id), "operation": "prepare", "error": error}

    async def _save_state(
        self, session_id: UUID, state: BuildPreparationState, expected_revision: int
    ) -> None:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise BuildPreparationOperationError(
                "SESSION_NOT_FOUND", "Portfolio session was not found.", status_code=404
            )
        new_state = dict(session.current_state)
        new_state["build_preparation"] = state.model_dump(mode="json")
        updated = await self._sessions.update_state(session_id, new_state, expected_revision)
        if updated is None:
            raise BuildPreparationOperationError(
                "REVISION_CONFLICT", "The session changed while Build Preparation was running."
            )


def _parse_datetime(value: str) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _elapsed_seconds(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return max(0.0, (datetime.now(UTC) - _parse_datetime(value)).total_seconds())
    except ValueError:
        return 0.0
