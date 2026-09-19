"""Production session service for explicit Code Generator execution."""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, NoReturn
from uuid import UUID, uuid4

from sqlalchemy import select

from oryxenai.agents.build_preparation.input_integrator import BuildPreparationInputIntegrator
from oryxenai.agents.build_preparation.schemas import BuildPreparationStatus
from oryxenai.agents.code_generator.core.coordinator import advance_after
from oryxenai.agents.code_generator.core.design_variant import create_design_variant_receipt
from oryxenai.agents.code_generator.core.development_input import DevelopmentInputAdapter
from oryxenai.agents.code_generator.core.development_schemas import (
    DesignFingerprintV1,
    DesignVariantReceiptV1,
    DevelopmentRunStatus,
)
from oryxenai.agents.code_generator.core.development_service import browser_ready
from oryxenai.agents.code_generator.core.pipeline_contract import (
    stage_job_kind,
    stage_scope,
    uses_blueprint,
    uses_v5_namespace,
)
from oryxenai.agents.code_generator.core.provider_preflight import (
    code_generator_wire_schema_issues,
)
from oryxenai.agents.code_generator.core.quality_review import (
    normalize_persisted_quality_review_for_read,
)
from oryxenai.agents.code_generator.core.stage_attempt import (
    StageAttemptToken,
    StageCoordinator,
    fingerprint_input,
    stage_idempotency_key,
)
from oryxenai.agents.code_generator.core.worker_readiness import worker_contract_readiness
from oryxenai.agents.code_generator.session_schemas import (
    CodeGeneratorSessionState,
    CodeGeneratorSessionStatus,
    CodeGeneratorSourceRef,
    ProviderPreflightEnvelope,
)
from oryxenai.agents.content_architect.schemas import ContentArchitectState
from oryxenai.agents.shared.model_client import build_provider_client, resolve_api_key
from oryxenai.agents.shared.providers.errors import stable_provider_failure
from oryxenai.agents.visual_design_director.schemas import VisualDesignDirectorState
from oryxenai.auth.authorization import durable_snapshot
from oryxenai.auth.domain import AuthRole
from oryxenai.auth.errors import (
    EntitlementBindingConflictError,
    GenerationVariantLockedError,
    PortfolioReadOnlyError,
)
from oryxenai.auth.models import AppUser
from oryxenai.core.logging import get_logger
from oryxenai.db.repositories.code_generator import CodeGeneratorRepository
from oryxenai.db.session import get_sessionmaker
from oryxenai.jobs.handlers.code_generator_failure import reconcile_terminal_failure
from oryxenai.jobs.service import JobService
from oryxenai.storage.artifacts import (
    ArtifactReference,
    ArtifactStorageError,
    ArtifactStore,
    create_artifact_store,
)

_PREFLIGHT_TTL_SECONDS = 300.0
_PREFLIGHT_CACHE: dict[str, float] = {}
logger = get_logger("oryxenai.agents.code_generator.service")


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
        creation_reason: str = "initial",
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
        normal_entitlement = await self._normal_owner_entitlement(session_id)
        if normal_entitlement is not None:
            if normal_entitlement.successful_run_id is not None:
                raise PortfolioReadOnlyError()
            # A normal account has one immutable generation variant.  A
            # changed idempotency key must not trigger external preflight or a
            # second variant; the canonical server binding wins.
            if normal_entitlement.generation_run_id is not None:
                return await self.get_state(session_id)
        if current is not None and current.status not in {
            DevelopmentRunStatus.READY.value,
            DevelopmentRunStatus.NEEDS_ATTENTION.value,
            DevelopmentRunStatus.PREVIEW_PENDING.value,
        }:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_RUN_IN_PROGRESS",
                "A Code Generator attempt is already in progress for this session.",
            )

        preparation = await self._repo.get_build_preparation_state(session_id)
        if preparation.status is not BuildPreparationStatus.READY:
            self._not_ready("Build Preparation has not reached ready status.")
        content_brief = str(getattr(preparation, "content_brief_markdown", "") or "")
        visual_brief = str(getattr(preparation, "visual_brief_markdown", "") or "")
        if not content_brief.strip() or not visual_brief.strip():
            self._not_ready("Build Preparation has not produced both Markdown briefs.")
        await self._ensure_build_preparation_current(session, preparation)
        worker_readiness = await worker_contract_readiness(self._repo, self._settings)
        if worker_readiness.get("checked") and not worker_readiness.get("ready"):
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_WORKER_NOT_READY",
                "No compatible Code Generator worker is ready to claim this run.",
                status_code=409,
                details={"worker_contract": worker_readiness},
            )
        profile = self._settings.code_generator_development.planner_profile
        if model_profile and model_profile != profile:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_PROFILE_OVERRIDE_UNSUPPORTED",
                "Code Generator model selection is controlled by the configured profile.",
                status_code=400,
            )
        try:
            reference = DevelopmentInputAdapter(self._settings).from_build_preparation_briefs(
                source_id=preparation.run_id or preparation.scope_hash or "build-preparation",
                content_markdown=content_brief,
                visual_markdown=visual_brief,
            )
        except Exception as exc:
            if isinstance(exc, CodeGeneratorOperationError):
                raise
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_BRIEF_INVALID",
                "Build Preparation produced briefs that do not satisfy the Code Generator contract.",
                status_code=409,
                details={"reason": str(exc)[:500]},
            ) from exc
        try:
            receipt, _projections = DevelopmentInputAdapter(self._settings).admit(reference)
        except Exception as exc:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_BRIEF_INVALID",
                "The Build Preparation brief pair failed immutable admission.",
                status_code=409,
                details={"reason": str(exc)[:500]},
            ) from exc
        stored_content_hash = str(getattr(preparation, "content_brief_hash", "") or "")
        stored_visual_hash = str(getattr(preparation, "visual_brief_hash", "") or "")
        if stored_content_hash and stored_content_hash != receipt.content_brief_sha256:
            self._not_ready("The persisted content brief hash does not match its Markdown body.")
        if stored_visual_hash and stored_visual_hash != receipt.visual_brief_sha256:
            self._not_ready("The persisted visual brief hash does not match its Markdown body.")
        preflight = await self._preflight(profile)
        source_ref = CodeGeneratorSourceRef(
            build_preparation_run_id=preparation.run_id,
            build_preparation_scope_hash=preparation.scope_hash,
            build_preparation_source_ref=preparation.source_ref.model_dump(mode="json"),
            content_brief_sha256=receipt.content_brief_sha256,
            visual_brief_sha256=receipt.visual_brief_sha256,
            brief_contract_hash=receipt.contract_hash,
            bound_session_revision=session.revision,
        )
        scope = f"code_generator:{session_id}"
        existing = await self._repo.runs.find_idempotent(idempotency_key, scope=scope)
        if existing is not None:
            existing_source = str((existing.input_reference or {}).get("source_sha256", ""))
            if existing_source != reference.source_sha256:
                raise CodeGeneratorOperationError(
                    "IDEMPOTENCY_KEY_CONFLICT",
                    "Idempotency-Key was already used for another Build Preparation brief pair.",
                )
            return await self.get_state(session_id)
        pipeline_contract_version = str(
            getattr(
                self._settings.code_generator_development,
                "pipeline_contract_version",
                "code-generator-v4",
            )
        )
        variant_receipt: DesignVariantReceiptV1 | None = None
        prior_fingerprints: list[DesignFingerprintV1] = []
        if uses_blueprint(pipeline_contract_version):
            history_limit = int(self._settings.code_generator_development.design_similarity_history)
            accepted_variants = getattr(self._repo.runs, "accepted_variants_for_session", None)
            prior_runs = (
                await accepted_variants(session_id, limit=history_limit)
                if accepted_variants is not None
                else []
            )
            prior_ordinals: list[int] = []
            for prior in reversed(prior_runs):
                creative = prior.creative_direction or {}
                fingerprint_payload = creative.get("design_fingerprint")
                variant_payload = creative.get("variant_receipt")
                if isinstance(fingerprint_payload, dict):
                    with suppress(ValueError):
                        prior_fingerprints.append(
                            DesignFingerprintV1.model_validate(fingerprint_payload)
                        )
                if isinstance(variant_payload, dict):
                    with suppress(ValueError):
                        prior_ordinals.append(
                            DesignVariantReceiptV1.model_validate(variant_payload).ordinal
                        )
            variant_receipt = create_design_variant_receipt(
                input_hash=hashlib.sha256(
                    f"{receipt.contract_hash}:{preparation.scope_hash}".encode()
                ).hexdigest(),
                ordinal=max(prior_ordinals, default=0) + 1,
                idempotency_key=idempotency_key,
                creation_reason="regenerate" if current is not None else creation_reason,
                prior_fingerprint_hashes=[
                    item.fingerprint_hash for item in prior_fingerprints[-history_limit:]
                ],
            )
        entitlement_revision: int | None = None
        if normal_entitlement is not None:
            normal_entitlement = await self._repo.entitlements.get_for_user(
                self._normal_owner_id(), lock=True
            )
            if normal_entitlement is None or normal_entitlement.portfolio_session_id != session_id:
                raise EntitlementBindingConflictError()
            if normal_entitlement.successful_run_id is not None:
                raise PortfolioReadOnlyError()
            if normal_entitlement.generation_run_id is not None:
                return await self.get_state(session_id)
            entitlement_revision = normal_entitlement.revision + 1
            context = getattr(self._jobs, "authorization_context", None)
            if context is None:
                raise EntitlementBindingConflictError()
            self._jobs.authorization_context = replace(
                context, entitlement_revision=entitlement_revision
            )
        context = getattr(self._jobs, "authorization_context", None)
        if context is not None and context.authorization_context_version != 1:
            raise EntitlementBindingConflictError()
        lock_session = getattr(self._repo, "get_session_for_update", None)
        bound_session = await lock_session(session_id) if lock_session is not None else session
        if bound_session is None:
            raise CodeGeneratorOperationError(
                "SESSION_NOT_FOUND", "Portfolio session was not found.", status_code=404
            )
        if bound_session.revision != session.revision:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_SESSION_REVISION_CONFLICT",
                "The portfolio changed while Code Generator was preparing. Reload and try again.",
            )
        if context is not None and (
            bound_session.legacy_quarantined
            or bound_session.owner_user_id != context.owner_user_id
            or context.portfolio_session_id != session_id
        ):
            raise EntitlementBindingConflictError()
        session = bound_session
        run_snapshot = durable_snapshot(getattr(self._jobs, "authorization_context", None))
        if run_snapshot["portfolio_session_id"] is None:
            run_snapshot["portfolio_session_id"] = session_id
        trace_id = uuid4().hex
        run = await self._repo.runs.create(
            input_reference=reference.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            idempotency_scope=scope,
            auto_advance=True,
            run_mode="session",
            build_preparation_source_ref=source_ref.model_dump(mode="json"),
            artifact_reference=None,
            preflight_receipt=preflight,
            preview_host=_session_preview_host(session_id),
            pipeline_contract_version=pipeline_contract_version,
            trace_id=trace_id,
            creative_direction=(
                {
                    "variant_receipt": variant_receipt.model_dump(mode="json"),
                    "prior_fingerprints": [
                        item.model_dump(mode="json") for item in prior_fingerprints
                    ],
                }
                if variant_receipt is not None
                else None
            ),
            **run_snapshot,
        )
        if normal_entitlement is not None:
            await self._repo.entitlements.bind_generation_run(
                user_id=self._normal_owner_id(),
                session_id=session_id,
                run_id=run.id,
                revision=normal_entitlement.revision,
                actor_user_id=getattr(self._jobs.authorization_context, "actor_user_id", None),
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
                worker_version=pipeline_contract_version,
            )
        await self._repo.runs.append_event(
            run.id,
            event_type="created",
            level="info",
            message="Session Code Generator run created from the immutable Build Preparation brief pair.",
            details={
                "content_brief_sha256": receipt.content_brief_sha256,
                "visual_brief_sha256": receipt.visual_brief_sha256,
                "brief_contract_hash": receipt.contract_hash,
                "run_mode": "session",
            },
        )
        job_payload: dict[str, Any] = {"code_generator_run_id": str(run.id)}
        if uses_v5_namespace(pipeline_contract_version):
            job_payload.update(
                {
                    "required_pipeline_contract_version": pipeline_contract_version,
                    "required_worker_release_id": str(
                        getattr(
                            self._settings.code_generator_development,
                            "worker_release_id",
                            "",
                        )
                        or ""
                    ),
                }
            )
        if stage_attempt is not None:
            job_payload = StageCoordinator.payload_for_attempt(
                StageAttemptToken(
                    attempt_id=stage_attempt.id,
                    run_id=run.id,
                    stage="plan",
                    attempt_no=stage_attempt.attempt_no,
                    expected_run_revision=run.revision,
                    input_fingerprint=stage_attempt.input_fingerprint,
                    trace_id=trace_id,
                ),
                job_payload,
            )
        plan_kind = stage_job_kind("plan", pipeline_contract_version)
        job = await self._jobs.enqueue(
            plan_kind,
            job_payload,
            max_attempts=int(self._settings.worker_retry.code_generator_max_attempts),
            idempotency_scope=stage_scope("plan", pipeline_contract_version),
            idempotency_key=f"{run.id}:{reference.source_sha256}",
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
            candidate_preview=state.candidate_preview,
            started_at=datetime.now(UTC).isoformat(),
            pipeline_contract_version=pipeline_contract_version,
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
        if await self._normal_owner_entitlement(session_id) is not None:
            raise GenerationVariantLockedError()
        return await self.start(
            session_id,
            idempotency_key=idempotency_key,
            model_profile=model_profile,
            creation_reason="regenerate",
        )

    async def retry(
        self,
        session_id: UUID,
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Retry the failed stage while preserving the admitted design variant.

        Regeneration creates a new run and may ask for a new creative
        direction.  Retry only requeues the first incomplete durable stage on
        the existing run, so its variant receipt, accepted plan, source
        checkpoint, and previously promoted preview remain intact.
        """

        if not idempotency_key.strip():
            raise CodeGeneratorOperationError(
                "IDEMPOTENCY_KEY_REQUIRED",
                "Idempotency-Key is required.",
                status_code=400,
            )
        session = await self._require_session(session_id)
        state = await self._repo.get_state(session_id)
        if not state.current_run_id:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_RUN_NOT_FOUND",
                "There is no Code Generator run to retry.",
                status_code=409,
            )
        run = await self._repo.runs.get(UUID(state.current_run_id))
        if run is None:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_RUN_NOT_FOUND",
                "The current Code Generator run no longer exists.",
                status_code=409,
            )
        # A failed worker can leave the run row on its previous stage status
        # for a short window. Reconcile that terminal job before applying the
        # retry-state guard so the recovery button can actually requeue the
        # same run instead of reporting that generation is still in progress.
        run = await self._reconcile_terminal_active_job(run)
        normal_entitlement = await self._normal_owner_entitlement(session_id)
        if normal_entitlement is not None:
            if normal_entitlement.successful_run_id is not None:
                raise PortfolioReadOnlyError()
            await self._repo.entitlements.assert_bound_retry(
                user_id=self._normal_owner_id(),
                session_id=session_id,
                run_id=run.id,
                revision=normal_entitlement.revision,
            )
            context = getattr(self._jobs, "authorization_context", None)
            if context is None:
                raise EntitlementBindingConflictError()
            self._jobs.authorization_context = replace(
                context, entitlement_revision=normal_entitlement.revision
            )
        if run.status == DevelopmentRunStatus.READY.value:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_RETRY_NOT_ALLOWED",
                "This run is already ready; use regenerate to request a new design variant.",
                status_code=409,
            )
        if run.status not in {
            DevelopmentRunStatus.NEEDS_ATTENTION.value,
            DevelopmentRunStatus.PREVIEW_PENDING.value,
        }:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_RUN_IN_PROGRESS",
                "The current Code Generator stage is still running.",
                status_code=409,
            )
        stale_reasons = await self._stale_reasons(session_id, state)
        if stale_reasons:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_SOURCE_STALE",
                "The approved Build Preparation brief source changed; start a new run from the latest briefs.",
                status_code=409,
                details={"stale_reasons": stale_reasons},
            )

        # Retry is the other short durable mutation transaction.  A normal
        # entitlement is already locked by assert_bound_retry; acquire the
        # session and exact run next, then create only the next stage attempt
        # and job while those identity bindings remain stable.
        lock_session = getattr(self._repo, "get_session_for_update", None)
        bound_session = await lock_session(session_id) if lock_session is not None else session
        if bound_session is None or bound_session.revision != session.revision:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_SESSION_REVISION_CONFLICT",
                "The portfolio changed while retry was being prepared. Reload and try again.",
            )
        session = bound_session
        get_run = self._repo.runs.get
        try:
            locked_run = await get_run(run.id, lock=True)
        except TypeError:
            # Small in-memory service fixtures predate the optional lock
            # argument; production repositories always take the row lock.
            locked_run = await get_run(run.id)
        if locked_run is None:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_RUN_NOT_FOUND",
                "The current Code Generator run no longer exists.",
                status_code=409,
            )
        context = getattr(self._jobs, "authorization_context", None)
        if context is not None and (
            context.authorization_context_version != 1
            or context.portfolio_session_id != session_id
            or locked_run.portfolio_session_id != session_id
            or locked_run.owner_user_id != context.owner_user_id
            or locked_run.actor_user_id != context.actor_user_id
        ):
            raise EntitlementBindingConflictError()
        run = locked_run
        if run.status == DevelopmentRunStatus.READY.value:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_RETRY_NOT_ALLOWED",
                "This run is already ready; the existing variant cannot be retried.",
                status_code=409,
            )
        if run.status not in {
            DevelopmentRunStatus.NEEDS_ATTENTION.value,
            DevelopmentRunStatus.PREVIEW_PENDING.value,
        }:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_RUN_IN_PROGRESS",
                "The current Code Generator stage is still running.",
                status_code=409,
            )

        stage = _retry_stage(run)
        retry_scope = "code_generator.retry"
        retry_key = f"{run.id}:{idempotency_key.strip()}"
        find_idempotent = getattr(self._jobs, "find_idempotent", None)
        if find_idempotent is not None:
            existing_job = await find_idempotent(retry_scope, retry_key)
            if existing_job is not None:
                return await self.get_state(session_id)

        stage_material = _retry_stage_material(run, stage)
        creative_direction = getattr(run, "creative_direction", None)
        creative_payload = creative_direction if isinstance(creative_direction, dict) else {}
        input_fingerprint = fingerprint_input(
            {
                "stage": stage,
                "material": stage_material,
                "variant_id": str(
                    (creative_payload.get("variant_receipt", {}) or {}).get("variant_id", "")
                ),
            }
        )
        stage_attempt = None
        create_stage_attempt = getattr(self._repo.runs, "create_stage_attempt", None)
        if create_stage_attempt is not None:
            stage_attempt = await create_stage_attempt(
                run.id,
                stage=stage,
                input_fingerprint=input_fingerprint,
                idempotency_key=stage_idempotency_key(
                    run.id, stage, input_fingerprint, attempt_no=run.revision + 1
                ),
                expected_run_revision=run.revision,
                trace_id=str(getattr(run, "trace_id", "") or ""),
                worker_version=str(
                    getattr(run, "pipeline_contract_version", "code-generator-v4")
                    or "code-generator-v4"
                ),
            )
        pipeline_contract_version = str(
            getattr(run, "pipeline_contract_version", "code-generator-v4") or "code-generator-v4"
        )
        job_field = {
            "plan": "background_job_id",
            "acquire": "acquire_job_id",
            "generate": "generation_job_id",
            "verify": "verification_job_id",
        }[stage]
        job_kind = stage_job_kind(stage, pipeline_contract_version)
        payload: dict[str, Any] = {"code_generator_run_id": str(run.id)}
        if uses_v5_namespace(pipeline_contract_version):
            payload.update(
                {
                    "required_pipeline_contract_version": pipeline_contract_version,
                    "required_worker_release_id": str(
                        getattr(
                            self._settings.code_generator_development,
                            "worker_release_id",
                            "",
                        )
                        or ""
                    ),
                }
            )
        if stage_attempt is not None:
            payload = StageCoordinator.payload_for_attempt(
                StageAttemptToken(
                    attempt_id=stage_attempt.id,
                    run_id=run.id,
                    stage=stage,
                    attempt_no=stage_attempt.attempt_no,
                    expected_run_revision=run.revision,
                    input_fingerprint=input_fingerprint,
                    trace_id=str(getattr(run, "trace_id", "") or ""),
                ),
                payload,
            )
        job = await self._jobs.enqueue(
            job_kind,
            payload,
            max_attempts=int(self._settings.worker_retry.code_generator_max_attempts),
            idempotency_scope=retry_scope,
            idempotency_key=retry_key,
        )
        updated = await self._repo.runs.compare_and_swap(
            run.id,
            expected_revision=run.revision,
            values={
                "status": DevelopmentRunStatus.QUEUED.value,
                "coordinator_stage": stage,
                job_field: job.id,
                "active_attempt_id": stage_attempt.id if stage_attempt is not None else None,
                "issues": [],
                "terminal_failure": None,
            },
        )
        if updated is None:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_REVISION_CONFLICT",
                "The Code Generator run changed while retry was being queued.",
            )
        if stage_attempt is not None:
            bind_stage_attempt_job = getattr(self._repo.runs, "bind_stage_attempt_job", None)
            if bind_stage_attempt_job is not None:
                await bind_stage_attempt_job(stage_attempt.id, job_id=job.id)
        await self._repo.runs.append_event(
            run.id,
            event_type="retry_queued",
            level="info",
            message=f"Retry queued for the existing {stage} stage without changing the design variant.",
            details={"stage": stage, "variant_id": _variant_id(run)},
        )
        next_state = state.model_copy(
            update={
                "status": CodeGeneratorSessionStatus.QUEUED,
                "latest_error": None,
                "retry_status": f"queued:{stage}",
                "trace_id": str(getattr(run, "trace_id", "") or state.trace_id),
                "active_preview": run.active_preview or state.active_preview,
                "candidate_preview": state.candidate_preview,
            }
        )
        saved = await self._repo.save_state(session_id, next_state, session.revision)
        if saved is None:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_SESSION_REVISION_CONFLICT",
                "The session changed while retry was being queued. Reload and try again.",
            )
        return await self.get_state(session_id)

    async def get_state(self, session_id: UUID) -> dict[str, Any]:
        session = await self._require_session(session_id)
        state = await self._repo.get_state(session_id)
        run = (
            await self._repo.runs.get(UUID(state.current_run_id)) if state.current_run_id else None
        )
        admin_override = await self._is_admin_run_override(session_id, run)
        normal_entitlement = await self._normal_owner_entitlement(session_id)
        if normal_entitlement is not None:
            if (
                normal_entitlement.generation_run_id is None
                and state.current_run_id is not None
                and not admin_override
            ):
                # A normal user's entitlement, not a mutable JSON projection,
                # decides which production run exists. Do not expose a legacy
                # or manually inserted run as a new entitlement.
                raise EntitlementBindingConflictError()
            if (
                normal_entitlement.generation_run_id is not None
                and state.current_run_id != str(normal_entitlement.generation_run_id)
                and not admin_override
            ):
                # The entitlement is the authoritative run binding. A stale
                # or manually altered session projection must fail closed.
                raise EntitlementBindingConflictError()
        if (
            normal_entitlement is not None
            and normal_entitlement.generation_run_id is not None
            and not admin_override
        ):
            context = getattr(self._jobs, "authorization_context", None)
            successful_replay = (
                normal_entitlement.successful_run_id == normal_entitlement.generation_run_id
            )
            if (
                run is None
                or str(getattr(run, "run_mode", "")) != "session"
                or run.portfolio_session_id != session_id
                or context is None
                or run.owner_user_id != context.owner_user_id
                or run.actor_user_id != context.actor_user_id
                or run.authorization_context_version != 1
                or run.entitlement_revision is None
                or (
                    run.entitlement_revision != normal_entitlement.revision
                    and not (
                        successful_replay
                        and run.entitlement_revision + 1 == normal_entitlement.revision
                    )
                )
            ):
                raise EntitlementBindingConflictError()
        run = await self._reconcile_terminal_active_job(run)
        stale_reasons = await self._stale_reasons(session_id, state)
        payload = state.model_dump(mode="json")
        jobs: list[dict[str, Any]] = []
        if run is not None:
            payload["status"] = _session_status(run.status)
            payload["phase"] = run.status
            payload["run_revision"] = run.revision
            payload["pipeline_contract_version"] = str(
                getattr(run, "pipeline_contract_version", "code-generator-v4")
                or "code-generator-v4"
            )
            payload["trace_id"] = str(getattr(run, "trace_id", "") or "")
            payload["active_attempt_id"] = str(getattr(run, "active_attempt_id", "") or "")
            payload["issues"] = list(run.issues or [])
            payload["active_preview"] = run.active_preview or state.active_preview
            verification_payload = getattr(run, "verification_projection", None) or {}
            payload["candidate_preview"] = (
                verification_payload.get("candidate_preview")
                if isinstance(verification_payload, dict)
                else None
            )
            payload["warnings"] = (
                verification_payload.get("advisories", [])
                if isinstance(verification_payload, dict)
                else []
            )
            payload["creative_direction"] = run.creative_direction or {}
            creative = run.creative_direction or {}
            payload["design_variant"] = creative.get("variant_receipt")
            payload["design_fingerprint"] = creative.get("design_fingerprint")
            generation_projection = getattr(run, "generation_projection", None) or {}
            quality_review = generation_projection.get("quality_review")
            payload["quality_review"] = (
                normalize_persisted_quality_review_for_read(quality_review)
                if isinstance(quality_review, dict)
                else quality_review
            )
            payload["realization_contracts"] = verification_payload.get(
                "verification_plan", {}
            ).get("realization_contracts", [])
            payload["progress"] = {
                "coordinator_stage": run.coordinator_stage,
                "current_attempt": run.current_attempt,
                "plan_summary": run.plan_summary or {},
                "source_summary": run.source_summary or {},
            }
            # Additive-only: `stage_estimate` is a new sub-object under the
            # existing `progress` key. No existing key above is read or
            # changed by this block. Local import mirrors `coordinator.py`'s
            # own precedent (settings are resolved lazily, not at module
            # scope, so lightweight test fixtures that omit unrelated
            # settings attributes stay compatible).
            from oryxenai.core.settings import get_settings

            payload["progress"]["stage_estimate"] = _compute_stage_estimate(
                stage_durations_ms=getattr(run, "stage_durations_ms", None),
                created_at=getattr(run, "created_at", None),
                now=datetime.now(UTC),
                timeout_for=get_settings().worker_job.timeout_for,
            )
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
                            "execution_lane": getattr(job, "execution_lane", None),
                            "attempt": job.attempt,
                            "max_attempts": getattr(job, "max_attempts", None),
                            "created_at": _safe_job_timestamp(getattr(job, "created_at", None)),
                            "started_at": _safe_job_timestamp(getattr(job, "started_at", None)),
                            "heartbeat_at": _safe_job_timestamp(getattr(job, "heartbeat_at", None)),
                            "finished_at": _safe_job_timestamp(getattr(job, "finished_at", None)),
                            "error": _safe_job_error(getattr(job, "error_payload", None)),
                        }
                    )

            stage_job_fields = {
                "plan": "background_job_id",
                "acquire": "acquire_job_id",
                "generate": "generation_job_id",
                "verify": "verification_job_id",
                "preview": "verification_job_id",
            }
            coordinator_stage = str(getattr(run, "coordinator_stage", "") or "")
            active_job_field = stage_job_fields.get(coordinator_stage)
            active_job_id = (
                getattr(run, active_job_field, None) if active_job_field is not None else None
            )
            active_job = next(
                (job for job in jobs if job["id"] == str(active_job_id)),
                None,
            )
            active_job_terminal = active_job is not None and active_job["status"] in {
                "failed",
                "cancelled",
            }
            run_retryable = str(getattr(run, "status", "")) in {
                DevelopmentRunStatus.NEEDS_ATTENTION.value,
                DevelopmentRunStatus.PREVIEW_PENDING.value,
            }
            # These are additive fields on the existing state response; they
            # do not introduce a second polling endpoint or alter run state.
            payload["active_job_id"] = str(active_job_id) if active_job_id is not None else None
            payload["active_job_kind"] = active_job["kind"] if active_job is not None else None
            payload["retry_available"] = bool(
                not stale_reasons
                and _manual_retry_allowed(run)
                and (run_retryable or active_job_terminal)
            )
        else:
            payload["active_job_id"] = None
            payload["active_job_kind"] = None
            payload["retry_available"] = False
        payload["stale"] = bool(stale_reasons)
        payload["stale_reasons"] = stale_reasons
        return {
            "session_id": str(session_id),
            "session_revision": session.revision,
            "code_generator": payload,
            "jobs": jobs,
        }

    async def _reconcile_terminal_active_job(self, run: Any | None) -> Any | None:
        """Repair legacy/stuck runs whose selected durable job is terminal.

        New failures are reconciled by the worker hook.  This read-path repair
        is intentionally idempotent and covers rows created before that hook
        existed or a worker process that exited between job failure and the
        hook.  Authorization failures remain fail-closed and are not turned
        into a manual retry affordance.
        """

        if run is None or str(getattr(run, "status", "")) == DevelopmentRunStatus.READY.value:
            return run
        stage_job_fields = {
            "plan": "background_job_id",
            "acquire": "acquire_job_id",
            "generate": "generation_job_id",
            "verify": "verification_job_id",
            "preview": "verification_job_id",
        }
        stage = str(getattr(run, "coordinator_stage", "") or "")
        job_field = stage_job_fields.get(stage)
        job_id = getattr(run, job_field, None) if job_field is not None else None
        if job_id is None:
            return run
        job = await self._jobs.get(job_id)
        if job is None or str(getattr(job, "status", "")) not in {"failed", "cancelled"}:
            return run
        error = _safe_job_error(getattr(job, "error_payload", None)) or {
            "code": "CODE_GENERATOR_JOB_FAILED",
            "message": "Code Generator stopped before this stage completed.",
            "retryable": False,
        }
        code = str(error.get("code") or "").upper()
        if code.startswith(("AUTHORIZATION", "ENTITLEMENT", "SECURITY", "PORTFOLIO_READ_ONLY")):
            return run

        # A stage checkpoint is authoritative evidence that the failed job
        # completed its own work. Repair the missing successor handoff before
        # projecting a user-facing attention state. This self-heals runs
        # created by older workers (and failures between checkpoint commit and
        # enqueue) without requiring the user to leave the frontend and
        # manually launch the application.
        completed_stage = _checkpointed_completion_stage(run, stage)
        if completed_stage is not None:
            try:
                advanced = await advance_after(
                    get_sessionmaker(self._settings),
                    run.id,
                    completed_stage=completed_stage,
                )
            except Exception as exc:
                logger.warning(
                    "checkpointed Code Generator handoff recovery deferred run_id=%s "
                    "stage=%s error=%s",
                    run.id,
                    stage,
                    type(exc).__name__,
                )
                advanced = False
            if advanced:
                local_session = getattr(self._repo, "_session", None)
                refresh = getattr(local_session, "refresh", None)
                if refresh is not None:
                    with suppress(Exception):
                        await refresh(run)
                refreshed = await self._repo.runs.get(run.id)
                return refreshed or run

        await reconcile_terminal_failure(
            {
                "code_generator_run_id": str(run.id),
                "development_run_id": str(run.id),
                "job_id": str(job.id),
                "job_kind": str(getattr(job, "job_kind", "")),
            },
            {**error, "retryable": False, "will_retry": False},
        )
        local_session = getattr(self._repo, "_session", None)
        refresh = getattr(local_session, "refresh", None)
        if refresh is not None:
            with suppress(Exception):
                await refresh(run)
        refreshed = await self._repo.runs.get(run.id)
        return refreshed or run

    async def _is_admin_run_override(self, session_id: UUID, run: Any | None) -> bool:
        """Allow a durable admin-on-owner run without weakening normal entitlement state."""

        context = getattr(self._jobs, "authorization_context", None)
        if (
            run is None
            or context is None
            or context.authorization_context_version != 1
            or context.owner_user_id is None
            or context.owner_user_id != context.actor_user_id
            or getattr(run, "run_mode", "") != "session"
            or getattr(run, "portfolio_session_id", None) != session_id
            or getattr(run, "owner_user_id", None) != context.owner_user_id
            or getattr(run, "actor_user_id", None) in {None, context.owner_user_id}
            or getattr(run, "authorization_context_version", 0) != 1
        ):
            return False
        actor_id = getattr(run, "actor_user_id", None)
        if actor_id is None:
            return False
        db = getattr(self._repo, "_session", None)
        if db is None:
            return False
        result = await db.execute(
            select(AppUser.role, AppUser.status).where(AppUser.id == actor_id)
        )
        actor = result.one_or_none()
        return actor is not None and actor[0] == AuthRole.ADMIN.value and actor[1] == "active"

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
        wire_schema_issues = code_generator_wire_schema_issues()
        incompatible = {name: issues for name, issues in wire_schema_issues.items() if issues}
        if incompatible:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_WIRE_SCHEMA_UNSUPPORTED",
                "A Code Generator structured-output schema is not provider-compatible.",
                status_code=503,
                details={
                    "schemas": "; ".join(
                        f"{name}:{','.join(issues)}" for name, issues in incompatible.items()
                    )[:1000]
                },
            )
        profile_names = [
            self._settings.code_generator_development.director_profile,
            selected_profile,
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
            if (
                profile.capabilities is None
                or not profile.capabilities.json_schema_mode
                or profile.capabilities.structured_output_mode != "native_json_schema"
            ):
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
                json.dumps(
                    {
                        "provider": profile.provider,
                        "base_url": profile.base_url,
                        "model": profile.model,
                        "capabilities": profile.capabilities.model_dump(mode="json")
                        if profile.capabilities is not None
                        else {},
                        "max_output_tokens": profile.max_output_tokens,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
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
                    try:
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
                    finally:
                        close = getattr(client, "aclose", None)
                        if close is not None:
                            await close()
                    envelope = ProviderPreflightEnvelope.model_validate(
                        getattr(result, "parsed_output", result)
                    )
                    if not envelope.ok or envelope.protocol != "code-generator-preflight-v1":
                        raise RuntimeError("provider preflight returned an invalid envelope")
            except Exception as exc:
                code, message = stable_provider_failure(exc)
                raise CodeGeneratorOperationError(
                    code,
                    message,
                    status_code=503,
                    details={},
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
        if preparation.run_id != state.source_ref.build_preparation_run_id:
            reasons.append("build_preparation_run_changed")
        if preparation.scope_hash != state.source_ref.build_preparation_scope_hash:
            reasons.append("build_preparation_scope_changed")
        if str(getattr(preparation, "content_brief_hash", "") or "") not in {
            "",
            state.source_ref.content_brief_sha256,
        }:
            reasons.append("build_preparation_content_brief_changed")
        if str(getattr(preparation, "visual_brief_hash", "") or "") not in {
            "",
            state.source_ref.visual_brief_sha256,
        }:
            reasons.append("build_preparation_visual_brief_changed")
        return reasons

    async def _ensure_build_preparation_current(self, session: Any, preparation: Any) -> None:
        """Reject a ready brief pair whose approved upstream snapshot changed."""

        raw_state = getattr(session, "current_state", {})
        if not isinstance(raw_state, dict):
            raw_state = {}
        raw_content = raw_state.get("content_architect")
        raw_visual = raw_state.get("visual_design_director")
        if not isinstance(raw_content, dict) or not isinstance(raw_visual, dict):
            # Lightweight repository doubles intentionally do not carry the
            # complete upstream aggregate.  A real repository does, and must
            # fail closed rather than admitting an unprovable handoff.
            if getattr(self._repo, "_session", None) is None:
                return
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_BUILD_PREPARATION_STALE",
                "The approved Build Preparation upstream snapshot is unavailable. Regenerate Build Preparation before generating.",
                status_code=409,
                details={"stale_reasons": ["approved_upstream_unavailable"]},
            )
        try:
            content = ContentArchitectState.model_validate(raw_content)
            visual = VisualDesignDirectorState.model_validate(raw_visual)
            if content.approved is None or visual.approved is None:
                raise ValueError("approved upstream snapshot is unavailable")
            current_source_ref = BuildPreparationInputIntegrator(self._settings).compose(
                content,
                visual,
            ).source_ref
        except Exception as exc:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_BUILD_PREPARATION_STALE",
                "The approved Build Preparation upstream snapshot could not be revalidated. Regenerate Build Preparation before generating.",
                status_code=409,
                details={"stale_reasons": ["approved_upstream_unavailable"]},
            ) from exc

        persisted_source_ref = getattr(preparation, "source_ref", None)
        mismatches: list[str] = []
        if (
            persisted_source_ref is None
            or current_source_ref.visual_design_director_direction_hash
            != persisted_source_ref.visual_design_director_direction_hash
        ):
            mismatches.append("approved_upstream_changed")
        if (
            persisted_source_ref is None
            or current_source_ref.input_projection_hash != persisted_source_ref.input_projection_hash
        ):
            mismatches.append("approved_upstream_changed")
        if mismatches:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_BUILD_PREPARATION_STALE",
                "The approved upstream handoff changed after Build Preparation. Regenerate Build Preparation before generating.",
                status_code=409,
                details={"stale_reasons": list(dict.fromkeys(mismatches))},
            )

    async def _require_session(self, session_id: UUID) -> Any:
        session = await self._repo.get_session(session_id)
        if session is None:
            raise CodeGeneratorOperationError(
                "SESSION_NOT_FOUND", "Portfolio session was not found.", status_code=404
            )
        return session

    def _normal_owner_id(self) -> UUID:
        context = getattr(self._jobs, "authorization_context", None)
        if context is None or context.authorization_context_version != 1:
            raise EntitlementBindingConflictError()
        if context.owner_user_id != context.actor_user_id or context.owner_user_id is None:
            raise EntitlementBindingConflictError()
        return UUID(str(context.owner_user_id))

    async def _normal_owner_entitlement(self, session_id: UUID) -> Any | None:
        context = getattr(self._jobs, "authorization_context", None)
        if context is None or context.authorization_context_version != 1:
            return None
        if context.portfolio_session_id != session_id:
            raise EntitlementBindingConflictError()
        if context.owner_user_id != context.actor_user_id or context.owner_user_id is None:
            return None
        result = await self._repo._session.execute(
            select(AppUser.role).where(AppUser.id == context.actor_user_id)
        )
        role = result.scalar_one_or_none()
        if role != AuthRole.USER.value:
            return None
        entitlement = await self._repo.entitlements.get_for_user(context.owner_user_id)
        if entitlement is None:
            raise EntitlementBindingConflictError()
        return entitlement

    @staticmethod
    def _not_ready(message: str) -> NoReturn:
        raise CodeGeneratorOperationError("CODE_GENERATOR_BUILD_PREPARATION_NOT_READY", message)


def _session_preview_host(session_id: UUID) -> str:
    encoded = base64.b32encode(hashlib.sha256(str(session_id).encode()).digest()).decode().lower()
    return f"session-{encoded[:24].rstrip('=')}"


def _safe_job_timestamp(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return value if isinstance(value, str) else None


# Pipeline order matters only for readability here; the summation itself is
# order-independent. This is the exact `stage_durations_ms` key vocabulary
# written by `coordinator.py`/`code_generator_verification.py` (task 2) --
# "plan", "acquire", "generate", "verify" -- which is deliberately NOT the
# same string vocabulary as `config/app.toml`'s dotted `kind_timeouts` keys
# below. The two are mapped explicitly rather than assumed identical.
_STAGE_ORDER: tuple[str, ...] = ("plan", "acquire", "generate", "verify")

# Maps a `stage_durations_ms` stage name to its `worker.job.kind_timeouts`
# config key. Confirmed against `config/app.toml`: the verify stage's
# configured budget key is `"code_generator.verify_and_preview"`, not
# `"code_generator.verify"` -- the two vocabularies diverge on that one
# stage, which is exactly why this mapping exists instead of a `f"code_
# generator.{stage}"` string-concat shortcut.
_STAGE_TIMEOUT_KIND: dict[str, str] = {
    "plan": "code_generator.plan",
    "acquire": "code_generator.acquire",
    "generate": "code_generator.generate",
    "verify": "code_generator.verify_and_preview",
}


def _compute_stage_estimate(
    *,
    stage_durations_ms: Any,
    created_at: datetime | None,
    now: datetime,
    timeout_for: Callable[[str], float],
) -> dict[str, Any]:
    """Backend-only, non-fabricated estimated-time-remaining computation.

    Correctness Property 3 (design.md): every millisecond in the returned
    ``estimated_total_ms`` must trace back to either (a) an observed
    ``stage_durations_ms`` entry for a stage already completed in this run,
    or (b) `config/app.toml`'s `worker.job.kind_timeouts` budget for a stage
    not yet completed -- never an arbitrary constant. This function is a
    pure, DB-free, service-free computation specifically so that invariant
    is directly unit- and property-testable without a service instance or a
    database session.

    ``timeout_for`` is passed in as a plain callable (rather than a
    ``WorkerJobConfig`` instance) so tests can supply a trivial fake without
    constructing real settings.
    """

    durations = stage_durations_ms if isinstance(stage_durations_ms, dict) else {}
    has_observed_entry = False
    estimated_total_ms = 0.0
    for stage in _STAGE_ORDER:
        observed = durations.get(stage)
        if isinstance(observed, (int, float)) and not isinstance(observed, bool):
            has_observed_entry = True
            estimated_total_ms += max(0.0, float(observed))
        else:
            budget_seconds = timeout_for(_STAGE_TIMEOUT_KIND[stage])
            estimated_total_ms += max(0.0, float(budget_seconds) * 1000.0)

    # `CodeGeneratorDevelopmentRun`/`CodeGeneratorRun` rows have no
    # `started_at` of their own -- only `created_at` (see
    # `db/models/code_generator_development.py`). This mirrors task 2's own
    # `coordinator.py` precedent of falling back to an honest, already-
    # persisted timestamp rather than a fabricated one when the more
    # semantically precise field does not exist on this row.
    if created_at is not None:
        elapsed_ms = max(0.0, (now - created_at).total_seconds() * 1000.0)
    else:
        elapsed_ms = 0.0

    estimated_remaining_ms = max(0.0, estimated_total_ms - elapsed_ms)
    return {
        "elapsed_ms": int(elapsed_ms),
        "estimated_total_ms": int(estimated_total_ms),
        "estimated_remaining_ms": int(estimated_remaining_ms),
        "source": "observed_and_budget" if has_observed_entry else "configured_budget",
    }


def _safe_job_error(value: Any) -> dict[str, Any] | None:
    """Project only the stable, user-safe portion of a job error."""

    if not isinstance(value, dict):
        return None
    result: dict[str, Any] = {}
    code = value.get("code")
    message = value.get("message")
    if isinstance(code, str) and code.strip():
        result["code"] = code.strip()[:120]
    if isinstance(message, str) and message.strip():
        result["message"] = message.strip()[:300]
    if value.get("retryable") is True:
        result["retryable"] = True
    return result or None


def _manual_retry_allowed(run: Any) -> bool:
    """Keep retry UI fail-closed for security/contract terminal reports."""

    report = getattr(run, "terminal_failure", None)
    if not isinstance(report, dict):
        return True
    code = str(report.get("terminal_code") or report.get("code") or "").upper()
    return not code.startswith(
        (
            "AUTHORIZATION",
            "ENTITLEMENT",
            "SECURITY",
            "PORTFOLIO_READ_ONLY",
            "CODE_GENERATOR_WORKER_CONTRACT",
        )
    )


def _variant_id(run: Any) -> str:
    creative = getattr(run, "creative_direction", None) or {}
    receipt = creative.get("variant_receipt", {}) if isinstance(creative, dict) else {}
    return str(receipt.get("variant_id", "")) if isinstance(receipt, dict) else ""


def _retry_stage(run: Any) -> str:
    """Choose the first incomplete durable stage for same-variant recovery."""

    if str(getattr(run, "status", "")) == DevelopmentRunStatus.PREVIEW_PENDING.value:
        return "verify"
    if not getattr(run, "plan", None) or not getattr(run, "planner_receipt", None):
        return "plan"
    if not (
        getattr(run, "acquire_receipt", None)
        and getattr(run, "resource_ledger", None)
        and getattr(run, "dependency_ledger", None)
    ):
        return "acquire"
    if not getattr(run, "source_checkpoint", None) or not getattr(
        run, "generation_projection", None
    ):
        return "generate"
    return "verify"


def _checkpointed_completion_stage(run: Any, stage: str) -> str | None:
    """Return the durable completion marker that can resume a failed handoff."""

    if (
        stage == "plan"
        and str(getattr(run, "status", "")) == DevelopmentRunStatus.PLANNED.value
        and getattr(run, "plan", None)
        and getattr(run, "planner_receipt", None)
    ):
        return "planned"
    if (
        stage == "acquire"
        and str(getattr(run, "status", "")) == DevelopmentRunStatus.ACQUIRED.value
        and getattr(run, "acquire_receipt", None)
        and getattr(run, "resource_ledger", None)
        and getattr(run, "dependency_ledger", None)
    ):
        return "acquired"
    if (
        stage == "generate"
        and str(getattr(run, "status", "")) == DevelopmentRunStatus.SOURCE_READY.value
        and getattr(run, "source_checkpoint", None)
        and getattr(run, "generation_projection", None)
    ):
        return "source_ready"
    return None


def _retry_stage_material(run: Any, stage: str) -> str:
    fields = {
        "plan": getattr(run, "artifact_reference", None),
        "acquire": getattr(run, "planner_receipt", None),
        "generate": getattr(run, "resource_ledger", None),
        "verify": getattr(run, "source_checkpoint", None)
        or getattr(run, "pending_promotion", None),
    }
    value = fields.get(stage) or {}
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


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
        DevelopmentRunStatus.PREVIEW_PENDING.value,
        DevelopmentRunStatus.REPAIRING.value,
    }:
        return CodeGeneratorSessionStatus.VERIFYING.value
    return CodeGeneratorSessionStatus.QUEUED.value
