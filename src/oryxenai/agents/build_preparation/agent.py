"""Build Preparation orchestration from Stage 0 through Phase 3."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from oryxenai.agents.build_preparation.compiler import compile_stage0
from oryxenai.agents.build_preparation.fixture import (
    _offline_candidates,
    _offline_context,
    _offline_download,
    _offline_query_plan,
    _offline_selection_plan,
    _offline_trigger,
)
from oryxenai.agents.build_preparation.materializer import (
    TARGET_ALLOWED_DEPENDENCIES,
    materialize_build_context,
)
from oryxenai.agents.build_preparation.packager import package_and_store, staging_directory
from oryxenai.agents.build_preparation.prompt_builder import (
    build_instructions,
    output_model_for,
)
from oryxenai.agents.build_preparation.providers import ProviderLookup
from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    BuildPreparationSourceRef,
    FetchedResource,
    ResourceSelection,
    RouteBuildContext,
    Stage1QueryPlan,
    Stage2SelectionPlan,
    Stage3BuildContextResult,
    Stage4IntegratedContextResult,
    StageEvent,
)
from oryxenai.agents.build_preparation.validators import (
    BuildPreparationValidationError,
    validate_build_context,
    validate_fetched_candidates,
    validate_query_plan,
    validate_selection_plan,
)
from oryxenai.agents.shared.contracts import Agent, AgentContext, AgentKey, AgentResult, ModelClient
from oryxenai.core.logging import get_logger
from oryxenai.core.settings import get_settings

logger = get_logger("oryxenai.agents.build_preparation")


class BuildPreparationModelOutputError(BuildPreparationValidationError):
    """A model response failed a deterministic structured-output contract."""

    code = "BUILD_PREPARATION_MODEL_OUTPUT_INVALID"


def _event(
    event_id: str,
    stage: str,
    message: str,
    *,
    level: str = "info",
    details: dict[str, Any] | None = None,
) -> StageEvent:
    return StageEvent(
        event_id=event_id,
        stage=stage,
        level=level,  # type: ignore[arg-type]
        message=message,
        details=details or {},
        timestamp=datetime.now(UTC).isoformat(),
    )


def _parsed(result: Any) -> dict[str, Any]:
    parsed = getattr(result, "parsed_output", None)
    if not isinstance(parsed, dict):
        raise BuildPreparationModelOutputError("Model returned a non-object output.")
    return parsed


def _candidate_prompt(candidate: FetchedResource) -> dict[str, Any]:
    data = candidate.model_dump(mode="json")
    data.pop("source_files", None)
    return data


class BuildPreparationAgent(Agent):
    key = AgentKey.BUILD_PREPARATION

    def __init__(
        self,
        model_client: ModelClient | None = None,
        *,
        provider_lookup: ProviderLookup | None = None,
        artifact_store: Any | None = None,
        live_model: bool = True,
        live_providers: bool = True,
        settings: Any | None = None,
    ) -> None:
        self._model_client = model_client
        self._provider_lookup = provider_lookup
        self._artifact_store = artifact_store
        self._live_model = live_model
        self._live_providers = live_providers
        self._settings = settings or get_settings()

    async def run(self, context: AgentContext) -> AgentResult:
        operation = str(context.agent_input.get("operation", "stage_0") or "stage_0")
        if operation not in {"build", "stage_0"}:
            raise ValueError(f"Unknown Build Preparation operation: {operation}")
        return await self._run_build(context, phase2=operation == "build")

    async def _run_build(self, context: AgentContext, *, phase2: bool) -> AgentResult:
        payload = context.agent_input
        visual = payload.get("visual_design_director")
        if not isinstance(visual, dict):
            visual = context.current_state.get("visual_design_director", {})
        content = payload.get("content_architect")
        if not isinstance(content, dict):
            content = context.current_state.get("content_architect")
        if not isinstance(visual, dict):
            visual = {}
        if not isinstance(content, dict):
            content = None
        raw_ref = payload.get("source_ref")
        source_ref = (
            BuildPreparationSourceRef.model_validate(raw_ref) if isinstance(raw_ref, dict) else None
        )
        stage0 = compile_stage0(
            content,
            visual,
            source_ref=source_ref,
            max_routes=int(
                payload.get("max_routes", self._settings.build_preparation.max_routes) or 12
            ),
        )
        events = list(stage0.events)
        if not phase2:
            return AgentResult(
                output=stage0.model_dump(mode="json"),
                prompt_version="phase1-stage0",
                model_metadata={
                    "provider": "deterministic",
                    "agent": self.key.value,
                    "model_calls": 0,
                },
            )

        need_ids = {need.need_id for need in stage0.resource_needs}
        route_ids = {route.route_id for route in stage0.routes}
        live_model = bool(payload.get("live_model", self._live_model))
        live_providers = bool(payload.get("live_providers", self._live_providers))
        model_profile = str(payload.get("model_profile", "") or "")
        stages_meta: list[dict[str, Any]] = []
        prompt_version = "build_preparation.phase2"
        model_calls = 0

        if live_model:
            query_plan_value, prompt_version, meta = await self._call_stage(
                "compose_resource_queries",
                {
                    "routes": [route.model_dump(mode="json") for route in stage0.routes],
                    "resource_needs": [
                        need.model_dump(mode="json") for need in stage0.resource_needs
                    ],
                    "visual_design_director": visual,
                },
                model_profile,
            )
            query_plan = cast(Stage1QueryPlan, query_plan_value)
            model_calls += 1
            stages_meta.append(meta)
        else:
            query_plan = _offline_query_plan(stage0.resource_needs)
        validate_query_plan(query_plan, need_ids)
        events.append(
            _event(
                "stage_1_complete",
                "stage_1",
                "Resource queries composed.",
                details={"query_count": len(query_plan.queries)},
            )
        )

        lookup = self._provider_lookup or ProviderLookup(self._settings, live=live_providers)
        candidates = (
            await lookup.lookup(query_plan.queries)
            if live_providers
            else _offline_candidates(query_plan.queries)
        )
        validate_fetched_candidates(candidates, need_ids)
        events.append(
            _event(
                "provider_lookup_complete",
                "providers",
                "Provider lookup completed.",
                details={"candidate_count": len(candidates)},
            )
        )

        candidate_payload = [_candidate_prompt(candidate) for candidate in candidates]
        if live_model:
            selection_plan_value, prompt_version, meta = await self._call_stage(
                "select_resources",
                {
                    "resource_needs": [
                        need.model_dump(mode="json") for need in stage0.resource_needs
                    ],
                    "candidate_resources": candidate_payload,
                    "routes": [route.model_dump(mode="json") for route in stage0.routes],
                },
                model_profile,
            )
            selection_plan = cast(Stage2SelectionPlan, selection_plan_value)
            model_calls += 1
            stages_meta.append(meta)
        else:
            selection_plan = _offline_selection_plan(stage0.resource_needs, candidates)
        candidate_by_id = {candidate.resource_id: candidate for candidate in candidates}
        selection_warnings = list(selection_plan.warnings)
        candidate_need_ids = {candidate.need_id for candidate in candidates}
        for query in query_plan.queries:
            if query.need_id in candidate_need_ids:
                continue
            if query.kind == "icon":
                selection_warnings.append(
                    f"Icon '{query.icon_name}' could not be resolved; no icon ID was invented."
                )
            elif query.kind == "photo":
                selection_warnings.append(
                    f"No photo candidate was returned for need '{query.need_id}'; using its fallback."
                )
            elif query.kind == "component":
                selection_warnings.append(
                    f"No registry component was returned for need '{query.need_id}'; using its fallback."
                )
        normalized_selections: list[ResourceSelection] = []
        for selection in selection_plan.selections:
            candidate = candidate_by_id.get(selection.selected_resource_id or "")
            if (
                candidate is not None
                and candidate.kind == "component"
                and not set(candidate.dependencies).issubset(TARGET_ALLOWED_DEPENDENCIES)
            ):
                need = next(
                    (item for item in stage0.resource_needs if item.need_id == selection.need_id),
                    None,
                )
                selection = selection.model_copy(
                    update={
                        "selected_resource_id": None,
                        "fallback": selection.fallback
                        or (need.fallback if need else "Use an explicit custom implementation."),
                        "adaptation_notes": (
                            f"Rejected registry dependencies: {', '.join(candidate.dependencies)}. "
                            "Implement the approved intent without this component."
                        ),
                    }
                )
                selection_warnings.append(
                    f"Component '{candidate.resource_id}' was rejected because its dependencies exceed the target contract."
                )
            normalized_selections.append(selection)
        selection_plan = selection_plan.model_copy(
            update={"selections": normalized_selections, "warnings": selection_warnings}
        )
        validate_selection_plan(selection_plan, need_ids, candidates)
        events.append(
            _event(
                "stage_2_complete", "stage_2", "Resources selected or assigned explicit fallbacks."
            )
        )

        context_packet = {
            "routes": [route.model_dump(mode="json") for route in stage0.routes],
            "resource_needs": [need.model_dump(mode="json") for need in stage0.resource_needs],
            "candidate_resources": candidate_payload,
            "selections": [
                selection.model_dump(mode="json") for selection in selection_plan.selections
            ],
            "content_architect": content or {},
            "visual_design_director": visual,
        }
        if live_model:
            stage3, prompt_version, meta = await self._call_context_stage(
                "write_build_context", context_packet, model_profile, route_ids, selection_plan
            )
            model_calls += 1
            stages_meta.append(meta)
            build_context, reconciliation_warnings = _reconcile_model_context(
                stage3.context,
                stage0.routes,
                _selected_ids(selection_plan),
            )
            if reconciliation_warnings:
                events.append(
                    _event(
                        "stage_3_context_reconciled",
                        "stage_3",
                        "Stage 3 output was reconciled to the approved route and resource sets.",
                        level="warning",
                        details={"warning_count": len(reconciliation_warnings)},
                    )
                )
        else:
            build_context = _offline_context(
                stage0.routes, stage0.resource_needs, selection_plan, content or {}, visual
            )
        validate_build_context(build_context, route_ids, _selected_ids(selection_plan))
        events.append(_event("stage_3_complete", "stage_3", "Route-scoped build context written."))

        threshold = int(
            payload.get(
                "integration_route_threshold",
                self._settings.build_preparation.integration_route_threshold,
            )
            or 2
        )
        if len(stage0.routes) >= threshold:
            integration_packet = {
                **context_packet,
                "build_context": build_context.model_dump(mode="json"),
            }
            if live_model:
                stage4, prompt_version, meta = await self._call_context_stage(
                    "integrate_cross_route",
                    integration_packet,
                    model_profile,
                    route_ids,
                    selection_plan,
                )
                model_calls += 1
                stages_meta.append(meta)
                build_context, reconciliation_warnings = _reconcile_model_context(
                    stage4.context,
                    stage0.routes,
                    _selected_ids(selection_plan),
                    fallback=build_context,
                )
                if reconciliation_warnings:
                    events.append(
                        _event(
                            "stage_4_context_reconciled",
                            "stage_4",
                            "Stage 4 output was reconciled to the approved route and resource sets.",
                            level="warning",
                            details={"warning_count": len(reconciliation_warnings)},
                        )
                    )
            events.append(_event("stage_4_complete", "stage_4", "Cross-route context integrated."))
            validate_build_context(build_context, route_ids, _selected_ids(selection_plan))

        output_dir = str(
            payload.get("output_dir", self._settings.build_preparation.fixture_output_dir)
            or "output"
        )
        artifact_upload = bool(payload.get("artifact_upload", False))
        debug_mirror = bool(
            payload.get("debug_mirror", self._settings.build_preparation.debug_mirror_enabled)
        )
        with staging_directory(output_dir) as staging_path:
            staging_root = Path(staging_path) / "build-context"
            materialization = await materialize_build_context(
                output_dir=output_dir,
                run_id=context.run_id,
                routes=stage0.routes,
                needs=stage0.resource_needs,
                selections=selection_plan.selections,
                candidates=candidates,
                context=build_context,
                content_architect=content or {},
                settings=self._settings,
                download_image=_offline_download if not live_providers else None,
                trigger_download=_offline_trigger if not live_providers else None,
                root_override=staging_root,
            )
            package, materialization = await package_and_store(
                staging_root=staging_root,
                output_dir=output_dir,
                run_id=context.run_id,
                portfolio_session_id=UUID(context.portfolio_session_id),
                scope_hash=stage0.scope_hash,
                source_ref=stage0.source_ref,
                materialization=materialization,
                settings=self._settings,
                artifact_store=self._artifact_store,
                upload_enabled=artifact_upload,
                mirror_enabled=debug_mirror,
                expires_at=str(payload.get("bundle_expires_at", "") or "") or None,
            )
            prompt_version = "build_preparation.phase3"
        events.append(
            _event(
                "materialization_complete",
                "materialize",
                "Build-context staging tree materialized.",
                details={
                    "root_path": materialization.relative_root,
                    "file_count": len(materialization.files),
                },
            )
        )
        events.append(
            _event(
                "package_verified",
                "phase_3",
                "Deterministic ZIP was created and verified after storage read-back.",
                details={
                    "archive_sha256": package.archive_sha256,
                    "archive_size_bytes": package.archive_size_bytes,
                    "file_count": package.file_count,
                    "artifact_provider": package.artifact.provider if package.artifact else "",
                },
            )
        )
        if package.mirror_root:
            events.append(
                _event(
                    "debug_mirror_restored",
                    "phase_3",
                    "The verified ZIP was restored to the local debug mirror.",
                    details={"root_path": package.mirror_relative_root},
                )
            )
        if materialization.warnings:
            events.append(
                _event(
                    "materialization_warnings",
                    "materialize",
                    "Materialization completed with warnings.",
                    level="warning",
                    details={"warning_count": len(materialization.warnings)},
                )
            )
        events.append(_event("phase_3_complete", "phase_3", "Build Preparation Phase 3 completed."))
        warnings = (
            list(stage0.warnings)
            + list(query_plan.warnings)
            + list(selection_plan.warnings)
            + list(build_context.warnings)
            + list(materialization.warnings)
        )
        return AgentResult(
            output={
                "stage": "phase_3",
                "status": "ready",
                "scope_hash": stage0.scope_hash,
                "source_ref": stage0.source_ref.model_dump(mode="json"),
                "routes": [route.model_dump(mode="json") for route in stage0.routes],
                "resource_needs": [need.model_dump(mode="json") for need in stage0.resource_needs],
                "query_plan": query_plan.model_dump(mode="json"),
                "fetched_candidates": [
                    candidate.model_dump(mode="json") for candidate in candidates
                ],
                "selection_plan": selection_plan.model_dump(mode="json"),
                "build_context": build_context.model_dump(mode="json"),
                "materialization": materialization.model_dump(mode="json"),
                "package": package.model_dump(mode="json"),
                "warnings": warnings,
                "events": [event.model_dump(mode="json") for event in events],
                "model_calls": model_calls,
                "provider_calls": len(query_plan.queries) if live_providers else 0,
            },
            prompt_version=prompt_version,
            model_metadata={
                "stages": stages_meta,
                "model_calls": model_calls,
                "provider_calls": len(query_plan.queries) if live_providers else 0,
            },
        )

    async def _call_stage(
        self, operation: str, packet: dict[str, Any], model_profile: str
    ) -> tuple[Stage1QueryPlan | Stage2SelectionPlan, str, dict[str, Any]]:
        system, task, version, manifest = build_instructions(operation, packet)
        if self._model_client is None:
            raise BuildPreparationModelOutputError(
                "A live Build Preparation model client is required."
            )
        result = await self._model_client.generate_structured(
            operation=operation,
            system_prompt=system,
            instructions=task,
            input_payload=packet,
            output_model=output_model_for(operation),
            model_profile=model_profile,
        )
        parsed = _parsed(result)
        model = output_model_for(operation).model_validate(parsed)
        if not isinstance(model, (Stage1QueryPlan, Stage2SelectionPlan)):
            raise BuildPreparationModelOutputError(f"Unexpected output model for {operation}.")
        return model, version, _metadata(result, manifest, operation)

    async def _call_context_stage(
        self,
        operation: str,
        packet: dict[str, Any],
        model_profile: str,
        route_ids: set[str],
        selection_plan: Stage2SelectionPlan,
    ) -> tuple[Stage3BuildContextResult | Stage4IntegratedContextResult, str, dict[str, Any]]:
        system, task, version, manifest = build_instructions(operation, packet)
        if self._model_client is None:
            raise BuildPreparationModelOutputError(
                "A live Build Preparation model client is required."
            )
        result = await self._model_client.generate_structured(
            operation=operation,
            system_prompt=system,
            instructions=task,
            input_payload=packet,
            output_model=output_model_for(operation),
            model_profile=model_profile,
        )
        parsed = _parsed(result)
        model = output_model_for(operation).model_validate(parsed)
        if not isinstance(model, (Stage3BuildContextResult, Stage4IntegratedContextResult)):
            raise BuildPreparationModelOutputError(f"Unexpected output model for {operation}.")
        return model, version, _metadata(result, manifest, operation)


def _metadata(result: Any, manifest: dict[str, str], operation: str) -> dict[str, Any]:
    return {
        "operation": operation,
        "provider": str(getattr(result, "model", "") or ""),
        "model": str(getattr(result, "model", "") or ""),
        "response_id": str(getattr(result, "response_id", "") or ""),
        "usage": getattr(result, "usage", {}) or {},
        "latency_ms": getattr(result, "latency_ms", 0.0),
        "finish_reason": str(getattr(result, "finish_reason", "") or ""),
        "prompt_modules": manifest,
    }


def _selected_ids(plan: Stage2SelectionPlan) -> set[str]:
    return {
        selection.selected_resource_id
        for selection in plan.selections
        if selection.selected_resource_id
    }


def _reconcile_model_context(
    context: BuildContextDraft,
    routes: list[Any],
    selected_resource_ids: set[str],
    *,
    fallback: BuildContextDraft | None = None,
) -> tuple[BuildContextDraft, list[str]]:
    """Keep model-written context inside the deterministic approved boundary.

    The model receives the route/resource IDs in every context prompt, but a
    live response can still contain a typo or omit a route.  Drop dangling
    references and fill only from the already-approved route scope (or the
    previous integrated context).  This preserves the closed-set contract
    without inventing a route, resource, or fact.
    """
    scopes = {route.route_id: route for route in routes}
    previous = {route.route_id: route for route in (fallback.routes if fallback else [])}
    normalized: dict[str, RouteBuildContext] = {}
    warnings: list[str] = []

    for route in context.routes:
        scope = scopes.get(route.route_id)
        if scope is None:
            warnings.append(f"Dropped unknown model route '{route.route_id}'.")
            continue
        if route.route_id in normalized:
            warnings.append(f"Dropped duplicate model route '{route.route_id}'.")
            continue
        unknown_resources = sorted(set(route.resource_ids) - selected_resource_ids)
        if unknown_resources:
            warnings.append(
                f"Dropped unselected resources from route '{route.route_id}': "
                + ", ".join(unknown_resources)
            )
        safe_resources = [
            resource_id
            for resource_id in route.resource_ids
            if resource_id in selected_resource_ids
        ]
        prior = previous.get(route.route_id)
        brief = route.brief_markdown.strip()
        if not brief and prior is not None:
            brief = prior.brief_markdown
        if not brief:
            brief = _fallback_route_brief(scope)
            warnings.append(f"Added a grounded fallback brief for route '{route.route_id}'.")
        normalized[route.route_id] = route.model_copy(
            update={
                "path": scope.path,
                "brief_markdown": brief,
                "resource_ids": safe_resources,
            }
        )

    for scope in routes:
        if scope.route_id in normalized:
            continue
        prior = previous.get(scope.route_id)
        if prior is not None:
            normalized[scope.route_id] = prior.model_copy(update={"path": scope.path})
        else:
            normalized[scope.route_id] = RouteBuildContext(
                route_id=scope.route_id,
                path=scope.path,
                brief_markdown=_fallback_route_brief(scope),
                data={
                    "purpose": scope.purpose,
                    "scene_ids": scope.scene_ids,
                    "asset_ids": scope.asset_ids,
                    "resource_ids": scope.resource_ids,
                },
            )
        warnings.append(f"Added a grounded fallback brief for missing route '{scope.route_id}'.")

    context_warnings = list(dict.fromkeys([*context.warnings, *warnings]))
    ordered_routes = [normalized[scope.route_id] for scope in routes]
    return context.model_copy(
        update={"routes": ordered_routes, "warnings": context_warnings}
    ), warnings


def _fallback_route_brief(route: Any) -> str:
    title = route.title or route.route_id
    path = route.path or "/"
    return (
        f"# {title}\n\n"
        f"Implement the approved route at `{path}` using the supplied Content Architect "
        "content and Visual Design Director direction as the source of truth. "
        "No additional facts or requirements are implied by this fallback."
    )
