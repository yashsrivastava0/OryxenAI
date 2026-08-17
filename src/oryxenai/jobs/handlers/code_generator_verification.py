"""Durable Phase 4 build, DOM verification, and preview promotion job."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from pathlib import Path
from typing import Any
from uuid import UUID

from oryxenai.agents.code_generator.core.build_runner import run_clean_build
from oryxenai.agents.code_generator.core.candidate_identity import build_candidate_identity
from oryxenai.agents.code_generator.core.checkpoint_store import CheckpointStore
from oryxenai.agents.code_generator.core.development_input import DevelopmentInputAdapter
from oryxenai.agents.code_generator.core.development_planner import validate_site_plan
from oryxenai.agents.code_generator.core.development_schemas import (
    DevelopmentRunStatus,
    Diagnostic,
    GateResult,
    PendingPromotion,
    SafeIssue,
    SitePlan,
    TerminalFailureReport,
    VerificationProjection,
)
from oryxenai.agents.code_generator.core.final_repair import FinalRepairer, repair_allowed_paths
from oryxenai.agents.code_generator.core.final_source_validation import validate_final_source
from oryxenai.agents.code_generator.core.generation_orchestrator import (
    _allowed_packages,
    _public_text,
)
from oryxenai.agents.code_generator.core.repair_policy import RepairBudget
from oryxenai.agents.code_generator.core.runtime_verifier import RuntimeVerifier
from oryxenai.agents.code_generator.core.verification_plan import (
    build_verification_profile,
    derive_verification_plan,
)
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace
from oryxenai.core.logging import get_logger
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository
from oryxenai.db.session import get_sessionmaker
from oryxenai.preview.gateway import create_candidate_app
from oryxenai.preview.promotion import PreviewPromoter
from oryxenai.preview.reconciler import reconcile_pending_promotion
from oryxenai.preview.server import EphemeralServer, start_ephemeral_server
from oryxenai.storage.preview import create_preview_storage

logger = get_logger("oryxenai.jobs.code_generator_verification")


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

    run_id = UUID(str(payload["development_run_id"]))
    settings = get_settings()
    sessionmaker = get_sessionmaker(settings)
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        run = await repo.get(run_id)
        if run is None:
            return {"status": "discarded", "run_id": str(run_id)}
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
            DevelopmentRunStatus.REPAIRING.value,
            DevelopmentRunStatus.NEEDS_ATTENTION.value,
        }:
            return {"status": "discarded", "run_id": str(run_id)}
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
                active = await reconcile_pending_promotion(
                    storage=storage,
                    run_id=str(run_id),
                    host=host,
                    pending=pending,
                    manifest=pending_projection.build_manifest,
                    preview_base_url=str(settings.code_generator_verification.preview_base_url),
                )
                pending_projection.status = "ready"
                pending_projection.phase = "ready"
                await _persist_projection(
                    sessionmaker,
                    run_id,
                    pending_projection,
                    DevelopmentRunStatus.READY.value,
                    values={
                        "pending_promotion": None,
                        "active_preview": active.model_dump(mode="json"),
                    },
                    event=("reconciled", "A pending preview promotion was reconciled safely."),
                )
                return {
                    "status": "succeeded",
                    "run_id": str(run_id),
                    "preview_url": active.url,
                    "reconciled": True,
                }
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

    profile = build_verification_profile(settings)
    server: EphemeralServer | None = None
    projection: VerificationProjection | None = None
    try:
        reference = _reference(run)
        adapter = DevelopmentInputAdapter(settings)
        input_receipt, projections = adapter.admit(reference)
        plan = SitePlan.model_validate(run.plan)
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
            Path(settings.code_generator_acquisition.materials_root).resolve(),
        )
        workspace.synchronize_dependency_manifest(
            Path(settings.code_generator_dependencies.workspaces_root).resolve()
            / str(run_id)
            / "repo"
        )
        source_manifest = _source_manifest_hash(workspace.repo_dir)
        if source_manifest != checkpoint.source_manifest_hash:
            raise VerificationFailure(
                "SOURCE_CHECKPOINT_DRIFT",
                "The restored source checkpoint does not match its source manifest.",
            )
        identity = build_candidate_identity(
            run=run,
            plan=plan,
            checkpoint=checkpoint,
            source_manifest_hash=source_manifest,
            profile=profile,
        )
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
        token = secrets.token_urlsafe(32)
        server = await start_ephemeral_server(
            create_candidate_app(
                workspace.repo_dir / "dist",
                token=token,
                parent_origin=str(settings.code_generator_verification.preview_parent_origin),
                mount_prefix=(
                    f"{settings.code_generator_verification.preview_route_prefix.rstrip('/')}/"
                    f"{host}/"
                ),
            )
        )
        verifier = (
            runtime_verifier_factory()
            if runtime_verifier_factory is not None
            else RuntimeVerifier()
        )
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
        projection.runtime_evidence = evidence
        projection.diagnostics.extend(runtime_diagnostics)
        projection.gate_results.append(
            GateResult(
                gate_id="dom_runtime",
                status="failed" if runtime_diagnostics else "passed",
                candidate_identity_hash=identity.identity_hash,
                build_hash=manifest.build_hash,
                expected_check_ids=profile.runtime_check_ids,
                executed_check_ids=profile.runtime_check_ids,
                diagnostics=runtime_diagnostics,
            )
        )
        if runtime_diagnostics:
            if server is not None:
                await server.close()
                server = None
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
        )
        host = str(run.preview_host or _preview_host(str(run_id)))
        candidate_id = f"candidate-{identity.identity_hash[:24]}"
        artifact, stored_report_hash, candidate_pointer = await promoter.store_candidate(
            candidate_id=candidate_id,
            host=host,
            identity=identity,
            manifest=manifest,
            dist_dir=workspace.repo_dir / "dist",
            verification_report={**report, "verification_report_hash": report_hash},
        )
        artifact = artifact.model_copy(
            update={"route_ids": [route.route_id for route in plan.routes]}
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
        active = await promoter.promote(
            run_id=str(run_id),
            host=host,
            pending=pending,
            candidate_pointer=candidate_pointer,
            verification_report_hash=stored_report_hash,
        )
        projection.status = "ready"
        projection.phase = "ready"
        projection.active_gate = ""
        projection.candidate_artifact = artifact
        await _persist_projection(
            sessionmaker,
            run_id,
            projection,
            DevelopmentRunStatus.READY.value,
            values={
                "candidate_artifact": artifact.model_dump(mode="json"),
                "pending_promotion": None,
                "active_preview": active.model_dump(mode="json"),
                "terminal_failure": None,
                "preview_host": host,
                "source_summary": {"preview_url": active.url, "build_hash": manifest.build_hash},
            },
            event=("promoted", "Verified portfolio preview promoted atomically."),
        )
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
            pack_reference=str((run.input_reference or {}).get("source_id", "")),
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
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


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


def _reference(run: Any) -> Any:
    from oryxenai.agents.code_generator.core.development_schemas import AdmittedInputReference

    return AdmittedInputReference.model_validate(run.input_reference)


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
        values={"terminal_failure": report.model_dump(mode="json"), "pending_promotion": None},
        event=("needs_attention", summary),
    )
    if report.owner == "infrastructure":
        return {
            "status": "failed",
            "run_id": str(run_id),
            "code": code,
            "error": {"code": code, "message": summary, "retryable": True},
        }
    return {"status": "needs_attention", "run_id": str(run_id), "code": code}


async def _safe_issue(sessionmaker: Any, run_id: UUID, issue: SafeIssue) -> None:
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
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
    budget = RepairBudget(
        max_total=int(settings.code_generator_generation.max_repair_rounds_total),
        max_per_unit=int(settings.code_generator_generation.max_repair_rounds_per_unit),
        total_used=projection.repair_rounds,
        per_unit_used={"final": projection.repair_rounds},
    )
    for receipt in projection.repair_receipts:
        for fingerprint in receipt.diagnostic_fingerprints:
            budget.fingerprint_counts[fingerprint] = (
                budget.fingerprint_counts.get(fingerprint, 0) + 1
            )
    if not budget.can_attempt(diagnostics, unit_id="final"):
        return False
    strategy = budget.consume(diagnostics, unit_id="final")
    projection.status = "repairing"
    projection.phase = "repairing"
    projection.active_gate = diagnostics[0].group if diagnostics else ""
    await _persist_projection(
        sessionmaker,
        run_id,
        projection,
        DevelopmentRunStatus.REPAIRING.value,
        event=("repairing", "A bounded generator-owned verification repair is running."),
    )
    try:
        corrected, receipt = await FinalRepairer(model_factory=model_factory).repair(
            settings=settings,
            workspace=workspace,
            checkpoint_store=checkpoint_store,
            checkpoint=checkpoint,
            identity=identity,
            plan=plan,
            projections=projections,
            diagnostics=diagnostics,
            allowed_paths=repair_allowed_paths(diagnostics, plan, projections),
            public_text=public_text,
            allowed_packages=allowed_packages,
            strategy=strategy,
            round_number=budget.total_used,
        )
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
    pack_reference: str,
) -> None:
    """Copy the complete portfolio (source + dist + metadata) to the export
    root. Advisory only: failures are recorded as events, never raised."""

    from oryxenai.agents.code_generator.core.portfolio_export import export_portfolio

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
                "routes": [
                    {"route_id": route.route_id, "path": route.path} for route in plan.routes
                ],
            },
        )
    except Exception as exc:
        logger.warning("portfolio export failed run_id=%s error=%s", run_id, exc)
        event = ("export_failed", f"The portfolio export could not be written: {exc}")
        level = "warning"
    else:
        logger.info("portfolio exported run_id=%s path=%s", run_id, exported)
        event = ("exported", f"Complete portfolio exported to {exported}")
        level = "info"
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        await repo.append_event(run_id, event_type=event[0], level=level, message=event[1])
        await db.commit()


async def _cas(repo: Any, run: Any, status: str, values: dict[str, object]) -> Any:
    updated = await repo.compare_and_swap(
        run.id, expected_revision=run.revision, values={"status": status, **values}
    )
    if updated is None:
        raise VerificationFailure(
            "RUN_REVISION_CONFLICT", "The verification run changed concurrently."
        )
    return updated
