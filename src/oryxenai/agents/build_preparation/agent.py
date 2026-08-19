"""Build Preparation orchestration from Stage 0 through Phase 3."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from oryxenai.agents.build_preparation.compiler import compile_stage0
from oryxenai.agents.build_preparation.fixture import (
    _offline_candidates,
    _offline_context,
    _offline_query_plan,
    _offline_selection_plan,
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
from oryxenai.agents.build_preparation.providers import (
    ProviderLookup,
    download_image,
    trigger_unsplash_download,
)
from oryxenai.agents.build_preparation.quality import (
    build_handoff_report,
    normalize_query_plan,
    qualify_candidates,
    select_required_candidates,
)
from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    BuildPreparationSourceRef,
    FetchedResource,
    HandoffIssue,
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
from oryxenai.agents.build_preparation.visual_input import normalize_visual_input
from oryxenai.agents.shared.contracts import Agent, AgentContext, AgentKey, AgentResult, ModelClient
from oryxenai.agents.shared.resource_context import build_resource_context_packet
from oryxenai.agents.shared.retrieval_policy import plan_component_retrieval
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
        auto_derive = bool(
            payload.get(
                "auto_derive_visual_resources",
                getattr(self._settings.build_preparation, "auto_derive_visual_resources", True),
            )
        )
        raw_ref = payload.get("source_ref")
        source_ref = (
            BuildPreparationSourceRef.model_validate(raw_ref) if isinstance(raw_ref, dict) else None
        )
        declared_policy = visual.get("resource_policy")
        if not isinstance(declared_policy, dict):
            declared_policy = {}
        normalized_visual = normalize_visual_input(
            content,
            visual,
            image_target=int(
                payload.get(
                    "editorial_image_budget",
                    declared_policy.get(
                        "image_target_count",
                        self._settings.build_preparation.editorial_image_budget,
                    ),
                )
                or 0
            ),
            image_maximum=int(
                payload.get(
                    "editorial_image_maximum",
                    getattr(self._settings.build_preparation, "editorial_image_maximum", 6),
                )
                or 6
            ),
            component_target=int(
                payload.get(
                    "visual_component_budget",
                    declared_policy.get(
                        "component_target_count",
                        self._settings.build_preparation.visual_component_budget,
                    ),
                )
                or 0
            ),
            component_maximum=int(
                payload.get(
                    "visual_component_maximum",
                    getattr(self._settings.build_preparation, "visual_component_maximum", 6),
                )
                or 6
            ),
            enabled=auto_derive,
        )
        visual = normalized_visual.visual
        declared_policy = visual.get("resource_policy", {})
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
                    declared_policy.get(
                        "image_target_count",
                        self._settings.build_preparation.editorial_image_budget,
                    ),
                )
                or 0
            ),
            visual_component_budget=int(
                payload.get(
                    "visual_component_budget",
                    declared_policy.get(
                        "component_target_count",
                        self._settings.build_preparation.visual_component_budget,
                    ),
                )
                or 0
            ),
            editorial_image_maximum=int(
                payload.get(
                    "editorial_image_maximum",
                    getattr(self._settings.build_preparation, "editorial_image_maximum", 6),
                )
                or 6
            ),
            visual_component_maximum=int(
                payload.get(
                    "visual_component_maximum",
                    getattr(self._settings.build_preparation, "visual_component_maximum", 6),
                )
                or 6
            ),
            auto_derive_visual_resources=auto_derive,
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
        component_maximum = int(
            payload.get(
                "visual_component_maximum",
                declared_policy.get(
                    "component_maximum",
                    getattr(self._settings.build_preparation, "visual_component_maximum", 6),
                ),
            )
            or 0
        )
        base_resource_packet = build_resource_context_packet(
            content_architect=content or {},
            visual_design_director=visual,
            routes=stage0.routes,
            resource_needs=stage0.resource_needs,
            provider_capabilities={
                "images": list(getattr(self._settings.image_retrieval, "provider_order", [])),
                "components": list(
                    getattr(self._settings.resource_providers, "registry_order", [])
                ),
                "fonts": ["fontsource"],
                "runtime_network_assets": False,
            },
            dependency_limits={"component_request_maximum": component_maximum},
            query_history=list(payload.get("query_history", []) or []),
            provider_attempts=list(payload.get("provider_attempts", []) or []),
            previous_attempt_analysis=dict(payload.get("previous_attempt_analysis", {}) or {}),
            materialization_constraints={
                "runtime_network_assets": False,
                "source_fetched_only_after_selection": True,
                "component_source_attempt_maximum": int(
                    getattr(
                        self._settings.build_preparation,
                        "component_source_attempt_maximum",
                        3,
                    )
                    or 3
                ),
            },
        ).model_dump(mode="json")

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
                base_resource_packet,
                model_profile,
            )
            query_plan = cast(Stage1QueryPlan, query_plan_value)
            model_calls += 1
            stages_meta.append(meta)
        else:
            query_plan = _offline_query_plan(stage0.resource_needs)
        query_plan = normalize_query_plan(
            query_plan,
            stage0.resource_needs,
            settings=self._settings,
            context=base_resource_packet,
        )
        component_needs = [
            need
            for need in stage0.resource_needs
            if need.category.casefold() in {"visual_component", "component", "registry_component"}
        ]
        component_policy = plan_component_retrieval(
            component_needs,
            maximum=component_maximum,
        )
        policy_warnings: list[str] = []
        if component_policy.advisory_exceeded:
            policy_warnings.append(
                "Approved component roles exceed the configured advisory maximum; all roles remain attempted and per-role provider/source limits still apply."
            )
        if policy_warnings:
            query_plan = query_plan.model_copy(
                update={"warnings": [*query_plan.warnings, *policy_warnings]}
            )
        validate_query_plan(query_plan, need_ids)
        query_terms_by_need = _query_terms_by_need(query_plan)
        await record(
            _event(
                "stage_1_complete",
                "stage_1",
                "Resource queries composed.",
                details={
                    "query_count": len(query_plan.queries),
                    "component_retrieval_policy": component_policy.as_metadata(),
                },
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
        qualifications = qualify_candidates(
            stage0.resource_needs,
            candidates,
            source_required=not live_providers,
            query_terms_by_need=query_terms_by_need,
        )
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

        candidate_payload = [_candidate_prompt(candidate) for candidate in candidates]
        await self._emit_event(
            _event(
                "stage_2_started",
                "stage_2",
                "Selecting resources from the returned candidate set."
                if live_model
                else "Recording offline provider gaps; no visual fallback is fabricated.",
            )
        )
        if live_model:
            selection_plan_value, prompt_version, meta = await self._call_stage(
                "select_resources",
                {
                    **base_resource_packet,
                    "candidate_resources": candidate_payload,
                    "existing_resources": candidate_payload,
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
                    f"No photo candidate was returned for need '{query.need_id}'; the visual role remains an execution gap."
                )
            elif query.kind == "component":
                selection_warnings.append(
                    f"No registry component was returned for need '{query.need_id}'; the component role remains an execution gap."
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
        selection_plan, selection_warnings = _normalize_selection_ids(
            selection_plan,
            candidates,
            stage0.resource_needs,
        )
        selection_plan = selection_plan.model_copy(update={"warnings": selection_warnings})

        forced_selections, forced_warnings = select_required_candidates(
            selection_plan.selections,
            stage0.resource_needs,
            qualifications,
        )
        selection_plan = selection_plan.model_copy(
            update={
                "selections": _complete_alternate_rankings(
                    forced_selections,
                    candidates,
                    qualifications,
                ),
                "warnings": [*selection_plan.warnings, *forced_warnings],
            }
        )

        # Discovery returns metadata only for live components. Fetch real
        # source after the closed candidate set has been selected, so weak
        # candidates do not consume source requests before selection; transport
        # retries and provider rate limits remain enforced after selection.
        if live_providers:
            candidate_by_id = {candidate.resource_id: candidate for candidate in candidates}
            source_attempt_limit = max(
                1,
                int(
                    getattr(
                        self._settings.build_preparation,
                        "component_source_attempt_maximum",
                        3,
                    )
                    or 3
                ),
            )
            post_fetch_selections: list[ResourceSelection] = []
            for selection in selection_plan.selections:
                need = next(
                    (item for item in stage0.resource_needs if item.need_id == selection.need_id),
                    None,
                )
                if need is None or need.category.casefold() not in {
                    "component",
                    "visual_component",
                    "registry_component",
                }:
                    post_fetch_selections.append(selection)
                    continue
                ordered_ids = list(
                    dict.fromkeys(
                        [
                            *(
                                [selection.selected_resource_id]
                                if selection.selected_resource_id
                                else []
                            ),
                            *selection.alternate_resource_ids,
                            *[
                                item.resource_id
                                for item in sorted(
                                    qualifications,
                                    key=lambda item: (
                                        -item.relevance_score,
                                        -item.quality_score,
                                        item.resource_id,
                                    ),
                                )
                                if item.need_id == need.need_id and item.eligible
                            ],
                        ]
                    )
                )
                attempts: list[dict[str, Any]] = []
                resolved: FetchedResource | None = None
                for candidate_id in ordered_ids[:source_attempt_limit]:
                    candidate = candidate_by_id.get(candidate_id)
                    if candidate is None or candidate.kind != "component":
                        continue
                    try:
                        fetched = await lookup.fetch_component(candidate)
                    except Exception as exc:
                        details = getattr(exc, "details", {})
                        details = details if isinstance(details, dict) else {}
                        error_code = str(
                            getattr(exc, "code", "SOURCE_FETCH_FAILED") or "SOURCE_FETCH_FAILED"
                        )
                        if error_code == "RATE_LIMITED":
                            lookup.rate_limit_events = (
                                int(getattr(lookup, "rate_limit_events", 0)) + 1
                            )
                        attempts.append(
                            {
                                "provider": candidate.provider,
                                "candidate_id": candidate_id,
                                "attempt": len(attempts) + 1,
                                "query": query_terms_by_need.get(need.need_id, []),
                                "source_fetch_status": "failed",
                                "http_status": details.get("http_status"),
                                "retry_delay": details.get("retry_delay", 0.0),
                                "rate_limit_event": error_code == "RATE_LIMITED",
                                "error_code": error_code,
                                "rejection_reason": str(exc),
                            }
                        )
                        continue
                    candidate_by_id[candidate_id] = fetched
                    qualified = qualify_candidates(
                        [need],
                        [fetched],
                        source_required=True,
                        query_terms_by_need=query_terms_by_need,
                    )[0]
                    attempts.append(
                        {
                            "provider": fetched.provider,
                            "candidate_id": candidate_id,
                            "attempt": len(attempts) + 1,
                            "query": query_terms_by_need.get(need.need_id, []),
                            "source_fetch_status": "accepted" if qualified.eligible else "rejected",
                            "http_status": 200,
                            "retry_delay": 0.0,
                            "cache_state": "not_cached",
                            "rejection_reason": "; ".join(qualified.reasons),
                            "license": fetched.license,
                            "source_file_count": len(fetched.source_files),
                        }
                    )
                    if qualified.eligible:
                        resolved = fetched
                        break
                lookup.provider_receipts.extend(attempts)
                if resolved is None:
                    post_fetch_selections.append(
                        selection.model_copy(
                            update={
                                "selected_resource_id": None,
                                "fallback": selection.fallback
                                or need.fallback
                                or "Implement the approved component intent locally.",
                                "adaptation_notes": (
                                    f"Exhausted {len(attempts)} bounded registry source attempts; "
                                    "the role remains an explicit execution gap."
                                ),
                            }
                        )
                    )
                    selection_warnings.append(
                        f"No component source passed validation for need '{selection.need_id}' after bounded alternates."
                    )
                else:
                    post_fetch_selections.append(
                        selection.model_copy(
                            update={
                                "selected_resource_id": resolved.resource_id,
                                "alternate_resource_ids": [
                                    item
                                    for item in ordered_ids
                                    if item != resolved.resource_id and item in candidate_by_id
                                ],
                                "why_selected": selection.why_selected
                                or "First closed-set registry candidate with valid local source and provenance.",
                            }
                        )
                    )
            candidates = list(candidate_by_id.values())
            candidate_by_id = {candidate.resource_id: candidate for candidate in candidates}
            qualifications = qualify_candidates(
                stage0.resource_needs,
                candidates,
                source_required=True,
                query_terms_by_need=query_terms_by_need,
            )
            selection_plan = selection_plan.model_copy(
                update={
                    "selections": post_fetch_selections,
                    "warnings": selection_warnings,
                }
            )
        validate_selection_plan(selection_plan, need_ids, candidates)
        await record(
            _event("stage_2_complete", "stage_2", "Resources selected or explicit gaps recorded.")
        )

        context_packet = build_resource_context_packet(
            content_architect=content or {},
            visual_design_director=visual,
            routes=stage0.routes,
            resource_needs=stage0.resource_needs,
            candidate_resources=candidate_payload,
            selections=[
                selection.model_dump(mode="json") for selection in selection_plan.selections
            ],
            provider_capabilities=base_resource_packet["provider_capabilities"],
            dependency_limits=base_resource_packet["dependency_limits"],
            query_history=[query.model_dump(mode="json") for query in query_plan.queries],
            provider_attempts=list(getattr(lookup, "provider_receipts", [])),
            previous_attempt_analysis=dict(payload.get("previous_attempt_analysis", {}) or {}),
            materialization_constraints=base_resource_packet["materialization_constraints"],
            quality_boundary=base_resource_packet["quality_boundary"],
        ).model_dump(mode="json")
        context_packet_hash = _packet_hash(context_packet)
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
                download_image=(
                    (lambda candidate: download_image(candidate, self._settings))
                    if live_providers
                    else None
                ),
                trigger_download=(
                    (lambda candidate: trigger_unsplash_download(candidate, self._settings))
                    if live_providers
                    else None
                ),
                root_override=staging_root,
            )
            if materialization.effective_selections:
                selection_plan = selection_plan.model_copy(
                    update={"selections": materialization.effective_selections}
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
                visual_input_mode=stage0.visual_input_mode,
                assumption_hash=stage0.assumption_hash,
                image_target=stage0.resource_targets.get("image_target", 0),
                component_target=stage0.resource_targets.get("component_target", 0),
                provider_calls=int(getattr(lookup, "calls_made", 0)) if live_providers else 0,
                cache_hits=int(getattr(lookup, "cache_hits", 0)) if live_providers else 0,
                rate_limit_events=int(getattr(lookup, "rate_limit_events", 0))
                if live_providers
                else 0,
                deferred_optional_roles=[],
            )
            if not live_model and not live_providers:
                handoff_report = handoff_report.model_copy(
                    update={
                        "handoff_eligible": False,
                        "status": "needs_attention",
                        "summary": "Offline Build Preparation output is diagnostic-only and cannot be handed to Code Generator.",
                        "issues": [
                            *handoff_report.issues,
                            HandoffIssue(
                                code="OFFLINE_DIAGNOSTIC_ONLY",
                                message="Offline model/provider mode cannot advertise a production-ready handoff.",
                                next_action="Run the normal workflow with the configured live model and providers.",
                            ),
                        ],
                    }
                )
            provider_calls = int(getattr(lookup, "calls_made", 0)) if live_providers else 0
            provider_rate_limit_events = (
                int(getattr(lookup, "rate_limit_events", 0)) if live_providers else 0
            )
            provider_cache_hits = int(getattr(lookup, "cache_hits", 0)) if live_providers else 0
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
                handoff_packet = {
                    "handoff_report": handoff_report.model_dump(mode="json"),
                    "resource_context_packet": context_packet,
                    "query_plan": query_plan.model_dump(mode="json"),
                    "candidate_resources": candidate_payload,
                    "candidate_qualifications": [
                        item.model_dump(mode="json") for item in qualifications
                    ],
                    "resource_needs": [
                        need.model_dump(mode="json") for need in stage0.resource_needs
                    ],
                    "selections": [
                        selection.model_dump(mode="json") for selection in selection_plan.selections
                    ],
                    "materialized_resources": materialization.resources,
                    "provider_attempts": list(getattr(lookup, "provider_receipts", [])),
                    "context_packet_hash": context_packet_hash,
                    "authority": {"model_may_not_grant_handoff": True},
                }
                try:
                    review, prompt_version, meta = await self._call_handoff_stage(
                        handoff_packet,
                        model_profile,
                    )
                except Exception as exc:
                    # Deterministic admission is authoritative. A live Stage 5
                    # review is advisory, so a provider rejection must retain
                    # the package for review while never granting eligibility.
                    error_code = str(
                        getattr(exc, "code", "MODEL_REVIEW_UNAVAILABLE")
                        or "MODEL_REVIEW_UNAVAILABLE"
                    )
                    handoff_report = handoff_report.model_copy(
                        update={
                            "handoff_eligible": False,
                            "status": "needs_attention",
                            "summary": (
                                "The deterministic handoff report is retained, but the live "
                                "Stage 5 review was unavailable."
                            ),
                            "issues": [
                                *handoff_report.issues,
                                HandoffIssue(
                                    code="MODEL_REVIEW_UNAVAILABLE",
                                    message=(
                                        "The live Stage 5 handoff review could not be completed; "
                                        "deterministic admission remains authoritative."
                                    ),
                                    next_action=(
                                        "Retry the live handoff review after the configured model "
                                        "provider accepts the request."
                                    ),
                                ),
                            ],
                            "model_review": {
                                "stage": "stage_5",
                                "mode": "live_model_unavailable",
                                "summary": "Live model review failed; no model eligibility decision was used.",
                                "error_code": error_code,
                            },
                        }
                    )
                    model_calls += 1
                    stages_meta.append(
                        {
                            "operation": "review_handoff_quality",
                            "status": "failed",
                            "error_code": error_code,
                            "input_packet_hash": _packet_hash(handoff_packet),
                        }
                    )
                    await self._emit_event(
                        _event(
                            "stage_5_model_review_failed",
                            "stage_5",
                            "Live handoff review failed; deterministic admission was retained.",
                            level="warning",
                            details={"error_code": error_code},
                        )
                    )
                else:
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
            run_analysis = {
                "schema_version": "build-preparation-run-analysis-v1",
                "input": {
                    "scope_hash": stage0.scope_hash,
                    "content_hash": stage0.source_ref.content_architect_content_hash,
                    "visual_direction_hash": stage0.source_ref.visual_design_director_direction_hash,
                    "approval_verified": handoff_report.upstream_approval_verified,
                    "visual_input_mode": stage0.visual_input_mode,
                    "assumption_hash": stage0.assumption_hash,
                    "assumptions": stage0.assumptions,
                },
                "derived_roles": [
                    {
                        "need_id": need.need_id,
                        "category": need.category,
                        "route_ids": need.route_ids,
                        "scene_ids": need.scene_ids,
                        "section_ids": need.section_ids,
                        "component_intent": (
                            need.component_intent.model_dump(mode="json")
                            if need.component_intent
                            else None
                        ),
                        "required": need.required_for_handoff,
                    }
                    for need in stage0.resource_needs
                ],
                "queries": [query.model_dump(mode="json") for query in query_plan.queries],
                "model_call_receipts": stages_meta,
                "provider_attempts": list(getattr(lookup, "provider_receipts", [])),
                "candidate_qualifications": [
                    item.model_dump(mode="json") for item in qualifications
                ],
                "selections": [item.model_dump(mode="json") for item in selection_plan.selections],
                "materialized_resources": materialization.resources,
                "role_failures": [issue.model_dump(mode="json") for issue in handoff_report.issues],
                "retryability": {
                    "provider_failures_retryable": any(
                        str(item.get("error_code", "")).upper()
                        in {"RATE_LIMITED", "PROVIDER_UNAVAILABLE"}
                        for item in getattr(lookup, "provider_receipts", [])
                    ),
                    "explicit_regeneration_required": bool(handoff_report.issues),
                },
                "recommended_next_action": (
                    "Review provider/source diagnostics and regenerate."
                    if handoff_report.issues
                    else "Proceed to Code Generator admission."
                ),
                "code_generator_eligible": handoff_report.handoff_eligible,
            }
            handoff_report = handoff_report.model_copy(update={"run_analysis": run_analysis})
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
        provider_calls = int(getattr(lookup, "calls_made", 0)) if live_providers else 0
        provider_rate_limit_events = (
            int(getattr(lookup, "rate_limit_events", 0)) if live_providers else 0
        )
        provider_cache_hits = int(getattr(lookup, "cache_hits", 0)) if live_providers else 0
        provider_receipts = list(getattr(lookup, "provider_receipts", [])) if live_providers else []
        handoff_report = handoff_report.model_copy(
            update={
                "handoff_summary": {
                    **handoff_report.handoff_summary,
                    "provider_calls": provider_calls,
                    "cache_hits": provider_cache_hits,
                    "rate_limit_events": provider_rate_limit_events,
                }
            }
        )
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
                "provider_calls": provider_calls,
                "provider_rate_limit_events": provider_rate_limit_events,
                "provider_cache_hits": provider_cache_hits,
                "provider_receipts": provider_receipts,
                "visual_input_mode": stage0.visual_input_mode,
                "assumption_hash": stage0.assumption_hash,
                "assumptions": stage0.assumptions,
                "context_packet_hash": context_packet_hash,
                "model_call_receipts": stages_meta,
            },
            prompt_version=prompt_version,
            model_metadata={
                "stages": stages_meta,
                "model_calls": model_calls,
                "provider_calls": provider_calls,
                "provider_rate_limit_events": provider_rate_limit_events,
                "provider_cache_hits": provider_cache_hits,
                "provider_receipts": provider_receipts,
                "visual_input_mode": stage0.visual_input_mode,
                "assumption_hash": stage0.assumption_hash,
                "context_packet_hash": context_packet_hash,
                "model_call_receipts": stages_meta,
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
        return model, version, _metadata(result, manifest, operation, packet)

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
        return model, version, _metadata(result, manifest, operation, packet)

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
        model = model.model_copy(
            update={
                "context": model.context.model_copy(
                    update={
                        "runtime_requirements": model.runtime_requirements
                        or model.context.runtime_requirements,
                        "fixed_facts": model.fixed_facts or model.context.fixed_facts,
                        "freedoms": model.freedoms or model.context.freedoms,
                        "warnings": model.warnings or model.context.warnings,
                    }
                )
            }
        )
        return model, version, _metadata(result, manifest, operation, packet)


def _metadata(
    result: Any, manifest: dict[str, str], operation: str, packet: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "operation": operation,
        "provider": str(getattr(result, "model", "") or ""),
        "model": str(getattr(result, "model", "") or ""),
        "response_id": str(getattr(result, "response_id", "") or ""),
        "usage": getattr(result, "usage", {}) or {},
        "latency_ms": getattr(result, "latency_ms", 0.0),
        "finish_reason": str(getattr(result, "finish_reason", "") or ""),
        "prompt_modules": manifest,
        "input_packet_hash": _packet_hash(packet) if packet is not None else "",
    }


def _packet_hash(packet: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _selected_ids(plan: Stage2SelectionPlan) -> set[str]:
    return {
        selection.selected_resource_id
        for selection in plan.selections
        if selection.selected_resource_id
    }


def _query_terms_by_need(plan: Stage1QueryPlan) -> dict[str, list[str]]:
    return {
        query.need_id: list(
            dict.fromkeys(
                [
                    *str(query.query or "").split(),
                    *[str(item) for item in query.provider_terms if str(item).strip()],
                ]
            )
        )
        for query in plan.queries
    }


def _complete_alternate_rankings(
    selections: list[ResourceSelection],
    candidates: list[FetchedResource],
    qualifications: list[Any],
) -> list[ResourceSelection]:
    """Fill alternate IDs only from the provider-returned closed candidate set."""
    by_need: dict[str, list[FetchedResource]] = {}
    for candidate in candidates:
        by_need.setdefault(candidate.need_id, []).append(candidate)
    qualification_order = {
        item.resource_id: (item.relevance_score, item.quality_score) for item in qualifications
    }
    result: list[ResourceSelection] = []
    for selection in selections:
        candidates_for_need = sorted(
            by_need.get(selection.need_id, []),
            key=lambda candidate: (
                -qualification_order.get(candidate.resource_id, (0, 0))[0],
                -qualification_order.get(candidate.resource_id, (0, 0))[1],
                candidate.resource_id,
            ),
        )
        closed_ids = {candidate.resource_id for candidate in candidates_for_need}
        ordered = list(
            dict.fromkeys(
                [
                    *selection.alternate_resource_ids,
                    *[candidate.resource_id for candidate in candidates_for_need],
                ]
            )
        )
        result.append(
            selection.model_copy(
                update={
                    "alternate_resource_ids": [
                        resource_id
                        for resource_id in ordered
                        if resource_id in closed_ids
                        and resource_id != selection.selected_resource_id
                    ]
                }
            )
        )
    return result


def _normalize_selection_ids(
    plan: Stage2SelectionPlan,
    candidates: list[FetchedResource],
    needs: list[Any],
) -> tuple[Stage2SelectionPlan, list[str]]:
    """Keep model-selected IDs inside the deterministic closed sets.

    The model is allowed to rank and explain returned candidates, but it is
    never allowed to create a need or candidate. A stale or invented ID becomes
    an explicit fallback so the deterministic pipeline can continue to
    materialization and report the resulting required-role gap instead of
    failing before analysis.
    """
    candidate_ids = {candidate.resource_id for candidate in candidates}
    need_by_id = {need.need_id: need for need in needs}
    warnings: list[str] = list(plan.warnings)
    selections_by_need: dict[str, ResourceSelection] = {}
    for selection in plan.selections:
        need = need_by_id.get(selection.need_id)
        if need is None:
            warnings.append(
                f"Model referenced unknown need '{selection.need_id}'; the selection was discarded."
            )
            continue
        if selection.need_id in selections_by_need:
            warnings.append(
                f"Model produced duplicate selections for need '{selection.need_id}'; the later selection was discarded."
            )
            continue
        selected_id = selection.selected_resource_id
        if selected_id and selected_id not in candidate_ids:
            warnings.append(
                f"Model selected resource '{selected_id}' for need '{selection.need_id}', "
                "but providers did not return it; the selection was discarded."
            )
            selected_id = None
        alternate_ids = [
            resource_id
            for resource_id in dict.fromkeys(selection.alternate_resource_ids)
            if resource_id in candidate_ids and resource_id != selected_id
        ]
        selections_by_need[selection.need_id] = selection.model_copy(
            update={
                "selected_resource_id": selected_id,
                "alternate_resource_ids": alternate_ids,
                "fallback": selection.fallback
                or need.fallback
                or "Implement the approved intent using the typed local fallback.",
            }
        )
    selections: list[ResourceSelection] = []
    for need in needs:
        selection = selections_by_need.get(need.need_id)
        if selection is None:
            warnings.append(
                f"Model did not produce a valid selection for need '{need.need_id}'; an explicit fallback was recorded."
            )
            selection = ResourceSelection(
                need_id=need.need_id,
                fallback=need.fallback
                or "Implement the approved intent using the typed local fallback.",
            )
        selections.append(selection)
    return plan.model_copy(update={"selections": selections}), warnings


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
