"""Build Preparation orchestration from Stage 0 through Phase 3."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
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
    dependencies_allowed,
    materialize_build_context,
    materialize_handoff_report,
)
from oryxenai.agents.build_preparation.packager import package_and_store, staging_directory
from oryxenai.agents.build_preparation.prompt_builder import (
    build_instructions,
    output_model_for,
)
from oryxenai.agents.build_preparation.providers import ProviderLookup
from oryxenai.agents.build_preparation.quality import (
    build_handoff_report,
    normalize_query_plan,
    qualify_candidates,
    select_required_candidates,
)
from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    BuildPreparationSourceRef,
    CandidateQualification,
    FetchedResource,
    ResourceSelection,
    RouteBuildContext,
    Stage1QueryPlan,
    Stage2SelectionPlan,
    Stage3BuildContextResult,
    Stage4IntegratedContextResult,
    Stage5HandoffReview,
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

EventSink = Callable[[StageEvent], Awaitable[None]]


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


def _generated_visual_candidate(need: Any) -> tuple[FetchedResource, CandidateQualification]:
    """Create concrete local visual material when external lookup is absent."""

    import hashlib

    digest = hashlib.sha256(str(need.need_id).encode("utf-8")).hexdigest()[:16]
    is_photo = need.kind == "asset" or "photo" in str(need.category).casefold()
    resource_id = f"resource-generated-{digest}"
    if is_photo:
        candidate = FetchedResource(
            resource_id=resource_id,
            need_id=need.need_id,
            kind="photo",
            provider="generated-local",
            provider_asset_id=f"generated-{digest}",
            source_reference="local://oryxenai/generated-visual",
            title="Generated abstract technical visual",
            description="Locally materialized abstract technical editorial visual",
            width=1600,
            height=1000,
            orientation="landscape",
            mime_type="image/png",
            image_url="",
            license="OryxenAI generated visual",
            license_reference="local://oryxenai/generated-visual-license",
            fallback="",
        )
    else:
        candidate = FetchedResource(
            resource_id=resource_id,
            need_id=need.need_id,
            kind="component",
            provider="generated-local",
            provider_asset_id=f"visual-story-{digest}",
            source_reference="local://oryxenai/generated-component",
            title="Generated visual storytelling component",
            description="Generated local process topology visual component",
            source_files={
                "PreparedVisualStory.tsx": (
                    "import type { ReactNode } from 'react';\n\n"
                    "type Props = { label?: string; children?: ReactNode };\n\n"
                    "export function PreparedVisualStory({ label = 'Selected work', children }: Props) {\n"
                    '  return <div data-resource-role="visual-story" className="prepared-visual-story">'
                    '<span className="prepared-visual-story__label">{label}</span>{children}</div>;\n'
                    "}\n\nexport default PreparedVisualStory;\n"
                )
            },
            dependencies=["react"],
            license="OryxenAI generated component",
            license_reference="local://oryxenai/generated-component-license",
        )
    qualification = CandidateQualification(
        resource_id=resource_id,
        need_id=need.need_id,
        eligible=True,
        relevance_score=100,
        quality_score=100,
        policy_status="approved",
        technical_status="approved",
        reasons=[
            "No provider candidate was available; concrete local visual material was generated."
        ],
    )
    return candidate, qualification


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
        event_sink: EventSink | None = None,
    ) -> None:
        self._model_client = model_client
        self._provider_lookup = provider_lookup
        self._artifact_store = artifact_store
        self._live_model = live_model
        self._live_providers = live_providers
        self._settings = settings or get_settings()
        self._event_sink = event_sink

    async def _emit_event(self, event: StageEvent) -> None:
        if self._event_sink is not None:
            await self._event_sink(event)

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
            editorial_image_budget=int(
                payload.get(
                    "editorial_image_budget",
                    self._settings.build_preparation.editorial_image_budget,
                )
                or 0
            ),
        )
        events = list(stage0.events)
        for event in events:
            await self._emit_event(event)

        async def record(event: StageEvent) -> None:
            events.append(event)
            await self._emit_event(event)

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

        await self._emit_event(
            _event(
                "stage_1_started",
                "stage_1",
                "Composing resource queries with the configured model."
                if live_model
                else "Composing deterministic offline resource queries.",
            )
        )
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
        query_plan = normalize_query_plan(query_plan, stage0.resource_needs)
        validate_query_plan(query_plan, need_ids)
        await record(
            _event(
                "stage_1_complete",
                "stage_1",
                "Resource queries composed.",
                details={"query_count": len(query_plan.queries)},
            )
        )

        await self._emit_event(
            _event(
                "provider_lookup_started",
                "providers",
                "Looking up approved resource candidates from live providers."
                if live_providers
                else "Preparing deterministic offline resource candidates.",
            )
        )
        lookup = self._provider_lookup or ProviderLookup(self._settings, live=live_providers)
        candidates = (
            await lookup.lookup(query_plan.queries)
            if live_providers
            else _offline_candidates(query_plan.queries)
        )
        validate_fetched_candidates(candidates, need_ids)
        qualifications = qualify_candidates(stage0.resource_needs, candidates)
        qualified_ids = {item.resource_id for item in qualifications if item.eligible}
        await record(
            _event(
                "provider_lookup_complete",
                "providers",
                "Provider lookup completed.",
                details={
                    "candidate_count": len(candidates),
                    "qualified_count": len(qualified_ids),
                },
            )
        )

        candidate_payload = [
            _candidate_prompt(candidate)
            for candidate in candidates
            if candidate.resource_id in qualified_ids
        ]
        await self._emit_event(
            _event(
                "stage_2_started",
                "stage_2",
                "Selecting resources from the returned candidate set."
                if live_model
                else "Selecting deterministic offline resource fallbacks.",
            )
        )
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
                and not dependencies_allowed(candidate.dependencies)
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

        # Visual-floor slots may be backed by a provider, but they may never
        # disappear into prose when a provider is unavailable. Materialize a
        # concrete local image/component candidate so the downstream generator
        # always receives an executable visual surface.
        selected_by_need = {
            item.need_id: item.selected_resource_id for item in selection_plan.selections
        }
        for need in stage0.resource_needs:
            if not need.required_for_handoff or selected_by_need.get(need.need_id):
                continue
            if need.category not in {"editorial_photo", "visual_component"}:
                continue
            candidate, qualification = _generated_visual_candidate(need)
            candidates.append(candidate)
            qualifications.append(qualification)
            replacement = ResourceSelection(
                need_id=need.need_id,
                selected_resource_id=candidate.resource_id,
                why_selected="Concrete local visual fallback materialized because provider lookup returned no usable candidate.",
                fallback="",
                adaptation_notes="Use the local material as a real visual component or image; do not replace it with a prose recipe.",
            )
            selection_plan.selections = [
                replacement if item.need_id == need.need_id else item
                for item in selection_plan.selections
            ]
            selection_plan.warnings.append(
                f"Materialized local visual fallback for required need '{need.source_id}'."
            )
        forced_selections, forced_warnings = select_required_candidates(
            selection_plan.selections,
            stage0.resource_needs,
            qualifications,
        )
        selection_plan = selection_plan.model_copy(
            update={
                "selections": forced_selections,
                "warnings": [*selection_plan.warnings, *forced_warnings],
            }
        )
        validate_selection_plan(selection_plan, need_ids, candidates)
        await record(
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
        await self._emit_event(
            _event(
                "stage_3_started",
                "stage_3",
                "Writing route-scoped build context."
                if live_model
                else "Writing deterministic route-scoped build context.",
            )
        )
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
                await record(
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
        await record(_event("stage_3_complete", "stage_3", "Route-scoped build context written."))

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
            await self._emit_event(
                _event(
                    "stage_4_started",
                    "stage_4",
                    "Integrating cross-route build constraints."
                    if live_model
                    else "Applying deterministic cross-route build constraints.",
                )
            )
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
                    await record(
                        _event(
                            "stage_4_context_reconciled",
                            "stage_4",
                            "Stage 4 output was reconciled to the approved route and resource sets.",
                            level="warning",
                            details={"warning_count": len(reconciliation_warnings)},
                        )
                    )
            await record(_event("stage_4_complete", "stage_4", "Cross-route context integrated."))
            validate_build_context(build_context, route_ids, _selected_ids(selection_plan))

        output_dir = str(
            payload.get("output_dir", self._settings.build_preparation.fixture_output_dir)
            or "output"
        )
        artifact_upload = bool(payload.get("artifact_upload", False))
        debug_mirror = bool(
            payload.get("debug_mirror", self._settings.build_preparation.debug_mirror_enabled)
        )
        local_result_root = payload.get("local_result_root")
        with staging_directory(output_dir) as staging_path:
            staging_root = Path(staging_path) / "build-context"
            await self._emit_event(
                _event(
                    "materialization_started",
                    "materialize",
                    "Materializing the local build-context tree.",
                )
            )
            materialization = await materialize_build_context(
                output_dir=output_dir,
                run_id=context.run_id,
                routes=stage0.routes,
                needs=stage0.resource_needs,
                selections=selection_plan.selections,
                candidates=candidates,
                context=build_context,
                content_architect={
                    **(content or {}),
                    "_build_preparation_source_ref": stage0.source_ref.model_dump(mode="json"),
                },
                visual_design_director=visual,
                legacy_route_layout=bool(payload.get("legacy_route_layout", False))
                or not bool((content or {}).get("route_plan")),
                settings=self._settings,
                download_image=_offline_download if not live_providers else None,
                trigger_download=_offline_trigger if not live_providers else None,
                root_override=staging_root,
            )
            await record(
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
            handoff_report = build_handoff_report(
                source_ref=stage0.source_ref,
                routes=stage0.routes,
                build_context=build_context,
                content_architect=content or {},
                needs=stage0.resource_needs,
                selections=selection_plan.selections,
                qualifications=qualifications,
                materialization=materialization,
            )
            await self._emit_event(
                _event(
                    "stage_5_started",
                    "stage_5",
                    "Reviewing the package for Code Generator handoff."
                    if live_model
                    else "Applying deterministic Code Generator handoff checks.",
                )
            )
            if live_model:
                review, prompt_version, meta = await self._call_handoff_stage(
                    {
                        "handoff_report": handoff_report.model_dump(mode="json"),
                        "resource_needs": [
                            need.model_dump(mode="json") for need in stage0.resource_needs
                        ],
                        "selections": [
                            selection.model_dump(mode="json")
                            for selection in selection_plan.selections
                        ],
                        "materialized_resources": materialization.resources,
                    },
                    model_profile,
                )
                model_calls += 1
                stages_meta.append(meta)
                handoff_report = handoff_report.model_copy(
                    update={"model_review": review.model_dump(mode="json")}
                )
            else:
                handoff_report = handoff_report.model_copy(
                    update={
                        "model_review": {
                            "stage": "stage_5",
                            "mode": "deterministic_offline",
                            "summary": "No live model was requested for the handoff review.",
                        }
                    }
                )
            materialization = materialize_handoff_report(
                staging_root,
                materialization,
                handoff_report.model_dump(mode="json"),
            )
            await record(
                _event(
                    "stage_5_complete",
                    "stage_5",
                    "Code Generator handoff is eligible."
                    if handoff_report.handoff_eligible
                    else "Code Generator handoff is blocked; package retained for review.",
                    level="info" if handoff_report.handoff_eligible else "warning",
                    details={
                        "handoff_eligible": handoff_report.handoff_eligible,
                        "issue_count": len(handoff_report.issues),
                    },
                )
            )
            await self._emit_event(
                _event(
                    "package_started",
                    "phase_3",
                    "Verifying the local ZIP and preparing artifact storage.",
                )
            )
            if artifact_upload:
                await self._emit_event(
                    _event(
                        "artifact_upload_started",
                        "artifact_storage",
                        "Uploading the verified ZIP to configured artifact storage.",
                    )
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
                local_result_root=(
                    local_result_root
                    if isinstance(local_result_root, str) and local_result_root
                    else None
                ),
                expires_at=str(payload.get("bundle_expires_at", "") or "") or None,
            )
            prompt_version = "build_preparation.phase3"
        await record(
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
            await record(
                _event(
                    "debug_mirror_restored",
                    "phase_3",
                    "The verified ZIP was restored to the local debug mirror.",
                    details={"root_path": package.mirror_relative_root},
                )
            )
        if materialization.warnings:
            await record(
                _event(
                    "materialization_warnings",
                    "materialize",
                    "Materialization completed with warnings.",
                    level="warning",
                    details={"warning_count": len(materialization.warnings)},
                )
            )
        await record(_event("phase_3_complete", "phase_3", "Build Preparation Phase 3 completed."))
        warnings = (
            list(stage0.warnings)
            + list(query_plan.warnings)
            + list(selection_plan.warnings)
            + list(build_context.warnings)
            + list(materialization.warnings)
            + [issue.message for issue in handoff_report.issues]
        )
        return AgentResult(
            output={
                "stage": "phase_3",
                "status": "ready" if handoff_report.handoff_eligible else "needs_attention",
                "scope_hash": stage0.scope_hash,
                "source_ref": stage0.source_ref.model_dump(mode="json"),
                "routes": [route.model_dump(mode="json") for route in stage0.routes],
                "resource_needs": [need.model_dump(mode="json") for need in stage0.resource_needs],
                "query_plan": query_plan.model_dump(mode="json"),
                "fetched_candidates": [
                    candidate.model_dump(mode="json") for candidate in candidates
                ],
                "selection_plan": selection_plan.model_dump(mode="json"),
                "candidate_qualifications": [
                    qualification.model_dump(mode="json") for qualification in qualifications
                ],
                "build_context": build_context.model_dump(mode="json"),
                "materialization": materialization.model_dump(mode="json"),
                "package": package.model_dump(mode="json"),
                "handoff_report": handoff_report.model_dump(mode="json"),
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

    async def _call_handoff_stage(
        self, packet: dict[str, Any], model_profile: str
    ) -> tuple[Stage5HandoffReview, str, dict[str, Any]]:
        operation = "review_handoff_quality"
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
        if not isinstance(model, Stage5HandoffReview):
            raise BuildPreparationModelOutputError("Unexpected output model for handoff review.")
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
