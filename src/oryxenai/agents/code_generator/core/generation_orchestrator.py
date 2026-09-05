"""Progressive, receipt-driven Phase 3 source-generation orchestration."""

from __future__ import annotations

import asyncio
import contextlib
import fnmatch
import hashlib
import json
import re
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from pydantic import ValidationError

from oryxenai.agents.code_generator.core import fs_safe
from oryxenai.agents.code_generator.core.acquisition_validators import (
    AcquisitionValidationError,
    filter_candidates_by_policy,
    select_candidate,
    validate_plan_delta,
    validate_resource_request,
)
from oryxenai.agents.code_generator.core.blueprint_compiler import canonicalize_generation_plan
from oryxenai.agents.code_generator.core.check_runner import prepare_toolchain, run_source_checks
from oryxenai.agents.code_generator.core.checkpoint_store import CheckpointError, CheckpointStore
from oryxenai.agents.code_generator.core.content_compiler import (
    content_ids_by_section,
    write_content_module,
)
from oryxenai.agents.code_generator.core.coordinator import advance_after
from oryxenai.agents.code_generator.core.dependency_manager import (
    DependencyManager,
    build_dependency_ledger,
)
from oryxenai.agents.code_generator.core.design_realization import compile_design_realization
from oryxenai.agents.code_generator.core.development_input import (
    DevelopmentInputAdapter,
    DevelopmentInputError,
)
from oryxenai.agents.code_generator.core.development_planner import validate_site_plan
from oryxenai.agents.code_generator.core.development_schemas import (
    DependencyLedger,
    DevelopmentRunStatus,
    ExperienceBlueprintV3,
    ExperienceBlueprintV4,
    GenerationCallReceipt,
    GenerationChanges,
    GenerationContextReceipt,
    GenerationProjection,
    GenerationResult,
    GenerationWorkUnitProjection,
    IntegrationReviewV1,
    PlanDelta,
    QualityReviewDraftV1,
    ResourceBinding,
    ResourceLedger,
    ResourceReceipt,
    SafeIssue,
    SitePlan,
    SourceCheckpoint,
    SourceDiagnostic,
    SourceGenerationEnvelopeV2,
    WorkUnit,
)
from oryxenai.agents.code_generator.core.generation_contract import build_generation_contract
from oryxenai.agents.code_generator.core.generation_prompt_builder import (
    ROUTE_UNIT_KEY_ORDER,
    build_instructions,
)
from oryxenai.agents.code_generator.core.integration_review_operation import (
    run_integration_review_operation,
)
from oryxenai.agents.code_generator.core.parallel_scheduler import (
    execute_waves,
    isolated_workspace_path,
)
from oryxenai.agents.code_generator.core.path_policy import semantic_segment
from oryxenai.agents.code_generator.core.quality_review import (
    QualityReviewError,
    stamp_quality_review_receipt,
)
from oryxenai.agents.code_generator.core.resource_adapters import (
    OfflineResourceProviderRegistry,
    ResourceProviderError,
    default_adapters,
)
from oryxenai.agents.code_generator.core.source_generation_adapter import (
    adapt_v4_generation_result,
    stamp_v4_required_coverage,
)
from oryxenai.agents.code_generator.core.source_manifest import (
    build_source_manifest,
    digest,
    materialize_trusted_manifests,
)
from oryxenai.agents.code_generator.core.source_validation import (
    SourceValidationError,
    validate_generation_changes,
    validate_route_batch_contract,
    validate_route_composer_contract,
)
from oryxenai.agents.code_generator.core.token_compiler import (
    TokenCompilationError,
    write_generated_tokens,
)
from oryxenai.agents.code_generator.core.workspace import (
    GenerationWorkspace,
    WorkspaceError,
    repository_root,
)
from oryxenai.agents.shared.providers.errors import (
    ModelJsonInvalidError,
    ModelOutputTruncatedError,
    ProviderError,
    stable_provider_failure,
)
from oryxenai.auth.worker_fence import WorkerAuthorizationFence
from oryxenai.core.logging import get_logger
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository
from oryxenai.db.session import get_sessionmaker

logger = get_logger("oryxenai.agents.code_generator.generation")


def _unit_dir_slug(unit_id: str) -> str:
    """Filesystem-safe workspace suffix for a work-unit id.

    Unit ids follow the colon-namespaced convention (``unit:route:home``);
    Windows forbids colons (and other reserved characters) in paths.
    """

    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", unit_id).strip("._")
    return slug or "unit"


class GenerationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _reset_generation_attempt_projection(projection: GenerationProjection) -> None:
    """Drop rejected-attempt diagnostics before a same-run retry."""

    projection.diagnostics = []
    projection.issues = []
    for unit_projection in projection.work_units:
        unit_projection.diagnostics = []


async def _prepare_isolated_route_repo(source_repo: Path, isolated_root: Path) -> Path:
    """Create a source-only route workspace without blocking the event loop.

    Route batches never execute the toolchain inside their disposable copies;
    dependency and build trees are explicitly excluded by source and export
    validation. Keeping the copy source-only avoids multiplying a potentially
    large ``node_modules`` tree and running the recursive filesystem work on
    the worker's event loop.
    """

    if isolated_root.exists():
        await asyncio.to_thread(shutil.rmtree, isolated_root)
    isolated_root.mkdir(parents=True, exist_ok=True)
    isolated_repo = isolated_root / "repo"
    await asyncio.to_thread(
        shutil.copytree,
        source_repo,
        isolated_repo,
        ignore=shutil.ignore_patterns("node_modules", "dist"),
    )
    dependency_tree = source_repo / "node_modules"
    if dependency_tree.is_dir():
        isolated_dependencies = isolated_repo / "node_modules"
        try:
            isolated_dependencies.symlink_to(dependency_tree, target_is_directory=True)
        except OSError:
            # Some Windows hosts do not grant directory-symlink creation to
            # the worker account. Preserve the same toolchain contract with a
            # bounded background copy rather than blocking the event loop.
            await asyncio.to_thread(
                shutil.copytree,
                dependency_tree,
                isolated_dependencies,
                symlinks=True,
            )
    return isolated_repo


def _resolve_config_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (repository_root() / path).resolve()


class CodeGeneratorGenerationOrchestrator:
    def __init__(
        self,
        *,
        model_factory: Callable[[str], Any] | None = None,
        adapter_factory: Callable[[Any], dict[str, Any]] | None = None,
    ) -> None:
        self._model_factory = model_factory
        self._adapter_factory = adapter_factory

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        del instance_id
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
            if run.status == DevelopmentRunStatus.SOURCE_READY.value and run.generation_projection:
                return {"status": "succeeded", "run_id": str(run_id), "reused": True}
            if run.status not in {
                DevelopmentRunStatus.QUEUED.value,
                DevelopmentRunStatus.ACQUIRED.value,
                DevelopmentRunStatus.NEEDS_ATTENTION.value,
                DevelopmentRunStatus.GENERATING_FOUNDATION.value,
                DevelopmentRunStatus.GENERATING_ROUTES.value,
                DevelopmentRunStatus.INTEGRATING.value,
            }:
                return {"status": "discarded", "run_id": str(run_id)}
            plan = canonicalize_generation_plan(SitePlan.model_validate(run.plan or {}))
            if not run.input_receipt:
                raise GenerationError(
                    "INPUT_RECEIPT_MISSING", "The generation run has no admitted input receipt."
                )
            generation_id = (
                str((run.generation_projection or {}).get("generation_id", ""))
                or f"generation-{run_id}"
            )
            resumed = bool(run.generation_projection)
            projection = (
                GenerationProjection.model_validate(run.generation_projection)
                if resumed
                else self._initial_projection(run, generation_id, plan)
            )
            if resumed:
                # A frontend resume starts a new executable attempt. Keep
                # accepted checkpoints and immutable receipts, but do not
                # feed diagnostics from the rejected attempt back into the
                # next model operation; those diagnostics can describe a
                # candidate tree that will be rebuilt or restored below.
                _reset_generation_attempt_projection(projection)
            updated = await _cas(
                repo,
                run,
                DevelopmentRunStatus.GENERATING_FOUNDATION.value,
                {
                    "current_attempt": run.current_attempt if resumed else run.current_attempt + 1,
                    "generation_projection": projection.model_dump(mode="json"),
                    "issues": [],
                },
            )
            del updated
            await repo.append_event(
                run_id,
                event_type="generating_foundation",
                level="info",
                message="Creating the trusted source workspace and shared foundation.",
            )
            await db.commit()

        try:
            await _validate_worker_payload(sessionmaker, payload)
            reference = self._reference(run)
            input_adapter = DevelopmentInputAdapter(settings)
            input_receipt, projections = input_adapter.admit(reference)
            plan = canonicalize_generation_plan(SitePlan.model_validate(run.plan or {}))
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
            checkpoint_store = CheckpointStore(workspace, generation_id=generation_id)
            if projection.accepted_checkpoint is not None:
                checkpoint_store.restore(projection.accepted_checkpoint)
                # A checkpoint may have been produced by an older generator
                # version. Restore its mutable source, then reassert the
                # immutable shell before any toolchain or source checks run.
                workspace.reassert_trusted_shell()
            if run.resource_ledger:
                projections["resources/ledger.json"] = dict(run.resource_ledger)
            generated_manifests = materialize_trusted_manifests(
                workspace,
                projections,
                plan,
                acquisition_ledger=run.resource_ledger,
                # Receipt local_paths are recorded relative to the configured
                # materials root (already prefixed with the run id).
                acquisition_materials_root=_resolve_config_path(
                    settings.code_generator_acquisition.materials_root
                ),
                settings=settings,
            )
            projections["generated/resource-assets.json"] = {
                "image_assets": list(generated_manifests.get("image_assets", []))
            }
            configured_workspace_root = Path(settings.code_generator_dependencies.workspaces_root)
            dependency_repo = (
                (
                    configured_workspace_root
                    if configured_workspace_root.is_absolute()
                    else (repository_root() / configured_workspace_root).resolve()
                )
                / str(run_id)
                / "repo"
            )
            workspace.synchronize_dependency_manifest(dependency_repo)
            toolchain_issue = await prepare_toolchain(workspace.repo_dir, settings=settings)
            if toolchain_issue is not None:
                raise GenerationError(toolchain_issue.code, toolchain_issue.normalized_message)
            workspace.write_json(
                workspace.ledger_dir / "site-plan.json", plan.model_dump(mode="json")
            )
            workspace.write_json(workspace.ledger_dir / "projections.json", projections)
            allowed_packages = _allowed_packages(
                workspace.repo_dir, projections, run.dependency_ledger
            )
            public_text = _public_text(projections)
            stale_route_diagnostics = _invalidate_stale_route_batch_checkpoint(
                projection,
                plan=plan,
                workspace=workspace,
                projections=projections,
            )
            if stale_route_diagnostics:
                projection.diagnostics.extend(stale_route_diagnostics)
            projection = self._prepare_projection(projection, plan)
            await self._persist(
                sessionmaker,
                run_id,
                projection,
                status=DevelopmentRunStatus.GENERATING_FOUNDATION.value,
            )
            checkpoint = await self._run_units(
                sessionmaker=sessionmaker,
                run_id=run_id,
                settings=settings,
                run=run,
                plan=plan,
                projections=projections,
                workspace=workspace,
                checkpoint_store=checkpoint_store,
                projection=projection,
                allowed_packages=allowed_packages,
                public_text=public_text,
            )
            projection.accepted_checkpoint = checkpoint
            projection.source_ready = True
            projection.phase = "source_ready"
            projection.active_work_unit_id = ""
            projection.source_file_count = checkpoint.file_count
            projection.source_total_bytes = checkpoint.total_bytes
            await self._persist(
                sessionmaker,
                run_id,
                projection,
                status=DevelopmentRunStatus.SOURCE_READY.value,
                source_checkpoint=checkpoint,
                source_summary={
                    "checkpoint_hash": checkpoint.checkpoint_hash,
                    "file_count": checkpoint.file_count,
                    "total_bytes": checkpoint.total_bytes,
                    "source_ready": True,
                },
                event=(
                    "source_ready",
                    "Source generation completed with an accepted source checkpoint.",
                ),
            )
            await advance_after(sessionmaker, run_id, completed_stage="source_ready")
            return {"status": "succeeded", "run_id": str(run_id)}
        except GenerationError as exc:
            await self._fail(
                sessionmaker,
                run_id,
                SafeIssue(
                    code=exc.code,
                    message=exc.message,
                    next_action="Review the generation issue and start a corrected run.",
                ),
            )
            return {"status": "needs_attention", "run_id": str(run_id), "code": exc.code}
        except (
            WorkspaceError,
            SourceValidationError,
            QualityReviewError,
            AcquisitionValidationError,
            CheckpointError,
            fs_safe.FsSafeError,
        ) as exc:
            code = getattr(exc, "code", "GENERATION_FAILED")
            message = getattr(exc, "message", str(exc))
            await self._fail(
                sessionmaker,
                run_id,
                SafeIssue(
                    code=code,
                    message=message,
                    next_action="Review the generation issue and start a corrected run.",
                ),
            )
            return {"status": "needs_attention", "run_id": str(run_id)}
        except DevelopmentInputError as exc:
            await self._fail(
                sessionmaker,
                run_id,
                SafeIssue(
                    code=exc.code,
                    message=exc.message,
                    next_action="Review the generation input and start a corrected run.",
                    details=exc.details,
                ),
            )
            return {"status": "needs_attention", "run_id": str(run_id)}
        except ValidationError as exc:
            summary = _safe_generation_validation_summary(exc)
            await self._fail(
                sessionmaker,
                run_id,
                SafeIssue(
                    code="GENERATION_OUTPUT_INVALID",
                    message=f"The generated structured result failed local validation: {summary}",
                    next_action="Retry generation with the bounded schema-correction path.",
                    details={
                        "exception_type": type(exc).__name__,
                        "validation_summary": summary,
                    },
                ),
            )
            return {"status": "needs_attention", "run_id": str(run_id)}
        except TokenCompilationError as exc:
            reason = str(exc).strip()[:400] or "The visual token blueprint could not be compiled."
            await self._fail(
                sessionmaker,
                run_id,
                SafeIssue(
                    code="TOKEN_COMPILATION_INVALID",
                    message=f"The visual token blueprint could not be compiled safely: {reason}",
                    next_action="Retry with a corrected typed visual blueprint.",
                    details={"exception_type": type(exc).__name__, "reason": reason},
                ),
            )
            return {"status": "needs_attention", "run_id": str(run_id)}
        except ProviderError as exc:
            code, message = stable_provider_failure(exc)
            details: dict[str, str | int | float | bool] = {"exception_type": type(exc).__name__}
            await self._fail(
                sessionmaker,
                run_id,
                SafeIssue(
                    code=code,
                    message=message,
                    next_action="Review the provider contract and start a corrected run.",
                    details=details,
                ),
            )
            return {"status": "needs_attention", "run_id": str(run_id), "code": code}
        except Exception as exc:
            logger.error(
                "code generator generation failed run_id=%s error=%s",
                run_id,
                type(exc).__name__,
                exc_info=exc,
            )
            await self._fail(
                sessionmaker,
                run_id,
                SafeIssue(
                    code="GENERATION_FAILED",
                    message="Source generation could not complete safely.",
                    next_action="Review the run diagnostics and start a corrected run.",
                    details={"exception_type": type(exc).__name__},
                ),
            )
            return {"status": "needs_attention", "run_id": str(run_id)}

    async def _run_units(
        self,
        *,
        sessionmaker: Any,
        run_id: UUID,
        settings: Any,
        run: Any,
        plan: SitePlan,
        projections: dict[str, dict[str, Any]],
        workspace: GenerationWorkspace,
        checkpoint_store: CheckpointStore,
        projection: GenerationProjection,
        allowed_packages: set[str],
        public_text: set[str],
    ) -> SourceCheckpoint:
        units = _topological_units(plan.work_graph.units)
        checkpoint: SourceCheckpoint | None = projection.accepted_checkpoint
        index = 0
        while index < len(units):
            unit = units[index]
            existing_unit = _unit_projection(projection, unit)
            if existing_unit.status == "checkpointed" and existing_unit.checkpoint_after:
                index += 1
                continue
            if unit.kind == "integration":
                status = DevelopmentRunStatus.INTEGRATING.value
            elif unit.kind == "foundation":
                status = DevelopmentRunStatus.GENERATING_FOUNDATION.value
            else:
                status = DevelopmentRunStatus.GENERATING_ROUTES.value

            if (
                isinstance(
                    plan.experience_blueprint, (ExperienceBlueprintV3, ExperienceBlueprintV4)
                )
                and unit.kind == "route_batch"
            ):
                batch_units: list[WorkUnit] = []
                while index < len(units) and units[index].kind == "route_batch":
                    batch_units.append(units[index])
                    index += 1
                projection.phase = status
                projection.active_work_unit_id = batch_units[0].unit_id
                for batch in batch_units:
                    batch_projection = _unit_projection(projection, batch)
                    batch_projection.status = "context_ready"
                    batch_projection.checkpoint_before = (
                        checkpoint.checkpoint_hash if checkpoint else ""
                    )
                await self._persist(sessionmaker, run_id, projection, status=status)
                checkpoint = await self._run_route_batch_wave(
                    sessionmaker=sessionmaker,
                    run_id=run_id,
                    settings=settings,
                    run=run,
                    plan=plan,
                    projections=projections,
                    workspace=workspace,
                    checkpoint_store=checkpoint_store,
                    projection=projection,
                    units=batch_units,
                    checkpoint=checkpoint,
                    allowed_packages=allowed_packages,
                    public_text=public_text,
                )
                await self._persist(sessionmaker, run_id, projection, status=status)
                continue

            index += 1
            projection.phase = status
            projection.active_work_unit_id = unit.unit_id
            unit_projection = _unit_projection(projection, unit)
            unit_projection.status = "context_ready"
            unit_projection.checkpoint_before = checkpoint.checkpoint_hash if checkpoint else ""
            await self._persist(sessionmaker, run_id, projection, status=status)
            checkpoint = await self._run_unit(
                sessionmaker=sessionmaker,
                run_id=run_id,
                settings=settings,
                run=run,
                plan=plan,
                projections=projections,
                workspace=workspace,
                checkpoint_store=checkpoint_store,
                projection=projection,
                unit=unit,
                checkpoint=checkpoint,
                allowed_packages=allowed_packages,
                public_text=public_text,
            )
            unit_projection.status = "checkpointed"
            unit_projection.checkpoint_after = checkpoint.checkpoint_hash
            projection.accepted_checkpoint = checkpoint
            await self._persist(sessionmaker, run_id, projection, status=status)
        if checkpoint is None:
            raise GenerationError("SOURCE_CHECKPOINT_MISSING", "No source checkpoint was accepted.")
        return checkpoint

    async def _run_route_batch_wave(
        self,
        *,
        sessionmaker: Any,
        run_id: UUID,
        settings: Any,
        run: Any,
        plan: SitePlan,
        projections: dict[str, dict[str, Any]],
        workspace: GenerationWorkspace,
        checkpoint_store: CheckpointStore,
        projection: GenerationProjection,
        units: list[WorkUnit],
        checkpoint: SourceCheckpoint | None,
        allowed_packages: set[str],
        public_text: set[str],
    ) -> SourceCheckpoint:
        async def execute(unit: WorkUnit) -> tuple[GenerationProjection, SourceCheckpoint, Path]:
            isolated_root = isolated_workspace_path(workspace.root, unit)
            if not isolated_root.resolve().is_relative_to(workspace.root.resolve()):
                raise GenerationError(
                    "PARALLEL_WORKSPACE_PATH_UNSAFE",
                    "A parallel route workspace escaped the generation workspace.",
                )
            await _prepare_isolated_route_repo(
                workspace.repo_dir,
                isolated_root,
            )
            isolated = GenerationWorkspace(
                isolated_root,
                workspace.input_dir,
                workspace.checkpoint_root,
            )
            isolated.scaffold_dir = workspace.scaffold_dir
            isolated.ledger_dir.mkdir(parents=True, exist_ok=True)
            local_checkpoint_store = CheckpointStore(
                isolated, generation_id=projection.generation_id
            )
            local_projection = projection.model_copy(deep=True)
            local_checkpoint = await self._run_unit(
                sessionmaker=sessionmaker,
                run_id=run_id,
                settings=settings,
                run=run,
                plan=plan,
                projections=projections,
                workspace=isolated,
                checkpoint_store=local_checkpoint_store,
                projection=local_projection,
                unit=unit,
                checkpoint=checkpoint,
                allowed_packages=allowed_packages,
                public_text=public_text,
                persist_projection=False,
            )
            return local_projection, local_checkpoint, isolated_root

        # The foundation dependency has already been accepted by the caller's
        # preceding sequential wave.  The bounded scheduler receives only the
        # current route-batch wave, so retain only dependencies that are also
        # in this subset; otherwise an already-satisfied external dependency
        # is indistinguishable from an unknown graph edge.
        batch_ids = {unit.unit_id for unit in units}
        schedulable_units = [
            unit.model_copy(
                update={
                    "depends_on": [
                        dependency for dependency in unit.depends_on if dependency in batch_ids
                    ]
                }
            )
            for unit in units
        ]
        scheduled = await execute_waves(
            schedulable_units,
            execute,
            max_concurrency=int(settings.code_generator_generation.route_concurrency),
        )
        merged_projection = projection.model_copy(deep=True)
        merged_checkpoints: list[tuple[WorkUnit, SourceCheckpoint, Path]] = []
        for item in scheduled:
            local_projection, local_checkpoint, isolated_root = cast(
                tuple[GenerationProjection, SourceCheckpoint, Path], item.value
            )
            unit = next(unit for unit in units if unit.unit_id == item.unit_id)
            for relative in unit.owns_paths:
                source = isolated_root / "repo" / relative
                target = workspace.repo_dir / relative
                if source.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
            local_contexts = isolated_root / "ledger" / "contexts"
            if local_contexts.is_dir():
                target_contexts = workspace.ledger_dir / "contexts"
                target_contexts.mkdir(parents=True, exist_ok=True)
                for context in local_contexts.glob("*.json"):
                    shutil.copyfile(context, target_contexts / context.name)
            local_unit = _unit_projection(local_projection, unit)
            main_unit = _unit_projection(merged_projection, unit)
            merged_unit_ids = {item.unit_id for item in merged_projection.work_units}
            merged_projection.work_units.extend(
                item for item in local_projection.work_units if item.unit_id not in merged_unit_ids
            )
            main_unit.status = local_unit.status
            main_unit.request_round = local_unit.request_round
            main_unit.repair_round = local_unit.repair_round
            main_unit.call_receipt_id = local_unit.call_receipt_id
            main_unit.diagnostics = list(local_unit.diagnostics)
            merged_projection.context_receipts.extend(
                receipt
                for receipt in local_projection.context_receipts
                if receipt.receipt_id
                not in {existing.receipt_id for existing in merged_projection.context_receipts}
            )
            merged_projection.call_receipts.extend(
                receipt
                for receipt in local_projection.call_receipts
                if receipt.receipt_id
                not in {existing.receipt_id for existing in merged_projection.call_receipts}
            )
            merged_projection.diagnostics.extend(
                diagnostic
                for diagnostic in local_projection.diagnostics
                if diagnostic.diagnostic_id
                not in {existing.diagnostic_id for existing in merged_projection.diagnostics}
            )
            merged_checkpoints.append((unit, local_checkpoint, isolated_root))

        diagnostics = await run_source_checks(
            workspace.repo_dir,
            allowed_packages=allowed_packages,
            public_text=public_text,
            max_source_bytes=int(settings.code_generator_generation.max_source_bytes),
            work_unit_id="route-batch-wave",
            settings=settings,
            # Route batches own section modules only.  The route shell is
            # intentionally composed in the following route_compose unit, so
            # the whole-site V4 audit must wait until that contract exists.
            include_source_audit=False,
        )
        if diagnostics:
            raise GenerationError(
                "PARALLEL_ROUTE_SOURCE_CHECK_FAILED",
                "The merged route-batch wave failed the deterministic source audit.",
            )
        projection.context_receipts = merged_projection.context_receipts
        projection.call_receipts = merged_projection.call_receipts
        projection.diagnostics = merged_projection.diagnostics
        for unit, _local_checkpoint, _isolated_root in merged_checkpoints:
            checkpoint = checkpoint_store.accept(
                work_unit_id=unit.unit_id,
                parent_hash=checkpoint.checkpoint_hash if checkpoint else "",
            )
            unit_projection = _unit_projection(projection, unit)
            unit_projection.status = "checkpointed"
            unit_projection.checkpoint_after = checkpoint.checkpoint_hash
            projection.accepted_checkpoint = checkpoint
        if checkpoint is None:
            raise GenerationError(
                "SOURCE_CHECKPOINT_MISSING",
                "The route-batch wave did not produce an accepted checkpoint.",
            )
        return checkpoint

    async def _run_unit(
        self,
        *,
        sessionmaker: Any,
        run_id: UUID,
        settings: Any,
        run: Any,
        plan: SitePlan,
        projections: dict[str, dict[str, Any]],
        workspace: GenerationWorkspace,
        checkpoint_store: CheckpointStore,
        projection: GenerationProjection,
        unit: WorkUnit,
        checkpoint: SourceCheckpoint | None,
        allowed_packages: set[str],
        public_text: set[str],
        persist_projection: bool = True,
    ) -> SourceCheckpoint:
        if unit.kind == "foundation" and isinstance(
            plan.experience_blueprint, (ExperienceBlueprintV3, ExperienceBlueprintV4)
        ):
            # V3 foundation material is a deterministic compiler boundary, not
            # a model-authored surface. This keeps tokens and approved copy
            # stable across retries and makes the trusted shared systems the
            # only shell implementation.
            write_generated_tokens(
                workspace.repo_dir,
                plan.experience_blueprint,
                plan.execution_bindings,
            )
            public_content = projections.get("site/contract.json", {}).get("public_content", [])
            if not isinstance(public_content, list):
                raise GenerationError(
                    "PUBLIC_CONTENT_MISSING", "The admitted public content projection is invalid."
                )
            write_content_module(
                workspace.repo_dir,
                public_content,
                [
                    item
                    for item in projections["site/contract.json"].get("facts", [])
                    if isinstance(item, dict)
                ],
            )
            diagnostics = await run_source_checks(
                workspace.repo_dir,
                allowed_packages=allowed_packages,
                public_text=public_text,
                max_source_bytes=int(settings.code_generator_generation.max_source_bytes),
                work_unit_id=unit.unit_id,
                settings=settings,
                # The foundation updates trusted generated manifests while
                # route composition is still the scaffold placeholder.  Keep
                # the toolchain and structural checks active, but defer the
                # complete route audit to route_compose/integration.
                include_source_audit=False,
            )
            if diagnostics:
                projection.diagnostics.extend(diagnostics)
                unit_projection = _unit_projection(projection, unit)
                unit_projection.diagnostics.extend(item.diagnostic_id for item in diagnostics)
                raise GenerationError(
                    "FOUNDATION_SOURCE_CHECK_FAILED",
                    "The deterministic foundation failed the source audit.",
                )
            return checkpoint_store.accept(
                work_unit_id=unit.unit_id,
                parent_hash=checkpoint.checkpoint_hash if checkpoint else "",
            )
        operation = _operation_for(unit)
        role_profile = _profile_for(operation, settings)
        unit_projection = _unit_projection(projection, unit)
        if unit.kind == "integration":
            # Always run the deterministic source audit first. Session runs
            # then add one bounded, structured whole-site review and an
            # owner-scoped polish pass; standalone compatibility runs keep
            # their historical provider-free terminal audit.
            diagnostics = await run_source_checks(
                workspace.repo_dir,
                allowed_packages=allowed_packages,
                public_text=public_text,
                max_source_bytes=int(settings.code_generator_generation.max_source_bytes),
                work_unit_id=unit.unit_id,
                settings=settings,
                include_source_audit=unit.kind in {"route_compose", "integration"},
            )
            if diagnostics:
                projection.diagnostics.extend(diagnostics)
                unit_projection.diagnostics.extend(item.diagnostic_id for item in diagnostics)
                raise GenerationError(
                    "INTEGRATION_SOURCE_CHECK_FAILED",
                    "The completed source tree failed the deterministic integration audit.",
                )
            if str(getattr(run, "run_mode", "development")) == "session" or isinstance(
                plan.experience_blueprint, ExperienceBlueprintV4
            ):
                await self._review_and_polish(
                    sessionmaker=sessionmaker,
                    run_id=run_id,
                    settings=settings,
                    run=run,
                    plan=plan,
                    projections=projections,
                    workspace=workspace,
                    projection=projection,
                    checkpoint_store=checkpoint_store,
                    checkpoint=checkpoint,
                    allowed_packages=allowed_packages,
                    public_text=public_text,
                )
            return checkpoint_store.accept(
                work_unit_id=unit.unit_id,
                parent_hash=checkpoint.checkpoint_hash if checkpoint else "",
            )
        request_round = 0
        repair_round = 0
        rejected_attempt_files: dict[str, str] = {}
        while True:
            context = _operation_context(
                plan=plan,
                projections=projections,
                unit=unit,
                operation=operation,
                checkpoint=checkpoint,
                workspace=workspace,
                role_profile=role_profile,
                output_ceiling=int(settings.code_generator_generation.max_response_bytes),
                diagnostics=projection.diagnostics,
                repair_round=repair_round,
                rejected_attempt_files=rejected_attempt_files,
            )
            context = _enforce_context_ceiling(
                context,
                int(settings.code_generator_generation.max_context_chars),
            )
            output_model = (
                SourceGenerationEnvelopeV2
                if _context_uses_v4_contract(context)
                else GenerationResult
            )
            system, instructions, context_receipt = build_instructions(
                operation, context, output_model=output_model
            )
            context_path = (
                workspace.ledger_dir / "contexts" / f"{context_receipt.context_hash}.json"
            )
            workspace.write_json(context_path, context)
            context_receipt = context_receipt.model_copy(
                update={"stored_relative_path": context_path.relative_to(workspace.root).as_posix()}
            )
            projection.context_receipts.append(context_receipt)
            unit_projection.status = "model_requested"
            unit_projection.request_round = request_round
            if persist_projection:
                await self._persist(sessionmaker, run_id, projection, status=projection.phase)
            try:
                await self._validate_run(sessionmaker, run_id)
                result, call_receipt = await self._model_result(
                    settings=settings,
                    operation=operation,
                    role_profile=role_profile,
                    context=context,
                    system=system,
                    instructions=instructions,
                    context_receipt=context_receipt,
                    workspace=workspace,
                    generation_id=projection.generation_id,
                    unit_id=unit.unit_id,
                    request_round=request_round,
                )
            except ModelOutputTruncatedError:
                if isinstance(plan.experience_blueprint, ExperienceBlueprintV4):
                    split_units = _bisect_v4_work_unit(unit, blueprint=plan.experience_blueprint)
                    if split_units:
                        return await self._run_truncated_v4_unit(
                            sessionmaker=sessionmaker,
                            run_id=run_id,
                            settings=settings,
                            run=run,
                            plan=plan,
                            projections=projections,
                            workspace=workspace,
                            checkpoint_store=checkpoint_store,
                            projection=projection,
                            unit=unit,
                            split_units=split_units,
                            checkpoint=checkpoint,
                            allowed_packages=allowed_packages,
                            public_text=public_text,
                            persist_projection=persist_projection,
                        )
                raise
            projection.call_receipts.append(call_receipt)
            unit_projection.call_receipt_id = call_receipt.receipt_id
            if result.mode == "cannot_complete":
                if result.cannot_complete is None:
                    raise GenerationError(
                        "GENERATION_FAILURE_UNSPECIFIED", "The operation could not complete safely."
                    )
                raise GenerationError(
                    result.cannot_complete.code, result.cannot_complete.safe_reason
                )
            if result.mode == "requests":
                if not persist_projection:
                    raise GenerationError(
                        "PARALLEL_RESOURCE_REQUEST_UNSUPPORTED",
                        "A parallel route batch requested mutable resources; retry it in the serial acquisition path.",
                    )
                if request_round >= int(settings.code_generator_generation.max_request_rounds):
                    raise GenerationError(
                        "GENERATION_REQUEST_ROUND_LIMIT",
                        "The generation request-round ceiling was reached.",
                    )
                unit_projection.status = "needs_resources"
                projection.request_rounds += 1
                if persist_projection:
                    await self._persist(sessionmaker, run_id, projection, status="acquiring")
                await self._resolve_requests(
                    sessionmaker=sessionmaker,
                    run_id=run_id,
                    settings=settings,
                    run=run,
                    plan=plan,
                    projections=projections,
                    workspace=workspace,
                    projection=projection,
                    requests=result.requests,
                    allowed_packages=allowed_packages,
                )
                request_round += 1
                continue
            if result.mode == "accepted":
                # "accepted" is a valid GenerationResult.mode, but this unit
                # dispatch loop has no notion of an already-generated file to
                # accept as-is - every unit reaching here is being generated
                # (or regenerated) for the first time in this attempt, so a
                # bare mode="accepted" with no changes was previously silently
                # treated as GENERATION_CHANGES_MISSING with no indication of
                # what the model actually returned or why. Surface the
                # model's own stated reasoning instead, so a real occurrence
                # is diagnosable rather than a black box.
                summary = result.accepted.summary if result.accepted else ""
                raise GenerationError(
                    "GENERATION_UNIT_ACCEPTED_WITHOUT_CHANGES",
                    f"The model returned mode=accepted for {unit.kind} unit "
                    f"{unit.unit_id!r}, which has no prior generated content to "
                    f"accept - it must return mode=changes instead. "
                    f"Model's stated reasoning: {summary or '(none given)'}",
                )
            rejected_attempt_files = (
                {
                    item.path.replace("\\", "/").strip("/"): item.complete_utf8_content
                    for item in result.changes.files
                }
                if result.changes is not None
                else {}
            )
            try:
                self._apply_changes(
                    changes=result.changes,
                    unit=unit,
                    plan=plan,
                    projections=projections,
                    workspace=workspace,
                    allowed_packages=allowed_packages,
                    public_text=public_text,
                    settings=settings,
                    checkpoint=checkpoint,
                )
            except SourceValidationError as exc:
                diagnostics = [_diagnostic_from_exception(exc, unit.unit_id)]
                projection.diagnostics.extend(diagnostics)
                unit_projection.diagnostics.extend(item.diagnostic_id for item in diagnostics)
                _consume_repair_budget(
                    projection,
                    diagnostics,
                    repair_round=repair_round,
                    settings=settings,
                )
                repair_round += 1
                unit_projection.repair_round = repair_round
                operation = "repair"
                role_profile = str(settings.code_generator_generation.repair_profile)
                continue
            diagnostics = await run_source_checks(
                workspace.repo_dir,
                allowed_packages=allowed_packages,
                public_text=public_text,
                max_source_bytes=int(settings.code_generator_generation.max_source_bytes),
                work_unit_id=unit.unit_id,
                settings=settings,
                # Route batches are fragment owners.  Their route shell is
                # still the scaffold until the dependent composer runs, so a
                # whole-site audit here would report composer-owned failures
                # back to the wrong model operation.
                include_source_audit=unit.kind != "route_batch",
                # A parallel batch starts from a source-only copy of the
                # current repository, which can contain stale files owned by
                # another batch. Attribute repository policy diagnostics only
                # to files this operation can actually replace; the merged
                # wave and integration checks remain whole-repository.
                source_paths=list(unit.owns_paths) if unit.kind == "route_batch" else None,
            )
            if diagnostics:
                projection.diagnostics.extend(diagnostics)
                unit_projection.diagnostics.extend(item.diagnostic_id for item in diagnostics)
                _consume_repair_budget(
                    projection,
                    diagnostics,
                    repair_round=repair_round,
                    settings=settings,
                )
                repair_round += 1
                unit_projection.repair_round = repair_round
                operation = "repair"
                role_profile = str(settings.code_generator_generation.repair_profile)
                continue
            if unit.kind == "route_batch":
                (
                    section_content_ids,
                    section_selectors,
                    interaction_markers,
                    interaction_contracts,
                ) = _v4_route_batch_contract_data(plan, unit)
                batch_diagnostics = validate_route_batch_contract(
                    workspace.repo_dir,
                    list(unit.owns_paths),
                    route_id=unit.route_id,
                    section_ids=list(unit.section_ids),
                    source_markers=[
                        coverage.source_marker
                        for coverage in plan.acceptance_coverage
                        if coverage.route_id == unit.route_id
                        and coverage.criterion_id in unit.criterion_ids
                    ],
                    content_ids_by_section=section_content_ids,
                    section_selectors_by_section=section_selectors,
                    interaction_ids=list(unit.interaction_ids),
                    interaction_markers=interaction_markers,
                    interaction_contracts=interaction_contracts,
                    image_assets_by_slot=_v4_image_assets_for_unit(plan, unit, projections),
                    distinctive_moves=_v4_distinctive_moves_for_unit(plan, unit),
                    motion_beats=_v4_motion_beats_for_unit(plan, unit),
                    h1_owner_section_id=_v4_h1_owner_for_route(plan, unit.route_id),
                    work_unit_id=unit.unit_id,
                )
                if batch_diagnostics:
                    projection.diagnostics.extend(batch_diagnostics)
                    unit_projection.diagnostics.extend(
                        item.diagnostic_id for item in batch_diagnostics
                    )
                    _consume_repair_budget(
                        projection,
                        batch_diagnostics,
                        repair_round=repair_round,
                        settings=settings,
                    )
                    repair_round += 1
                    unit_projection.repair_round = repair_round
                    operation = "repair"
                    role_profile = str(settings.code_generator_generation.repair_profile)
                    continue
            if unit.kind == "route_compose" and isinstance(
                plan.experience_blueprint, ExperienceBlueprintV4
            ):
                composer_diagnostics = validate_route_composer_contract(
                    workspace.repo_dir,
                    list(unit.owns_paths),
                    section_selectors_by_section={
                        region.section_id: region.section_selector
                        for region in plan.experience_blueprint.section_regions
                        if region.route_id == unit.route_id
                    },
                    work_unit_id=unit.unit_id,
                )
                if composer_diagnostics:
                    projection.diagnostics.extend(composer_diagnostics)
                    unit_projection.diagnostics.extend(
                        item.diagnostic_id for item in composer_diagnostics
                    )
                    _consume_repair_budget(
                        projection,
                        composer_diagnostics,
                        repair_round=repair_round,
                        settings=settings,
                    )
                    repair_round += 1
                    unit_projection.repair_round = repair_round
                    operation = "repair"
                    role_profile = str(settings.code_generator_generation.repair_profile)
                    continue
            return checkpoint_store.accept(
                work_unit_id=unit.unit_id,
                parent_hash=checkpoint.checkpoint_hash if checkpoint else "",
            )

    async def _run_truncated_v4_unit(
        self,
        *,
        sessionmaker: Any,
        run_id: UUID,
        settings: Any,
        run: Any,
        plan: SitePlan,
        projections: dict[str, dict[str, Any]],
        workspace: GenerationWorkspace,
        checkpoint_store: CheckpointStore,
        projection: GenerationProjection,
        unit: WorkUnit,
        split_units: list[WorkUnit],
        checkpoint: SourceCheckpoint | None,
        allowed_packages: set[str],
        public_text: set[str],
        persist_projection: bool,
    ) -> SourceCheckpoint:
        """Resume a truncated V4 section unit as bounded child units.

        The parent unit has already been prepared against ``checkpoint``. Each
        child receives the latest accepted checkpoint, so a later child never
        sees a partially accepted response from an earlier attempt. The parent
        projection remains the durable aggregate while child projections and
        call receipts make the bisection observable.
        """

        parent_projection = _unit_projection(projection, unit)
        parent_projection.status = "split_for_truncation"
        child_checkpoint = checkpoint
        for child in split_units:
            child_projection = _unit_projection(projection, child)
            child_projection.status = "context_ready"
            child_projection.checkpoint_before = (
                child_checkpoint.checkpoint_hash if child_checkpoint else ""
            )
            child_checkpoint = await self._run_unit(
                sessionmaker=sessionmaker,
                run_id=run_id,
                settings=settings,
                run=run,
                plan=plan,
                projections=projections,
                workspace=workspace,
                checkpoint_store=checkpoint_store,
                projection=projection,
                unit=child,
                checkpoint=child_checkpoint,
                allowed_packages=allowed_packages,
                public_text=public_text,
                persist_projection=persist_projection,
            )
            child_projection.status = "checkpointed"
            child_projection.checkpoint_after = child_checkpoint.checkpoint_hash
            projection.accepted_checkpoint = child_checkpoint

        if child_checkpoint is None:
            raise GenerationError(
                "SOURCE_CHECKPOINT_MISSING",
                "Truncated V4 sections did not produce an accepted checkpoint.",
            )
        parent_projection.status = "checkpointed"
        parent_projection.checkpoint_before = checkpoint.checkpoint_hash if checkpoint else ""
        parent_projection.checkpoint_after = child_checkpoint.checkpoint_hash
        return child_checkpoint

    async def _review_and_polish(
        self,
        *,
        sessionmaker: Any,
        run_id: UUID,
        settings: Any,
        run: Any,
        plan: SitePlan,
        projections: dict[str, dict[str, Any]],
        workspace: GenerationWorkspace,
        projection: GenerationProjection,
        checkpoint_store: CheckpointStore,
        checkpoint: SourceCheckpoint | None,
        allowed_packages: set[str],
        public_text: set[str],
    ) -> None:
        review = await self._integration_review(
            sessionmaker=sessionmaker,
            run_id=run_id,
            settings=settings,
            run=run,
            plan=plan,
            workspace=workspace,
            projection=projection,
            round_number=0,
        )
        owners = {item.unit_id: item for item in plan.work_graph.units if not item.terminal}
        maximum_rounds = int(
            getattr(settings.code_generator_generation, "max_integration_polish_rounds", 2)
        )
        for polish_round in range(1, maximum_rounds + 1):
            if _review_accepted(review):
                return
            blocking_findings = [
                finding for finding in review.findings if finding.severity == "blocking"
            ]
            if not blocking_findings:
                # Advisory observations are persisted for the receipt but
                # cannot spend an owner-scoped source-polish call.
                return
            grouped: dict[str, list[SourceDiagnostic]] = {}
            for finding in blocking_findings:
                owner = owners.get(finding.owner_work_unit_id)
                if owner is None:
                    raise GenerationError(
                        "INTEGRATION_REVIEW_OWNER_INVALID",
                        "The integration reviewer returned a finding without a valid work owner.",
                    )
                grouped.setdefault(owner.unit_id, []).append(
                    SourceDiagnostic(
                        diagnostic_id=f"integration-{finding.finding_id}",
                        group="source_contract",
                        code=finding.code,
                        severity=finding.severity,
                        phase="integration_review",
                        normalized_message=finding.requested_outcome,
                        work_unit_id=owner.unit_id,
                        route_id=str(getattr(finding, "route_id", "")),
                        file=str(
                            getattr(finding, "file", "") or getattr(finding, "section_id", "")
                        ),
                        line=int(getattr(finding, "line", 0) or 0),
                        observed=finding.evidence,
                        expected=finding.requested_outcome,
                        fingerprint=digest(
                            {
                                "finding_id": finding.finding_id,
                                "owner": owner.unit_id,
                                "code": finding.code,
                            }
                        ),
                    )
                )
            for owner_id, diagnostics in grouped.items():
                owner = owners[owner_id]
                projection.diagnostics.extend(diagnostics)
                role_profile = str(settings.code_generator_generation.repair_profile)
                active_diagnostics = list(diagnostics)
                rejected_attempt_files: dict[str, str] = {}
                source_repair_round = 0
                while True:
                    context = _operation_context(
                        plan=plan,
                        projections=projections,
                        unit=owner,
                        operation="repair",
                        checkpoint=checkpoint,
                        workspace=workspace,
                        role_profile=role_profile,
                        output_ceiling=int(settings.code_generator_generation.max_response_bytes),
                        diagnostics=active_diagnostics,
                        repair_round=source_repair_round,
                        rejected_attempt_files=rejected_attempt_files,
                    )
                    context = _enforce_context_ceiling(
                        context,
                        int(settings.code_generator_generation.max_context_chars),
                    )
                    repair_output_model = (
                        SourceGenerationEnvelopeV2
                        if _context_uses_v4_contract(context)
                        else GenerationResult
                    )
                    system, instructions, context_receipt = build_instructions(
                        "repair", context, output_model=repair_output_model
                    )
                    context_path = (
                        workspace.ledger_dir / "contexts" / f"{context_receipt.context_hash}.json"
                    )
                    workspace.write_json(context_path, context)
                    context_receipt = context_receipt.model_copy(
                        update={
                            "stored_relative_path": context_path.relative_to(
                                workspace.root
                            ).as_posix()
                        }
                    )
                    projection.context_receipts.append(context_receipt)
                    await self._validate_run(sessionmaker, run_id)
                    polish_unit_id = f"{owner.unit_id}-integration-polish"
                    if polish_round > 1:
                        polish_unit_id = f"{polish_unit_id}-{polish_round}"
                    if source_repair_round:
                        polish_unit_id = f"{polish_unit_id}-source-repair-{source_repair_round}"
                    result, call_receipt = await self._model_result(
                        settings=settings,
                        operation="repair",
                        role_profile=role_profile,
                        context=context,
                        system=system,
                        instructions=instructions,
                        context_receipt=context_receipt,
                        workspace=workspace,
                        generation_id=projection.generation_id,
                        unit_id=polish_unit_id,
                        request_round=0,
                    )
                    projection.call_receipts.append(call_receipt)
                    if result.mode != "changes":
                        # The model honestly reported it could not produce a
                        # bounded owner-scoped correction this round
                        # (repair_source.md's cannot_complete escape hatch) --
                        # discovered live 2026-09-05, this used to raise and
                        # kill the entire run on the very first such response,
                        # with no retry at all. That's the same class of gap
                        # Fix A closed for the final-verification-gate's own
                        # post-repair rejection: the outer polish-round loop
                        # is already bounded (max_integration_polish_rounds)
                        # precisely to give a different round/context another
                        # try. Leave this owner's files untouched this round
                        # and let that existing bounded loop decide whether to
                        # retry this owner next round or move on -- if it
                        # never converges, the run still lands cleanly on the
                        # pre-existing INTEGRATION_REVIEW_UNRESOLVED terminal
                        # state below, not an abrupt, less-informative one.
                        logger.warning(
                            "integration polish call reported cannot_complete "
                            "run_id=%s owner=%s round=%s",
                            run_id,
                            owner.unit_id,
                            polish_round,
                        )
                        break
                    rejected_attempt_files = (
                        {
                            item.path.replace("\\", "/").strip("/"): item.complete_utf8_content
                            for item in result.changes.files
                        }
                        if result.changes is not None
                        else {}
                    )
                    source_diagnostics: list[SourceDiagnostic] = []
                    try:
                        self._apply_changes(
                            changes=result.changes,
                            unit=owner,
                            plan=plan,
                            projections=projections,
                            workspace=workspace,
                            allowed_packages=allowed_packages,
                            public_text=public_text,
                            settings=settings,
                            checkpoint=checkpoint,
                        )
                    except SourceValidationError as exc:
                        source_diagnostics = [_diagnostic_from_exception(exc, owner.unit_id)]
                    if not source_diagnostics:
                        source_diagnostics = await run_source_checks(
                            workspace.repo_dir,
                            allowed_packages=allowed_packages,
                            public_text=public_text,
                            max_source_bytes=int(
                                settings.code_generator_generation.max_source_bytes
                            ),
                            work_unit_id=owner.unit_id,
                            settings=settings,
                        )
                    if source_diagnostics:
                        projection.diagnostics.extend(source_diagnostics)
                        _consume_repair_budget(
                            projection,
                            source_diagnostics,
                            repair_round=source_repair_round,
                            settings=settings,
                        )
                        source_repair_round += 1
                        active_diagnostics = [*diagnostics, *source_diagnostics]
                        continue

                    # A polish is durable only after the complete candidate
                    # tree passes independent source/type checks. A malformed
                    # structured response therefore remains a rejected
                    # attempt available to the bounded repair call, never an
                    # accepted checkpoint that poisons a same-run resume.
                    checkpoint = checkpoint_store.accept(
                        work_unit_id=polish_unit_id,
                        parent_hash=checkpoint.checkpoint_hash if checkpoint else "",
                    )
                    projection.accepted_checkpoint = checkpoint
                    projection.source_file_count = checkpoint.file_count
                    projection.source_total_bytes = checkpoint.total_bytes
                    await self._persist(
                        sessionmaker,
                        run_id,
                        projection,
                        status=DevelopmentRunStatus.INTEGRATING.value,
                        source_checkpoint=checkpoint,
                    )
                    break
            diagnostics = await run_source_checks(
                workspace.repo_dir,
                allowed_packages=allowed_packages,
                public_text=public_text,
                max_source_bytes=int(settings.code_generator_generation.max_source_bytes),
                work_unit_id="integration-review",
                settings=settings,
            )
            if diagnostics:
                projection.diagnostics.extend(diagnostics)
                raise GenerationError(
                    "INTEGRATION_POLISH_SOURCE_CHECK_FAILED",
                    "The bounded integration polish pass introduced source diagnostics.",
                )
            review = await self._integration_review(
                sessionmaker=sessionmaker,
                run_id=run_id,
                settings=settings,
                run=run,
                plan=plan,
                workspace=workspace,
                projection=projection,
                round_number=polish_round,
            )
        if not _review_accepted(review):
            raise GenerationError(
                "INTEGRATION_REVIEW_UNRESOLVED",
                "The completed source tree did not pass the bounded whole-site quality review "
                f"after {maximum_rounds} polish rounds.",
            )

    async def _integration_review(
        self,
        *,
        sessionmaker: Any,
        run_id: UUID,
        settings: Any,
        run: Any,
        plan: SitePlan,
        workspace: GenerationWorkspace,
        projection: GenerationProjection,
        round_number: int,
        persist: bool = True,
    ) -> IntegrationReviewV1 | QualityReviewDraftV1:
        profile = str(settings.code_generator_generation.integration_profile)
        client = self._client(settings, profile)
        if client is None:
            raise GenerationError(
                "INTEGRATION_PROFILE_UNAVAILABLE",
                "No usable model profile is configured for whole-site integration review.",
            )
        source: dict[str, str] = {}
        source_bytes = 0
        for path in sorted(workspace.repo_dir.rglob("*")):
            if (
                not path.is_file()
                or path.suffix.casefold() not in {".css", ".html", ".js", ".jsx", ".ts", ".tsx"}
                or any(part in {"node_modules", "dist"} for part in path.parts)
            ):
                continue
            relative = path.relative_to(workspace.repo_dir).as_posix()
            try:
                value = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            encoded_size = len(value.encode("utf-8"))
            source[relative] = value
            source_bytes += encoded_size
        realization_contracts = []
        if isinstance(plan.experience_blueprint, ExperienceBlueprintV4):
            realization_contracts = [
                compile_design_realization(
                    plan.experience_blueprint,
                    route_id=route.route_id,
                    section_order=list(route.section_order or route.section_ids),
                )
                for route in plan.routes
            ]
        context = {
            "role_profile": profile,
            "round": round_number,
            "creative_direction": dict(getattr(run, "creative_direction", None) or {}),
            "experience_blueprint": (
                plan.experience_blueprint.model_dump(mode="json")
                if plan.experience_blueprint is not None
                else {}
            ),
            "work_graph": plan.work_graph.model_dump(mode="json"),
            "execution_bindings": [
                item.model_dump(mode="json") for item in plan.execution_bindings
            ],
            "design_realization_contracts": [
                item.model_dump(mode="json") for item in realization_contracts
            ],
            "trusted_build_runtime": {
                "bundler": "vite",
                "base": "./",
                "public_source_prefix": "/resources/pack/",
                "public_css_build_behavior": (
                    "Vite rewrites admitted root-public CSS URLs to base-relative "
                    "../resources/pack URLs in the built artifact. Nested-preview safety is "
                    "verified after build, not inferred from the source URL alone."
                ),
            },
            "source_manifest": build_source_manifest(workspace.repo_dir),
            "assembled_source": source,
        }
        context_size = len(json.dumps(context, ensure_ascii=False, separators=(",", ":")))
        if context_size > int(settings.code_generator_generation.quality_review_max_context_chars):
            raise GenerationError(
                "QUALITY_REVIEW_CONTEXT_TOO_LARGE",
                "The complete source review exceeds the configured provider context ceiling.",
            )
        await self._validate_run(sessionmaker, run_id)
        review, context_receipt, raw = await run_integration_review_operation(
            client,
            context=context,
            profile_name=profile,
            output_version=(
                "v4" if isinstance(plan.experience_blueprint, ExperienceBlueprintV4) else "legacy"
            ),
            cache_key=f"codegen:{projection.generation_id}:review",
        )
        review = _canonicalize_review_owners(
            review,
            {unit.unit_id for unit in plan.work_graph.units},
        )
        context_path = workspace.ledger_dir / "contexts" / f"{context_receipt.context_hash}.json"
        workspace.write_json(context_path, context)
        context_receipt = context_receipt.model_copy(
            update={"stored_relative_path": context_path.relative_to(workspace.root).as_posix()}
        )
        projection.context_receipts.append(context_receipt)
        projection.call_receipts.append(
            GenerationCallReceipt(
                receipt_id=f"call-review-{context_receipt.context_hash[:20]}",
                operation_id="integration_review",
                idempotency_key=f"{projection.generation_id}:integration-review:{round_number}",
                context_receipt_hash=context_receipt.context_hash,
                result_hash=digest(review.model_dump(mode="json")),
                profile=profile,
                response_id=str(getattr(raw, "response_id", "") or ""),
                model=str(getattr(raw, "model", "") or ""),
                usage={
                    str(key): int(value)
                    for key, value in dict(getattr(raw, "usage", {}) or {}).items()
                    if isinstance(value, int)
                },
                finish_reason=str(getattr(raw, "finish_reason", "") or ""),
                duration_ms=float(getattr(raw, "latency_ms", 0.0) or 0.0),
            )
        )
        review_payload = review.model_dump(mode="json")
        if isinstance(plan.experience_blueprint, ExperienceBlueprintV4):
            if not isinstance(review, QualityReviewDraftV1):
                raise GenerationError(
                    "QUALITY_REVIEW_SCHEMA_INVALID",
                    "The v4 reviewer returned a legacy acceptance envelope.",
                )
            quality = stamp_quality_review_receipt(
                review,
                source_manifest_hash=digest(build_source_manifest(workspace.repo_dir)),
                plan_hash=digest(plan.model_dump(mode="json")),
                realization_hash=digest(
                    [item.model_dump(mode="json") for item in realization_contracts]
                ),
                review_context_hash=context_receipt.context_hash,
                response_id=str(getattr(raw, "response_id", "") or "local-response-unavailable"),
                quality_gate_version=str(settings.code_generator_development.quality_gate_version),
            )
            projection.quality_review = quality
            review_payload["quality_receipt"] = quality.model_dump(mode="json")
        if persist:
            await self._persist_integration_review(sessionmaker, run_id, projection, review_payload)
        return review

    async def _persist_integration_review(
        self,
        sessionmaker: Any,
        run_id: UUID,
        projection: GenerationProjection,
        review: dict[str, Any],
    ) -> None:
        async with sessionmaker() as db:
            repo = CodeGeneratorDevelopmentRepository(db)
            run = await repo.get(run_id)
            if run is None:
                raise GenerationError("RUN_NOT_FOUND", "The generation run was not found.")
            await _cas(
                repo,
                run,
                DevelopmentRunStatus.INTEGRATING.value,
                {
                    "generation_projection": projection.model_dump(mode="json"),
                    "integration_review": review,
                },
            )
            await db.commit()

    async def _validate_run(self, sessionmaker: Any, run_id: UUID) -> None:
        async with sessionmaker() as db:
            await WorkerAuthorizationFence(db).validate_run(run_id)

    def _apply_changes(
        self,
        *,
        changes: GenerationChanges | None,
        unit: WorkUnit,
        plan: SitePlan,
        projections: dict[str, dict[str, Any]],
        workspace: GenerationWorkspace,
        allowed_packages: set[str],
        public_text: set[str],
        settings: Any,
        checkpoint: SourceCheckpoint | None,
    ) -> None:
        if changes is None:
            raise GenerationError(
                "GENERATION_CHANGES_MISSING", "The generation result did not include changes."
            )
        if isinstance(plan.experience_blueprint, ExperienceBlueprintV4):
            _validate_v4_generation_coverage(changes, unit, plan, projections)
        owners = _owned_paths(unit, plan, projections)
        original = workspace.repo_dir
        unit_slug = _unit_dir_slug(unit.unit_id)
        candidate = workspace.root / f"candidate-{unit_slug}"
        if candidate.exists():
            fs_safe.remove_tree(candidate)
        _copy_without_disposables(original, candidate)
        normalized = validate_generation_changes(
            changes,
            owned_paths=owners,
            repo_dir=candidate,
            max_file_bytes=int(settings.code_generator_generation.max_file_bytes),
            max_response_bytes=int(settings.code_generator_generation.max_response_bytes),
            allowed_packages=allowed_packages,
            public_text=public_text,
        )
        for change in normalized:
            target = (candidate / change.path).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(change.complete_utf8_content, encoding="utf-8", newline="\n")
        old = workspace.root / f"repo-{unit_slug}-old"
        fs_safe.remove_tree(old, required=False)
        try:
            fs_safe.rename_dir_with_retry(original, old)
            fs_safe.rename_dir_with_retry(candidate, original)
        except fs_safe.FsSafeError as exc:
            # Keep the workspace coherent: put the accepted tree back before
            # surfacing the failure as a resumable generation error.
            if not original.exists() and old.exists():
                fs_safe.remove_tree(candidate, required=False)
                fs_safe.rename_dir_with_retry(old, original)
            raise GenerationError(
                "GENERATION_SWAP_FAILED",
                "The candidate tree could not be swapped in under filesystem "
                "locks; the run stays resumable from the last checkpoint.",
            ) from exc
        installed = old / "node_modules"
        if installed.is_dir():
            # node_modules is disposable; the next toolchain install
            # recreates it.
            with contextlib.suppress(fs_safe.FsSafeError):
                fs_safe.rename_dir_with_retry(installed, original / "node_modules")
        fs_safe.remove_tree(old, required=False)

    async def _model_result(
        self,
        *,
        settings: Any,
        operation: str,
        role_profile: str,
        context: dict[str, Any],
        system: str,
        instructions: str,
        context_receipt: GenerationContextReceipt,
        workspace: GenerationWorkspace,
        generation_id: str,
        unit_id: str,
        request_round: int,
    ) -> tuple[GenerationResult, GenerationCallReceipt]:
        output_model = (
            SourceGenerationEnvelopeV2 if _context_uses_v4_contract(context) else GenerationResult
        )
        generation_contract = context.get("generation_contract")
        required_coverage = (
            generation_contract.get("required_coverage")
            if isinstance(generation_contract, dict)
            and isinstance(generation_contract.get("required_coverage"), dict)
            else None
        )
        # The cache key binds the prompt text (via the operation-prompt hash)
        # so a prompt change invalidates previously cached model calls.
        prompt_hash = str((context_receipt.prompt_versions or {}).get("operation_hash", ""))
        key = hashlib.sha256(
            f"{generation_id}:{unit_id}:{operation}:{prompt_hash}:{context_receipt.context_hash}:{request_round}".encode()
        ).hexdigest()
        result_path = workspace.ledger_dir / "calls" / f"{key}.json"
        if result_path.is_file():
            cached_result = GenerationResult.model_validate(
                json.loads(result_path.read_text(encoding="utf-8"))
            )
            cached_result = stamp_v4_required_coverage(cached_result, required_coverage)
            # Calls are cached before source validation. An older cache may
            # therefore contain a model-transcribed coverage typo that the
            # current trusted contract can normalize without another paid
            # call. Persist the normalized internal DTO for later resumes.
            workspace.write_json(result_path, cached_result.model_dump(mode="json"))
            return cached_result, GenerationCallReceipt(
                receipt_id=f"call-{key[:20]}",
                operation_id=operation,
                idempotency_key=key,
                context_receipt_hash=context_receipt.context_hash,
                result_hash=digest(cached_result.model_dump(mode="json")),
                profile=role_profile,
                attempt=0,
                retry_class="cache_hit",
            )
        client = self._client(settings, role_profile)
        if client is None:
            raise GenerationError(
                "GENERATION_PROFILE_UNAVAILABLE",
                f"No usable model profile is configured for {operation}.",
            )
        raw: Any = None
        result: GenerationResult | None = None
        last_issue = ""
        # _model_result has exactly two callers (_run_unit's main dispatch
        # loop and _review_and_polish's owner-scoped polish loop), and both
        # already treat mode/result="accepted" as unconditionally invalid on
        # their own terms: _run_unit raises GENERATION_UNIT_ACCEPTED_WITHOUT_
        # CHANGES for it regardless of operation, and _review_and_polish
        # requires exactly mode="changes", rejecting anything else including
        # "accepted". An operation-name allowlist here (`operation not in
        # {"integrate", "repair"}`) was wrong: _run_unit's own retry loop
        # reassigns its local `operation` variable to "repair" after a
        # validation failure purely to select the repair prompt (see the
        # `operation = "repair"` reassignments a few hundred lines up), which
        # is a completely different meaning from FinalRepairer's standalone
        # post-generation repair operation (a separate function entirely,
        # never routed through _model_result) - the allowlist accidentally
        # let a mid-generation diagnostic-retry accept its own unfixed
        # response instead of correcting it. Forbid it unconditionally here
        # instead of trying to name every operation that shouldn't get it.
        validation_context = {"forbid_accepted_result": True}
        for attempt in range(2):
            call_instructions = instructions
            if last_issue:
                call_instructions += (
                    "\n\nThe previous structured generation response failed local "
                    "validation. Return a complete replacement object and correct "
                    f"this safe schema summary: {last_issue}. Do not include commentary."
                )
            try:
                raw = await client.generate_structured(
                    operation=f"code_generator.{operation}",
                    instructions=call_instructions,
                    input_payload={**context, "context_receipt_hash": context_receipt.context_hash},
                    output_model=output_model,
                    system_prompt=system,
                    model_profile=role_profile,
                    strict_schema=True,
                    request_context={
                        "key_order": ROUTE_UNIT_KEY_ORDER,
                        "prompt_cache_key": f"codegen:{generation_id}:{role_profile}",
                    },
                )
                parsed = getattr(raw, "parsed_output", raw)
                if (
                    output_model is GenerationResult
                    and isinstance(parsed, dict)
                    and not str(parsed.get("operation_id", "")).strip()
                ):
                    # The operation id is host-owned execution metadata, not
                    # portfolio content. Complete it deterministically when
                    # a provider omits the envelope field; all creative and
                    # source-bearing fields remain strictly model-validated.
                    parsed = {**parsed, "operation_id": f"{operation}:{unit_id}"}
                if output_model is SourceGenerationEnvelopeV2:
                    envelope = SourceGenerationEnvelopeV2.model_validate(
                        parsed, context=validation_context
                    )
                    if envelope.result == "accepted" and validation_context.get(
                        "forbid_accepted_result"
                    ):
                        raise GenerationError(
                            "GENERATION_DIAGNOSTIC_VALIDATOR_DID_NOT_FIRE",
                            f"DIAGNOSTIC: envelope validated as accepted despite "
                            f"forbid_accepted_result=True; operation={operation!r} "
                            f"validation_context={validation_context!r} "
                            f"envelope_class={type(envelope).__module__}.{type(envelope).__qualname__}",
                        )
                    result = adapt_v4_generation_result(
                        envelope,
                        operation_id=f"{operation}:{unit_id}",
                        context_receipt=context_receipt,
                        required_coverage=required_coverage,
                    )
                else:
                    result = GenerationResult.model_validate(parsed, context=validation_context)
                break
            except (ModelJsonInvalidError, ModelOutputTruncatedError, ValidationError) as exc:
                last_issue = _safe_generation_model_issue(exc)
                if attempt == 1:
                    raise
        if result is None or raw is None:
            raise GenerationError(
                "GENERATION_OUTPUT_INVALID",
                "The model did not produce a locally valid generation result.",
            )
        if result.based_on_context_receipt not in {
            context_receipt.context_hash,
            context_receipt.receipt_id,
        }:
            raise GenerationError(
                "GENERATION_CONTEXT_MISMATCH",
                "The generation result was not based on the current context receipt.",
            )
        workspace.write_json(result_path, result.model_dump(mode="json"))
        raw_usage = {
            str(k): int(v)
            for k, v in dict(getattr(raw, "usage", {}) or {}).items()
            if isinstance(v, int)
        }
        return result, GenerationCallReceipt(
            receipt_id=f"call-{key[:20]}",
            operation_id=operation,
            idempotency_key=key,
            context_receipt_hash=context_receipt.context_hash,
            result_hash=digest(result.model_dump(mode="json")),
            profile=role_profile,
            response_id=str(getattr(raw, "response_id", "") or ""),
            model=str(getattr(raw, "model", "") or ""),
            usage=raw_usage,
            finish_reason=str(getattr(raw, "finish_reason", "") or ""),
            attempt=attempt + 1,
            retry_class="schema_correction" if attempt else "",
            duration_ms=float(getattr(raw, "latency_ms", 0.0) or 0.0),
            cached_tokens=sum(
                raw_usage.get(key, 0)
                for key in (
                    "cached_tokens",
                    "cache_read_input_tokens",
                    "prompt_cache_hit_tokens",
                )
            ),
        )

    async def _resolve_requests(
        self,
        *,
        sessionmaker: Any,
        run_id: UUID,
        settings: Any,
        run: Any,
        plan: SitePlan,
        projections: dict[str, dict[str, Any]],
        workspace: GenerationWorkspace,
        projection: GenerationProjection,
        requests: Any,
        allowed_packages: set[str],
    ) -> None:
        if requests is None:
            raise GenerationError(
                "GENERATION_REQUESTS_MISSING", "The generation result omitted its requests payload."
            )
        resource_ledger = ResourceLedger.model_validate(
            run.resource_ledger or {"based_on_input_and_plan": {}}
        )
        receipts = list(resource_ledger.receipts)
        bindings = list(resource_ledger.active_bindings)
        deltas = list(resource_ledger.plan_deltas)
        adapters = self._adapters(settings)
        materials_root = _resolve_config_path(
            settings.code_generator_acquisition.materials_root
        ) / str(run_id)
        for request in requests.resource_requests:
            if any(receipt.request_hash == request.request_hash for receipt in receipts):
                continue
            validate_resource_request(
                request,
                plan=plan,
                ledger_excluding=ResourceLedger(
                    based_on_input_and_plan=resource_ledger.based_on_input_and_plan,
                    requests=resource_ledger.requests,
                    receipts=receipts,
                ),
                settings=settings,
                projections=projections,
                request_rounds=projection.request_rounds,
            )
            adapter = adapters.get(request.category)
            if adapter is None:
                raise GenerationError(
                    "CATEGORY_UNSUPPORTED", f"No trusted adapter exists for {request.category}."
                )
            try:
                candidates = filter_candidates_by_policy(
                    await adapter.search(request, settings=settings), request
                )
                if request.request_id.startswith("delegated-"):
                    delegated_limit = int(
                        getattr(
                            getattr(settings, "build_preparation", None),
                            "delegated_candidate_limit",
                            8,
                        )
                    )
                    candidates = sorted(candidates, key=lambda item: item.candidate_id)[
                        : max(1, delegated_limit)
                    ]
                if not candidates:
                    if request.requiredness == "required" and request.fallback.kind == "none":
                        raise GenerationError(
                            "REQ_FALLBACK_BLOCKED",
                            "The emergent required resource has no honest fallback.",
                        )
                    receipt = _fallback_receipt(request, "No policy-approved candidate exists.")
                else:
                    candidate_id, _ = select_candidate(request, candidates)
                    candidate = next(
                        item for item in candidates if item.candidate_id == candidate_id
                    )
                    intended_paths = _intended_paths_for_candidate(
                        projections.get("execution/contract.json", {}), candidate
                    )
                    component_reference_only = (
                        request.category == "component_source"
                        and request.request_id.startswith("deferred-")
                        and not intended_paths
                    )
                    if (
                        component_reference_only
                        and request.requiredness == "required"
                        and request.fallback.kind == "none"
                    ):
                        raise GenerationError(
                            "REQ_REQUIRED_COMPONENT_PATH_MISSING",
                            "A required component source has no executable local destination or fallback.",
                        )
                    materialized_result = await adapter.materialize(
                        candidate, request, storage_root=materials_root, settings=settings
                    )
                    materialized_files = (
                        list(materialized_result)
                        if isinstance(materialized_result, list)
                        else [materialized_result]
                    )
                    # Registry component payloads are reference material, not
                    # executable files for this target.  They frequently carry
                    # imports into a provider-owned alias tree (for example
                    # ``@/registry/...``); copying them into ``src`` would make
                    # the whole portfolio fail the AST/build audit even when
                    # no generated route imports the suggestion.  Keep the
                    # acquisition provenance, but let the route generator use
                    # the requested accessible local equivalent.  A legacy or
                    # explicitly planned component with an executable local
                    # destination remains materializable; only an unbound
                    # suggestion is reference-only.
                    receipt_files = []
                    if not component_reference_only:
                        for materialized in materialized_files:
                            source_file = materials_root / materialized.local_path
                            local_name = (
                                f"{materialized.sha256}{Path(materialized.local_path).suffix}"
                            )
                            generated_path = workspace.materialize_acquired_file(
                                source_file, local_name
                            )
                            inspection = dict(materialized.inspection)
                            licence_name = str(inspection.get("licence_path", ""))
                            if licence_name:
                                licence_source = materials_root / licence_name
                                licence_target = (
                                    workspace.repo_dir
                                    / "public"
                                    / "licences"
                                    / Path(licence_name).name
                                ).resolve()
                                if licence_source.is_file() and licence_target.is_relative_to(
                                    workspace.repo_dir.resolve()
                                ):
                                    licence_target.parent.mkdir(parents=True, exist_ok=True)
                                    shutil.copyfile(licence_source, licence_target)
                                    inspection["licence_path"] = licence_target.relative_to(
                                        workspace.repo_dir
                                    ).as_posix()
                            receipt_files.append(
                                materialized.model_copy(
                                    update={"local_path": generated_path, "inspection": inspection}
                                )
                            )
                    receipt = ResourceReceipt(
                        request_hash=request.request_hash,
                        disposition="fallback" if component_reference_only else "admitted",
                        selected_candidate_id=candidate.candidate_id,
                        provider_key=candidate.provider_key,
                        canonical_source=candidate.canonical_source,
                        licence=candidate.licence,
                        attribution=candidate.attribution,
                        original_hash=materialized_files[0].sha256 if materialized_files else "",
                        materialized_files=receipt_files,
                        dependencies=sorted(candidate.dependency_metadata),
                        satisfied_placements=[]
                        if component_reference_only
                        else [request.placement.purpose],
                        fallback=(
                            {
                                "kind": request.fallback.kind,
                                "reason": "Component source retained as reference-only material.",
                            }
                            if component_reference_only
                            else {}
                        ),
                        acquired_at=datetime.now(UTC).isoformat(),
                    )
            except (ResourceProviderError, AcquisitionValidationError) as exc:
                if request.requiredness == "required" and request.fallback.kind == "none":
                    raise GenerationError(
                        "REQ_REQUIRED_PROVIDER_UNAVAILABLE",
                        "The required emergent resource provider is unavailable.",
                    ) from exc
                receipt = _fallback_receipt(request, str(exc))
            receipts.append(receipt)
            binding = ResourceBinding(
                binding_id=f"binding-{request.request_hash[:20]}",
                request_id_or_pack_need_id=request.request_hash,
                local_paths=[item.local_path for item in receipt.materialized_files],
                placement_ids=[request.placement.purpose],
                disposition=receipt.disposition,
            )
            bindings.append(binding)
            delta = PlanDelta(
                delta_id=f"delta-{binding.binding_id}",
                based_on_plan_hash=str((run.planner_receipt or {}).get("plan_hash", "")),
                binding_changes=[binding],
            )
            validate_plan_delta(delta, plan=plan)
            deltas.append(delta)
        resource_ledger = ResourceLedger(
            based_on_input_and_plan=resource_ledger.based_on_input_and_plan,
            requests=[*resource_ledger.requests, *requests.resource_requests],
            receipts=receipts,
            active_bindings=bindings,
            plan_deltas=deltas,
        )
        projections["resources/ledger.json"] = resource_ledger.model_dump(mode="json")
        dependency_ledger = DependencyLedger.model_validate(
            run.dependency_ledger or {"receipts": []}
        )
        if requests.dependency_requests:
            manager = DependencyManager(receipts)
            repo_dir = workspace.repo_dir
            prior_manifest = _read_json(repo_dir / "package.json")
            prior_lock = _read_json(repo_dir / "package-lock.json")
            dependency_receipts = list(dependency_ledger.receipts)
            for request in requests.dependency_requests:
                dependency_receipts.append(
                    await manager.resolve(
                        request,
                        repo_dir=repo_dir,
                        prior_manifest=prior_manifest,
                        prior_lock=prior_lock,
                        settings=settings,
                    )
                )
            dependency_ledger = build_dependency_ledger(dependency_receipts)
        run.resource_ledger = resource_ledger.model_dump(mode="json")
        run.dependency_ledger = dependency_ledger.model_dump(mode="json")
        projection.resource_ledger_hash = resource_ledger.ledger_hash
        projection.dependency_ledger_hash = dependency_ledger.dependency_ledger_hash
        await self._persist_ledgers(sessionmaker, run_id, resource_ledger, dependency_ledger)

    def _initial_projection(
        self, run: Any, generation_id: str, plan: SitePlan
    ) -> GenerationProjection:
        return GenerationProjection(
            generation_id=generation_id,
            input_receipt_hash=str((run.input_receipt or {}).get("admitted_identity", "")),
            site_plan_hash=str((run.planner_receipt or {}).get("plan_hash", "")),
            resource_ledger_hash=str((run.resource_ledger or {}).get("ledger_hash", "")),
            dependency_ledger_hash=str(
                (run.dependency_ledger or {}).get("dependency_ledger_hash", "")
            ),
            phase="generating_foundation",
            work_units=[
                GenerationWorkUnitProjection.model_validate(_unit_projection_dict(unit))
                for unit in plan.work_graph.units
            ],
        )

    @staticmethod
    def _prepare_projection(
        projection: GenerationProjection, plan: SitePlan
    ) -> GenerationProjection:
        existing = {unit.unit_id for unit in projection.work_units}
        projection.work_units.extend(
            GenerationWorkUnitProjection.model_validate(_unit_projection_dict(unit))
            for unit in plan.work_graph.units
            if unit.unit_id not in existing
        )
        return projection

    async def _persist(
        self,
        sessionmaker: Any,
        run_id: UUID,
        projection: GenerationProjection,
        *,
        status: str,
        source_checkpoint: SourceCheckpoint | None = None,
        source_summary: dict[str, Any] | None = None,
        event: tuple[str, str] | None = None,
    ) -> None:
        async with sessionmaker() as db:
            repo = CodeGeneratorDevelopmentRepository(db)
            run = await repo.get(run_id)
            if run is None:
                raise GenerationError("RUN_NOT_FOUND", "The generation run was not found.")
            values: dict[str, object] = {
                "generation_projection": projection.model_dump(mode="json"),
                "issues": [item.model_dump(mode="json") for item in projection.issues],
            }
            if source_checkpoint is not None:
                values["source_checkpoint"] = source_checkpoint.model_dump(mode="json")
            if source_summary is not None:
                values["source_summary"] = source_summary
            await _cas(repo, run, status, values)
            if event:
                await repo.append_event(run_id, event_type=event[0], level="info", message=event[1])
            await db.commit()

    async def _persist_ledgers(
        self,
        sessionmaker: Any,
        run_id: UUID,
        resource: ResourceLedger,
        dependency: DependencyLedger,
    ) -> None:
        async with sessionmaker() as db:
            repo = CodeGeneratorDevelopmentRepository(db)
            run = await repo.get(run_id)
            if run is None:
                raise GenerationError("RUN_NOT_FOUND", "The generation run was not found.")
            await _cas(
                repo,
                run,
                "acquiring",
                {
                    "resource_ledger": resource.model_dump(mode="json"),
                    "dependency_ledger": dependency.model_dump(mode="json"),
                    "plan_delta_count": len(resource.plan_deltas),
                },
            )
            await db.commit()

    async def _fail(self, sessionmaker: Any, run_id: UUID, issue: SafeIssue) -> None:
        async with sessionmaker() as db:
            repo = CodeGeneratorDevelopmentRepository(db)
            run = await repo.get(run_id)
            if run is None:
                return
            issues = [issue.model_dump(mode="json")]
            await _cas(repo, run, DevelopmentRunStatus.NEEDS_ATTENTION.value, {"issues": issues})
            await repo.append_event(
                run_id,
                event_type="needs_attention",
                level="error",
                message=issue.message,
                details={"code": issue.code},
            )
            await db.commit()

    def _client(self, settings: Any, profile: str) -> Any | None:
        if self._model_factory is not None:
            try:
                return self._model_factory(profile)
            except TypeError:
                return self._model_factory("")
        from oryxenai.agents.shared.model_client import build_provider_client

        return build_provider_client(profile, settings.models)

    def _adapters(self, settings: Any) -> dict[str, Any]:
        if self._adapter_factory is not None:
            return self._adapter_factory(settings)
        root = str(getattr(settings.code_generator_acquisition, "offline_resource_root", "") or "")
        registry = OfflineResourceProviderRegistry.from_directory(Path(root)) if root else None
        return default_adapters(registry=registry)

    @staticmethod
    def _reference(run: Any) -> Any:
        from oryxenai.agents.code_generator.core.development_schemas import AdmittedInputReference

        return AdmittedInputReference.model_validate(run.input_reference)


def _topological_units(units: list[WorkUnit]) -> list[WorkUnit]:
    by_id = {unit.unit_id: unit for unit in units}
    result: list[WorkUnit] = []
    remaining = set(by_id)
    while remaining:
        ready = sorted(
            unit_id
            for unit_id in remaining
            if set(by_id[unit_id].depends_on).issubset({item.unit_id for item in result})
        )
        if not ready:
            raise GenerationError(
                "PLAN_WORK_GRAPH_CYCLE", "The generation work graph cannot be scheduled."
            )
        for unit_id in ready:
            result.append(by_id[unit_id])
            remaining.remove(unit_id)
    return result


def _operation_for(unit: WorkUnit) -> str:
    return {
        "foundation": "foundation",
        "route": "route_batch",
        "route_batch": "route_batch",
        "route_compose": "route_compose",
        "integration": "integrate",
    }.get(unit.kind, "route_batch")


def _profile_for(operation: str, settings: Any) -> str:
    config = settings.code_generator_generation
    return {
        # Blueprint-backed V3/V4 foundations are compiled above without a
        # model call. Legacy SitePlans with no blueprint still carry a
        # foundation work unit, so keep that compatibility operation on the
        # existing route profile instead of resurrecting a dedicated model
        # profile that production never needs.
        "foundation": str(config.route_profile),
        "route_batch": str(config.route_profile),
        "route_compose": str(config.compose_profile),
        "integrate": str(config.integration_profile),
        "repair": str(config.repair_profile),
    }[operation]


def _operation_context(
    *,
    plan: SitePlan,
    projections: dict[str, dict[str, Any]],
    unit: WorkUnit,
    operation: str,
    checkpoint: SourceCheckpoint | None,
    workspace: GenerationWorkspace,
    role_profile: str,
    output_ceiling: int,
    diagnostics: list[SourceDiagnostic],
    repair_round: int,
    rejected_attempt_files: dict[str, str] | None = None,
) -> dict[str, Any]:
    site = projections["site/contract.json"]
    routes = {
        str(item.get("route_id", "")): item
        for item in site.get("routes", [])
        if isinstance(item, dict)
    }
    route_ids = set(unit.route_ids) or ({unit.route_id} if unit.route_id else set())
    route_slices = [routes[route_id] for route_id in route_ids if route_id in routes]
    existing_files = sorted(
        path.relative_to(workspace.repo_dir).as_posix()
        for path in workspace.repo_dir.rglob("*")
        if path.is_file() and not any(part in {"node_modules", "dist"} for part in path.parts)
    )[:500]
    owned = _owned_paths(unit, plan, projections)
    exact_owned_paths = {path.replace("\\", "/").strip("/") for path in owned if "*" not in path}
    if unit.kind in {"route_batch", "route_compose"} and exact_owned_paths:
        # Create-vs-replace only needs ground truth for the files this unit
        # can write. Sending the entire repository inventory is redundant and
        # can consume the bounded context on large resumed workspaces.
        existing_files = [path for path in existing_files if path in exact_owned_paths]
    # The provider receives only the trusted interfaces and direct dependency
    # source needed by this unit.  Walking the entire generated repository here
    # would serialize large manifests and unrelated content into every call.
    context_plan = _scoped_operation_plan(plan, unit)
    context_visual = _scoped_visual_direction(
        projections.get("design/visual-direction.json", {}), unit
    )
    context_resource_bindings = _scoped_resource_ledger(
        projections.get("resources/ledger.json", {}), unit
    )
    context_execution_contract = _scoped_execution_contract(
        projections.get("execution/contract.json", {}), unit
    )
    if operation == "repair":
        context_plan = _scoped_repair_plan(context_plan)
        context_visual = _scoped_repair_visual(context_visual)
    shared_source = _shared_source_for_unit(plan, projections, unit, workspace.repo_dir)
    relevant_diagnostics = [
        item for item in diagnostics if not item.work_unit_id or item.work_unit_id == unit.unit_id
    ][-12:]
    owner_wide_repair = operation == "repair" and any(
        item.phase == "integration_review" for item in relevant_diagnostics
    )
    diagnostic_paths = {
        str(item.file).replace("\\", "/").strip("/")
        for item in relevant_diagnostics
        if str(item.file).strip()
    }
    # Source diagnostics name the primary offending file, but executable
    # behavior commonly spans a section module and its sibling stylesheet.
    # Keep that exact owned source pair visible to repair calls so a rejected
    # one-file correction cannot hide the companion file needed by the next
    # diagnostic round.
    for relative in list(diagnostic_paths):
        path = Path(relative)
        if path.suffix.lower() in {".ts", ".tsx"}:
            companion = path.with_suffix(".css").as_posix()
            if companion in exact_owned_paths:
                diagnostic_paths.add(companion)
        elif path.suffix.lower() == ".css":
            for suffix in (".tsx", ".ts"):
                companion = path.with_suffix(suffix).as_posix()
                if companion in exact_owned_paths:
                    diagnostic_paths.add(companion)

    def belongs_to_owned_paths(relative: str) -> bool:
        if exact_owned_paths:
            return relative in exact_owned_paths
        return any(fnmatch.fnmatchcase(relative, owner) for owner in owned)

    def belongs_to_unit(relative: str) -> bool:
        return belongs_to_owned_paths(relative) and (
            owner_wide_repair or not diagnostic_paths or relative in diagnostic_paths
        )

    # A structured model result is persisted to the call ledger before host
    # source validation. Preserve its exact file bodies in the next repair
    # context even when validation failed before a candidate tree could be
    # created. The candidate/repository reads below remain fallbacks for later
    # checks that reject an already-materialized attempt.
    previous_attempt_files: dict[str, str] = {}
    included_bytes = 0
    max_candidate_bytes = 48_000

    def include_source(relative: str, source: str, *, use_diagnostic_scope: bool = True) -> None:
        nonlocal included_bytes
        normalized = relative.replace("\\", "/").strip("/")
        belongs = belongs_to_unit if use_diagnostic_scope else belongs_to_owned_paths
        if (
            normalized in previous_attempt_files
            or Path(normalized).suffix.lower() not in {".ts", ".tsx", ".css"}
            or not belongs(normalized)
            or len(source) > 20_000
            or included_bytes + len(source) > max_candidate_bytes
            or len(previous_attempt_files) >= 8
        ):
            return
        previous_attempt_files[normalized] = source
        included_bytes += len(source)

    for relative, source in sorted((rejected_attempt_files or {}).items()):
        # A rejected structured response is one atomic proposed change set.
        # Its diagnostic may point at only the first offending file (for
        # example, one repeated path), but repairing it safely requires every
        # returned file in the unit's ownership surface.
        include_source(relative, source, use_diagnostic_scope=False)

    candidate_dir = workspace.root / f"candidate-{_unit_dir_slug(unit.unit_id)}"
    if not previous_attempt_files and candidate_dir.is_dir():
        for path in sorted(candidate_dir.rglob("*")):
            if (
                not path.is_file()
                or path.suffix.lower() not in {".ts", ".tsx", ".css"}
                or any(part in {"node_modules", "dist"} for part in path.parts)
            ):
                continue
            relative = path.relative_to(candidate_dir).as_posix()
            if not belongs_to_unit(relative):
                continue
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            include_source(relative, source)
            if len(previous_attempt_files) >= 8:
                break
    if operation == "repair":
        # Repair calls need the current diagnostic-scoped repository source in
        # addition to any rejected response bodies. The rejected files remain
        # authoritative because include_source keeps the first copy, while
        # current companion files fill the gaps needed for cross-file fixes.
        # This also covers integration polish, which starts from an accepted
        # repository checkpoint rather than a rejected per-unit candidate.
        for path in sorted(workspace.repo_dir.rglob("*")):
            if (
                not path.is_file()
                or path.suffix.lower() not in {".ts", ".tsx", ".css"}
                or any(part in {"node_modules", "dist"} for part in path.parts)
            ):
                continue
            relative = path.relative_to(workspace.repo_dir).as_posix()
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            include_source(relative, source)
            if len(previous_attempt_files) >= 8:
                break
    return {
        "role_profile": role_profile,
        "operation": operation,
        "unit": unit.model_dump(mode="json"),
        # The normative per-unit contract: every mechanically enforced rule
        # with the exact data it is checked against. Also rendered into the
        # operation prompt by build_instructions.
        "generation_contract": build_generation_contract(
            unit=unit,
            plan=plan,
            projections=projections,
            operation=operation,
            owned_paths=owned,
        ),
        "site_contract": {
            "routes": route_slices,
            "criteria": site.get("criteria", []),
            "facts": [] if unit.kind == "route_compose" else site.get("facts", []),
            # The approved copy this unit renders — without it the builder can
            # only see metadata and must refuse to fabricate content.
            "public_content": [
                item
                for item in site.get("public_content", [])
                if isinstance(item, dict) and str(item.get("route_id", "")) in route_ids
            ]
            if unit.kind != "route_compose"
            else [],
        },
        "visual_direction": context_visual,
        "plan": context_plan,
        "resource_bindings": context_resource_bindings,
        "execution_contract": context_execution_contract,
        "prior_checkpoint": checkpoint.model_dump(mode="json") if checkpoint else {},
        "owned_paths": owned,
        # Ground truth for create-vs-replace: files present in the current
        # candidate tree (disposables excluded).
        "existing_files": existing_files,
        # The frozen shared foundation source this unit builds against.
        "shared_source": shared_source,
        # Rejected files from the prior attempt of this unit, when present.
        "previous_attempt_files": previous_attempt_files,
        "input_hashes": [
            str(projections.get("handoff-report.json", {}).get("projection_hashes", {})),
            checkpoint.checkpoint_hash if checkpoint else "",
        ],
        "workspace_api": [
            "React",
            "TypeScript",
            "local-resource-only",
            "trusted-generated-manifests",
        ],
        "diagnostics": [item.model_dump(mode="json") for item in relevant_diagnostics],
        "repair_round": repair_round,
        "output_ceiling": output_ceiling,
    }


def _scoped_repair_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Keep repair design authority without repeating generation-only data."""

    blueprint = plan.get("experience_blueprint", {})
    scoped: dict[str, Any] = {
        key: plan[key]
        for key in (
            "plan_id",
            "routes",
            "creative_thesis",
            "visual_system",
            "shell",
            "shared_component_contracts",
        )
        if key in plan
    }
    if isinstance(blueprint, dict):
        scoped["experience_blueprint"] = {
            key: blueprint[key]
            for key in (
                # This discriminator selects the exact v4 source envelope;
                # dropping it would silently route a v4 repair through the
                # legacy coverage contract.
                "schema_version",
                "narrative_arc",
                "distinctive_moves",
                "resource_placements",
                "motion_beats",
                "anti_patterns",
            )
            if key in blueprint
        }
    return scoped


def _scoped_repair_visual(visual: dict[str, Any]) -> dict[str, Any]:
    """Retain visual system outcomes while omitting asset/history repetition."""

    return {
        key: visual[key]
        for key in (
            "global",
            "routes",
            "navigation_contract",
            "pack_version",
            "schema_version",
        )
        if key in visual
    }


def _scoped_operation_plan(plan: SitePlan, unit: WorkUnit) -> dict[str, Any]:
    """Build the plan slice needed by one source-generation operation.

    The complete SitePlan remains immutable host input and is used for every
    validation decision. Prompt context is a different concern: route work
    should receive the assigned route and sections plus the token contract,
    not unrelated route graphs and duplicate global resource records.
    """

    value = plan.model_dump(mode="json")
    route_ids = set(unit.route_ids) or ({unit.route_id} if unit.route_id else set())
    section_ids = set(unit.section_ids)
    slot_ids = set(unit.resource_slot_ids)
    interaction_ids = set(unit.interaction_ids)
    criterion_ids = set(unit.criterion_ids)
    if not route_ids:
        return value

    def belongs(item: Any) -> bool:
        if not isinstance(item, dict):
            return False
        item_route = str(item.get("route_id", ""))
        item_routes_value = item.get("route_ids", [])
        item_routes = (
            {str(entry) for entry in item_routes_value if str(entry)}
            if isinstance(item_routes_value, list)
            else set()
        )
        if item_route and item_route not in route_ids:
            return False
        if item_routes and not item_routes.intersection(route_ids):
            return False
        item_section = str(item.get("section_id", ""))
        item_sections_value = item.get("section_ids", [])
        item_sections = (
            {str(entry) for entry in item_sections_value if str(entry)}
            if isinstance(item_sections_value, list)
            else set()
        )
        if section_ids and item_section and item_section not in section_ids:
            return False
        if section_ids and item_sections and not item_sections.intersection(section_ids):
            return False
        item_slot = str(item.get("resource_slot_id", ""))
        if slot_ids and item_slot and item_slot not in slot_ids:
            return False
        item_criterion = str(item.get("criterion_id", ""))
        return not criterion_ids or not item_criterion or item_criterion in criterion_ids

    value["routes"] = [item for item in value.get("routes", []) if belongs(item)]
    if unit.kind == "route_compose":
        # The composer consumes the completed section modules. Content and
        # fact ownership stays with those batch units; exposing route-level
        # content bindings here invites the composer to retype their copy.
        for route in value["routes"]:
            if isinstance(route, dict):
                route["content_bindings"] = []
                route["fact_ids"] = []
    value["resource_slots"] = [item for item in value.get("resource_slots", []) if belongs(item)]
    value["resource_inventory"] = [
        item for item in value.get("resource_inventory", []) if belongs(item)
    ]
    value["execution_bindings"] = [
        item
        for item in value.get("execution_bindings", [])
        if isinstance(item, dict)
        and (str(item.get("resource_slot_id", "")) in slot_ids or (not slot_ids and belongs(item)))
    ]
    value["acceptance_coverage"] = [
        item
        for item in value.get("acceptance_coverage", [])
        if belongs(item)
        and (not criterion_ids or str(item.get("criterion_id", "")) in criterion_ids)
    ]
    value["interactions"] = [
        item
        for item in value.get("interactions", [])
        if belongs(item)
        and (unit.kind != "route_batch" or str(item.get("interaction_id", "")) in interaction_ids)
    ]

    blueprint = value.get("experience_blueprint")
    if isinstance(blueprint, dict):
        blueprint["route_shells"] = [
            item for item in blueprint.get("route_shells", []) if belongs(item)
        ]
        blueprint["section_regions"] = [
            item for item in blueprint.get("section_regions", []) if belongs(item)
        ]
        blueprint["distinctive_moves"] = [
            item for item in blueprint.get("distinctive_moves", []) if belongs(item)
        ]
        blueprint["interaction_assignments"] = [
            item
            for item in blueprint.get("interaction_assignments", [])
            if belongs(item)
            and (
                unit.kind != "route_batch" or str(item.get("interaction_id", "")) in interaction_ids
            )
        ]
        blueprint["resource_placements"] = [
            item
            for item in blueprint.get("resource_placements", [])
            if belongs(item) and (not slot_ids or str(item.get("resource_slot_id", "")) in slot_ids)
        ]
        blueprint["motion_beats"] = [
            item for item in blueprint.get("motion_beats", []) if belongs(item)
        ]

    graph = value.get("work_graph")
    if isinstance(graph, dict):
        related_ids = {unit.unit_id, *unit.depends_on}
        graph["units"] = [
            item
            for item in graph.get("units", [])
            if isinstance(item, dict) and str(item.get("unit_id", "")) in related_ids
        ]
    if unit.kind == "route_compose":
        # Route sections already received their executable resource bindings.
        # The composer only needs their frozen signatures and the route's
        # composition contract, not duplicate inventory/placement records.
        value["resource_slots"] = []
        value["resource_inventory"] = []
        value["execution_bindings"] = []
    return value


def _scoped_visual_direction(value: dict[str, Any], unit: WorkUnit) -> dict[str, Any]:
    """Keep global visual rules and only the assigned route's direction."""

    if not isinstance(value, dict):
        return {}
    route_ids = set(unit.route_ids) or ({unit.route_id} if unit.route_id else set())
    section_ids = set(unit.section_ids)

    def in_scope(item: Any) -> bool:
        if not isinstance(item, dict):
            return False
        route = str(item.get("route_id", ""))
        routes_value = item.get("route_ids", [])
        routes = (
            {str(entry) for entry in routes_value if str(entry)}
            if isinstance(routes_value, list)
            else set()
        )
        section = str(item.get("section_id", ""))
        sections_value = item.get("section_ids", [])
        sections = (
            {str(entry) for entry in sections_value if str(entry)}
            if isinstance(sections_value, list)
            else set()
        )
        if route_ids and route and route not in route_ids:
            return False
        if route_ids and routes and not routes.intersection(route_ids):
            return False
        if section_ids and section and section not in section_ids:
            return False
        return not section_ids or not sections or bool(sections.intersection(section_ids))

    result = dict(value)
    for key in ("routes", "assets", "resources"):
        items = value.get(key)
        if isinstance(items, list):
            result[key] = [item for item in items if in_scope(item)]
    return result


def _scoped_resource_ledger(value: dict[str, Any], unit: WorkUnit) -> dict[str, Any]:
    """Retain only resource-ledger records usable by the current unit."""

    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {
        key: value[key]
        for key in ("schema_version", "ledger_hash", "based_on_input_and_plan")
        if key in value
    }
    active_bindings = value.get("active_bindings")
    if isinstance(active_bindings, list):
        result["active_bindings"] = active_bindings
    if unit.kind == "route_compose":
        result.pop("active_bindings", None)
    return result


def _scoped_execution_contract(value: dict[str, Any], unit: WorkUnit) -> dict[str, Any]:
    """Retain the execution policy and route/unit resource slot bindings."""

    if not isinstance(value, dict):
        return {}
    route_ids = set(unit.route_ids) or ({unit.route_id} if unit.route_id else set())
    slot_ids = set(unit.resource_slot_ids)
    result = dict(value)
    if unit.kind == "route_compose":
        result["slots"] = []
        return result
    items = value.get("slots")
    if isinstance(items, list):
        result["slots"] = [
            item
            for item in items
            if isinstance(item, dict)
            and (
                str(item.get("resource_slot_id", "")) in slot_ids
                if slot_ids
                else (
                    not route_ids
                    or not str(item.get("route_id", ""))
                    or str(item.get("route_id", "")) in route_ids
                )
            )
        ]
    return result


def _shared_source_for_unit(
    plan: SitePlan,
    projections: dict[str, dict[str, Any]],
    unit: WorkUnit,
    repo_dir: Path,
) -> dict[str, str]:
    """Read only trusted interfaces and direct dependency-owned source.

    The old fallback walked the entire repository and accidentally supplied
    generated manifests, public-data modules, and other unrelated source.
    This operation-specific allowlist keeps the prompt useful and bounded.
    """

    if unit.kind == "foundation":
        return {}
    paths: set[str] = set()
    if unit.kind == "route_compose":
        dependency_ids = set(unit.depends_on)
        for dependency in plan.work_graph.units:
            if dependency.unit_id in dependency_ids:
                paths.update(
                    path
                    for path in dependency.owns_paths
                    if "*" not in path and path.startswith("src/routes/")
                )

    if unit.kind in {"route_batch", "route_compose"}:
        paths.update(
            {
                "src/app/ResourceUrl.ts",
                "src/components/generated/SharedSystems.tsx",
                "src/design/generated-tokens.css",
            }
        )
    if unit.kind == "route_batch":
        # Route batches receive the trusted content API alongside their
        # route-scoped approved copy.  The composer consumes the frozen batch
        # modules and does not need this duplicate interface, which can push
        # an otherwise bounded composition context over its ceiling.
        paths.add("src/content/generated-content.ts")
    if unit.kind == "route_compose":
        paths.update({"src/app/AppRouter.tsx", "src/main.tsx"})

    execution = projections.get("execution/contract.json", {})
    requested_slots = set(unit.resource_slot_ids)
    for slot in execution.get("slots", []) if isinstance(execution, dict) else []:
        if (
            not isinstance(slot, dict)
            or str(slot.get("resource_slot_id", "")) not in requested_slots
        ):
            continue
        resolution = slot.get("resolution", {})
        if not isinstance(resolution, dict):
            continue
        for local_path in resolution.get("local_paths", []):
            normalized = str(local_path).replace("\\", "/").strip("/")
            if normalized:
                paths.add(f"src/generated/{normalized}")
                if normalized.startswith("resources/"):
                    paths.add(
                        "src/generated/resources/pack/" + normalized.removeprefix("resources/")
                    )

    source_extensions = {".ts", ".tsx", ".css", ".html"}
    shared_source: dict[str, str] = {}
    for relative in sorted(paths):
        path = repo_dir / relative
        candidates = [path]
        if path.is_dir():
            candidates = sorted(
                item
                for item in path.rglob("*")
                if item.is_file() and item.suffix.lower() in source_extensions
            )[:8]
        for candidate in candidates:
            if not candidate.is_file() or candidate.suffix.lower() not in source_extensions:
                continue
            try:
                relative_candidate = candidate.relative_to(repo_dir).as_posix()
                source = candidate.read_text(encoding="utf-8")
                if relative_candidate == "src/content/generated-content.ts":
                    source = _compact_generated_content_interface(source)
                shared_source[relative_candidate] = source[:30_000]
            except (OSError, UnicodeDecodeError):
                continue
    return shared_source


def _compact_generated_content_interface(source: str) -> str:
    """Expose the generated-content API without duplicating approved prose.

    Route batches already receive their route-scoped approved content and
    literal content keys in the operation contract. Sending the complete
    generated module would duplicate that prose and can push a bounded model
    context over its ceiling. The source excerpt keeps the frozen export names,
    signatures, and exact approved key union available to the model.
    """

    index_match = re.search(
        r"export const CONTENT_INDEX = (?P<index>\[.*?\]) as const;",
        source,
        flags=re.DOTALL,
    )
    entries: list[dict[str, str]] = []
    if index_match:
        try:
            parsed = json.loads(index_match.group("index"))
        except json.JSONDecodeError:
            parsed = []
        if isinstance(parsed, list):
            entries = [
                {"content_id": str(item.get("content_id", ""))}
                for item in parsed
                if isinstance(item, dict) and str(item.get("content_id", ""))
            ]
    ids = [json.dumps(item["content_id"], ensure_ascii=False) for item in entries]
    approved_type = " | ".join(ids) or "never"
    return (
        "/* Trusted generated-content API excerpt; approved values remain in the generated module. */\n"
        "export interface PublicContentPack { readonly route_id: string; readonly sections: readonly unknown[]; }\n"
        "export declare const PUBLIC_CONTENT: readonly PublicContentPack[];\n"
        f"export type ApprovedContentId = {approved_type};\n"
        "export declare function contentForRoute(routeId: string): PublicContentPack | undefined;\n"
        "export declare function sectionForRoute(routeId: string, sectionId: string): unknown;\n"
        "export declare function contentValue(contentId: ApprovedContentId): string;\n"
    )


def _enforce_context_ceiling(context: dict[str, Any], maximum: int) -> dict[str, Any]:
    """Reject oversized model context before a provider call is attempted."""

    serialized = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if maximum <= 0 or len(serialized) > maximum:
        largest_keys = sorted(
            (
                (key, len(json.dumps(value, ensure_ascii=False, default=str)))
                for key, value in context.items()
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:5]
        raise GenerationError(
            "GENERATION_CONTEXT_LIMIT",
            f"The bounded generation context ({len(serialized)} chars) exceeds the "
            f"configured character ceiling ({maximum} chars). Largest fields: "
            + ", ".join(f"{key}={size}" for key, size in largest_keys),
        )
    return context


def _owned_paths(
    unit: WorkUnit, plan: SitePlan, projections: dict[str, dict[str, Any]]
) -> list[str]:
    # Integration is a terminal audit/reconciliation pass. The executable
    # shell is scaffold-owned and route/foundation units already own every
    # mutable source path, so integration must not receive a write surface.
    if unit.kind == "integration":
        return []
    if unit.kind in {"route", "route_batch", "route_compose"}:
        if unit.owns_paths:
            return list(unit.owns_paths)
        # Route ownership is fully determined by the trusted route-registry
        # wiring: the site contract's storage key, never the plan's prose.
        route_id = unit.route_id or (unit.route_ids[0] if unit.route_ids else "route")
        storage_key = route_id
        for route in projections.get("site/contract.json", {}).get("routes", []):
            if isinstance(route, dict) and str(route.get("route_id", "")) == route_id:
                storage_key = str(route.get("storage_key", route_id))
                storage_key = storage_key.replace("\\", "/").strip("/")
                if storage_key.startswith("routes/"):
                    storage_key = storage_key.removeprefix("routes/")
                if isinstance(plan.experience_blueprint, ExperienceBlueprintV4):
                    storage_key = semantic_segment(storage_key or route_id)
                break
        return [f"src/routes/{storage_key}/**"]
    if unit.owns_paths:
        paths = list(unit.owns_paths)
        if unit.kind == "foundation":
            # Older planner outputs used the broad design glob. Keep their
            # useful ownership while removing the immutable global entrypoint.
            paths = [
                item for item in paths if item not in {"src/design/global.css", "src/design/**"}
            ] + (
                [
                    "src/design/tokens.css",
                    "src/design/fonts.css",
                    "src/design/motion.css",
                ]
                if any(item == "src/design/**" for item in unit.owns_paths)
                else []
            )
        return paths
    if unit.kind == "foundation":
        return [
            "src/design/tokens.css",
            "src/design/fonts.css",
            "src/design/motion.css",
            "src/components/shared/**",
        ]
    return []


def _allowed_packages(
    repo_dir: Path, projections: dict[str, dict[str, Any]], dependency_ledger: Any
) -> set[str]:
    packages = {"react", "react-dom", "vite", "@vitejs/plugin-react", "typescript"}
    package_json = _read_json(repo_dir / "package.json")
    packages.update(str(key) for key in package_json.get("dependencies", {}))
    packages.update(str(key) for key in package_json.get("devDependencies", {}))
    target = projections.get("provenance/targets.json", {}).get("target", {})
    packages.update(str(value) for value in target.get("allowed_dependencies", []))
    if dependency_ledger:
        packages.update(
            str(item.package_name)
            for item in DependencyLedger.model_validate(dependency_ledger).receipts
            if item.package_name
        )
    return packages


def _public_text(projections: dict[str, dict[str, Any]]) -> set[str]:
    values: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, str) and value.strip():
            values.add(" ".join(value.split()))
        elif isinstance(value, dict):
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(projections.get("site/contract.json", {}))
    return values


def _unit_projection_dict(unit: WorkUnit) -> dict[str, Any]:
    return GenerationWorkUnitProjection(
        unit_id=unit.unit_id,
        kind=unit.kind,
        status="pending",
        route_ids=list(unit.route_ids) or ([unit.route_id] if unit.route_id else []),
        section_ids=list(unit.section_ids),
        depends_on=list(unit.depends_on),
        owned_paths=list(unit.owns_paths),
    ).model_dump(mode="json")


def _bisect_v4_work_unit(
    unit: WorkUnit,
    *,
    blueprint: ExperienceBlueprintV4 | None = None,
) -> list[WorkUnit]:
    """Split a multi-section V4 route unit into semantic child units.

    V4 route-batch paths are generated deterministically from section IDs, so
    splitting never invents a path or widens ownership. Resource, interaction,
    and criterion coverage is partitioned conservatively; any item without an
    executable section association stays on the first child instead of being
    silently dropped.
    """

    if unit.kind not in {"route_batch", "route"} or len(unit.section_ids) < 2:
        return []
    midpoint = max(1, len(unit.section_ids) // 2)
    section_groups = [unit.section_ids[:midpoint], unit.section_ids[midpoint:]]
    path_groups: list[list[str]] = [[] for _ in section_groups]
    unmatched_paths: list[str] = []
    for path in unit.owns_paths:
        normalized = path.replace("\\", "/")
        matching_group: int | None = None
        for index, sections in enumerate(section_groups):
            if any(f"/{semantic_segment(section)}." in normalized for section in sections):
                matching_group = index
                break
        if matching_group is None:
            unmatched_paths.append(path)
        else:
            path_groups[matching_group].append(path)
    path_groups[0].extend(unmatched_paths)

    def partition_ids(
        values: list[str],
        section_for_id: Callable[[str], str | None],
    ) -> list[list[str]]:
        groups: list[list[str]] = [[] for _ in section_groups]
        for value in values:
            section = section_for_id(value)
            target = next(
                (
                    index
                    for index, sections in enumerate(section_groups)
                    if section is not None and section in sections
                ),
                0,
            )
            groups[target].append(value)
        return groups

    def resource_section(resource_id: str) -> str | None:
        if blueprint is None:
            return None
        route_ids = set(unit.route_ids or ([unit.route_id] if unit.route_id else []))
        matches = [
            item.section_id
            for item in blueprint.resource_placements
            if item.resource_slot_id == resource_id and item.route_id in route_ids
        ]
        return matches[0] if len(set(matches)) == 1 else None

    # Work units produced by the V4 compiler have section-scoped paths. Their
    # resource IDs can be mapped from the blueprint; unclassified IDs remain
    # on the first child instead of being silently dropped.
    resource_groups = partition_ids(unit.resource_slot_ids, resource_section)
    interaction_groups = partition_ids(unit.interaction_ids, lambda _value: None)
    criterion_groups = partition_ids(unit.criterion_ids, lambda _value: None)

    children: list[WorkUnit] = []
    for index, sections in enumerate(section_groups, start=1):
        children.append(
            unit.model_copy(
                update={
                    "unit_id": f"{unit.unit_id}-split-{index}",
                    "section_ids": list(sections),
                    "owns_paths": path_groups[index - 1],
                    "resource_slot_ids": resource_groups[index - 1],
                    "interaction_ids": interaction_groups[index - 1],
                    "criterion_ids": criterion_groups[index - 1],
                    "isolated_workspace_key": (
                        f"{unit.isolated_workspace_key or unit.unit_id}-split-{index}"
                    ),
                    "context_estimate": max(1, unit.context_estimate // 2),
                    "output_estimate": max(1, unit.output_estimate // 2),
                }
            )
        )
    return children


def _unit_projection(
    projection: GenerationProjection, unit: WorkUnit
) -> GenerationWorkUnitProjection:
    for item in projection.work_units:
        if item.unit_id == unit.unit_id:
            return item
    item = GenerationWorkUnitProjection.model_validate(_unit_projection_dict(unit))
    projection.work_units.append(item)
    return item


def _copy_without_disposables(source: Path, target: Path) -> None:
    shutil.copytree(
        source,
        target,
        symlinks=False,
        ignore=shutil.ignore_patterns("node_modules", "dist"),
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _intended_paths_for_candidate(execution_contract: dict[str, Any], candidate: Any) -> list[str]:
    """Return plan-owned local destinations for one acquired candidate.

    Build Preparation's migrated brief deliberately omits executable component
    paths, while legacy/explicit plans may still bind a vetted component to a
    concrete destination.  Matching both the provider asset identity and the
    adapter's candidate identity keeps this check deterministic without
    trusting a model-authored filename.
    """

    if not isinstance(execution_contract, dict):
        return []
    provider = str(getattr(candidate, "provider_key", "")).strip()
    candidate_ids = {
        str(getattr(candidate, "candidate_id", "")).strip(),
        str(getattr(candidate, "provider_resource_id", "")).strip(),
    }
    candidate_ids.discard("")
    if not provider or not candidate_ids:
        return []
    matches: list[str] = []
    for raw_slot in execution_contract.get("slots", []):
        if not isinstance(raw_slot, dict):
            continue
        resolution_value = raw_slot.get("resolution")
        resolution = resolution_value if isinstance(resolution_value, dict) else {}
        if resolution.get("resolution_type") != "deferred_materialized":
            continue
        if str(resolution.get("provider", "")).strip() != provider:
            continue
        bound_ids = {
            str(resolution.get("provider_asset_id", "")).strip(),
            str(resolution.get("resource_id", "")).strip(),
        }
        if not candidate_ids.intersection(bound_ids):
            continue
        for value in resolution.get("local_paths", []):
            path = str(value).strip()
            if path and path not in matches:
                matches.append(path)
    return matches


def _invalidate_stale_route_batch_checkpoint(
    projection: GenerationProjection,
    *,
    plan: SitePlan,
    workspace: GenerationWorkspace,
    projections: dict[str, dict[str, Any]] | None = None,
) -> list[SourceDiagnostic]:
    """Reopen route batches that fail the bounded source contract."""

    route_batches = [unit for unit in plan.work_graph.units if unit.kind == "route_batch"]
    if not route_batches or projection.accepted_checkpoint is None:
        return []
    projections_by_id = {item.unit_id: item for item in projection.work_units}
    checkpointed = [
        unit
        for unit in route_batches
        if projections_by_id.get(unit.unit_id) is not None
        and projections_by_id[unit.unit_id].status == "checkpointed"
    ]
    if not checkpointed:
        return []
    diagnostics: list[SourceDiagnostic] = []
    for unit in checkpointed:
        (
            section_content_ids,
            section_selectors,
            interaction_markers,
            interaction_contracts,
        ) = _v4_route_batch_contract_data(plan, unit)
        diagnostics.extend(
            validate_route_batch_contract(
                workspace.repo_dir,
                list(unit.owns_paths),
                route_id=str(getattr(unit, "route_id", "")),
                section_ids=list(getattr(unit, "section_ids", [])),
                source_markers=[
                    coverage.source_marker
                    for coverage in getattr(plan, "acceptance_coverage", [])
                    if coverage.route_id == getattr(unit, "route_id", "")
                    and coverage.criterion_id in getattr(unit, "criterion_ids", [])
                ],
                content_ids_by_section=section_content_ids,
                section_selectors_by_section=section_selectors,
                interaction_ids=list(getattr(unit, "interaction_ids", [])),
                interaction_markers=interaction_markers,
                interaction_contracts=interaction_contracts,
                image_assets_by_slot=_v4_image_assets_for_unit(plan, unit, projections or {}),
                distinctive_moves=_v4_distinctive_moves_for_unit(plan, unit),
                motion_beats=_v4_motion_beats_for_unit(plan, unit),
                h1_owner_section_id=_v4_h1_owner_for_route(
                    plan, str(getattr(unit, "route_id", ""))
                ),
                work_unit_id=unit.unit_id,
            )
        )
    if not diagnostics:
        return []
    for item in projection.work_units:
        if item.kind not in {"route_batch", "route_compose"}:
            continue
        item.status = "pending"
        item.checkpoint_after = ""
        item.call_receipt_id = ""
        item.repair_round = 0
    projection.phase = "generating_routes"
    projection.active_work_unit_id = ""
    projection.source_ready = False
    projection.source_file_count = 0
    projection.source_total_bytes = 0
    return diagnostics


def _v4_route_batch_contract_data(
    plan: SitePlan | Any,
    unit: WorkUnit | Any,
) -> tuple[
    dict[str, list[str]],
    dict[str, str],
    dict[str, str],
    dict[str, dict[str, Any]],
]:
    """Compile the exact V4 batch selector and interaction evidence."""

    blueprint = getattr(plan, "experience_blueprint", None)
    if not isinstance(blueprint, ExperienceBlueprintV4):
        return {}, {}, {}, {}
    route_id = str(getattr(unit, "route_id", ""))
    section_ids = set(getattr(unit, "section_ids", []) or [])
    interaction_ids = set(getattr(unit, "interaction_ids", []) or [])
    regions = [
        region
        for region in blueprint.section_regions
        if region.route_id == route_id and region.section_id in section_ids
    ]
    return (
        {region.section_id: list(region.content_ids) for region in regions},
        {region.section_id: region.section_selector for region in regions},
        {
            assignment.interaction_id: assignment.literal_marker
            for assignment in blueprint.interaction_assignments
            if assignment.route_id == route_id and assignment.interaction_id in interaction_ids
        },
        {
            assignment.interaction_id: assignment.model_dump(mode="json")
            for assignment in blueprint.interaction_assignments
            if assignment.route_id == route_id and assignment.interaction_id in interaction_ids
        },
    )


def _v4_image_assets_for_unit(
    plan: SitePlan | Any,
    unit: WorkUnit | Any,
    projections: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    blueprint = getattr(plan, "experience_blueprint", None)
    if not isinstance(blueprint, ExperienceBlueprintV4):
        return {}
    section_ids = set(getattr(unit, "section_ids", []) or [])
    placements = {
        placement.resource_slot_id: placement
        for placement in blueprint.resource_placements
        if placement.route_id == str(getattr(unit, "route_id", ""))
        and placement.section_id in section_ids
    }
    materialized = projections.get("generated/resource-assets.json", {})
    assets = materialized.get("image_assets", []) if isinstance(materialized, dict) else []
    return {
        str(asset.get("resource_id", "")): {
            **dict(asset),
            "element_marker": placements[str(asset.get("resource_id", ""))].element_marker,
            "element_selector": placements[str(asset.get("resource_id", ""))].element_selector,
        }
        for asset in assets
        if isinstance(asset, dict) and str(asset.get("resource_id", "")) in placements
    }


def _v4_motion_beats_for_unit(
    plan: SitePlan | Any,
    unit: WorkUnit | Any,
) -> list[dict[str, Any]]:
    blueprint = getattr(plan, "experience_blueprint", None)
    if not isinstance(blueprint, ExperienceBlueprintV4):
        return []
    section_ids = set(getattr(unit, "section_ids", []) or [])
    return [
        beat.model_dump(mode="json")
        for beat in blueprint.motion_beats
        if beat.route_id == str(getattr(unit, "route_id", "")) and beat.section_id in section_ids
    ]


def _v4_distinctive_moves_for_unit(
    plan: SitePlan | Any,
    unit: WorkUnit | Any,
) -> list[dict[str, Any]]:
    blueprint = getattr(plan, "experience_blueprint", None)
    if not isinstance(blueprint, ExperienceBlueprintV4):
        return []
    section_ids = set(getattr(unit, "section_ids", []) or [])
    return [
        move.model_dump(mode="json")
        for move in blueprint.distinctive_moves
        if move.route_id == str(getattr(unit, "route_id", "")) and move.section_id in section_ids
    ]


def _v4_h1_owner_for_route(plan: SitePlan | Any, route_id: str) -> str:
    blueprint = getattr(plan, "experience_blueprint", None)
    if not isinstance(blueprint, ExperienceBlueprintV4):
        return ""
    shell = next((item for item in blueprint.route_shells if item.route_id == route_id), None)
    if shell is None or not shell.section_order:
        return ""
    return shell.section_order[0]


def _fallback_receipt(request: Any, reason: str) -> ResourceReceipt:
    return ResourceReceipt(
        request_hash=request.request_hash,
        disposition="fallback",
        fallback={
            "kind": request.fallback.kind,
            "implementation": request.fallback.implementation,
            "reason": reason,
        },
        satisfied_placements=[request.placement.purpose],
        acquired_at=datetime.now(UTC).isoformat(),
    )


def _diagnostic_from_exception(exc: Exception, work_unit_id: str) -> SourceDiagnostic:
    code = str(getattr(exc, "code", "SOURCE_CHANGE_INVALID"))
    message = str(getattr(exc, "message", str(exc)))
    fingerprint = hashlib.sha256(f"{code}:{message}:{work_unit_id}".encode()).hexdigest()[:24]
    return SourceDiagnostic(
        diagnostic_id=f"diagnostic-{fingerprint}",
        group="source_contract",
        code=code,
        phase="source_generation",
        work_unit_id=work_unit_id,
        normalized_message=message,
        file=str(getattr(exc, "file", "")),
        fingerprint=fingerprint,
    )


def _consume_repair_budget(
    projection: GenerationProjection,
    diagnostics: list[SourceDiagnostic],
    *,
    repair_round: int,
    settings: Any,
) -> None:
    diagnostic_summary = "; ".join(
        f"{item.code}: {item.normalized_message}" for item in diagnostics[:4]
    )[:1200]
    if repair_round >= int(settings.code_generator_generation.max_repair_rounds_per_unit):
        raise GenerationError(
            "SOURCE_REPAIR_EXHAUSTED",
            "Source generation repair budget was exhausted. Final diagnostics: "
            + (diagnostic_summary or "none recorded"),
        )
    if projection.repair_budget_used >= int(
        settings.code_generator_generation.max_repair_rounds_total
    ):
        raise GenerationError(
            "SOURCE_REPAIR_TOTAL_EXHAUSTED",
            "The total source repair budget was exhausted. Final diagnostics: "
            + (diagnostic_summary or "none recorded"),
        )
    fingerprints = sorted({item.fingerprint for item in diagnostics})
    recurrence = any(projection.repair_fingerprint_counts.get(item, 0) > 0 for item in fingerprints)
    projection.repair_budget_used += 1
    projection.repair_rounds += 1
    for fingerprint in fingerprints:
        projection.repair_fingerprint_counts[fingerprint] = (
            projection.repair_fingerprint_counts.get(fingerprint, 0) + 1
        )
    projection.repair_strategies.append(
        "bounded-simplification" if recurrence else "bounded-correction"
    )


def _safe_generation_model_issue(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        entries: list[str] = []
        for error in exc.errors(include_url=False)[:8]:
            location = ".".join(str(part) for part in error.get("loc", ())) or "root"
            message = str(error.get("msg", "invalid value"))[:160]
            entries.append(f"{location}: {message}")
        return "; ".join(entries)[:500] or "The generation result failed local schema validation."
    return str(exc).strip()[:500] or "The model response was not usable."


def _safe_generation_validation_summary(exc: ValidationError) -> str:
    return _safe_generation_model_issue(exc)


def _validate_v4_generation_coverage(
    changes: GenerationChanges,
    unit: WorkUnit,
    plan: SitePlan,
    projections: dict[str, dict[str, Any]],
) -> None:
    site = projections["site/contract.json"]
    grouped_content = content_ids_by_section(
        [item for item in site.get("public_content", []) if isinstance(item, dict)],
        [item for item in site.get("facts", []) if isinstance(item, dict)],
    )
    expected_content = [
        content_id
        for section_id in unit.section_ids
        for route_id in unit.route_ids or ([unit.route_id] if unit.route_id else [])
        for content_id in grouped_content.get((route_id, section_id), [])
    ]
    expected = {
        "content": expected_content,
        "criterion": list(unit.criterion_ids),
        "resource": list(unit.resource_slot_ids),
        "interaction": list(unit.interaction_ids),
    }
    observed = {
        "content": list(changes.content_coverage),
        "criterion": list(changes.criterion_coverage),
        "resource": list(changes.resource_usage),
        "interaction": list(changes.interaction_coverage),
    }
    for category, expected_ids in expected.items():
        if observed[category] != expected_ids:
            raise SourceValidationError(
                "SOURCE_COVERAGE_MISMATCH",
                f"The v4 {category} coverage array does not exactly match its work unit.",
            )
    changed_paths = [item.path.replace("\\", "/") for item in changes.files]
    if len(changed_paths) != len(set(changed_paths)):
        seen_paths: set[str] = set()
        duplicate_paths = []
        for path in changed_paths:
            if path in seen_paths and path not in duplicate_paths:
                duplicate_paths.append(path)
            seen_paths.add(path)
        # Name the exact duplicated path(s) so a repair attempt has something
        # to act on. Leaving `file` empty here previously gave the repair
        # model no way to know which file to fix, and it correctly (if
        # unhelpfully) reported cannot_complete rather than guess.
        raise SourceValidationError(
            "SOURCE_DUPLICATE_PATH",
            "The v4 source envelope lists the same file path more than once: "
            f"{', '.join(duplicate_paths)}. Return one entry per path, merging any "
            "content that belongs together.",
            file=duplicate_paths[0] if duplicate_paths else "",
        )
    signatures = {
        (item.path.replace("\\", "/"), item.export_name) for item in changes.exported_signatures
    }
    if any(path not in changed_paths for path, _export in signatures):
        raise SourceValidationError(
            "SOURCE_EXPORT_SIGNATURE_PATH",
            "An exported signature references a file outside the v4 source envelope.",
        )
    signature_paths = {path for path, _export in signatures}
    changed_exported_paths = {
        item.path.replace("\\", "/")
        for item in changes.files
        if Path(item.path).suffix.casefold() in {".js", ".jsx", ".ts", ".tsx"}
        and re.search(r"(?m)^\s*export\b", item.complete_utf8_content)
    }
    missing_signature_paths = changed_exported_paths - signature_paths
    if unit.kind in {"route_batch", "route_compose", "route"} and missing_signature_paths:
        raise SourceValidationError(
            "SOURCE_EXPORT_SIGNATURE_MISSING",
            "V4 route work must declare a concrete exported signature for every changed "
            f"exported source file; missing: {', '.join(sorted(missing_signature_paths))}.",
        )


def _context_uses_v4_contract(context: dict[str, Any]) -> bool:
    plan = context.get("plan")
    if not isinstance(plan, dict):
        return False
    blueprint = plan.get("experience_blueprint")
    return isinstance(blueprint, dict) and str(blueprint.get("schema_version", "")).endswith("-v4")


def _review_accepted(review: IntegrationReviewV1 | QualityReviewDraftV1) -> bool:
    if isinstance(review, IntegrationReviewV1):
        return review.status == "accepted"
    return min(
        review.hierarchy_score,
        review.composition_score,
        review.typography_score,
        review.resource_fit_score,
        review.motion_score,
    ) >= 4 and not any(item.severity == "blocking" for item in review.findings)


def _canonicalize_review_owners(
    review: IntegrationReviewV1 | QualityReviewDraftV1,
    valid_owner_ids: set[str],
) -> IntegrationReviewV1 | QualityReviewDraftV1:
    """Map the reviewer's human composer label to the canonical work-unit ID.

    The model-facing work graph uses ``-compose`` as the executable unit ID,
    while a reviewer may describe that same owner as ``-composer``. Only this
    unambiguous suffix alias is accepted; every other unknown owner remains
    unchanged and is rejected by the owner validation in the polish path.
    """

    def canonical(owner_id: str) -> str:
        if owner_id in valid_owner_ids:
            return owner_id
        if owner_id.endswith("-composer"):
            candidate = f"{owner_id[: -len('-composer')]}-compose"
            if candidate in valid_owner_ids:
                return candidate
        return owner_id

    updates: dict[str, object] = {}
    findings = [
        item.model_copy(update={"owner_work_unit_id": canonical(item.owner_work_unit_id)})
        for item in review.findings
    ]
    if findings != review.findings:
        updates["findings"] = findings
    if isinstance(review, QualityReviewDraftV1):
        score_evidence = [
            item.model_copy(update={"owner_work_unit_id": canonical(item.owner_work_unit_id)})
            for item in review.score_evidence
        ]
        if score_evidence != review.score_evidence:
            updates["score_evidence"] = score_evidence
    return review.model_copy(update=updates) if updates else review


async def _cas(repo: Any, run: Any, status: str, values: dict[str, object]) -> Any:
    await WorkerAuthorizationFence(repo._session).validate_run(run.id)
    updated = await repo.compare_and_swap(
        run.id, expected_revision=run.revision, values={"status": status, **values}
    )
    if updated is None:
        raise GenerationError("RUN_REVISION_CONFLICT", "The generation run changed concurrently.")
    return updated


async def _validate_worker_payload(sessionmaker: Any, payload: dict[str, Any]) -> None:
    async with sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_payload(payload)


__all__ = ["CodeGeneratorGenerationOrchestrator", "GenerationError"]
