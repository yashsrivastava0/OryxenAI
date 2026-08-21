"""Durable standalone planning and acquisition jobs for Code Generator."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from oryxenai.agents.code_generator.core.acquisition_validators import (
    AcquisitionValidationError,
    filter_candidates_by_policy,
    select_candidate,
    validate_plan_delta,
    validate_resource_request,
)
from oryxenai.agents.code_generator.core.coordinator import advance_after
from oryxenai.agents.code_generator.core.creative_operation import (
    run_creative_direction_operation,
)
from oryxenai.agents.code_generator.core.dependency_manager import (
    DependencyManager,
    DependencyPolicyError,
    build_dependency_ledger,
)
from oryxenai.agents.code_generator.core.development_input import (
    DevelopmentInputAdapter,
    DevelopmentInputError,
)
from oryxenai.agents.code_generator.core.development_planner import (
    build_planner_context,
    canonical_json,
    context_hash,
    plan_summary,
)
from oryxenai.agents.code_generator.core.development_schemas import (
    AcquireCallReceipt,
    AcquisitionSummary,
    AdmittedInputReference,
    ContextReceipt,
    DependencyLedger,
    DependencyReceipt,
    DependencyReceiptBasis,
    DependencyRequest,
    DevelopmentRunStatus,
    PlanDelta,
    PlannerCallReceipt,
    RequestBasis,
    RequestOrigin,
    ResourceBinding,
    ResourceFallback,
    ResourceLedger,
    ResourcePlacement,
    ResourceQuery,
    ResourceReceipt,
    ResourceRequest,
    ResourceSourceConstraints,
    ResourceTechnicalConstraints,
    SafeIssue,
    SitePlan,
)
from oryxenai.agents.code_generator.core.planner_operation import run_planner_operation
from oryxenai.agents.code_generator.core.resource_adapters import (
    OfflineResourceProviderRegistry,
    ResourceProviderError,
    default_adapters,
)
from oryxenai.agents.code_generator.core.resource_scout import select_candidate_with_scout
from oryxenai.agents.code_generator.core.workspace import repository_root
from oryxenai.agents.shared.model_client import build_provider_client
from oryxenai.core.logging import get_logger
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository
from oryxenai.db.session import get_sessionmaker
from oryxenai.storage.artifacts import (
    ArtifactReference,
    ArtifactStorageError,
    create_artifact_store,
)

_KIND = "code_generator.plan"
logger = get_logger("oryxenai.jobs.handlers.code_generator")


def _planner_failure_issue(exc: Exception) -> SafeIssue:
    """Turn planner/provider failures into safe, actionable UI diagnostics."""
    code = str(getattr(exc, "code", "PLANNER_OUTPUT_INVALID") or "PLANNER_OUTPUT_INVALID")
    actions = {
        "PROVIDER_CONNECTION_ERROR": (
            "Check worker DNS, proxy/firewall access, and the configured planner endpoint, then retry."
        ),
        "PROVIDER_TIMEOUT_ERROR": (
            "Check worker network access or increase the configured planner timeout, then retry."
        ),
        "PROVIDER_AUTH_ERROR": (
            "Verify the planner API-key environment variable and provider account, then retry."
        ),
        "PROVIDER_RATE_LIMIT_ERROR": (
            "Wait for the provider rate-limit window to reset, then retry once."
        ),
        "PROVIDER_SERVER_ERROR": "Retry after the planner provider recovers.",
        "PROVIDER_INVALID_REQUEST_ERROR": (
            "Correct the configured planner request capabilities (thinking/effort/schema), "
            "run provider preflight again, then retry."
        ),
        "MODEL_CAPABILITY_UNSUPPORTED": (
            "Configure a planner profile that supports the required structured-output contract, then retry."
        ),
    }
    messages = {
        "PROVIDER_CONNECTION_ERROR": "The configured planner provider could not be reached before it produced a SitePlan.",
        "PROVIDER_TIMEOUT_ERROR": "The configured planner provider timed out before it produced a SitePlan.",
        "PROVIDER_AUTH_ERROR": "The configured planner provider rejected its API key before it produced a SitePlan.",
        "PROVIDER_RATE_LIMIT_ERROR": "The configured planner provider rate-limited the SitePlan request.",
        "PROVIDER_SERVER_ERROR": "The configured planner provider returned a server error before it produced a SitePlan.",
        "PROVIDER_INVALID_REQUEST_ERROR": "The configured planner provider rejected the planner request before producing a SitePlan.",
        "MODEL_CAPABILITY_UNSUPPORTED": "The configured planner profile does not support the required structured-output contract.",
    }
    raw_details = getattr(exc, "details", {})
    allowed = (str, int, float, bool)
    details = (
        {
            str(key): value
            for key, value in raw_details.items()
            if isinstance(key, str) and isinstance(value, allowed)
        }
        if isinstance(raw_details, dict)
        else {}
    )
    message = messages.get(code)
    if code in {"PROVIDER_INVALID_REQUEST_ERROR", "PLANNER_OUTPUT_INVALID"} and str(exc):
        message = f"{message} Detail: {str(exc)[:400]}"
    return SafeIssue(
        code=code,
        message=message
        or (str(exc)[:300] if str(exc) else "The planner could not produce a valid SitePlan."),
        next_action=actions.get(
            code,
            "Review the planner diagnostics and admitted pack projections, then retry after correcting the failure.",
        ),
        details=details,
    )


class CodeGeneratorPlanningHandler:
    kind = _KIND

    def __init__(self, planner_factory: Callable[[], Any] | None = None) -> None:
        self._planner_factory = planner_factory

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        del instance_id
        return await _execute(payload, planner_factory=self._planner_factory)


async def _execute(
    payload: dict[str, Any], *, planner_factory: Callable[[], Any] | None
) -> dict[str, Any]:
    from oryxenai.core.settings import get_settings

    run_id = UUID(str(payload.get("code_generator_run_id") or payload["development_run_id"]))
    settings = get_settings()
    sessionmaker = get_sessionmaker(settings)
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        run = await repo.get(run_id)
        if run is None:
            return {"status": "discarded", "run_id": str(run_id)}
        if run.status == DevelopmentRunStatus.PLANNED.value and run.planner_receipt and run.plan:
            return {"status": "succeeded", "run_id": str(run_id), "reused": True}
        if run.status == DevelopmentRunStatus.NEEDS_ATTENTION.value:
            return {"status": "needs_attention", "run_id": str(run_id), "reused": True}
        run = await _cas_status(
            repo,
            run,
            DevelopmentRunStatus.ADMITTING.value,
            values={"current_attempt": run.current_attempt + 1},
        )
        await repo.append_event(
            run_id,
            event_type="admitting",
            level="info",
            message="Verifying immutable pack input and v3 projections.",
        )
        await db.commit()
        reference = AdmittedInputReference.model_validate(run.input_reference)

    adapter = DevelopmentInputAdapter(settings)
    if reference.mode == "build_preparation_artifact":
        try:
            artifact = ArtifactReference.model_validate(run.artifact_reference)
            data = await create_artifact_store(settings).get_verified(artifact)
            reference = adapter.from_build_preparation_artifact(
                source_id=reference.source_id,
                filename=reference.original_filename,
                data=data,
            )
            async with sessionmaker() as db:
                repo = CodeGeneratorDevelopmentRepository(db)
                current = await repo.get(run_id)
                if current is None:
                    return {"status": "discarded", "run_id": str(run_id)}
                updated = await repo.compare_and_swap(
                    run_id,
                    expected_revision=current.revision,
                    values={
                        "input_reference": reference.model_dump(mode="json"),
                        "artifact_receipt": {
                            "artifact_sha256": artifact.sha256,
                            "size_bytes": artifact.size_bytes,
                            "stored_relative_path": reference.stored_relative_path,
                            "verified": True,
                        },
                    },
                )
                if updated is None:
                    raise RuntimeError("Code Generator run changed during artifact admission")
                await repo.append_event(
                    run_id,
                    event_type="artifact_downloaded",
                    level="info",
                    message="Build Preparation artifact downloaded and copied immutably.",
                    details={"sha256": artifact.sha256, "size_bytes": artifact.size_bytes},
                )
                await db.commit()
                run = updated
        except ArtifactStorageError as exc:
            attempt = int(payload.get("attempt", 1))
            max_attempts = int(payload.get("max_attempts", settings.worker_retry.max_attempts))
            if bool(exc.retryable) and attempt < max_attempts:
                return {
                    "status": "failed",
                    "error": {"code": exc.code, "message": exc.message, "retryable": True},
                }
            await _needs_attention(
                sessionmaker,
                run_id,
                SafeIssue(
                    code=exc.code,
                    message="The Build Preparation artifact could not be downloaded and verified.",
                    next_action="Restore artifact-store access or regenerate Build Preparation.",
                ),
            )
            return {"status": "needs_attention", "run_id": str(run_id)}
        except DevelopmentInputError as exc:
            await _needs_attention(
                sessionmaker,
                run_id,
                SafeIssue(
                    code=exc.code,
                    message=exc.message,
                    next_action="Regenerate a valid Build Preparation artifact.",
                    details=exc.details,
                ),
            )
            return {"status": "needs_attention", "run_id": str(run_id)}
    try:
        receipt, projections = adapter.admit(reference)
    except DevelopmentInputError as exc:
        await _needs_attention(
            sessionmaker,
            run_id,
            SafeIssue(
                code=exc.code,
                message=exc.message,
                next_action="Correct the pack and start a new run.",
                details=exc.details,
            ),
        )
        return {"status": "needs_attention", "run_id": str(run_id)}

    context = build_planner_context(projections, receipt.model_dump(mode="json"))
    context_digest = context_hash(context)
    context_path = _write_context(settings, receipt.admitted_identity, context_digest, context)
    context_receipt = ContextReceipt(
        receipt_id=f"context-{context_digest[:20]}",
        context_hash=context_digest,
        stored_relative_path=context_path,
        route_ids=receipt.route_ids,
        section_count=sum(
            len(pack.get("sections", []))
            for pack in projections["site/contract.json"].get("public_content", [])
            if isinstance(pack, dict)
        ),
        resource_slot_count=len(projections["resources/projection.json"].get("resource_needs", [])),
    )
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        run = await repo.get(run_id)
        if run is None:
            return {"status": "discarded", "run_id": str(run_id)}
        if run.planner_receipt and run.plan:
            return {"status": "succeeded", "run_id": str(run_id), "reused": True}
        run = await _cas_status(
            repo,
            run,
            DevelopmentRunStatus.PLANNING.value,
            values={
                "input_receipt": receipt.model_dump(mode="json"),
                "admitted_identity": receipt.admitted_identity,
                "context_receipt": context_receipt.model_dump(mode="json"),
            },
        )
        await repo.append_event(
            run_id,
            event_type="admitted",
            level="info",
            message=f"Pack {receipt.pack_version} admitted; immutable planner context written.",
            details={"route_count": len(receipt.route_ids)},
        )
        await db.commit()

    profile = settings.models.get_profile(settings.code_generator_development.planner_profile)
    if (
        profile is None
        or profile.capabilities is None
        or not profile.capabilities.json_schema_mode
        or profile.capabilities.structured_output_mode != "native_json_schema"
    ):
        await _needs_attention(
            sessionmaker,
            run_id,
            SafeIssue(
                code="PLANNER_STRICT_SCHEMA_UNSUPPORTED",
                message="The configured planner profile does not declare native JSON-schema support.",
                next_action=(
                    "Configure code_generator_planner with native_json_schema support before retrying."
                ),
            ),
        )
        return {"status": "needs_attention", "run_id": str(run_id)}
    planner = planner_factory() if planner_factory is not None else _build_planner(settings)
    if planner is None:
        await _needs_attention(
            sessionmaker,
            run_id,
            SafeIssue(
                code="PLANNER_PROFILE_UNAVAILABLE",
                message="The configured planner profile has no usable provider credential.",
                next_action="Configure the planner profile and its indirect API-key environment variable.",
            ),
        )
        return {"status": "needs_attention", "run_id": str(run_id)}
    # V4 development runs use the same creative/planning contract as
    # production sessions.  Legacy v3 fixtures remain readable without being
    # forced through the new provider schema.
    require_blueprint = str(getattr(run, "run_mode", "development")) == "session" or str(
        receipt.pack_version
    ).endswith("-v4")
    if require_blueprint:
        director_profile = settings.code_generator_development.director_profile
        director_capabilities = settings.models.get_profile(director_profile)
        if (
            director_capabilities is None
            or director_capabilities.capabilities is None
            or not director_capabilities.capabilities.json_schema_mode
            or director_capabilities.capabilities.structured_output_mode != "native_json_schema"
        ):
            await _needs_attention(
                sessionmaker,
                run_id,
                SafeIssue(
                    code="DIRECTOR_STRICT_SCHEMA_UNSUPPORTED",
                    message=(
                        "The configured creative-director profile does not declare native "
                        "JSON-schema support."
                    ),
                    next_action="Configure a strict-schema director profile and retry.",
                ),
            )
            return {"status": "needs_attention", "run_id": str(run_id)}
        director = (
            planner_factory()
            if planner_factory is not None
            else build_provider_client(director_profile, settings.models)
        )
        if director is None:
            await _needs_attention(
                sessionmaker,
                run_id,
                SafeIssue(
                    code="DIRECTOR_PROFILE_UNAVAILABLE",
                    message="The configured creative-director profile is unavailable.",
                    next_action="Configure the director profile and retry the session run.",
                ),
            )
            return {"status": "needs_attention", "run_id": str(run_id)}
        try:
            direction_context = {**context, "role_profile": director_profile}
            direction, direction_receipt, direction_result = await run_creative_direction_operation(
                director,
                context=direction_context,
                profile_name=director_profile,
                output_version="v3" if str(receipt.pack_version).endswith("-v4") else "v2",
            )
        except Exception as exc:
            await _needs_attention(sessionmaker, run_id, _planner_failure_issue(exc))
            return {"status": "needs_attention", "run_id": str(run_id)}
        direction_path = _write_context(
            settings,
            receipt.admitted_identity,
            direction_receipt.context_hash,
            direction_context,
        )
        direction_receipt = direction_receipt.model_copy(
            update={"stored_relative_path": direction_path}
        )
        context = {**context, "creative_direction": direction.model_dump(mode="json")}
        context_digest = context_hash(context)
        context_path = _write_context(settings, receipt.admitted_identity, context_digest, context)
        context_receipt = ContextReceipt(
            receipt_id=f"context-{context_digest[:20]}",
            context_hash=context_digest,
            stored_relative_path=context_path,
            route_ids=receipt.route_ids,
            section_count=context_receipt.section_count,
            resource_slot_count=context_receipt.resource_slot_count,
        )
        async with sessionmaker() as db:
            repo = CodeGeneratorDevelopmentRepository(db)
            current = await repo.get(run_id)
            if current is None:
                return {"status": "discarded", "run_id": str(run_id)}
            updated = await repo.compare_and_swap(
                run_id,
                expected_revision=current.revision,
                values={
                    "creative_direction": {
                        "direction": direction.model_dump(mode="json"),
                        "context_receipt": direction_receipt.model_dump(mode="json"),
                        "response_id": str(getattr(direction_result, "response_id", "") or ""),
                    },
                    "context_receipt": context_receipt.model_dump(mode="json"),
                },
            )
            if updated is None:
                raise RuntimeError("Code Generator run changed after creative direction")
            await repo.append_event(
                run_id,
                event_type="creative_direction_ready",
                level="info",
                message="Two grounded creative concepts were evaluated before planning.",
                details={"recommended_concept_id": direction.recommended_concept_id},
            )
            await db.commit()
            run = updated
    try:
        plan, _prompt_version, prompt_receipt, result = await run_planner_operation(
            planner,
            context=context,
            profile_name=settings.code_generator_development.planner_profile,
            projections=projections,
            max_work_units=int(settings.code_generator_development.max_work_units),
            max_sections_per_unit=int(settings.code_generator_generation.max_route_batch_sections),
            require_blueprint=require_blueprint,
        )
    except Exception as exc:
        await _needs_attention(sessionmaker, run_id, _planner_failure_issue(exc))
        return {"status": "needs_attention", "run_id": str(run_id)}

    plan_digest = hashlib.sha256(canonical_json(plan.model_dump(mode="json"))).hexdigest()
    usage = {
        str(key): int(value)
        for key, value in dict(getattr(result, "usage", {}) or {}).items()
        if isinstance(value, int)
    }
    planner_receipt = PlannerCallReceipt(
        receipt_id=f"planner-{plan_digest[:20]}",
        context_hash=context_digest,
        plan_hash=plan_digest,
        profile=settings.code_generator_development.planner_profile,
        response_id=str(getattr(result, "response_id", "") or ""),
        model=str(getattr(result, "model", "") or ""),
        usage=usage,
        finish_reason=str(getattr(result, "finish_reason", "") or ""),
        prompt_receipt=prompt_receipt.model_dump(mode="json"),
    )
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        run = await repo.get(run_id)
        if run is None:
            return {"status": "discarded", "run_id": str(run_id)}
        if run.planner_receipt and run.plan:
            return {"status": "succeeded", "run_id": str(run_id), "reused": True}
        await _cas_status(
            repo,
            run,
            DevelopmentRunStatus.PLANNED.value,
            values={
                "planner_receipt": planner_receipt.model_dump(mode="json"),
                "plan": plan.model_dump(mode="json"),
                "plan_summary": plan_summary(plan),
                "issues": [],
            },
        )
        await repo.append_event(
            run_id,
            event_type="planned",
            level="info",
            message="Validated SitePlan and WorkGraph accepted.",
            details={
                "route_count": len(plan.routes),
                "work_unit_count": len(plan.work_graph.units),
            },
        )
        await db.commit()
    await advance_after(sessionmaker, run_id, completed_stage="planned")
    return {"status": "succeeded", "run_id": str(run_id)}


class CodeGeneratorAcquisitionHandler:
    """Durable initial resource/dependency acquisition for a planned run."""

    kind = "code_generator.acquire"

    def __init__(
        self,
        selector_factory: Callable[[], Any] | None = None,
        adapter_factory: Callable[[Any], dict[str, Any]] | None = None,
        dependency_manager_factory: Callable[[list[ResourceReceipt]], DependencyManager]
        | None = None,
    ) -> None:
        self._selector_factory = selector_factory
        self._adapter_factory = adapter_factory
        self._dependency_manager_factory = dependency_manager_factory

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        del instance_id
        return await _execute_acquisition(
            payload,
            selector_factory=self._selector_factory,
            adapter_factory=self._adapter_factory,
            dependency_manager_factory=self._dependency_manager_factory,
        )


async def _execute_acquisition(
    payload: dict[str, Any],
    *,
    selector_factory: Callable[[], Any] | None,
    adapter_factory: Callable[[Any], dict[str, Any]] | None,
    dependency_manager_factory: Callable[[list[ResourceReceipt]], DependencyManager] | None,
) -> dict[str, Any]:
    from oryxenai.core.settings import get_settings

    run_id = UUID(str(payload.get("code_generator_run_id") or payload["development_run_id"]))
    settings = get_settings()
    sessionmaker = get_sessionmaker(settings)
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        run = await repo.get(run_id)
        if run is None:
            return {"status": "discarded", "run_id": str(run_id)}
        if (
            run.status == DevelopmentRunStatus.ACQUIRED.value
            and run.acquire_receipt
            and run.resource_ledger
            and run.dependency_ledger
        ):
            return {"status": "succeeded", "run_id": str(run_id), "reused": True}
        if run.status == DevelopmentRunStatus.NEEDS_ATTENTION.value and run.acquire_receipt:
            return {"status": "needs_attention", "run_id": str(run_id), "reused": True}
        # A needs_attention run without an acquire receipt is a failed
        # acquisition: retryable, mirroring the generate/verify handlers.
        acquire_retry = (
            run.status == DevelopmentRunStatus.NEEDS_ATTENTION.value and not run.acquire_receipt
        )
        if (
            run.status
            not in {
                DevelopmentRunStatus.PLANNED.value,
                DevelopmentRunStatus.ACQUIRING.value,
            }
            and not acquire_retry
        ):
            return {"status": "discarded", "run_id": str(run_id)}
        run = await _cas_status(
            repo,
            run,
            DevelopmentRunStatus.ACQUIRING.value,
            values={"current_attempt": run.current_attempt + 1},
        )
        await repo.append_event(
            run_id,
            event_type="acquiring",
            level="info",
            message="Resolving initial resource gaps and trusted dependencies.",
        )
        await db.commit()

    reference = AdmittedInputReference.model_validate(run.input_reference)
    input_adapter = DevelopmentInputAdapter(settings)
    partial_resource_ledger: ResourceLedger | None = None
    partial_dependency_ledger: DependencyLedger | None = None
    try:
        input_receipt, projections = input_adapter.admit(reference)
        plan = SitePlan.model_validate(run.plan)
        plan_hash = str((run.planner_receipt or {}).get("plan_hash", ""))
        requests = _build_initial_requests(
            plan, projections, input_receipt.admitted_identity, plan_hash
        )
        existing_resource_receipts: list[ResourceReceipt] = []
        if run.resource_ledger:
            existing_resource_receipts = [
                ResourceReceipt.model_validate(item)
                for item in run.resource_ledger.get("receipts", [])
            ]
        resource_receipts = list(existing_resource_receipts)
        bindings: list[ResourceBinding] = []
        plan_deltas: list[PlanDelta] = []
        dependency_receipts = [
            *(
                DependencyLedger.model_validate(run.dependency_ledger).receipts
                if run.dependency_ledger
                else []
            )
        ]
        adapters = (
            adapter_factory(settings)
            if adapter_factory is not None
            else _default_adapter_factory(settings)
        )
        configured_materials_root = Path(settings.code_generator_acquisition.materials_root)
        materials_root = (
            configured_materials_root
            if configured_materials_root.is_absolute()
            else (repository_root() / configured_materials_root).resolve()
        )
        run_material_root = materials_root / str(run_id)
        configured_workspace_root = Path(settings.code_generator_dependencies.workspaces_root)
        workspace_root = (
            configured_workspace_root
            if configured_workspace_root.is_absolute()
            else (repository_root() / configured_workspace_root).resolve()
        )
        repo_dir = workspace_root / str(run_id) / "repo"
        _seed_dependency_workspace(settings, repo_dir)
        prior_manifest = _read_json(repo_dir / "package.json", {})
        prior_lock = _read_json(repo_dir / "package-lock.json", {})
        dependency_manager = (
            dependency_manager_factory(resource_receipts)
            if dependency_manager_factory is not None
            else DependencyManager(
                resource_receipts,
                authorized_hashes={
                    _execution_binding_hash(slot_id, package_name)
                    for slot_id, package_name, _exports, _required, _fallback in (
                        _execution_package_bindings(projections)
                    )
                },
            )
        )
        selector = selector_factory() if selector_factory is not None else None
        scout: Any = None
        if selector is None and settings.code_generator_acquisition.prefer_resource_scout_model:
            scout = build_provider_client("code_generator_resource_scout", settings.models)
        for request in requests:
            existing = next(
                (
                    receipt
                    for receipt in resource_receipts
                    if receipt.request_hash == request.request_hash
                ),
                None,
            )
            if existing is not None:
                bindings.append(_binding_for(request, existing))
                continue
            validate_resource_request(
                request,
                plan=plan,
                ledger_excluding=ResourceLedger(
                    based_on_input_and_plan={
                        "input_receipt_hash": input_receipt.admitted_identity,
                        "site_plan_hash": plan_hash,
                    },
                    receipts=resource_receipts,
                ),
                settings=settings,
                projections=projections,
            )
            adapter = adapters.get(request.category)
            if adapter is None:
                raise AcquisitionValidationError(
                    "CATEGORY_UNSUPPORTED", f"No trusted adapter exists for {request.category}."
                )
            try:
                candidates = await adapter.search(request, settings=settings)
                filtered = filter_candidates_by_policy(candidates, request)
                if not filtered:
                    if request.requiredness == "required" and request.fallback.kind == "none":
                        rejected = _rejected_receipt(
                            request, "No policy-approved candidate exists."
                        )
                        resource_receipts.append(rejected)
                        partial_resource_ledger = ResourceLedger(
                            based_on_input_and_plan={
                                "input_receipt_hash": input_receipt.admitted_identity,
                                "site_plan_hash": plan_hash,
                            },
                            requests=requests,
                            receipts=resource_receipts,
                            active_bindings=bindings,
                        )
                        raise AcquisitionValidationError(
                            "REQ_FALLBACK_BLOCKED",
                            "The required resource has no honest fallback.",
                        )
                    receipt = _fallback_receipt(request, "No policy-approved candidate exists.")
                    resource_receipts.append(receipt)
                    bindings.append(_binding_for(request, receipt))
                    continue
                if selector is not None:
                    selected_id, _ = select_candidate(
                        request,
                        filtered,
                        prefer_model=True,
                        model_callable=selector,
                    )
                elif scout is not None:
                    selected_id, _ = await select_candidate_with_scout(scout, request, filtered)
                else:
                    selected_id, _ = select_candidate(request, filtered)
                candidate = next(item for item in filtered if item.candidate_id == selected_id)
                materialized = await adapter.materialize(
                    candidate,
                    request,
                    storage_root=run_material_root,
                    settings=settings,
                )
                materialized = _prefix_materialized_file(materialized, str(run_id))
                receipt = ResourceReceipt(
                    request_hash=request.request_hash,
                    disposition="admitted",
                    selected_candidate_id=candidate.candidate_id,
                    provider_key=candidate.provider_key,
                    canonical_source=candidate.canonical_source,
                    licence=candidate.licence,
                    attribution=candidate.attribution,
                    original_hash=materialized.sha256,
                    materialized_files=[materialized],
                    dependencies=sorted(candidate.dependency_metadata),
                    satisfied_placements=[request.placement.purpose],
                    acquired_at=datetime.now(UTC).isoformat(),
                )
                resource_receipts.append(receipt)
                bindings.append(_binding_for(request, receipt))
                if receipt.dependencies:
                    for package_name in receipt.dependencies:
                        dep_request = DependencyRequest(
                            request_id=f"dep-{request.request_hash[:16]}-{package_name}",
                            requesting_resource_receipt_hash=receipt.request_hash,
                            package_name=package_name,
                            required_api_or_exports=list(
                                candidate.dependency_metadata.get(package_name, [])
                            ),
                            compatibility_constraints="configured target runtime",
                            reason_existing_stack_is_insufficient="The admitted component declares this API.",
                            fallback_component_strategy="vendor source without the package or use simple_dom",
                        )
                        dep_receipt = await dependency_manager.resolve(
                            dep_request,
                            repo_dir=repo_dir,
                            prior_manifest=prior_manifest,
                            prior_lock=prior_lock,
                            settings=settings,
                        )
                        dependency_receipts.append(dep_receipt)
                        if dep_receipt.decision == "admitted":
                            prior_manifest = _read_json(repo_dir / "package.json", prior_manifest)
                            prior_lock = _read_json(repo_dir / "package-lock.json", prior_lock)
            except ResourceProviderError as exc:
                if request.requiredness == "required" and request.fallback.kind == "none":
                    rejected = _rejected_receipt(request, str(exc))
                    resource_receipts.append(rejected)
                    partial_resource_ledger = ResourceLedger(
                        based_on_input_and_plan={
                            "input_receipt_hash": input_receipt.admitted_identity,
                            "site_plan_hash": plan_hash,
                        },
                        requests=requests,
                        receipts=resource_receipts,
                        active_bindings=bindings,
                    )
                    raise AcquisitionValidationError(
                        "REQ_REQUIRED_PROVIDER_UNAVAILABLE",
                        "The required resource provider is unavailable and no fallback exists.",
                    ) from exc
                receipt = _fallback_receipt(request, str(exc))
                resource_receipts.append(receipt)
                bindings.append(_binding_for(request, receipt))

        # Admitted execution-contract package bindings go through the same
        # trusted dependency manager as receipt-bound requests: real npm
        # lockfile + offline install, never a hand-written manifest entry.
        for (
            slot_id,
            package_name,
            expected_exports,
            required,
            fallback_strategy,
        ) in _execution_package_bindings(projections):
            if any(
                item.package_name == package_name and item.decision in {"admitted", "existing"}
                for item in dependency_receipts
            ):
                continue
            binding_request = DependencyRequest(
                request_id=f"dep-execution-{package_name}",
                requesting_resource_receipt_hash=_execution_binding_hash(slot_id, package_name),
                package_name=package_name,
                required_api_or_exports=list(expected_exports),
                compatibility_constraints="configured target runtime",
                reason_existing_stack_is_insufficient=(
                    "The admitted execution contract binds this package to a declared slot."
                ),
                fallback_component_strategy="Use the plain DOM affordance without the bound package.",
            )
            try:
                dependency_receipt = await dependency_manager.resolve(
                    binding_request,
                    repo_dir=repo_dir,
                    prior_manifest=prior_manifest,
                    prior_lock=prior_lock,
                    settings=settings,
                )
            except DependencyPolicyError as exc:
                if required:
                    raise
                dependency_receipt = DependencyReceipt(
                    based_on=DependencyReceiptBasis(
                        toolchain_profile="react-vite-v1",
                        prior_manifest_hash=_model_hash(prior_manifest),
                        prior_lock_hash=_model_hash(prior_lock),
                        resource_receipt_hash=binding_request.requesting_resource_receipt_hash,
                    ),
                    decision="rejected_fallback",
                    package_name=package_name,
                    licence_result="install_unavailable",
                    vulnerability_policy_result="not_evaluated",
                    install_script_result="not_run",
                    manifest_hash=_model_hash(prior_manifest),
                    lock_hash=_model_hash(prior_lock),
                    fallback={
                        "strategy": fallback_strategy or "Use the plain DOM affordance.",
                        "reason_code": exc.code,
                    },
                )
            dependency_receipts.append(dependency_receipt)
            prior_manifest = _read_json(repo_dir / "package.json", prior_manifest)
            prior_lock = _read_json(repo_dir / "package-lock.json", prior_lock)

        for binding in bindings:
            delta = PlanDelta(
                delta_id=f"delta-{binding.binding_id}",
                based_on_plan_hash=plan_hash,
                binding_changes=[binding],
            )
            validate_plan_delta(delta, plan=plan)
            plan_deltas.append(delta)
        resource_ledger = ResourceLedger(
            based_on_input_and_plan={
                "input_receipt_hash": input_receipt.admitted_identity,
                "site_plan_hash": plan_hash,
            },
            requests=requests,
            receipts=resource_receipts,
            active_bindings=bindings,
            plan_deltas=plan_deltas,
        )
        resource_ledger.ledger_hash = _model_hash(
            resource_ledger.model_dump(mode="json", exclude={"ledger_hash"})
        )
        dependency_ledger = build_dependency_ledger(dependency_receipts)
        partial_resource_ledger = resource_ledger
        partial_dependency_ledger = dependency_ledger
        admitted_count = sum(item.disposition == "admitted" for item in resource_receipts)
        fallback_count = sum(item.disposition == "fallback" for item in resource_receipts)
        rejected_count = sum(item.disposition == "rejected" for item in resource_receipts)
        dependency_decisions: dict[str, str] = {
            item.package_name: item.decision for item in dependency_receipts if item.package_name
        }
        node_modules_recreated = (
            any(item.decision == "admitted" for item in dependency_receipts)
            and (repo_dir / "node_modules").is_dir()
        )
        attempt_hash = _model_hash(
            {
                "plan_hash": plan_hash,
                "request_hashes": sorted(item.request_hash for item in requests),
            }
        )
        acquire_receipt = AcquireCallReceipt(
            receipt_id=f"acquire-{attempt_hash[:20]}",
            attempt_hash=attempt_hash,
            profile=(
                "code_generator_resource_scout"
                if (selector is not None or scout is not None)
                else ""
            ),
            total_request_count=len(requests),
            admitted_count=admitted_count,
            fallback_count=fallback_count,
            rejected_count=rejected_count,
            request_rounds=1 if requests else 0,
            plan_deltas=plan_deltas,
        )
        summary = AcquisitionSummary(
            request_count=len(requests),
            admitted_resource_count=admitted_count,
            fallback_resource_count=fallback_count,
            rejected_resource_count=rejected_count,
            dependency_decisions=dependency_decisions,
            node_modules_recreated=node_modules_recreated,
            ledger_hash=resource_ledger.ledger_hash,
            dependency_ledger_hash=dependency_ledger.dependency_ledger_hash,
            attempts=run.current_attempt,
        )
    except Exception as exc:
        logger.warning(
            "code_generator acquisition failed code=%s type=%s",
            getattr(exc, "code", "ACQUISITION_FAILED"),
            type(exc).__name__,
        )
        issue = SafeIssue(
            code=getattr(exc, "code", "ACQUISITION_FAILED"),
            message=getattr(exc, "message", "Resource acquisition could not complete safely."),
            next_action=(
                "Add a suitable resource to the pack or relax the request, then retry acquire."
                if getattr(exc, "code", "") == "REQ_FALLBACK_BLOCKED"
                else "Review the safe acquisition issue and start a corrected run."
            ),
        )
        values: dict[str, object] = {"issues": [issue.model_dump(mode="json")]}
        if partial_resource_ledger is not None:
            values["resource_ledger"] = partial_resource_ledger.model_dump(mode="json")
            values["acquire_summary"] = AcquisitionSummary(
                request_count=len(partial_resource_ledger.requests),
                admitted_resource_count=sum(
                    item.disposition == "admitted" for item in partial_resource_ledger.receipts
                ),
                fallback_resource_count=sum(
                    item.disposition == "fallback" for item in partial_resource_ledger.receipts
                ),
                rejected_resource_count=sum(
                    item.disposition == "rejected" for item in partial_resource_ledger.receipts
                ),
                ledger_hash="",
                attempts=run.current_attempt,
            ).model_dump(mode="json")
        if partial_dependency_ledger is not None:
            values["dependency_ledger"] = partial_dependency_ledger.model_dump(mode="json")
        await _needs_attention(sessionmaker, run_id, issue, values=values)
        return {"status": "needs_attention", "run_id": str(run_id)}

    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        current = await repo.get(run_id)
        if current is None:
            return {"status": "discarded", "run_id": str(run_id)}
        if current.status == DevelopmentRunStatus.ACQUIRED.value and current.acquire_receipt:
            return {"status": "succeeded", "run_id": str(run_id), "reused": True}
        await _cas_status(
            repo,
            current,
            DevelopmentRunStatus.ACQUIRED.value,
            values={
                "acquire_receipt": acquire_receipt.model_dump(mode="json"),
                "resource_ledger": resource_ledger.model_dump(mode="json"),
                "dependency_ledger": dependency_ledger.model_dump(mode="json"),
                "acquire_summary": summary.model_dump(mode="json"),
                "plan_delta_count": len(plan_deltas),
                "issues": [],
            },
        )
        await repo.append_event(
            run_id,
            event_type="acquired",
            level="info",
            message="Initial resource and dependency acquisition completed.",
            details={
                "admitted_count": admitted_count,
                "fallback_count": fallback_count,
                "rejected_count": rejected_count,
                "node_modules_recreated": node_modules_recreated,
            },
        )
        await db.commit()
    await advance_after(sessionmaker, run_id, completed_stage="acquired")
    return {"status": "succeeded", "run_id": str(run_id)}


def _seed_dependency_workspace(settings: Any, repo_dir: Path) -> None:
    """Seed dependency resolution from the scaffold's committed manifest and
    lockfile.

    The dependency workspace is the merge base for every admitted binding.
    Starting it empty would let a single resolved package produce a minimal
    manifest+lock that — when synchronized back into the generation repo —
    REPLACES the scaffold's toolchain instead of extending it.
    """

    if (repo_dir / "package.json").is_file():
        return
    from oryxenai.agents.code_generator.core.workspace import repository_root

    config = settings.code_generator_generation
    scaffold_root = Path(str(config.scaffold_root))
    if not scaffold_root.is_absolute():
        scaffold_root = repository_root() / scaffold_root
    profile = str(getattr(config, "scaffold_profile", "") or "react-vite-v1")
    manifest = scaffold_root / profile / "package.json"
    lock = scaffold_root / profile / "package-lock.json"
    if not manifest.is_file() or not lock.is_file():
        raise AcquisitionValidationError(
            "SCAFFOLD_MANIFEST_UNAVAILABLE",
            "The scaffold manifest/lockfile required to seed dependency resolution is missing.",
        )
    repo_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(manifest, repo_dir / "package.json")
    shutil.copyfile(lock, repo_dir / "package-lock.json")


def _execution_resolved_slot_ids(projections: dict[str, dict[str, Any]]) -> set[str]:
    execution = projections.get("execution/contract.json", {})
    slots = execution.get("slots", []) if isinstance(execution, dict) else []
    return {
        str(slot.get("resource_slot_id", ""))
        for slot in slots
        if isinstance(slot, dict)
        and str(slot.get("resource_slot_id", ""))
        and _resolution_type(slot) not in {"delegated_acquisition", "execution_gap"}
    }


def _resolution_type(slot: dict[str, Any]) -> str:
    resolution = slot.get("resolution")
    return str(resolution.get("resolution_type", "")) if isinstance(resolution, dict) else ""


def _execution_package_bindings(
    projections: dict[str, dict[str, Any]],
) -> list[tuple[str, str, list[str], bool, str]]:
    """Admitted target-package bindings and their required/fallback policy."""

    execution = projections.get("execution/contract.json", {})
    slots = execution.get("slots", []) if isinstance(execution, dict) else []
    bindings: list[tuple[str, str, list[str], bool, str]] = []
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        resolution = slot.get("resolution", {})
        if (
            not isinstance(resolution, dict)
            or str(resolution.get("resolution_type", "")) != "target_package_binding"
        ):
            continue
        package_name = str(resolution.get("package_name", ""))
        if not package_name:
            continue
        exports = [str(value) for value in resolution.get("expected_exports", []) or []]
        bindings.append(
            (
                str(slot.get("resource_slot_id", "")),
                package_name,
                exports,
                bool(slot.get("required")),
                str(resolution.get("fallback_disposition", "")),
            )
        )
    return bindings


def _execution_binding_hash(slot_id: str, package_name: str) -> str:
    return _model_hash({"execution_slot": slot_id, "package": package_name})


def _build_initial_requests(
    plan: SitePlan, projections: dict[str, dict[str, Any]], input_hash: str, plan_hash: str
) -> list[ResourceRequest]:
    resources = projections.get("resources/projection.json", {}).get("resources", [])
    needs = projections.get("resources/projection.json", {}).get("resource_needs", [])
    visual_projection = projections.get("design/visual-direction.json", {})
    visual_global = (
        visual_projection.get("global", {}) if isinstance(visual_projection, dict) else {}
    )
    visual_language = (
        visual_global.get("visual_language", {}) if isinstance(visual_global, dict) else {}
    )
    image_style = " ".join(
        str(visual_language.get(key, "") or "")
        for key in ("creative_thesis", "color_behavior", "typography")
    ).strip()
    # v3 packs resolve every declared execution slot deterministically at
    # admission (local recipe / local materialized file / target package
    # binding). Emergent acquisition exists only for planner slots the pack
    # does NOT already resolve (D-018); re-acquiring resolved slots would
    # both duplicate bindings and risk stock substitutions for evidence.
    resolved_slot_ids = _execution_resolved_slot_ids(projections)
    requests: list[ResourceRequest] = _build_delegated_requests(
        plan, projections, input_hash, plan_hash
    )
    for slot in plan.resource_slots:
        if slot.slot_id in resolved_slot_ids:
            continue
        matched = any(
            isinstance(resource, dict)
            and str(resource.get("route_id", "")) == slot.route_id
            and (
                not resource.get("purpose")
                or str(resource.get("purpose", "")).casefold() in slot.purpose.casefold()
                or slot.purpose.casefold() in str(resource.get("purpose", "")).casefold()
            )
            for resource in resources
        )
        if matched:
            continue
        matching_need = next(
            (
                need
                for need in needs
                if isinstance(need, dict)
                and slot.route_id in [str(item) for item in need.get("route_ids", [])]
                and _words_overlap(slot.purpose, str(need.get("purpose", "")))
            ),
            {},
        )
        category = _infer_category(slot.purpose, matching_need)
        work_unit_id = next(
            (
                unit.unit_id
                for unit in plan.work_graph.units
                if unit.kind in {"route", "route_batch"} and unit.route_id == slot.route_id
            ),
            "foundation",
        )
        required = bool(matching_need.get("required_for_handoff", False))
        fallback = _fallback_for(category, required)
        allowed = _allowed_sources(category)
        request = ResourceRequest(
            request_id=f"request-{slot.slot_id}",
            based_on=RequestBasis(input_receipt_hash=input_hash, site_plan_hash=plan_hash),
            origin=RequestOrigin(work_unit_id=work_unit_id),
            category=category,  # type: ignore[arg-type]
            placement=ResourcePlacement(
                route_id=slot.route_id,
                purpose=slot.purpose,
            ),
            why_existing_is_insufficient="The admitted pack has no suitable resource binding for this slot.",
            query=ResourceQuery(
                positive_terms=list(re_split_words(slot.purpose)),
                negative_terms=[],
                forbidden_subjects=[],
                style_mood=image_style[:240]
                if category in {"image", "texture", "illustration"}
                else "",
                theme_colors=(
                    [str(visual_language.get("color_behavior", ""))[:120]]
                    if category in {"image", "texture", "illustration"}
                    and visual_language.get("color_behavior")
                    else []
                ),
                orientation=(
                    "landscape"
                    if category in {"image", "texture", "illustration"}
                    and any(
                        token in slot.purpose.casefold() for token in ("hero", "banner", "showcase")
                    )
                    else ""
                ),
            ),
            technical_constraints=ResourceTechnicalConstraints(
                media_types=[], max_bytes=_max_bytes_for(category)
            ),
            source_constraints=ResourceSourceConstraints(
                allowed_source_kinds=allowed,
                upstream_source_policy=str(matching_need.get("source_policy", "")),
            ),
            requiredness="required" if required else "preferred",
            fallback=ResourceFallback.model_validate(
                {"kind": fallback, "implementation": _fallback_text(category)}
            ),
            affected_work_unit_ids=[work_unit_id],
        )
        requests.append(request)
    return requests


def _build_delegated_requests(
    plan: SitePlan,
    projections: dict[str, dict[str, Any]],
    input_hash: str,
    plan_hash: str,
) -> list[ResourceRequest]:
    """Translate v4 delegated slots into deterministic provider-bound requests."""

    execution = projections.get("execution/contract.json", {})
    policy = execution.get("policy", {}).get("delegated_acquisition", {})
    if not isinstance(policy, dict) or not policy.get("enabled"):
        return []
    providers = [str(value) for value in policy.get("allowed_providers", []) if str(value)]
    requests: list[ResourceRequest] = []
    for slot in execution.get("slots", []) if isinstance(execution, dict) else []:
        if not isinstance(slot, dict):
            continue
        resolution = slot.get("resolution")
        if (
            not isinstance(resolution, dict)
            or resolution.get("resolution_type") != "delegated_acquisition"
        ):
            continue
        raw_category = str(slot.get("category", "")).casefold()
        category = {
            "photo": "image",
            "editorial_photo": "image",
            "visual_component": "component_source",
            "component": "component_source",
            "typography_system": "font",
        }.get(raw_category, raw_category)
        if category not in {"image", "font", "component_source"}:
            continue
        route_id = str(slot.get("route_id", ""))
        section_ids = [str(value) for value in slot.get("section_ids", []) if str(value)]
        unit_id = next(
            (
                unit.unit_id
                for unit in plan.work_graph.units
                if unit.kind in {"route", "route_batch"} and unit.route_id == route_id
            ),
            "foundation",
        )
        purpose = str(slot.get("rationale", "") or slot.get("component_placement", ""))
        required = bool(slot.get("required"))
        fallback = _fallback_for(category, required)
        requests.append(
            ResourceRequest(
                request_id=f"delegated-{slot.get('resource_slot_id', '')}",
                based_on=RequestBasis(input_receipt_hash=input_hash, site_plan_hash=plan_hash),
                origin=RequestOrigin(work_unit_id=unit_id, origin_kind="initial_gap"),
                category=category,  # type: ignore[arg-type]
                placement=ResourcePlacement(
                    route_id=route_id,
                    section_id=section_ids[0] if section_ids else "",
                    purpose=purpose,
                ),
                why_existing_is_insufficient=(
                    "Build Preparation completed the configured upstream attempts; this v4 slot explicitly delegates the role."
                ),
                query=ResourceQuery(positive_terms=list(re_split_words(purpose))),
                technical_constraints=ResourceTechnicalConstraints(
                    max_bytes=_max_bytes_for(category),
                    required_exports=[
                        str(value) for value in resolution.get("expected_exports", []) if str(value)
                    ],
                ),
                source_constraints=ResourceSourceConstraints(
                    allowed_source_kinds=providers,
                    upstream_source_policy="explicit_delegation_after_upstream_attempts",
                ),
                requiredness="required" if required else "preferred",
                fallback=ResourceFallback.model_validate(
                    {"kind": fallback, "implementation": _fallback_text(category)}
                ),
                affected_work_unit_ids=[unit_id],
            )
        )
    return requests


def _infer_category(purpose: str, need: dict[str, Any]) -> str:
    value = f"{purpose} {need.get('category', '')}".casefold()
    if "font" in value or "type" in value:
        return "font"
    if "icon" in value:
        return "icon"
    if "component" in value:
        return "component_source"
    if "pattern" in value or "style" in value or "effect" in value:
        return "style_primitive"
    if "texture" in value:
        return "texture"
    if "illustr" in value:
        return "illustration"
    return "image"


def _allowed_sources(category: str) -> list[str]:
    return {
        "image": ["pexels", "pixabay", "unsplash", "fixture"],
        "texture": ["pexels", "pixabay", "unsplash", "fixture"],
        "illustration": ["pexels", "pixabay", "unsplash", "fixture"],
        "font": ["local", "fontsource", "fixture"],
        "icon": ["lucide", "fixture"],
        "component_source": ["shadcn", "magicui", "smoothui", "cultui", "fixture"],
        "style_primitive": ["pattern", "token_preset", "helper", "fixture"],
    }.get(category, ["fixture"])


def _fallback_for(category: str, required: bool) -> str:
    if required:
        return "none"
    return {
        "font": "system_font_stack",
        "icon": "lucide_default",
        "component_source": "simple_dom",
        "style_primitive": "discard_ornament",
    }.get(category, "generated_local")


def _fallback_text(category: str) -> str:
    return {
        "font": "Use the configured system font stack.",
        "icon": "Use a local Lucide/default icon.",
        "component_source": "Use a trusted source-only local component.",
        "style_primitive": "Use the approved tokens without the optional primitive.",
    }.get(category, "Use an honest local implementation without external media.")


def _max_bytes_for(category: str) -> int:
    return {
        "image": 4 * 1024 * 1024,
        "texture": 4 * 1024 * 1024,
        "illustration": 4 * 1024 * 1024,
        "font": 2 * 1024 * 1024,
        "icon": 384 * 1024,
        "component_source": 512 * 1024,
        "style_primitive": 256 * 1024,
    }.get(category, 0)


def _words_overlap(left: str, right: str) -> bool:
    return bool(set(re_split_words(left)).intersection(re_split_words(right)))


def re_split_words(value: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9]+", value.casefold()) if len(word) > 2]


def _binding_for(request: ResourceRequest, receipt: ResourceReceipt) -> ResourceBinding:
    return ResourceBinding(
        binding_id=f"binding-{request.request_hash[:20]}",
        request_id_or_pack_need_id=request.request_hash,
        local_paths=[file.local_path for file in receipt.materialized_files],
        placement_ids=[request.placement.purpose],
        disposition=receipt.disposition,
    )


def _fallback_receipt(request: ResourceRequest, reason: str) -> ResourceReceipt:
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


def _rejected_receipt(request: ResourceRequest, reason: str) -> ResourceReceipt:
    return ResourceReceipt(
        request_hash=request.request_hash,
        disposition="rejected",
        fallback={"kind": "none", "reason": reason},
        satisfied_placements=[request.placement.purpose],
        acquired_at=datetime.now(UTC).isoformat(),
    )


def _prefix_materialized_file(file: Any, run_id: str) -> Any:
    inspection = dict(file.inspection)
    for key, value in list(inspection.items()):
        if key.endswith("_path") and isinstance(value, str):
            inspection[key] = f"{run_id}/{value}"
    return file.model_copy(
        update={"local_path": f"{run_id}/{file.local_path}", "inspection": inspection}
    )


def _read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return dict(fallback)
    return value if isinstance(value, dict) else dict(fallback)


def _model_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _default_adapter_factory(settings: Any) -> dict[str, Any]:
    root = str(getattr(settings.code_generator_acquisition, "offline_resource_root", "") or "")
    registry = OfflineResourceProviderRegistry.from_directory(Path(root)) if root else None
    return default_adapters(registry=registry)


def _build_planner(settings: Any) -> Any | None:
    from oryxenai.agents.shared.model_client import build_provider_client

    return build_provider_client(
        settings.code_generator_development.planner_profile, settings.models
    )


def _write_context(settings: Any, identity: str, digest: str, context: dict[str, Any]) -> str:
    from oryxenai.agents.code_generator.core import fs_safe

    configured_root = Path(settings.code_generator_development.input_root)
    root = (
        configured_root
        if configured_root.is_absolute()
        else (repository_root() / configured_root).resolve()
    )
    relative = Path("contexts") / identity[:2] / f"{identity}-{digest}.json"
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise RuntimeError("development context root is unsafe")
    target.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json(context)
    if not target.exists():
        fs_safe.write_text_atomic(target, data.decode("utf-8"))
    if target.read_bytes() != data:
        raise RuntimeError("development context read-back failed")
    return relative.as_posix()


class CodeGeneratorGenerationHandler:
    """Durable Phase 3 progressive source-generation job."""

    kind = "code_generator.generate"

    def __init__(
        self,
        model_factory: Callable[[str], Any] | None = None,
        adapter_factory: Callable[[Any], dict[str, Any]] | None = None,
    ) -> None:
        self._model_factory = model_factory
        self._adapter_factory = adapter_factory

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        from oryxenai.agents.code_generator.core.generation_orchestrator import (
            CodeGeneratorGenerationOrchestrator,
        )

        return await CodeGeneratorGenerationOrchestrator(
            model_factory=self._model_factory,
            adapter_factory=self._adapter_factory,
        ).execute(payload, instance_id)


async def _cas_status(
    repo: CodeGeneratorDevelopmentRepository,
    run: Any,
    status: str,
    *,
    values: dict[str, object] | None = None,
) -> Any:
    updated = await repo.compare_and_swap(
        run.id,
        expected_revision=run.revision,
        values={"status": status, **(values or {})},
    )
    if updated is None:
        raise RuntimeError("development run revision conflict")
    return updated


async def _needs_attention(
    sessionmaker: Any,
    run_id: UUID,
    issue: SafeIssue,
    *,
    values: dict[str, object] | None = None,
) -> None:
    async with sessionmaker() as db:
        repo = CodeGeneratorDevelopmentRepository(db)
        run = await repo.get(run_id)
        if run is None or run.status == DevelopmentRunStatus.PLANNED.value:
            return
        updated = await _cas_status(
            repo,
            run,
            DevelopmentRunStatus.NEEDS_ATTENTION.value,
            values={"issues": [issue.model_dump(mode="json")], **(values or {})},
        )
        del updated
        await repo.append_event(
            run_id,
            event_type="needs_attention",
            level="error",
            message=issue.message,
            details={"code": issue.code},
        )
        await db.commit()
