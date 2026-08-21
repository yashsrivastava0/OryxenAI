"""Progressive, receipt-driven Phase 3 source-generation orchestration."""

from __future__ import annotations

import asyncio
import contextlib
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
from oryxenai.agents.code_generator.core.check_runner import prepare_toolchain, run_source_checks
from oryxenai.agents.code_generator.core.checkpoint_store import CheckpointError, CheckpointStore
from oryxenai.agents.code_generator.core.content_compiler import write_content_module
from oryxenai.agents.code_generator.core.coordinator import advance_after
from oryxenai.agents.code_generator.core.dependency_manager import (
    DependencyManager,
    build_dependency_ledger,
)
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
    QualityFindingV1,
    QualityReviewReceiptV1,
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
from oryxenai.agents.code_generator.core.generation_prompt_builder import build_instructions
from oryxenai.agents.code_generator.core.integration_review_operation import (
    run_integration_review_operation,
)
from oryxenai.agents.code_generator.core.parallel_scheduler import (
    execute_waves,
    isolated_workspace_path,
)
from oryxenai.agents.code_generator.core.resource_adapters import (
    OfflineResourceProviderRegistry,
    ResourceProviderError,
    default_adapters,
)
from oryxenai.agents.code_generator.core.source_manifest import (
    digest,
    materialize_trusted_manifests,
)
from oryxenai.agents.code_generator.core.source_validation import (
    SourceValidationError,
    validate_generation_changes,
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
)
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
    return path if path.is_absolute() else (repository_root() / path).resolve()


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
            plan = SitePlan.model_validate(run.plan or {})
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
            reference = self._reference(run)
            input_adapter = DevelopmentInputAdapter(settings)
            input_receipt, projections = input_adapter.admit(reference)
            plan = SitePlan.model_validate(run.plan or {})
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
            materialize_trusted_manifests(
                workspace,
                projections,
                plan,
                acquisition_ledger=run.resource_ledger,
                # Receipt local_paths are recorded relative to the configured
                # materials root (already prefixed with the run id).
                acquisition_materials_root=_resolve_config_path(
                    settings.code_generator_acquisition.materials_root
                ),
            )
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
            return {"status": "needs_attention", "run_id": str(run_id)}
        except (
            WorkspaceError,
            SourceValidationError,
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
            details = dict(exc.details)
            details["exception_type"] = type(exc).__name__
            await self._fail(
                sessionmaker,
                run_id,
                SafeIssue(
                    code=exc.code,
                    message=exc.message,
                    next_action="Review the provider contract and start a corrected run.",
                    details=details,
                ),
            )
            return {"status": "needs_attention", "run_id": str(run_id)}
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
            write_content_module(workspace.repo_dir, public_content)
            diagnostics = await run_source_checks(
                workspace.repo_dir,
                allowed_packages=allowed_packages,
                public_text=public_text,
                max_source_bytes=int(settings.code_generator_generation.max_source_bytes),
                work_unit_id=unit.unit_id,
                settings=settings,
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
            return checkpoint_store.accept(
                work_unit_id=unit.unit_id,
                parent_hash=checkpoint.checkpoint_hash if checkpoint else "",
            )

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
        if review.status == "accepted":
            return
        blocking_findings = [
            finding for finding in review.findings if finding.severity == "blocking"
        ]
        if not blocking_findings:
            # Advisory observations are persisted for the receipt but cannot
            # spend the single owner-scoped polish call.
            return
        owners = {item.unit_id: item for item in plan.work_graph.units if not item.terminal}
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
                    route_id=finding.route_id,
                    file=finding.section_id,
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
            context = _operation_context(
                plan=plan,
                projections=projections,
                unit=owner,
                operation="repair",
                checkpoint=checkpoint,
                workspace=workspace,
                role_profile=role_profile,
                output_ceiling=int(settings.code_generator_generation.max_response_bytes),
                diagnostics=diagnostics,
                repair_round=1,
            )
            context = _enforce_context_ceiling(
                context,
                int(settings.code_generator_generation.max_context_chars),
            )
            system, instructions, context_receipt = build_instructions("repair", context)
            context_path = (
                workspace.ledger_dir / "contexts" / f"{context_receipt.context_hash}.json"
            )
            workspace.write_json(context_path, context)
            context_receipt = context_receipt.model_copy(
                update={"stored_relative_path": context_path.relative_to(workspace.root).as_posix()}
            )
            projection.context_receipts.append(context_receipt)
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
                unit_id=f"{owner.unit_id}-integration-polish",
                request_round=0,
            )
            projection.call_receipts.append(call_receipt)
            if result.mode != "changes":
                raise GenerationError(
                    "INTEGRATION_POLISH_INCOMPLETE",
                    "The bounded integration polish pass did not return owner-scoped source changes.",
                )
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
        final_review = await self._integration_review(
            sessionmaker=sessionmaker,
            run_id=run_id,
            settings=settings,
            run=run,
            plan=plan,
            workspace=workspace,
            projection=projection,
            round_number=1,
        )
        if final_review.status != "accepted":
            raise GenerationError(
                "INTEGRATION_REVIEW_UNRESOLVED",
                "The completed source tree did not pass the bounded whole-site quality review.",
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
    ) -> IntegrationReviewV1:
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
                value = path.read_text(encoding="utf-8")[:30_000]
            except (OSError, UnicodeDecodeError):
                continue
            encoded_size = len(value.encode("utf-8"))
            if source and source_bytes + encoded_size > 500_000:
                break
            source[relative] = value
            source_bytes += encoded_size
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
            "assembled_source": source,
        }
        review, context_receipt, raw = await run_integration_review_operation(
            client, context=context, profile_name=profile
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
            )
        )
        review_payload = review.model_dump(mode="json")
        if isinstance(plan.experience_blueprint, ExperienceBlueprintV4):
            quality = QualityReviewReceiptV1(
                source_hash=digest(source),
                plan_hash=digest(plan.model_dump(mode="json")),
                context_hash=context_receipt.context_hash,
                hierarchy_score=review.distinctiveness_score,
                composition_score=review.composition_score,
                typography_score=review.typography_score,
                resource_fit_score=review.resource_fit_score,
                motion_score=review.motion_score,
                findings=[
                    QualityFindingV1(
                        finding_id=item.finding_id,
                        severity=item.severity,
                        owner_work_unit_id=item.owner_work_unit_id,
                        code=item.code,
                        evidence=item.evidence,
                        requested_outcome=item.requested_outcome,
                    )
                    for item in review.findings
                ],
                reviewer_receipt=digest(review.model_dump(mode="json")),
                accepted=(
                    review.status == "accepted"
                    or (
                        min(
                            review.distinctiveness_score,
                            review.composition_score,
                            review.typography_score,
                            review.resource_fit_score,
                            review.motion_score,
                        )
                        >= 4
                        and not any(item.severity == "blocking" for item in review.findings)
                    )
                ),
            )
            projection.quality_review = quality
            review_payload["quality_receipt"] = quality.model_dump(mode="json")
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
                    result = _adapt_v4_generation_result(
                        SourceGenerationEnvelopeV2.model_validate(parsed),
                        operation_id=f"{operation}:{unit_id}",
                        context_receipt=context_receipt,
                    )
                else:
                    result = GenerationResult.model_validate(parsed)
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
        return result, GenerationCallReceipt(
            receipt_id=f"call-{key[:20]}",
            operation_id=operation,
            idempotency_key=key,
            context_receipt_hash=context_receipt.context_hash,
            result_hash=digest(result.model_dump(mode="json")),
            profile=role_profile,
            response_id=str(getattr(raw, "response_id", "") or ""),
            model=str(getattr(raw, "model", "") or ""),
            usage={
                str(k): int(v)
                for k, v in dict(getattr(raw, "usage", {}) or {}).items()
                if isinstance(v, int)
            },
            finish_reason=str(getattr(raw, "finish_reason", "") or ""),
            attempt=attempt + 1,
            retry_class="schema_correction" if attempt else "",
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
                    materialized_result = await adapter.materialize(
                        candidate, request, storage_root=materials_root, settings=settings
                    )
                    materialized_files = (
                        list(materialized_result)
                        if isinstance(materialized_result, list)
                        else [materialized_result]
                    )
                    receipt_files = []
                    for materialized in materialized_files:
                        source_file = materials_root / materialized.local_path
                        local_name = f"{materialized.sha256}{Path(materialized.local_path).suffix}"
                        generated_path = workspace.materialize_acquired_file(
                            source_file, local_name
                        )
                        inspection = dict(materialized.inspection)
                        licence_name = str(inspection.get("licence_path", ""))
                        if licence_name:
                            licence_source = materials_root / licence_name
                            licence_target = (
                                workspace.repo_dir / "public" / "licences" / Path(licence_name).name
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
                        disposition="admitted",
                        selected_candidate_id=candidate.candidate_id,
                        provider_key=candidate.provider_key,
                        canonical_source=candidate.canonical_source,
                        licence=candidate.licence,
                        attribution=candidate.attribution,
                        original_hash=materialized_files[0].sha256,
                        materialized_files=receipt_files,
                        dependencies=sorted(candidate.dependency_metadata),
                        satisfied_placements=[request.placement.purpose],
                        acquired_at=datetime.now(UTC).isoformat(),
                    )
            except ResourceProviderError as exc:
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
        "foundation": str(config.foundation_profile),
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
) -> dict[str, Any]:
    site = projections["site/contract.json"]
    visual = projections["design/visual-direction.json"]
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
    # Frozen source this unit builds against (scaffold app layer, foundation
    # shared files, generated manifest shapes) — the checkpoint's file hashes
    # alone are not enough to author compatible imports.
    shared_source: dict[str, str] = {}
    if unit.kind != "foundation":
        dependency_ids = set(unit.depends_on)
        dependency_paths = [
            owned_path
            for dependency in plan.work_graph.units
            if dependency.unit_id in dependency_ids
            for owned_path in dependency.owns_paths
            if "*" not in owned_path
        ]
        for relative in dependency_paths:
            path = workspace.repo_dir / relative
            if not path.is_file() or path.suffix.lower() not in {".ts", ".tsx", ".css"}:
                continue
            try:
                shared_source[relative] = path.read_text(encoding="utf-8")[:30_000]
            except (OSError, UnicodeDecodeError):
                continue
        for path in sorted(workspace.repo_dir.rglob("*")):
            if (
                not path.is_file()
                or path.suffix.lower() not in {".ts", ".tsx", ".css", ".html"}
                or any(part in {"node_modules", "dist"} for part in path.parts)
            ):
                continue
            relative = path.relative_to(workspace.repo_dir).as_posix()
            try:
                shared_source[relative] = path.read_text(encoding="utf-8")[:20_000]
            except (OSError, UnicodeDecodeError):
                continue
            if len(shared_source) >= 32:
                break
    # The rejected files from a prior attempt, when its candidate tree is
    # still on disk — the repairer needs the exact content it must correct.
    previous_attempt_files: dict[str, str] = {}
    candidate_dir = workspace.root / f"candidate-{_unit_dir_slug(unit.unit_id)}"
    if candidate_dir.is_dir():
        for path in sorted(candidate_dir.rglob("*")):
            if (
                not path.is_file()
                or path.suffix.lower() not in {".ts", ".tsx", ".css"}
                or any(part in {"node_modules", "dist"} for part in path.parts)
            ):
                continue
            relative = path.relative_to(candidate_dir).as_posix()
            try:
                previous_attempt_files[relative] = path.read_text(encoding="utf-8")[:20_000]
            except (OSError, UnicodeDecodeError):
                continue
            if len(previous_attempt_files) >= 12:
                break
    owned = _owned_paths(unit, plan, projections)
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
            "facts": site.get("facts", []),
            # The approved copy this unit renders — without it the builder can
            # only see metadata and must refuse to fabricate content.
            "public_content": [
                item
                for item in site.get("public_content", [])
                if isinstance(item, dict) and str(item.get("route_id", "")) in route_ids
            ],
        },
        "visual_direction": visual,
        "plan": plan.model_dump(mode="json"),
        "resource_bindings": projections.get("resources/ledger.json", {}),
        "execution_contract": projections.get("execution/contract.json", {}),
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
        "diagnostics": [item.model_dump(mode="json") for item in diagnostics[-12:]],
        "repair_round": repair_round,
        "output_ceiling": output_ceiling,
    }


def _enforce_context_ceiling(context: dict[str, Any], maximum: int) -> dict[str, Any]:
    """Reject oversized model context before a provider call is attempted."""

    serialized = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if maximum <= 0 or len(serialized) > maximum:
        raise GenerationError(
            "GENERATION_CONTEXT_LIMIT",
            "The bounded generation context exceeds the configured character ceiling.",
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
    if repair_round >= int(settings.code_generator_generation.max_repair_rounds_per_unit):
        raise GenerationError(
            "SOURCE_REPAIR_EXHAUSTED", "Source generation repair budget was exhausted."
        )
    if projection.repair_budget_used >= int(
        settings.code_generator_generation.max_repair_rounds_total
    ):
        raise GenerationError(
            "SOURCE_REPAIR_TOTAL_EXHAUSTED", "The total source repair budget was exhausted."
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


def _context_uses_v4_contract(context: dict[str, Any]) -> bool:
    plan = context.get("plan")
    if not isinstance(plan, dict):
        return False
    blueprint = plan.get("experience_blueprint")
    return isinstance(blueprint, dict) and str(blueprint.get("schema_version", "")).endswith("-v4")


def _adapt_v4_generation_result(
    envelope: SourceGenerationEnvelopeV2,
    *,
    operation_id: str,
    context_receipt: GenerationContextReceipt,
) -> GenerationResult:
    """Adapt the mapping-free v4 envelope into the legacy internal domain DTO."""

    if envelope.result == "changes":
        return GenerationResult(
            operation_id=operation_id,
            based_on_context_receipt=context_receipt.context_hash,
            mode="changes",
            changes=GenerationChanges(
                files=list(envelope.files),
                content_coverage=list(envelope.coverage),
                criterion_coverage=list(envelope.coverage),
                resource_usage=list(envelope.coverage),
            ),
        )
    if envelope.result == "requests":
        from oryxenai.agents.code_generator.core.development_schemas import GenerationRequests

        return GenerationResult(
            operation_id=operation_id,
            based_on_context_receipt=context_receipt.context_hash,
            mode="requests",
            requests=GenerationRequests(resource_requests=list(envelope.resource_requests)),
        )
    if envelope.result == "accepted":
        from oryxenai.agents.code_generator.core.development_schemas import GenerationAccepted

        return GenerationResult(
            operation_id=operation_id,
            based_on_context_receipt=context_receipt.context_hash,
            mode="accepted",
            accepted=GenerationAccepted(
                summary="The v4 source work unit was accepted.",
                verified_contracts=list(envelope.coverage),
            ),
        )
    from oryxenai.agents.code_generator.core.development_schemas import GenerationCannotComplete

    detail = envelope.failure_details[0]
    return GenerationResult(
        operation_id=operation_id,
        based_on_context_receipt=context_receipt.context_hash,
        mode="cannot_complete",
        cannot_complete=GenerationCannotComplete(
            code=detail.code,
            safe_reason=detail.message,
            missing_authority_or_capability=detail.next_action,
        ),
    )


async def _cas(repo: Any, run: Any, status: str, values: dict[str, object]) -> Any:
    updated = await repo.compare_and_swap(
        run.id, expected_revision=run.revision, values={"status": status, **values}
    )
    if updated is None:
        raise GenerationError("RUN_REVISION_CONFLICT", "The generation run changed concurrently.")
    return updated


__all__ = ["CodeGeneratorGenerationOrchestrator", "GenerationError"]
