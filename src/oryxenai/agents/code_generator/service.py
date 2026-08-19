"""Production session service for explicit Code Generator execution."""

from __future__ import annotations

import base64
import hashlib
import shutil
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, NoReturn
from uuid import UUID, uuid4

from oryxenai.agents.build_preparation.schemas import BuildPreparationStatus
from oryxenai.agents.code_generator.core.development_schemas import (
    AdmittedInputReference,
    DevelopmentRunStatus,
)
from oryxenai.agents.code_generator.core.development_service import browser_ready
from oryxenai.agents.code_generator.core.stage_attempt import (
    StageAttemptToken,
    StageCoordinator,
    fingerprint_input,
    stage_idempotency_key,
)
from oryxenai.agents.code_generator.session_schemas import (
    CodeGeneratorSessionState,
    CodeGeneratorSessionStatus,
    CodeGeneratorSourceRef,
    ProviderPreflightEnvelope,
)
from oryxenai.agents.shared.model_client import build_provider_client, resolve_api_key
from oryxenai.db.repositories.code_generator import CodeGeneratorRepository
from oryxenai.jobs.service import JobService
from oryxenai.storage.artifacts import (
    ArtifactReference,
    ArtifactStorageError,
    ArtifactStore,
    create_artifact_store,
    is_expired,
)

_PREFLIGHT_TTL_SECONDS = 300.0
_PREFLIGHT_CACHE: dict[str, float] = {}


class CodeGeneratorOperationError(Exception):
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


PreflightCallable = Callable[[str], Awaitable[dict[str, Any]]]


class CodeGeneratorService:
    def __init__(
        self,
        repository: CodeGeneratorRepository,
        jobs: JobService,
        settings: Any,
        *,
        artifact_store: ArtifactStore | None = None,
        provider_preflight: PreflightCallable | None = None,
    ) -> None:
        self._repo = repository
        self._jobs = jobs
        self._settings = settings
        self._artifact_store = artifact_store
        self._provider_preflight = provider_preflight

    async def start(
        self,
        session_id: UUID,
        *,
        idempotency_key: str,
        model_profile: str = "",
    ) -> dict[str, Any]:
        if not idempotency_key.strip():
            raise CodeGeneratorOperationError(
                "IDEMPOTENCY_KEY_REQUIRED",
                "Idempotency-Key is required.",
                status_code=400,
            )
        session = await self._require_session(session_id)
        state = await self._repo.get_state(session_id)
        current = (
            await self._repo.runs.get(UUID(state.current_run_id)) if state.current_run_id else None
        )
        if current is not None and current.status not in {
            DevelopmentRunStatus.READY.value,
            DevelopmentRunStatus.NEEDS_ATTENTION.value,
        }:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_RUN_IN_PROGRESS",
                "A Code Generator attempt is already in progress for this session.",
            )

        preparation = await self._repo.get_build_preparation_state(session_id)
        if preparation.status is not BuildPreparationStatus.READY:
            self._not_ready("Build Preparation has not reached ready status.")
        if preparation.package is None or preparation.handoff_report is None:
            self._not_ready("Build Preparation has no verified package and handoff report.")
        report = preparation.handoff_report
        if (
            not report.handoff_eligible
            or report.status != "ready_for_handoff"
            or report.execution_gaps
            or not report.upstream_approval_verified
        ):
            self._not_ready("Build Preparation is not eligible for Code Generator handoff.")
        artifact = preparation.package.artifact
        if artifact is None:
            self._not_ready("The verified Build Preparation artifact reference is missing.")
        if (
            preparation.package.archive_sha256 != artifact.sha256
            or preparation.package.archive_size_bytes != artifact.size_bytes
        ):
            self._not_ready("Build Preparation package and artifact identities do not match.")
        if is_expired(artifact):
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_ARTIFACT_EXPIRED",
                "The Build Preparation artifact expired and must be regenerated.",
            )
        if artifact.size_bytes > int(
            self._settings.code_generator_development.max_uncompressed_bytes
        ):
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_ARTIFACT_TOO_LARGE",
                "The Build Preparation artifact exceeds the configured Code Generator limit.",
            )

        stored = await self._verify_artifact_head(artifact)
        profile = self._settings.code_generator_development.planner_profile
        if model_profile and model_profile != profile:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_PROFILE_OVERRIDE_UNSUPPORTED",
                "Code Generator model selection is controlled by the configured profile.",
                status_code=400,
            )
        preflight = await self._preflight(profile)
        source_ref = CodeGeneratorSourceRef(
            build_preparation_run_id=preparation.run_id,
            build_preparation_scope_hash=preparation.scope_hash,
            build_preparation_source_ref=preparation.source_ref.model_dump(mode="json"),
            archive_sha256=preparation.package.archive_sha256,
            artifact=artifact,
            bound_session_revision=session.revision,
        )
        scope = f"code_generator:{session_id}"
        existing = await self._repo.runs.find_idempotent(idempotency_key, scope=scope)
        if existing is not None:
            existing_sha = str((existing.artifact_reference or {}).get("sha256", ""))
            if existing_sha != artifact.sha256:
                raise CodeGeneratorOperationError(
                    "IDEMPOTENCY_KEY_CONFLICT",
                    "Idempotency-Key was already used for another Build Preparation artifact.",
                )
            return await self.get_state(session_id)

        input_reference = AdmittedInputReference(
            mode="build_preparation_artifact",
            source_id=preparation.run_id or artifact.sha256,
            original_filename=f"build-preparation-{artifact.sha256[:12]}.zip",
            source_sha256=artifact.sha256,
            stored_relative_path="",
            size_bytes=artifact.size_bytes,
        )
        host = _session_preview_host(session_id)
        trace_id = uuid4().hex
        run = await self._repo.runs.create(
            input_reference=input_reference.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            idempotency_scope=scope,
            auto_advance=True,
            run_mode="session",
            portfolio_session_id=session_id,
            build_preparation_source_ref=source_ref.model_dump(mode="json"),
            artifact_reference=artifact.model_dump(mode="json"),
            preflight_receipt={**preflight, "artifact_head": stored.model_dump(mode="json")},
            preview_host=host,
            pipeline_contract_version=str(
                getattr(
                    self._settings.code_generator_development,
                    "pipeline_contract_version",
                    "code-generator-v3",
                )
            ),
            trace_id=trace_id,
        )
        stage_attempt = None
        create_stage_attempt = getattr(self._repo.runs, "create_stage_attempt", None)
        if create_stage_attempt is not None:
            input_fingerprint = fingerprint_input(source_ref.model_dump(mode="json"))
            stage_attempt = await create_stage_attempt(
                run.id,
                stage="plan",
                input_fingerprint=input_fingerprint,
                idempotency_key=stage_idempotency_key(run.id, "plan", input_fingerprint),
                expected_run_revision=run.revision,
                trace_id=trace_id,
                worker_version=str(
                    getattr(
                        self._settings.code_generator_development,
                        "pipeline_contract_version",
                        "code-generator-v3",
                    )
                ),
            )
        await self._repo.runs.append_event(
            run.id,
            event_type="created",
            level="info",
            message="Session Code Generator run created from one immutable Build Preparation artifact.",
            details={"artifact_sha256": artifact.sha256, "run_mode": "session"},
        )
        job = await self._jobs.enqueue(
            "code_generator.plan",
            StageCoordinator.payload_for_attempt(
                StageAttemptToken(
                    attempt_id=stage_attempt.id,
                    run_id=run.id,
                    stage="plan",
                    attempt_no=stage_attempt.attempt_no,
                    expected_run_revision=run.revision,
                    input_fingerprint=stage_attempt.input_fingerprint,
                    trace_id=trace_id,
                ),
                {"code_generator_run_id": str(run.id)},
            )
            if stage_attempt is not None
            else {"code_generator_run_id": str(run.id)},
            max_attempts=int(self._settings.worker_retry.max_attempts),
            idempotency_scope="code_generator.plan",
            idempotency_key=f"{run.id}:{artifact.sha256}",
        )
        updated = await self._repo.runs.compare_and_swap(
            run.id,
            expected_revision=run.revision,
            values={
                "status": DevelopmentRunStatus.QUEUED.value,
                "background_job_id": job.id,
                **({"active_attempt_id": stage_attempt.id} if stage_attempt is not None else {}),
            },
        )
        if updated is None:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_REVISION_CONFLICT",
                "The Code Generator run changed while it was being queued.",
            )
        if stage_attempt is not None:
            bind_stage_attempt_job = getattr(self._repo.runs, "bind_stage_attempt_job", None)
            if bind_stage_attempt_job is not None:
                await bind_stage_attempt_job(stage_attempt.id, job_id=job.id)
        retained_preview = (
            dict(current.active_preview)
            if current is not None and current.active_preview
            else state.active_preview
        )
        next_state = CodeGeneratorSessionState(
            status=CodeGeneratorSessionStatus.QUEUED,
            current_run_id=str(run.id),
            model_profile=profile,
            source_ref=source_ref,
            active_preview=retained_preview,
            started_at=datetime.now(UTC).isoformat(),
            pipeline_contract_version=str(
                getattr(
                    self._settings.code_generator_development,
                    "pipeline_contract_version",
                    "code-generator-v3",
                )
            ),
            trace_id=trace_id,
        )
        saved = await self._repo.save_state(session_id, next_state, session.revision)
        if saved is None:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_SESSION_REVISION_CONFLICT",
                "The session changed while Code Generator was starting. Reload and try again.",
            )
        return await self.get_state(session_id)

    async def regenerate(
        self,
        session_id: UUID,
        *,
        idempotency_key: str,
        model_profile: str = "",
    ) -> dict[str, Any]:
        return await self.start(
            session_id,
            idempotency_key=idempotency_key,
            model_profile=model_profile,
        )

    async def get_state(self, session_id: UUID) -> dict[str, Any]:
        session = await self._require_session(session_id)
        state = await self._repo.get_state(session_id)
        run = (
            await self._repo.runs.get(UUID(state.current_run_id)) if state.current_run_id else None
        )
        payload = state.model_dump(mode="json")
        jobs: list[dict[str, Any]] = []
        if run is not None:
            payload["status"] = _session_status(run.status)
            payload["phase"] = run.status
            payload["run_revision"] = run.revision
            payload["pipeline_contract_version"] = str(
                getattr(run, "pipeline_contract_version", "code-generator-v3")
                or "code-generator-v3"
            )
            payload["trace_id"] = str(getattr(run, "trace_id", "") or "")
            payload["active_attempt_id"] = str(getattr(run, "active_attempt_id", "") or "")
            payload["issues"] = list(run.issues or [])
            payload["active_preview"] = run.active_preview or state.active_preview
            payload["progress"] = {
                "coordinator_stage": run.coordinator_stage,
                "current_attempt": run.current_attempt,
                "plan_summary": run.plan_summary or {},
                "source_summary": run.source_summary or {},
            }
            active_attempt_loader = getattr(self._repo.runs, "active_stage_attempt", None)
            if active_attempt_loader is not None:
                active_attempt = await active_attempt_loader(run.id)
                if active_attempt is not None:
                    payload["current_stage_attempt"] = {
                        "id": str(active_attempt.id),
                        "stage": active_attempt.stage,
                        "attempt_no": active_attempt.attempt_no,
                        "status": active_attempt.status,
                        "trace_id": active_attempt.trace_id or payload["trace_id"],
                    }
            if run.terminal_failure:
                payload["latest_error"] = run.terminal_failure
            for job_id in (
                run.background_job_id,
                run.acquire_job_id,
                run.generation_job_id,
                run.verification_job_id,
            ):
                if job_id is None:
                    continue
                job = await self._jobs.get(job_id)
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
        stale_reasons = await self._stale_reasons(session_id, state)
        payload["stale"] = bool(stale_reasons)
        payload["stale_reasons"] = stale_reasons
        return {
            "session_id": str(session_id),
            "session_revision": session.revision,
            "code_generator": payload,
            "jobs": jobs,
        }

    async def _verify_artifact_head(self, reference: ArtifactReference) -> ArtifactReference:
        try:
            store = self._artifact_store or create_artifact_store(self._settings)
            stored = await store.head(reference)
        except ArtifactStorageError as exc:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_ARTIFACT_UNAVAILABLE",
                "The Build Preparation artifact store could not be reached.",
                status_code=503,
                details={"provider_code": exc.code},
            ) from exc
        if stored is None:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_ARTIFACT_MISSING",
                "The Build Preparation artifact no longer exists.",
            )
        if stored.sha256 != reference.sha256 or stored.size_bytes != reference.size_bytes:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_ARTIFACT_CHANGED",
                "The Build Preparation artifact no longer matches its recorded identity.",
            )
        if reference.etag and stored.etag and reference.etag != stored.etag:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_ARTIFACT_CHANGED",
                "The Build Preparation artifact ETag changed after packaging.",
            )
        return stored

    async def _preflight(self, selected_profile: str) -> dict[str, Any]:
        profile_names = [
            self._settings.code_generator_development.director_profile,
            selected_profile,
            self._settings.code_generator_generation.foundation_profile,
            self._settings.code_generator_generation.route_profile,
            self._settings.code_generator_generation.compose_profile,
            self._settings.code_generator_generation.integration_profile,
            self._settings.code_generator_generation.repair_profile,
        ]
        identities: dict[str, str] = {}
        for name in dict.fromkeys(profile_names):
            profile = self._settings.models.get_profile(name)
            if profile is None or not profile.provider or not profile.model:
                raise CodeGeneratorOperationError(
                    "CODE_GENERATOR_PROFILE_UNAVAILABLE",
                    "A required Code Generator model profile is unavailable.",
                    status_code=503,
                    details={"profile": name},
                )
            if profile.capabilities is None or not profile.capabilities.json_schema_mode:
                raise CodeGeneratorOperationError(
                    "CODE_GENERATOR_STRICT_SCHEMA_UNSUPPORTED",
                    "A required Code Generator profile does not declare strict JSON Schema support.",
                    status_code=503,
                    details={"profile": name},
                )
            if not resolve_api_key(profile):
                raise CodeGeneratorOperationError(
                    "CODE_GENERATOR_PROVIDER_CREDENTIAL_MISSING",
                    "A required Code Generator provider credential is not configured.",
                    status_code=503,
                    details={"profile": name},
                )
            identity = hashlib.sha256(
                f"{profile.provider}:{profile.base_url}:{profile.api_key_env}:{profile.model}".encode()
            ).hexdigest()
            identities.setdefault(identity, name)
        npm = str(self._settings.code_generator_dependencies.npm_executable or "")
        if not npm or shutil.which(npm) is None:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_PACKAGE_MANAGER_UNAVAILABLE",
                "The configured package manager is unavailable.",
                status_code=503,
            )
        if not browser_ready(self._settings.code_generator_verification):
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_BROWSER_UNAVAILABLE",
                "The configured verification browser is unavailable.",
                status_code=503,
            )
        checked: list[str] = []
        for identity, profile_name in identities.items():
            if time.monotonic() - _PREFLIGHT_CACHE.get(identity, 0.0) <= _PREFLIGHT_TTL_SECONDS:
                checked.append(profile_name)
                continue
            try:
                if self._provider_preflight is not None:
                    await self._provider_preflight(profile_name)
                else:
                    client = build_provider_client(profile_name, self._settings.models)
                    if client is None:
                        raise RuntimeError("configured provider client is unavailable")
                    profile = self._settings.models.get_profile(profile_name)
                    result = await client.generate_structured(
                        operation="code_generator.provider_preflight",
                        instructions=(
                            "Return ok=true and protocol=code-generator-preflight-v1. "
                            "This fixed request contains no user or portfolio data."
                        ),
                        input_payload={"protocol": "code-generator-preflight-v1"},
                        output_model=ProviderPreflightEnvelope,
                        system_prompt="You are a transport preflight. Return only the required schema.",
                        model_profile=profile_name,
                        strict_schema=True,
                    )
                    envelope = ProviderPreflightEnvelope.model_validate(
                        getattr(result, "parsed_output", result)
                    )
                    if not envelope.ok or envelope.protocol != "code-generator-preflight-v1":
                        raise RuntimeError("provider preflight returned an invalid envelope")
            except Exception as exc:
                code = str(getattr(exc, "code", "PROVIDER_PREFLIGHT_FAILED"))
                raise CodeGeneratorOperationError(
                    code,
                    "The configured Code Generator provider did not pass its no-context preflight.",
                    status_code=503,
                    details={"profile": profile_name},
                ) from exc
            _PREFLIGHT_CACHE[identity] = time.monotonic()
            checked.append(profile_name)
        return {
            "status": "ready",
            "profile": selected_profile,
            "checked_profiles": checked,
            "checked_at": datetime.now(UTC).isoformat(),
            "private_context_sent": False,
        }

    async def _stale_reasons(self, session_id: UUID, state: CodeGeneratorSessionState) -> list[str]:
        if state.source_ref is None:
            return []
        try:
            preparation = await self._repo.get_build_preparation_state(session_id)
        except Exception:
            return ["build_preparation_unavailable"]
        reasons: list[str] = []
        if is_expired(state.source_ref.artifact):
            reasons.append("build_preparation_artifact_expired")
        if preparation.run_id != state.source_ref.build_preparation_run_id:
            reasons.append("build_preparation_run_changed")
        if preparation.scope_hash != state.source_ref.build_preparation_scope_hash:
            reasons.append("build_preparation_scope_changed")
        if (
            preparation.package is None
            or preparation.package.archive_sha256 != state.source_ref.archive_sha256
        ):
            reasons.append("build_preparation_artifact_changed")
        return reasons

    async def _require_session(self, session_id: UUID) -> Any:
        session = await self._repo.get_session(session_id)
        if session is None:
            raise CodeGeneratorOperationError(
                "SESSION_NOT_FOUND", "Portfolio session was not found.", status_code=404
            )
        return session

    @staticmethod
    def _not_ready(message: str) -> NoReturn:
        raise CodeGeneratorOperationError("CODE_GENERATOR_BUILD_PREPARATION_NOT_READY", message)


def _session_preview_host(session_id: UUID) -> str:
    encoded = base64.b32encode(hashlib.sha256(str(session_id).encode()).digest()).decode().lower()
    return f"session-{encoded[:24].rstrip('=')}"


def _session_status(run_status: str) -> str:
    if run_status == DevelopmentRunStatus.READY.value:
        return CodeGeneratorSessionStatus.READY.value
    if run_status == DevelopmentRunStatus.NEEDS_ATTENTION.value:
        return CodeGeneratorSessionStatus.NEEDS_ATTENTION.value
    if run_status in {
        DevelopmentRunStatus.PLANNING.value,
        DevelopmentRunStatus.ADMITTING.value,
        DevelopmentRunStatus.PLANNED.value,
    }:
        return CodeGeneratorSessionStatus.PLANNING.value
    if run_status in {DevelopmentRunStatus.ACQUIRING.value, DevelopmentRunStatus.ACQUIRED.value}:
        return CodeGeneratorSessionStatus.ACQUIRING.value
    if run_status in {
        DevelopmentRunStatus.GENERATING_FOUNDATION.value,
        DevelopmentRunStatus.GENERATING_ROUTES.value,
        DevelopmentRunStatus.INTEGRATING.value,
        DevelopmentRunStatus.SOURCE_READY.value,
    }:
        return CodeGeneratorSessionStatus.GENERATING.value
    if run_status in {
        DevelopmentRunStatus.BUILDING.value,
        DevelopmentRunStatus.SMOKE_TESTING.value,
        DevelopmentRunStatus.REPAIRING.value,
    }:
        return CodeGeneratorSessionStatus.VERIFYING.value
    return CodeGeneratorSessionStatus.QUEUED.value
