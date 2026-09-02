"""Durable Phase 3 build, DOM verification, and preview promotion job."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from oryxenai.agents.code_generator.core.blueprint_compiler import canonicalize_generation_plan
from oryxenai.agents.code_generator.core.build_runner import run_clean_build
from oryxenai.agents.code_generator.core.candidate_identity import build_candidate_identity
from oryxenai.agents.code_generator.core.checkpoint_store import CheckpointStore
from oryxenai.agents.code_generator.core.design_realization import compile_design_realization
from oryxenai.agents.code_generator.core.development_input import DevelopmentInputAdapter
from oryxenai.agents.code_generator.core.development_planner import validate_site_plan
from oryxenai.agents.code_generator.core.development_schemas import (
    DevelopmentRunStatus,
    Diagnostic,
    ExperienceBlueprintV3,
    ExperienceBlueprintV4,
    GateResult,
    GenerationProjection,
    PendingPromotion,
    QualityReviewReceiptV2,
    RepairReceipt,
    SafeIssue,
    SitePlan,
    TerminalFailureReport,
    VerificationProjection,
)
from oryxenai.agents.code_generator.core.final_repair import (
    FinalRepairer,
    FinalRepairError,
    repair_allowed_paths,
)
from oryxenai.agents.code_generator.core.final_source_validation import validate_final_source
from oryxenai.agents.code_generator.core.generation_orchestrator import (
    CodeGeneratorGenerationOrchestrator,
    _allowed_packages,
    _public_text,
)
from oryxenai.agents.code_generator.core.quality_review import (
    QualityReviewError,
    rebind_quality_review_receipt_source,
    validate_quality_review_receipt,
)
from oryxenai.agents.code_generator.core.repair_policy import RepairBudget
from oryxenai.agents.code_generator.core.runtime_verifier import RuntimeVerifier
from oryxenai.agents.code_generator.core.source_manifest import digest
from oryxenai.agents.code_generator.core.token_compiler import (
    compile_generated_tokens,
    write_generated_tokens,
)
from oryxenai.agents.code_generator.core.verification_plan import (
    build_verification_profile,
    derive_verification_plan,
)
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace, repository_root
from oryxenai.auth.finalization import finalize_promoted_success
from oryxenai.auth.worker_fence import AuthorizationFenceError, WorkerAuthorizationFence
from oryxenai.core.logging import get_logger
from oryxenai.db.repositories.code_generator import CodeGeneratorRepository
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository
from oryxenai.db.session import get_sessionmaker
from oryxenai.preview.gateway import create_candidate_app
from oryxenai.preview.promotion import PreviewPromoter
from oryxenai.preview.reconciler import reconcile_pending_promotion
from oryxenai.preview.server import EphemeralServer, start_ephemeral_server
from oryxenai.storage.artifacts import is_expired
from oryxenai.storage.preview import create_preview_storage

logger = get_logger("oryxenai.jobs.code_generator_verification")


def _reconstruct_repair_unit_counts(receipts: list[RepairReceipt]) -> dict[str, int]:
    """Rebuild per-gate repair usage, conservatively handling legacy receipts."""

    counts: dict[str, int] = {}
    for receipt in receipts:
        unit_id = receipt.repair_unit_id or "final"
        counts[unit_id] = counts.get(unit_id, 0) + 1
    return counts


class CodeGeneratorVerificationHandler:
    kind = "code_generator.verify_and_preview"

    def __init__(
        self,
        *,
        model_factory: Any | None = None,
        runtime_verifier_factory: Any | None = None,
        storage_factory: Any | None = None,
    ) -> None:
        self._model_factory = model_factory
        self._runtime_verifier_factory = runtime_verifier_factory
        self._storage_factory = storage_factory

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        del instance_id
        return await _execute(
            payload,
            model_factory=self._model_factory,
            runtime_verifier_factory=self._runtime_verifier_factory,
            storage_factory=self._storage_factory,
        )


async def _execute(
    payload: dict[str, Any],
    *,
    model_factory: Any | None = None,
    runtime_verifier_factory: Any | None = None,
    storage_factory: Any | None = None,
) -> dict[str, Any]:
    from oryxenai.core.settings import get_settings

    run_id = UUID(str(payload.get("code_generator_run_id") or payload["development_run_id"]))
    settings = get_settings()
    sessionmaker = get_sessionmaker(settings)
    await _validate_worker_payload(sessionmaker, payload)
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        run = await repo.get(run_id)
        if run is None:
            return {"status": "discarded", "run_id": str(run_id)}
        await WorkerAuthorizationFence(db).validate_run(run_id)
        if run.status == DevelopmentRunStatus.READY.value and run.active_preview:
            return {"status": "succeeded", "run_id": str(run_id), "reused": True}
        if run.source_checkpoint is None or run.generation_projection is None or run.plan is None:
            return {
                "status": "failed",
                "run_id": str(run_id),
                "error": {
                    "code": "SOURCE_NOT_READY",
                    "message": "An accepted source checkpoint is required before verification.",
                    "retryable": False,
                },
            }
        if run.status not in {
            DevelopmentRunStatus.QUEUED.value,
            DevelopmentRunStatus.SOURCE_READY.value,
            DevelopmentRunStatus.BUILDING.value,
            DevelopmentRunStatus.SMOKE_TESTING.value,
            DevelopmentRunStatus.PREVIEW_PENDING.value,
            DevelopmentRunStatus.REPAIRING.value,
            DevelopmentRunStatus.NEEDS_ATTENTION.value,
        }:
            return {"status": "discarded", "run_id": str(run_id)}
        if str(
            getattr(run, "run_mode", "development")
        ) == "session" and not await _session_source_is_current(CodeGeneratorRepository(db), run):
            issue = SafeIssue(
                code="CODE_GENERATOR_STALE_SOURCE",
                message=(
                    "Build Preparation changed or expired before preview promotion; "
                    "the stale candidate was not promoted."
                ),
                next_action="Start Code Generator again from the latest eligible artifact.",
            )
            await _cas(
                repo,
                run,
                DevelopmentRunStatus.NEEDS_ATTENTION.value,
                {"issues": [issue.model_dump(mode="json")]},
            )
            await repo.append_event(
                run_id,
                event_type="stale_source",
                level="error",
                message=issue.message,
            )
            await db.commit()
            return {"status": "needs_attention", "run_id": str(run_id)}
        if run.pending_promotion and run.verification_projection:
            try:
                pending = PendingPromotion.model_validate(run.pending_promotion)
                pending_projection = VerificationProjection.model_validate(
                    run.verification_projection
                )
                if pending_projection.build_manifest is None:
                    raise VerificationFailure(
                        "PENDING_PROMOTION_INVALID", "Pending promotion has no build manifest."
                    )
                storage = (
                    storage_factory(settings)
                    if storage_factory is not None
                    else create_preview_storage(settings)
                )
                host = str(run.preview_host or _preview_host(str(run_id)))
                await _validate_worker_payload(sessionmaker, payload)
                await _validate_run_fence(sessionmaker, run_id)
                active = await reconcile_pending_promotion(
                    storage=storage,
                    run_id=str(run_id),
                    host=host,
                    pending=pending,
                    manifest=pending_projection.build_manifest,
                    preview_base_url=str(settings.code_generator_verification.preview_base_url),
                    require_readback=bool(
                        getattr(
                            settings.code_generator_verification,
                            "preview_public_readback_required",
                            True,
                        )
                    ),
                )
                pending_projection.status = "ready"
                pending_projection.phase = "ready"
                await finalize_promoted_success(
                    sessionmaker,
                    run_id=run_id,
                    active_preview=active,
                    projection=pending_projection,
                    values={
                        "candidate_artifact": pending.candidate.model_dump(mode="json"),
                        "preview_host": host,
                        "source_summary": {
                            "preview_url": active.url,
                            "build_hash": pending.candidate.build_hash,
                        },
                    },
                    event=("reconciled", "A pending preview promotion was reconciled safely."),
                    job_id=_payload_uuid(payload, "job_id"),
                    attempt=_payload_int(payload, "attempt"),
                    lease_token=str(payload.get("lease_token", "") or "") or None,
                )
                return {
                    "status": "succeeded",
                    "run_id": str(run_id),
                    "preview_url": active.url,
                    "reconciled": True,
                }
            except AuthorizationFenceError:
                raise
            except Exception as exc:
                logger.debug("pending preview reconciliation deferred error=%s", type(exc).__name__)
        await _cas(
            repo,
            run,
            DevelopmentRunStatus.BUILDING.value,
            {"issues": [], "terminal_failure": None},
        )
        await repo.append_event(
            run_id,
            event_type="building",
            level="info",
            message="Restoring the accepted source checkpoint for final verification.",
        )
        await db.commit()

    await _validate_worker_payload(sessionmaker, payload)
    profile = build_verification_profile(settings)
    server: EphemeralServer | None = None
    projection: VerificationProjection | None = None
    try:
        reference = _reference(run)
        adapter = DevelopmentInputAdapter(settings)
        input_receipt, projections = adapter.admit(reference)
        plan = canonicalize_generation_plan(SitePlan.model_validate(run.plan))
        validate_site_plan(
            plan,
            projections,
            max_work_units=int(settings.code_generator_development.max_work_units),
        )
        workspace = GenerationWorkspace.open(
            settings,
            run_id=str(run_id),
            admitted_identity=input_receipt.admitted_identity,
        )
        checkpoint = _checkpoint(run)
        checkpoint_store = CheckpointStore(workspace, generation_id=str(run_id))
        checkpoint_store.restore(checkpoint)
        workspace.materialize_acquisition_resources(
            run.resource_ledger,
            # Receipt local_paths are relative to the configured materials
            # root (already prefixed with the run id).
            _resolve_config_path(settings.code_generator_acquisition.materials_root),
        )
        workspace.synchronize_dependency_manifest(
            _resolve_config_path(settings.code_generator_dependencies.workspaces_root)
            / str(run_id)
            / "repo"
        )
        source_manifest = _source_manifest_hash(workspace.repo_dir)
        if source_manifest != checkpoint.source_manifest_hash:
            raise VerificationFailure(
                "SOURCE_CHECKPOINT_DRIFT",
                "The restored source checkpoint does not match its source manifest.",
            )
        checkpoint_before_normalization = checkpoint.checkpoint_hash
        checkpoint = await _normalize_host_generated_tokens(
            sessionmaker=sessionmaker,
            run_id=run_id,
            run=run,
            plan=plan,
            workspace=workspace,
            checkpoint_store=checkpoint_store,
            checkpoint=checkpoint,
        )
        if checkpoint.checkpoint_hash != checkpoint_before_normalization:
            # Host normalization is deterministic, but it still changes the
            # immutable source manifest. Reload the projection that the
            # normalizer rebound so the final verification gate never mixes
            # the old in-memory quality receipt with the corrected source.
            async with sessionmaker() as db:
                current = await CodeGeneratorDevelopmentRepository(db).get(run_id)
            if current is None:
                raise VerificationFailure("RUN_NOT_FOUND", "The verification run was not found.")
            run = current
        source_manifest = checkpoint.source_manifest_hash
        identity = build_candidate_identity(
            run=run,
            plan=plan,
            checkpoint=checkpoint,
            source_manifest_hash=source_manifest,
            profile=profile,
        )
        realization_contracts = []
        quality_payload: dict[str, Any] | None = None
        generation_projection_payload = (
            run.generation_projection if isinstance(run.generation_projection, dict) else {}
        )
        if isinstance(plan.experience_blueprint, ExperienceBlueprintV4):
            realization_contracts = [
                compile_design_realization(
                    plan.experience_blueprint,
                    route_id=route.route_id,
                    section_order=list(route.section_order or route.section_ids),
                )
                for route in plan.routes
            ]
            candidate_quality = generation_projection_payload.get("quality_review")
            quality_payload = (
                dict(candidate_quality) if isinstance(candidate_quality, dict) else None
            )
            if not isinstance(quality_payload, dict):
                raise VerificationFailure(
                    "QUALITY_REVIEW_MISSING",
                    "The final v4 source has no host-stamped whole-site quality receipt.",
                    owner="generator",
                )
            try:
                quality_receipt = QualityReviewReceiptV2.model_validate(quality_payload)
                context_receipts_value = generation_projection_payload.get("context_receipts", [])
                context_receipts = (
                    context_receipts_value if isinstance(context_receipts_value, list) else []
                )
                known_context_hashes = {
                    str(item.get("context_hash", ""))
                    for item in context_receipts
                    if isinstance(item, dict)
                }
                if quality_receipt.review_context_hash not in known_context_hashes:
                    raise QualityReviewError(
                        "QUALITY_CONTEXT_STALE",
                        "The quality review context receipt is not part of this generation run.",
                    )
                validate_quality_review_receipt(
                    quality_receipt,
                    source_manifest_hash=source_manifest,
                    plan_hash=digest(plan.model_dump(mode="json")),
                    realization_hash=digest(
                        [item.model_dump(mode="json") for item in realization_contracts]
                    ),
                    quality_gate_version=str(
                        settings.code_generator_development.quality_gate_version
                    ),
                )
            except (ValueError, QualityReviewError) as exc:
                raise VerificationFailure(
                    str(getattr(exc, "code", "QUALITY_REVIEW_MISSING_OR_STALE")),
                    str(
                        getattr(
                            exc,
                            "message",
                            "The whole-site quality review does not match the final source.",
                        )
                    ),
                    owner="generator",
                ) from exc
        verification_plan = derive_verification_plan(
            identity=identity,
            plan=plan,
            projections=projections,
            profile=profile,
        )
        projection = VerificationProjection(
            generation_id=str((run.generation_projection or {}).get("generation_id", run_id)),
            candidate_identity=identity,
            verification_profile=profile,
            verification_plan=verification_plan,
            phase="source_contract",
            active_gate="source_contract",
            status="building",
        )
        prior_projection = None
        if run.verification_projection:
            try:
                prior_projection = VerificationProjection.model_validate(
                    run.verification_projection
                )
            except ValueError:
                prior_projection = None
        if prior_projection is not None:
            projection.repair_rounds = prior_projection.repair_rounds
            projection.repair_receipts = list(prior_projection.repair_receipts)
        await _persist_projection(
            sessionmaker, run_id, projection, DevelopmentRunStatus.BUILDING.value
        )
        allowed_packages = _allowed_packages(workspace.repo_dir, projections, run.dependency_ledger)
        public_text = _public_text(projections)
        source_diagnostics = validate_final_source(
            workspace.repo_dir,
            plan=plan,
            projections=projections,
            allowed_packages=allowed_packages,
            public_text=public_text,
        )
        prior_source_passed = _prior_gate_passed(
            prior_projection, "source_contract", identity.identity_hash
        )
        if prior_source_passed:
            source_diagnostics = []
        projection.diagnostics.extend(source_diagnostics)
        projection.gate_results.append(
            GateResult(
                gate_id="source_contract",
                status="failed" if source_diagnostics else "passed",
                candidate_identity_hash=identity.identity_hash,
                expected_check_ids=profile.source_check_ids,
                executed_check_ids=profile.source_check_ids,
                diagnostics=source_diagnostics,
            )
        )
        if source_diagnostics:
            repaired = await _attempt_repair(
                sessionmaker=sessionmaker,
                run_id=run_id,
                settings=settings,
                workspace=workspace,
                checkpoint_store=checkpoint_store,
                checkpoint=checkpoint,
                identity=identity,
                plan=plan,
                projections=projections,
                projection=projection,
                diagnostics=source_diagnostics,
                public_text=public_text,
                allowed_packages=allowed_packages,
                model_factory=model_factory,
            )
            if repaired:
                return await _execute(
                    {**payload, "repair_depth": int(payload.get("repair_depth", 0)) + 1},
                    model_factory=model_factory,
                    runtime_verifier_factory=runtime_verifier_factory,
                    storage_factory=storage_factory,
                )
            return await _terminal(
                sessionmaker,
                run_id,
                projection,
                code="SOURCE_CONTRACT_FAILED",
                summary="The generated source does not satisfy the approved route and resource contract.",
                next_action="Review the source diagnostics and regenerate the source checkpoint.",
            )
        projection.phase = "building"
        projection.active_gate = "type_build_artifact"
        await _persist_projection(
            sessionmaker, run_id, projection, DevelopmentRunStatus.BUILDING.value
        )
        reused_manifest = _prior_build_manifest(prior_projection, identity.identity_hash)
        if reused_manifest is not None and not _materialized_manifest_matches(
            workspace.repo_dir / "dist", reused_manifest
        ):
            # A persisted manifest is evidence about a previous workspace,
            # not the files served by this attempt. Rebuild when a retry or
            # repair restored source without its disposable dist tree.
            reused_manifest = None
        build_diagnostics: list[Diagnostic]
        if reused_manifest is not None:
            manifest, build_diagnostics = reused_manifest, []
        else:
            await _validate_worker_payload(sessionmaker, payload)
            await _validate_run_fence(sessionmaker, run_id)
            manifest, build_diagnostics = await run_clean_build(
                workspace.repo_dir,
                settings=settings,
                candidate_identity_hash=identity.identity_hash,
            )
        projection.diagnostics.extend(build_diagnostics)
        projection.gate_results.append(
            GateResult(
                gate_id="type_build_artifact",
                status="failed" if build_diagnostics or manifest is None else "passed",
                candidate_identity_hash=identity.identity_hash,
                build_hash=manifest.build_hash if manifest else "",
                expected_check_ids=profile.build_check_ids,
                executed_check_ids=profile.build_check_ids,
                diagnostics=build_diagnostics,
            )
        )
        if build_diagnostics or manifest is None:
            logger.warning(
                "code_generator build gate failed run_id=%s diagnostics=%s",
                run_id,
                " | ".join(
                    f"{item.code}:{item.normalized_message[:240]}" for item in build_diagnostics[:4]
                )
                or "manifest_missing",
            )
            repaired = await _attempt_repair(
                sessionmaker=sessionmaker,
                run_id=run_id,
                settings=settings,
                workspace=workspace,
                checkpoint_store=checkpoint_store,
                checkpoint=checkpoint,
                identity=identity,
                plan=plan,
                projections=projections,
                projection=projection,
                diagnostics=build_diagnostics,
                public_text=public_text,
                allowed_packages=allowed_packages,
                model_factory=model_factory,
            )
            if repaired:
                return await _execute(
                    {**payload, "repair_depth": int(payload.get("repair_depth", 0)) + 1},
                    model_factory=model_factory,
                    runtime_verifier_factory=runtime_verifier_factory,
                    storage_factory=storage_factory,
                )
            return await _terminal(
                sessionmaker,
                run_id,
                projection,
                code="TYPE_BUILD_ARTIFACT_FAILED",
                summary="The clean production build or artifact closure failed.",
                next_action="Review the build diagnostics and regenerate the source checkpoint.",
            )
        projection.build_manifest = manifest
        projection.build_hash = manifest.build_hash
        projection.phase = "smoke_testing"
        projection.active_gate = "dom_runtime"
        await _persist_projection(
            sessionmaker, run_id, projection, DevelopmentRunStatus.SMOKE_TESTING.value
        )
        host = str(run.preview_host or _preview_host(str(run_id)))
        token = secrets.token_urlsafe(32)
        try:
            await _validate_run_fence(sessionmaker, run_id)
            candidate_app = create_candidate_app(
                workspace.repo_dir / "dist",
                token=token,
                parent_origin=str(settings.code_generator_verification.preview_parent_origin),
                mount_prefix=(
                    f"{settings.code_generator_verification.preview_route_prefix.rstrip('/')}/"
                    f"{host}/"
                ),
            )
            server = await start_ephemeral_server(candidate_app)
        except Exception as exc:
            logger.warning(
                "preview gateway could not start run_id=%s error_type=%s",
                run_id,
                type(exc).__name__,
            )
            raise VerificationFailure(
                "PREVIEW_GATEWAY_START_FAILED",
                "The local preview gateway could not start safely.",
                owner="infrastructure",
            ) from exc
        verifier = (
            runtime_verifier_factory()
            if runtime_verifier_factory is not None
            else RuntimeVerifier()
        )
        await _validate_run_fence(sessionmaker, run_id)
        evidence, runtime_diagnostics = await verifier.verify(
            (
                f"{server.url}"
                f"{settings.code_generator_verification.preview_route_prefix.rstrip('/')}/"
                f"{host}/"
            ),
            plan=verification_plan,
            profile=profile,
            timeout_ms=int(settings.code_generator_verification.runtime_timeout_ms),
            verification_token=token,
        )
        executed_runtime_check_ids = sorted(
            set(profile.runtime_check_ids).union(item.journey_id for item in evidence)
        )
        expected_runtime_check_ids = sorted(
            set(profile.runtime_check_ids).union(
                item.journey_id for item in verification_plan.runtime_journeys
            )
        )
        if executed_runtime_check_ids != expected_runtime_check_ids:
            runtime_diagnostics.append(
                Diagnostic(
                    diagnostic_id="diagnostic-runtime-check-set-mismatch",
                    group="dom_runtime",
                    code="RUNTIME_CHECK_ID_SET_MISMATCH",
                    phase="dom_runtime",
                    normalized_message=(
                        "The runtime verifier did not execute the exact configured route and "
                        "journey check set."
                    ),
                    expected=",".join(expected_runtime_check_ids),
                    observed=",".join(executed_runtime_check_ids),
                    fingerprint=hashlib.sha256(
                        f"runtime-check-set:{expected_runtime_check_ids}:{executed_runtime_check_ids}".encode()
                    ).hexdigest()[:24],
                )
            )
        if not evidence:
            runtime_diagnostics.append(
                Diagnostic(
                    diagnostic_id="diagnostic-runtime-evidence-empty",
                    group="dom_runtime",
                    code="RUNTIME_EVIDENCE_EMPTY",
                    phase="dom_runtime",
                    normalized_message="The runtime verifier produced no journey evidence.",
                    fingerprint=hashlib.sha256(b"runtime-evidence-empty").hexdigest()[:24],
                )
            )
        evidence_hash = hashlib.sha256(
            _canonical([item.model_dump(mode="json") for item in evidence])
        ).hexdigest()
        projection.runtime_evidence = evidence
        projection.diagnostics.extend(runtime_diagnostics)
        projection.gate_results.append(
            GateResult(
                gate_id="dom_runtime",
                status="failed" if runtime_diagnostics else "passed",
                candidate_identity_hash=identity.identity_hash,
                build_hash=manifest.build_hash,
                expected_check_ids=expected_runtime_check_ids,
                executed_check_ids=executed_runtime_check_ids,
                diagnostics=runtime_diagnostics,
                evidence_hash=evidence_hash,
            )
        )
        if runtime_diagnostics:
            logger.warning(
                "code_generator runtime gate failed run_id=%s codes=%s",
                run_id,
                ",".join(sorted({item.code for item in runtime_diagnostics})),
            )
            if server is not None:
                await server.close()
                server = None
            if _has_infrastructure_diagnostic(runtime_diagnostics):
                return await _terminal(
                    sessionmaker,
                    run_id,
                    projection,
                    code=_first_infrastructure_code(runtime_diagnostics),
                    summary="The verification environment could not complete the browser smoke test.",
                    next_action="Check the local preview gateway and browser runtime, then retry verification.",
                )
            repaired = await _attempt_repair(
                sessionmaker=sessionmaker,
                run_id=run_id,
                settings=settings,
                workspace=workspace,
                checkpoint_store=checkpoint_store,
                checkpoint=checkpoint,
                identity=identity,
                plan=plan,
                projections=projections,
                projection=projection,
                diagnostics=runtime_diagnostics,
                public_text=public_text,
                allowed_packages=allowed_packages,
                model_factory=model_factory,
            )
            if repaired:
                return await _execute(
                    {**payload, "repair_depth": int(payload.get("repair_depth", 0)) + 1},
                    model_factory=model_factory,
                    runtime_verifier_factory=runtime_verifier_factory,
                    storage_factory=storage_factory,
                )
            return await _terminal(
                sessionmaker,
                run_id,
                projection,
                code="DOM_RUNTIME_FAILED",
                summary="The generated portfolio failed text/DOM/runtime smoke verification.",
                next_action="Review the route, interaction, accessibility, or request diagnostics and regenerate.",
            )
        report = projection.model_dump(mode="json")
        report_hash = hashlib.sha256(_canonical(report)).hexdigest()
        storage = (
            storage_factory(settings)
            if storage_factory is not None
            else create_preview_storage(settings)
        )
        promoter = PreviewPromoter(
            storage,
            preview_base_url=str(settings.code_generator_verification.preview_base_url),
            require_readback=bool(
                getattr(
                    settings.code_generator_verification,
                    "preview_public_readback_required",
                    True,
                )
            ),
        )
        host = str(run.preview_host or _preview_host(str(run_id)))
        candidate_id = f"candidate-{identity.identity_hash[:24]}"
        await _validate_run_fence(sessionmaker, run_id)
        artifact, stored_report_hash, candidate_pointer = await promoter.store_candidate(
            candidate_id=candidate_id,
            host=host,
            identity=identity,
            manifest=manifest,
            dist_dir=workspace.repo_dir / "dist",
            verification_report={**report, "verification_report_hash": report_hash},
        )
        artifact = artifact.model_copy(
            update={
                "route_ids": [route.route_id for route in plan.routes],
                "route_paths": [route.path for route in plan.routes],
            }
        )
        pending = await promoter.create_pending(
            run_id=str(run_id),
            host=host,
            artifact=artifact,
            verification_report_hash=stored_report_hash,
            expected_revision=await _current_revision(sessionmaker, run_id),
        )
        projection.candidate_artifact = artifact
        projection.verification_report_hash = stored_report_hash
        await _persist_projection(
            sessionmaker,
            run_id,
            projection,
            DevelopmentRunStatus.SMOKE_TESTING.value,
            values={
                "candidate_artifact": artifact.model_dump(mode="json"),
                "pending_promotion": pending.model_dump(mode="json"),
                "preview_host": host,
            },
        )
        try:
            await _validate_worker_payload(sessionmaker, payload)
            await _validate_run_fence(sessionmaker, run_id)
            active = await promoter.promote(
                run_id=str(run_id),
                host=host,
                pending=pending,
                candidate_pointer=candidate_pointer,
                verification_report_hash=stored_report_hash,
            )
        except AuthorizationFenceError:
            raise
        except Exception as exc:
            code = str(getattr(exc, "code", "PREVIEW_PUBLICATION_UNAVAILABLE"))
            message = str(
                getattr(
                    exc,
                    "message",
                    "The verified candidate is retained while public preview publication is unavailable.",
                )
            )
            projection.status = "preview_pending"
            projection.phase = "preview_pending"
            await _persist_projection(
                sessionmaker,
                run_id,
                projection,
                DevelopmentRunStatus.PREVIEW_PENDING.value,
                values={
                    "candidate_artifact": artifact.model_dump(mode="json"),
                    "pending_promotion": pending.model_dump(mode="json"),
                    "preview_host": host,
                    "issues": [
                        SafeIssue(
                            code=code,
                            message=message,
                            next_action="Retry publication after preview storage or gateway recovery.",
                        ).model_dump(mode="json")
                    ],
                },
                event=("preview_pending", message),
            )
            return {"status": "preview_pending", "run_id": str(run_id), "code": code}
        projection.status = "ready"
        projection.phase = "ready"
        projection.active_gate = ""
        projection.candidate_artifact = artifact
        await finalize_promoted_success(
            sessionmaker,
            run_id=run_id,
            active_preview=active,
            projection=projection,
            values={
                "candidate_artifact": artifact.model_dump(mode="json"),
                "preview_host": host,
                "source_summary": {"preview_url": active.url, "build_hash": manifest.build_hash},
            },
            event=("promoted", "Verified portfolio preview promoted atomically."),
            job_id=_payload_uuid(payload, "job_id"),
            attempt=_payload_int(payload, "attempt"),
            lease_token=str(payload.get("lease_token", "") or "") or None,
        )
        input_receipt_payload = run.input_receipt if isinstance(run.input_receipt, dict) else {}
        projection_hashes = input_receipt_payload.get("projection_hashes", {})
        await _export_portfolio(
            sessionmaker,
            run_id,
            settings,
            workspace=workspace,
            manifest=manifest,
            active=active,
            plan=plan,
            candidate_id=candidate_id,
            identity=identity,
            trace_id=str(run.trace_id or ""),
            pack_reference=str((run.input_reference or {}).get("source_id", "")),
            generation_projection=dict(generation_projection_payload),
            quality_review=quality_payload,
            realization_contracts=[item.model_dump(mode="json") for item in realization_contracts],
            provenance={
                "admitted_identity": str(input_receipt_payload.get("admitted_identity", "")),
                "input_receipt_hash": identity.input_receipt_hash,
                "source_checkpoint_hash": identity.source_checkpoint_hash,
                "source_manifest_hash": identity.source_manifest_hash,
                "resource_ledger_hash": identity.resource_ledger_hash,
                "dependency_ledger_hash": identity.dependency_ledger_hash,
                "projection_hashes": dict(projection_hashes)
                if isinstance(projection_hashes, dict)
                else {},
            },
            verification={
                "verification_report_hash": stored_report_hash,
                "verification_projection_hash": report_hash,
                "build_hash": manifest.build_hash,
                "candidate_identity_hash": identity.identity_hash,
                "verification_profile_hash": projection.verification_profile.profile_hash,
                "verification_plan_hash": (
                    projection.verification_plan.plan_hash
                    if projection.verification_plan is not None
                    else ""
                ),
                "gate_results": [
                    {
                        "gate_id": gate.gate_id,
                        "status": gate.status,
                        "evidence_hash": gate.evidence_hash,
                    }
                    for gate in projection.gate_results
                ],
                "runtime_journey_count": len(projection.runtime_evidence),
                "repair_receipt_hashes": [
                    receipt.receipt_hash for receipt in projection.repair_receipts
                ],
            },
            public_readback=(
                active.public_readback.model_dump(mode="json")
                if active.public_readback is not None
                else None
            ),
        )
        return {"status": "succeeded", "run_id": str(run_id), "preview_url": active.url}
    except VerificationFailure as exc:
        if isinstance(projection, VerificationProjection):
            return await _terminal(
                sessionmaker,
                run_id,
                projection,
                code=exc.code,
                summary=exc.message,
                next_action="Correct the source or input and start a new verification attempt.",
            )
        await _safe_issue(
            sessionmaker,
            run_id,
            SafeIssue(
                code=exc.code,
                message=exc.message,
                next_action="Start a corrected verification attempt.",
            ),
        )
        return {"status": "needs_attention", "run_id": str(run_id)}
    except Exception as exc:
        code = getattr(exc, "code", "VERIFICATION_FAILED")
        message = getattr(exc, "message", "Final verification could not complete safely.")
        if isinstance(projection, VerificationProjection):
            return await _terminal(
                sessionmaker,
                run_id,
                projection,
                code=code,
                summary=message,
                next_action="Review the safe verification issue and retry.",
            )
        await _safe_issue(
            sessionmaker,
            run_id,
            SafeIssue(
                code=code,
                message=message,
                next_action="Review the safe verification issue and retry.",
            ),
        )
        return {"status": "needs_attention", "run_id": str(run_id)}
    finally:
        if server is not None:
            await server.close()


class VerificationFailure(ValueError):
    def __init__(self, code: str, message: str, *, owner: str = "infrastructure") -> None:
        self.code = code
        self.message = message
        self.owner = owner
        super().__init__(message)


def _prior_gate_passed(
    projection: VerificationProjection | None, gate_id: str, identity_hash: str
) -> bool:
    if projection is None or projection.candidate_identity.identity_hash != identity_hash:
        return False
    return any(
        gate.gate_id == gate_id
        and gate.status == "passed"
        and gate.candidate_identity_hash == identity_hash
        for gate in projection.gate_results
    )


def _prior_build_manifest(
    projection: VerificationProjection | None, identity_hash: str
) -> Any | None:
    if projection is None or projection.candidate_identity.identity_hash != identity_hash:
        return None
    if not _prior_gate_passed(projection, "type_build_artifact", identity_hash):
        return None
    if projection.build_manifest is None:
        return None
    return projection.build_manifest


def _materialized_manifest_matches(dist_dir: Path, manifest: Any) -> bool:
    """Prove that a reused build manifest has a matching local artifact tree."""

    entries = getattr(manifest, "entries", None)
    if not isinstance(entries, list) or not entries or not (dist_dir / "index.html").is_file():
        return False
    for entry in entries:
        relative = str(getattr(entry, "path", ""))
        target = (dist_dir / relative).resolve()
        if (
            not relative
            or not target.is_relative_to(dist_dir.resolve())
            or not target.is_file()
            or target.stat().st_size != int(getattr(entry, "size_bytes", -1))
            or hashlib.sha256(target.read_bytes()).hexdigest() != str(getattr(entry, "sha256", ""))
        ):
            return False
    return True


def _has_infrastructure_diagnostic(diagnostics: list[Diagnostic]) -> bool:
    return any(item.owner == "infrastructure" for item in diagnostics)


def _first_infrastructure_code(diagnostics: list[Diagnostic]) -> str:
    for item in diagnostics:
        if item.owner == "infrastructure":
            return item.code
    return "VERIFICATION_INFRASTRUCTURE_FAILED"


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode()


def _preview_host(run_id: str) -> str:
    encoded = (
        base64.b32encode(hashlib.sha256(run_id.encode()).digest())
        .decode("ascii")
        .lower()
        .rstrip("=")
    )
    return f"preview-{encoded[:48]}"


async def _session_source_is_current(repository: CodeGeneratorRepository, run: Any) -> bool:
    session_id = getattr(run, "portfolio_session_id", None)
    source = dict(getattr(run, "build_preparation_source_ref", None) or {})
    if session_id is None or not source:
        return False
    try:
        preparation = await repository.get_build_preparation_state(session_id)
    except (LookupError, ValueError):
        return False
    if preparation.package is None or preparation.package.artifact is None:
        return False
    artifact = preparation.package.artifact
    expected_artifact_value = source.get("artifact")
    expected_artifact: dict[str, Any] = (
        expected_artifact_value if isinstance(expected_artifact_value, dict) else {}
    )
    return bool(
        preparation.run_id == str(source.get("build_preparation_run_id", ""))
        and preparation.scope_hash == str(source.get("build_preparation_scope_hash", ""))
        and preparation.package.archive_sha256 == str(source.get("archive_sha256", ""))
        and artifact.sha256 == str(expected_artifact.get("sha256", ""))
        and artifact.key == str(expected_artifact.get("key", ""))
        and not is_expired(artifact)
    )


def _reference(run: Any) -> Any:
    from oryxenai.agents.code_generator.core.development_schemas import AdmittedInputReference

    return AdmittedInputReference.model_validate(run.input_reference)


def _resolve_config_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (repository_root() / path).resolve()


def _checkpoint(run: Any) -> Any:
    from oryxenai.agents.code_generator.core.development_schemas import SourceCheckpoint

    return SourceCheckpoint.model_validate(run.source_checkpoint)


def _source_manifest_hash(repo_dir: Path) -> str:
    from oryxenai.agents.code_generator.core.source_manifest import build_source_manifest, digest

    return digest(build_source_manifest(repo_dir))


async def _current_revision(sessionmaker: Any, run_id: UUID) -> int:
    async with sessionmaker() as db:
        run = await CodeGeneratorDevelopmentRepository(db).get(run_id)
        if run is None:
            raise VerificationFailure("RUN_NOT_FOUND", "The verification run was not found.")
        return int(run.revision)


async def _persist_projection(
    sessionmaker: Any,
    run_id: UUID,
    projection: VerificationProjection,
    status: str,
    *,
    values: dict[str, object] | None = None,
    event: tuple[str, str] | None = None,
) -> None:
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        await WorkerAuthorizationFence(db).validate_run(run_id)
        run = await repo.get(run_id)
        if run is None:
            raise VerificationFailure("RUN_NOT_FOUND", "The verification run was not found.")
        await _cas(
            repo,
            run,
            status,
            {
                "verification_projection": projection.model_dump(mode="json"),
                "issues": [],
                **(values or {}),
            },
        )
        if event:
            await repo.append_event(run_id, event_type=event[0], level="info", message=event[1])
        await db.commit()


async def _validate_run_fence(sessionmaker: Any, run_id: UUID) -> None:
    """Recheck local owner/actor/entitlement state before costly/publishing work."""

    async with sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_run(run_id)


async def _validate_worker_payload(sessionmaker: Any, payload: dict[str, Any]) -> None:
    async with sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_payload(payload)


def _payload_uuid(payload: dict[str, Any], key: str) -> UUID | None:
    value = payload.get(key)
    if value in (None, ""):
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _payload_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def _normalize_host_generated_tokens(
    *,
    sessionmaker: Any,
    run_id: UUID,
    run: Any,
    plan: SitePlan,
    workspace: GenerationWorkspace,
    checkpoint_store: CheckpointStore,
    checkpoint: Any,
) -> Any:
    """Re-emit trusted v3 tokens before final gates when an old checkpoint predates a fix.

    The foundation token file is host-owned deterministic output.  Older
    checkpoints may contain a materialized resource directory as a CSS URL;
    re-emitting it through the current compiler removes that invalid artifact
    reference without asking the provider for a creative repair.  The corrected
    tree receives a new checkpoint and is persisted so retries remain bound to
    the same deterministic source.
    """

    changed = False
    blueprint = plan.experience_blueprint
    if (
        isinstance(blueprint, (ExperienceBlueprintV3, ExperienceBlueprintV4))
        and plan.execution_bindings
    ):
        target = workspace.repo_dir / "src" / "design" / "generated-tokens.css"
        if target.is_file():
            # Older source checkpoints placed pack fonts under src/generated
            # because the materialization rule treated fonts like importable
            # components. Copy the same admitted pack material through the
            # current host-owned rule before recompiling tokens, so retries
            # repair the resource boundary without asking the provider for a
            # creative response.
            workspace.materialize_pack_resources()
            expected = compile_generated_tokens(blueprint, plan.execution_bindings)
            if target.read_text(encoding="utf-8") != expected:
                write_generated_tokens(workspace.repo_dir, blueprint, plan.execution_bindings)
                changed = True
    if not changed:
        return checkpoint
    corrected = checkpoint_store.accept(
        work_unit_id="deterministic-token-normalization",
        parent_hash=checkpoint.checkpoint_hash,
    )
    quality_rebound = False
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        current = await repo.get(run_id)
        if current is None:
            raise VerificationFailure("RUN_NOT_FOUND", "The verification run was not found.")
        generation_projection_update: dict[str, Any] | None = None
        generation_payload = current.generation_projection
        quality_payload = (
            generation_payload.get("quality_review")
            if isinstance(generation_payload, dict)
            else None
        )
        if isinstance(quality_payload, dict):
            try:
                quality_receipt = QualityReviewReceiptV2.model_validate(quality_payload)
            except ValueError:
                # Leave malformed or legacy quality state untouched. The
                # normal verification path will report the precise binding
                # failure instead of silently manufacturing a receipt.
                quality_receipt = None
            if (
                quality_receipt is not None
                and quality_receipt.source_manifest_hash == checkpoint.source_manifest_hash
            ):
                rebound_receipt = rebind_quality_review_receipt_source(
                    quality_receipt,
                    source_manifest_hash=corrected.source_manifest_hash,
                )
                rebound_projection = GenerationProjection.model_validate(generation_payload)
                rebound_projection.accepted_checkpoint = corrected
                rebound_projection.source_file_count = corrected.file_count
                rebound_projection.source_total_bytes = corrected.total_bytes
                rebound_projection.quality_review = rebound_receipt
                generation_projection_update = rebound_projection.model_dump(mode="json")
                quality_rebound = True
        updated = await repo.compare_and_swap(
            run_id,
            expected_revision=current.revision,
            values={
                "source_checkpoint": corrected.model_dump(mode="json"),
                "source_summary": {
                    "file_count": corrected.file_count,
                    "total_bytes": corrected.total_bytes,
                    "source_ready": True,
                    "checkpoint_hash": corrected.checkpoint_hash,
                },
                **(
                    {"generation_projection": generation_projection_update}
                    if generation_projection_update is not None
                    else {}
                ),
            },
        )
        if updated is None:
            raise VerificationFailure(
                "RUN_REVISION_CONFLICT",
                "The generated source changed while deterministic normalization was saved.",
            )
        await repo.append_event(
            run_id,
            event_type="deterministic_source_normalized",
            level="info",
            message="Host-owned generated tokens were recompiled before final verification.",
            details={
                "parent_checkpoint": checkpoint.checkpoint_hash,
                "quality_receipt_rebound": quality_rebound,
                "source_manifest": corrected.source_manifest_hash,
            },
        )
        await db.commit()
    logger.info(
        "normalized host-owned route contract run_id=%s prior_checkpoint=%s new_checkpoint=%s",
        run_id,
        checkpoint.checkpoint_hash,
        corrected.checkpoint_hash,
    )
    del run
    return corrected


async def _terminal(
    sessionmaker: Any,
    run_id: UUID,
    projection: VerificationProjection,
    *,
    code: str,
    summary: str,
    next_action: str,
) -> dict[str, Any]:
    diagnostics = projection.diagnostics
    occurrences: dict[str, int] = {}
    for item in diagnostics:
        occurrences[item.fingerprint] = occurrences.get(item.fingerprint, 0) + 1
    report = TerminalFailureReport(
        generation_id=projection.generation_id,
        terminal_code=code,
        owner="generator"
        if any(item.owner == "generator" for item in diagnostics)
        else "infrastructure",
        phase=projection.phase,
        input_plan_source_build_hashes={
            "candidate_identity": projection.candidate_identity.identity_hash,
            "source_checkpoint": projection.candidate_identity.source_checkpoint_hash,
            "build": projection.build_hash,
        },
        diagnostics=diagnostics,
        fingerprint_occurrences=occurrences,
        accepted_checkpoint=projection.candidate_identity.source_checkpoint_hash,
        repair_receipts=[item.receipt_hash for item in projection.repair_receipts],
        safe_user_summary=summary,
        recommended_next_action=next_action,
    )
    projection.terminal_failure = report
    projection.status = "needs_attention"
    await _persist_projection(
        sessionmaker,
        run_id,
        projection,
        DevelopmentRunStatus.NEEDS_ATTENTION.value,
        values={
            "terminal_failure": report.model_dump(mode="json"),
            "pending_promotion": None,
            # A terminal verification job is no longer active. Clearing the
            # identifier keeps same-run retries and the frontend action state
            # aligned with the durable job lifecycle.
            "verification_job_id": None,
        },
        event=("needs_attention", summary),
    )
    # The run already contains a complete, fail-closed terminal report. Do
    # not return a retryable job error here: the generic worker would launch a
    # hidden second verification attempt and could overwrite this report (or
    # a passing projection) with a later race. Callers can explicitly retry
    # through the idempotent verify endpoint after the infrastructure issue is
    # understood.
    return {"status": "needs_attention", "run_id": str(run_id), "code": code}


async def _safe_issue(sessionmaker: Any, run_id: UUID, issue: SafeIssue) -> None:
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        await WorkerAuthorizationFence(db).validate_run(run_id)
        run = await repo.get(run_id)
        if run is None:
            return
        await _cas(
            repo,
            run,
            DevelopmentRunStatus.NEEDS_ATTENTION.value,
            {"issues": [issue.model_dump(mode="json")]},
        )
        await repo.append_event(
            run_id,
            event_type="needs_attention",
            level="error",
            message=issue.message,
            details={"code": issue.code},
        )
        await db.commit()


def _quality_rejection_summary(review: Any) -> str:
    """Build a concrete, human-readable rejection reason from a quality review.

    Handles both the draft (`QualityReviewDraftV1`, which carries a free-text
    `review_summary`) and receipt shapes defensively via getattr, since the
    exact type varies by schema version.
    """

    parts = ["The final repaired source did not pass bounded whole-site re-review."]
    scores = {
        dimension: getattr(review, f"{dimension}_score", None)
        for dimension in ("hierarchy", "composition", "typography", "resource_fit", "motion")
    }
    score_text = " ".join(
        f"{dimension}={value}" for dimension, value in scores.items() if value is not None
    )
    if score_text:
        parts.append(f"Scores: {score_text}.")
    findings = getattr(review, "findings", None) or []
    blocking = [item for item in findings if getattr(item, "severity", "") == "blocking"]
    if blocking:
        finding_text = "; ".join(
            f"{item.code} ({item.file}:{item.line}): {item.evidence}" for item in blocking[:3]
        )
        parts.append(f"{len(blocking)} blocking finding(s): {finding_text}.")
    review_summary = getattr(review, "review_summary", "") or ""
    if review_summary:
        parts.append(f"Reviewer summary: {review_summary}")
    return " ".join(parts)


async def _attempt_repair(
    *,
    sessionmaker: Any,
    run_id: UUID,
    settings: Any,
    workspace: GenerationWorkspace,
    checkpoint_store: CheckpointStore,
    checkpoint: Any,
    identity: Any,
    plan: SitePlan,
    projections: dict[str, dict[str, Any]],
    projection: VerificationProjection,
    diagnostics: list[Diagnostic],
    public_text: set[str],
    allowed_packages: set[str],
    model_factory: Any | None,
) -> bool:
    await _validate_run_fence(sessionmaker, run_id)
    budget = RepairBudget(
        max_total=int(settings.code_generator_generation.max_repair_rounds_total),
        max_per_unit=int(settings.code_generator_generation.max_repair_rounds_per_unit),
        total_used=projection.repair_rounds,
        # This call site only ever repairs unit_id="final"; seeding
        # per_unit_used["final"] to the same value as total_used made the
        # two counters increase in lockstep, so the per-unit ceiling always
        # bound before the independently configured total could ever be reached —
        # the configured total was unreachable dead configuration. Starting
        # this counter at 0 lets it track actual final-stage repair rounds
        # independently, so max_repair_rounds_total governs as its name
        # promises.
        per_unit_used=_reconstruct_repair_unit_counts(projection.repair_receipts),
    )
    for receipt in projection.repair_receipts:
        for fingerprint in receipt.diagnostic_fingerprints:
            budget.fingerprint_counts[fingerprint] = (
                budget.fingerprint_counts.get(fingerprint, 0) + 1
            )
    projection.active_gate = diagnostics[0].group if diagnostics else ""
    repair_unit_id = projection.active_gate or "final"
    if not budget.can_attempt(diagnostics, unit_id=repair_unit_id):
        return False
    while True:
        strategy = budget.consume(diagnostics, unit_id=repair_unit_id)
        projection.status = "repairing"
        projection.phase = "repairing"
        await _persist_projection(
            sessionmaker,
            run_id,
            projection,
            DevelopmentRunStatus.REPAIRING.value,
            event=("repairing", "A bounded generator-owned verification repair is running."),
        )
        try:
            await _validate_run_fence(sessionmaker, run_id)
            corrected, receipt = await FinalRepairer(model_factory=model_factory).repair(
                settings=settings,
                workspace=workspace,
                checkpoint_store=checkpoint_store,
                checkpoint=checkpoint,
                identity=identity,
                plan=plan,
                projections=projections,
                diagnostics=diagnostics,
                allowed_paths=repair_allowed_paths(
                    diagnostics,
                    plan,
                    projections,
                    repo_dir=workspace.repo_dir,
                ),
                public_text=public_text,
                allowed_packages=allowed_packages,
                strategy=strategy,
                round_number=budget.total_used,
            )
            break
        except FinalRepairError:
            # The model honestly reported it could not produce a bounded
            # correction this round (repair_source.md's cannot_complete
            # escape hatch, or a context-binding mismatch). That is a used
            # round, not an infrastructure failure — the budget exists to
            # give a different round/strategy value another chance, so
            # only give up once the budget itself is exhausted.
            logger.warning(
                "final repair round produced no usable correction run_id=%s round=%s",
                run_id,
                budget.total_used,
                exc_info=True,
            )
            if not budget.can_attempt(diagnostics, unit_id=repair_unit_id):
                return False
            continue
        except Exception:
            logger.error(
                "final repair attempt failed run_id=%s",
                run_id,
                exc_info=True,
            )
            return False
    projection.repair_rounds = budget.total_used
    projection.repair_receipts.append(receipt)
    projection.diagnostics = []
    projection.gate_results = []
    generation_projection_payload: dict[str, Any] | None = None
    integration_review_payload: dict[str, Any] | None = None
    quality_rejected_review: Any | None = None
    if isinstance(plan.experience_blueprint, ExperienceBlueprintV4):
        async with sessionmaker() as db:
            current = await CodeGeneratorDevelopmentRepository(db).get(run_id)
            if current is None or not current.generation_projection:
                raise VerificationFailure(
                    "QUALITY_REVIEW_STATE_MISSING",
                    "The repaired v4 source has no generation quality state.",
                    owner="generator",
                )
            generation_projection = GenerationProjection.model_validate(
                current.generation_projection
            )
            generation_projection.accepted_checkpoint = corrected
            generation_projection.source_file_count = corrected.file_count
            generation_projection.source_total_bytes = corrected.total_bytes
            generation_projection.quality_review = None
            await _validate_run_fence(sessionmaker, run_id)
            review = await CodeGeneratorGenerationOrchestrator(
                model_factory=model_factory
            )._integration_review(
                sessionmaker=sessionmaker,
                run_id=run_id,
                settings=settings,
                run=current,
                plan=plan,
                workspace=workspace,
                projection=generation_projection,
                round_number=2,
                persist=False,
            )
            generation_projection_payload = generation_projection.model_dump(mode="json")
            integration_review_payload = review.model_dump(mode="json")
            if generation_projection.quality_review is None or not bool(
                generation_projection.quality_review.accepted
            ):
                quality_rejected_review = review
        if quality_rejected_review is not None:
            # The rejection reason was previously computed and then silently
            # discarded: the raise below used to happen before any persist
            # ran, so GET /runs/{id}/quality kept showing the stale
            # pre-repair receipt with no record of why the repair failed.
            # Persist the real review now that the nested session above has
            # closed (mirroring the accepted-path persist further down,
            # which also waits until outside that session), but deliberately
            # do NOT write source_checkpoint/source_summary — a rejected
            # repair must never become the run's accepted checkpoint.
            await _persist_projection(
                sessionmaker,
                run_id,
                projection,
                DevelopmentRunStatus.REPAIRING.value,
                values={
                    "generation_projection": generation_projection_payload,
                    "integration_review": integration_review_payload,
                },
            )
            raise VerificationFailure(
                "QUALITY_REVIEW_REJECTED_AFTER_REPAIR",
                _quality_rejection_summary(quality_rejected_review),
                owner="generator",
            )
    await _persist_projection(
        sessionmaker,
        run_id,
        projection,
        DevelopmentRunStatus.REPAIRING.value,
        values={
            "source_checkpoint": corrected.model_dump(mode="json"),
            "source_summary": {
                "checkpoint_hash": corrected.checkpoint_hash,
                "source_ready": True,
                "repair_round": budget.total_used,
            },
            **(
                {"generation_projection": generation_projection_payload}
                if generation_projection_payload is not None
                else {}
            ),
            **(
                {"integration_review": integration_review_payload}
                if integration_review_payload is not None
                else {}
            ),
        },
        event=(
            "repair_accepted",
            "A bounded source repair checkpoint was accepted; final gates will rerun.",
        ),
    )
    return True


async def _export_portfolio(
    sessionmaker: Any,
    run_id: UUID,
    settings: Any,
    *,
    workspace: GenerationWorkspace,
    manifest: Any,
    active: Any,
    plan: SitePlan,
    candidate_id: str,
    identity: Any,
    trace_id: str,
    pack_reference: str,
    generation_projection: dict[str, Any],
    quality_review: dict[str, Any] | None,
    realization_contracts: list[dict[str, Any]],
    provenance: dict[str, Any],
    verification: dict[str, Any],
    public_readback: dict[str, Any] | None,
) -> None:
    """Copy the complete portfolio (source + dist + metadata) to the export
    root. Advisory only: failures are recorded as events, never raised."""

    from oryxenai.agents.code_generator.core.portfolio_export import export_portfolio

    details: dict[str, object]
    try:
        exported = export_portfolio(
            settings=settings,
            run_id=str(run_id),
            repo_dir=workspace.repo_dir,
            metadata={
                "preview_url": active.url,
                "build_hash": manifest.build_hash,
                "candidate_id": candidate_id,
                "candidate_identity_hash": identity.identity_hash,
                "checkpoint_hash": identity.source_checkpoint_hash,
                "pack_reference": pack_reference,
                "trace_id": trace_id,
                "quality_review": quality_review,
                "realization_contracts": realization_contracts,
                "provenance": provenance,
                "call_ledger": _export_call_ledger(generation_projection),
                "verification": verification,
                "public_readback": public_readback,
                "routes": [
                    {"route_id": route.route_id, "path": route.path} for route in plan.routes
                ],
            },
        )
    except Exception as exc:
        logger.warning("portfolio export failed run_id=%s error=%s", run_id, exc)
        event = ("export_failed", "The portfolio export could not be written safely.")
        level = "warning"
        receipt = {
            "status": "failed",
            "error_code": "PORTFOLIO_EXPORT_FAILED",
        }
        details = {"error_code": "PORTFOLIO_EXPORT_FAILED", "trace_id": trace_id}
    else:
        logger.info("portfolio exported run_id=%s path=%s", run_id, exported)
        try:
            relative_export_path = (
                exported.resolve().relative_to(repository_root().resolve()).as_posix()
            )
        except ValueError:
            # An explicitly configured test/export root may live outside the
            # repository. Keep the receipt useful without exposing an absolute
            # machine path through the browser API.
            relative_export_path = exported.name
        receipt = {
            "status": "exported",
            "relative_path": relative_export_path,
            "folder": exported.name,
            "source_path": "source",
            "dist_path": "dist" if (exported / "dist").is_dir() else "",
            "metadata_path": "portfolio.json",
            "report_path": "generation-report.md",
            "exported_at": datetime.now(UTC).isoformat(),
        }
        event = ("exported", "Complete portfolio export is available for evaluation.")
        level = "info"
        details = {
            "relative_path": receipt["relative_path"],
            "folder": receipt["folder"],
            "report_path": receipt["report_path"],
        }
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        current = await repo.get(run_id)
        if current is not None:
            try:
                await repo.compare_and_swap(
                    run_id,
                    expected_revision=current.revision,
                    values={"export_receipt": receipt},
                )
            except Exception as exc:
                logger.warning(
                    "portfolio export receipt persistence failed run_id=%s error=%s",
                    run_id,
                    type(exc).__name__,
                )
        await repo.append_event(
            run_id,
            event_type=event[0],
            level=level,
            message=event[1],
            details=details,
        )
        await db.commit()


def _export_call_ledger(generation_projection: dict[str, Any]) -> dict[str, Any]:
    """Export metadata-only call references, never provider prompts or source."""

    calls = generation_projection.get("call_receipts", [])
    contexts = generation_projection.get("context_receipts", [])
    call_items = [item for item in calls if isinstance(item, dict)]
    context_items = [item for item in contexts if isinstance(item, dict)]
    return {
        "generation_id": str(generation_projection.get("generation_id", "")),
        "call_count": len(call_items),
        "call_receipt_ids": [str(item.get("receipt_id", "")) for item in call_items],
        "call_result_hashes": [str(item.get("result_hash", "")) for item in call_items],
        "context_receipt_hashes": [str(item.get("context_hash", "")) for item in context_items],
        "repair_rounds": int(generation_projection.get("repair_rounds", 0) or 0),
        "request_rounds": int(generation_projection.get("request_rounds", 0) or 0),
    }


async def _cas(repo: Any, run: Any, status: str, values: dict[str, object]) -> Any:
    await WorkerAuthorizationFence(repo._session).validate_run(run.id)
    updated = await repo.compare_and_swap(
        run.id, expected_revision=run.revision, values={"status": status, **values}
    )
    if updated is None:
        raise VerificationFailure(
            "RUN_REVISION_CONFLICT", "The verification run changed concurrently."
        )
    return updated
