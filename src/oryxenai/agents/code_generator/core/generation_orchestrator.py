"""Progressive, receipt-driven Phase 3 source-generation orchestration."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from oryxenai.core.logging import get_logger

logger = get_logger("oryxenai.agents.code_generator.generation")


def _unit_dir_slug(unit_id: str) -> str:
    """Filesystem-safe workspace suffix for a work-unit id.

    Unit ids follow the colon-namespaced convention (``unit:route:home``);
    Windows forbids colons (and other reserved characters) in paths.
    """

    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", unit_id).strip("._")
    return slug or "unit"

from oryxenai.agents.code_generator.core.acquisition_validators import (
    AcquisitionValidationError,
    filter_candidates_by_policy,
    select_candidate,
    validate_plan_delta,
    validate_resource_request,
)
from oryxenai.agents.code_generator.core.check_runner import prepare_toolchain, run_source_checks
from oryxenai.agents.code_generator.core.checkpoint_store import CheckpointStore
from oryxenai.agents.code_generator.core.dependency_manager import (
    DependencyManager,
    build_dependency_ledger,
)
from oryxenai.agents.code_generator.core.development_input import DevelopmentInputAdapter
from oryxenai.agents.code_generator.core.development_planner import validate_site_plan
from oryxenai.agents.code_generator.core.development_schemas import (
    DependencyLedger,
    DevelopmentRunStatus,
    GenerationCallReceipt,
    GenerationChanges,
    GenerationContextReceipt,
    GenerationProjection,
    GenerationResult,
    GenerationWorkUnitProjection,
    PlanDelta,
    ResourceBinding,
    ResourceLedger,
    ResourceReceipt,
    SafeIssue,
    SitePlan,
    SourceCheckpoint,
    SourceDiagnostic,
    WorkUnit,
)
from oryxenai.agents.code_generator.core.generation_prompt_builder import build_instructions
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
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace, WorkspaceError
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository
from oryxenai.db.session import get_sessionmaker


class GenerationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


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

        run_id = UUID(str(payload["development_run_id"]))
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
            if run.resource_ledger:
                projections["resources/ledger.json"] = dict(run.resource_ledger)
            materialize_trusted_manifests(
                workspace,
                projections,
                plan,
                acquisition_ledger=run.resource_ledger,
                # Receipt local_paths are recorded relative to the configured
                # materials root (already prefixed with the run id).
                acquisition_materials_root=Path(
                    settings.code_generator_acquisition.materials_root
                ).resolve(),
            )
            dependency_repo = (
                Path(settings.code_generator_dependencies.workspaces_root).resolve()
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
        except (WorkspaceError, SourceValidationError, AcquisitionValidationError) as exc:
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
        for unit in units:
            existing_unit = _unit_projection(projection, unit)
            if existing_unit.status == "checkpointed" and existing_unit.checkpoint_after:
                continue
            if unit.kind == "integration":
                status = DevelopmentRunStatus.INTEGRATING.value
            elif unit.kind == "foundation":
                status = DevelopmentRunStatus.GENERATING_FOUNDATION.value
            else:
                status = DevelopmentRunStatus.GENERATING_ROUTES.value
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
    ) -> SourceCheckpoint:
        operation = _operation_for(unit)
        role_profile = _profile_for(operation, settings)
        unit_projection = _unit_projection(projection, unit)
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
            system, instructions, context_receipt = build_instructions(operation, context)
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
                if request_round >= int(settings.code_generator_generation.max_request_rounds):
                    raise GenerationError(
                        "GENERATION_REQUEST_ROUND_LIMIT",
                        "The generation request-round ceiling was reached.",
                    )
                unit_projection.status = "needs_resources"
                projection.request_rounds += 1
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
            shutil.rmtree(candidate)
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
        if old.exists():
            shutil.rmtree(old)
        os.replace(original, old)
        os.replace(candidate, original)
        installed = old / "node_modules"
        if installed.is_dir():
            os.replace(installed, original / "node_modules")
        shutil.rmtree(old, ignore_errors=True)

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
        # The cache key binds the prompt text (via the operation-prompt hash)
        # so a prompt change invalidates previously cached model calls.
        prompt_hash = str(
            (context_receipt.prompt_versions or {}).get("operation_hash", "")
        )
        key = hashlib.sha256(
            f"{generation_id}:{unit_id}:{operation}:{prompt_hash}:{context_receipt.context_hash}:{request_round}".encode()
        ).hexdigest()
        result_path = workspace.ledger_dir / "calls" / f"{key}.json"
        if result_path.is_file():
            result = GenerationResult.model_validate(
                json.loads(result_path.read_text(encoding="utf-8"))
            )
            return result, GenerationCallReceipt(
                receipt_id=f"call-{key[:20]}",
                operation_id=operation,
                idempotency_key=key,
                context_receipt_hash=context_receipt.context_hash,
                result_hash=digest(result.model_dump(mode="json")),
                profile=role_profile,
            )
        client = self._client(settings, role_profile)
        if client is None:
            raise GenerationError(
                "GENERATION_PROFILE_UNAVAILABLE",
                f"No usable model profile is configured for {operation}.",
            )
        raw = await client.generate_structured(
            operation=f"code_generator.{operation}",
            instructions=instructions,
            input_payload={**context, "context_receipt_hash": context_receipt.context_hash},
            output_model=GenerationResult,
            system_prompt=system,
            model_profile=role_profile,
            strict_schema=True,
        )
        parsed = getattr(raw, "parsed_output", raw)
        result = GenerationResult.model_validate(parsed)
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
        materials_root = Path(settings.code_generator_acquisition.materials_root).resolve() / str(
            run_id
        )
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
                    materialized = await adapter.materialize(
                        candidate, request, storage_root=materials_root, settings=settings
                    )
                    source_file = materials_root / materialized.local_path
                    local_name = f"{materialized.sha256}{Path(materialized.local_path).suffix}"
                    generated_path = workspace.materialize_acquired_file(source_file, local_name)
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
                    receipt = ResourceReceipt(
                        request_hash=request.request_hash,
                        disposition="admitted",
                        selected_candidate_id=candidate.candidate_id,
                        provider_key=candidate.provider_key,
                        canonical_source=candidate.canonical_source,
                        licence=candidate.licence,
                        attribution=candidate.attribution,
                        original_hash=materialized.sha256,
                        materialized_files=[
                            materialized.model_copy(
                                update={"local_path": generated_path, "inspection": inspection}
                            )
                        ],
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
            if len(shared_source) >= 24:
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
    return {
        "role_profile": role_profile,
        "operation": operation,
        "unit": unit.model_dump(mode="json"),
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
        "owned_paths": _owned_paths(unit, plan, projections),
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


def _owned_paths(
    unit: WorkUnit, plan: SitePlan, projections: dict[str, dict[str, Any]]
) -> list[str]:
    if unit.kind in {"route", "route_batch", "route_compose"}:
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
        return list(unit.owns_paths)
    if unit.kind == "foundation":
        return ["src/design/**", "src/components/shared/**"]
    if unit.kind == "integration":
        # The integrator reconciles the completed tree: every route path
        # plus the shared/design system it must keep coherent.
        return ["src/design/**", "src/components/shared/**", "src/routes/**"]
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


async def _cas(repo: Any, run: Any, status: str, values: dict[str, object]) -> Any:
    updated = await repo.compare_and_swap(
        run.id, expected_revision=run.revision, values={"status": status, **values}
    )
    if updated is None:
        raise GenerationError("RUN_REVISION_CONFLICT", "The generation run changed concurrently.")
    return updated


__all__ = ["CodeGeneratorGenerationOrchestrator", "GenerationError"]
