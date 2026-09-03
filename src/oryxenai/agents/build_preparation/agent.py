"""Build Preparation agent.

Compiles approved Content Architect + Visual Design Director output into two
Markdown briefs for Code Generator. The pipeline is: one deterministic scope
compilation (Stage 0, no I/O), one deterministic resource-research pass (real
provider search, no bytes), and at most one bounded model call
(``compose_visual_brief``) that may only pick among candidates it was
actually given. No ZIP, no object storage, no byte downloads -- Code
Generator's own acquisition adapters fetch bytes at generation time.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from oryxenai.agents.build_preparation.brief_assembly import (
    build_content_brief,
    build_visual_brief,
)
from oryxenai.agents.build_preparation.compiler import compile_stage0
from oryxenai.agents.build_preparation.debug_mirror import (
    resolve_debug_mirror_dir,
    write_debug_mirror,
)
from oryxenai.agents.build_preparation.prompt_builder import build_instructions
from oryxenai.agents.build_preparation.resource_research import classify_need, discover_resources
from oryxenai.agents.build_preparation.schemas import (
    BuildPreparationSourceRef,
    ComponentBriefEntry,
    ComponentGuidance,
    ResourceBriefEntry,
    ResourceGuidance,
    Stage0Result,
    StageEvent,
    VisualBriefOutput,
)
from oryxenai.agents.build_preparation.validators import (
    BuildPreparationValidationError,
    validate_visual_brief_output,
)
from oryxenai.agents.shared.contracts import Agent, AgentContext, AgentKey, AgentResult, ModelClient
from oryxenai.core.logging import get_logger

logger = get_logger("oryxenai.agents.build_preparation")


class BuildPreparationModelOutputError(BuildPreparationValidationError):
    """The model's structured output failed validation."""

    code = "BUILD_PREPARATION_MODEL_OUTPUT_INVALID"


def _event(
    stage: str, message: str, *, level: str = "info", details: dict[str, Any] | None = None
) -> StageEvent:
    return StageEvent(
        event_id=f"{stage}:{uuid4().hex[:8]}",
        stage=stage,
        level=level,  # type: ignore[arg-type]
        message=message,
        details=details or {},
        timestamp=datetime.now(UTC).isoformat(),
    )


def _source_ref_from_payload(value: Any) -> BuildPreparationSourceRef | None:
    if isinstance(value, dict) and value:
        try:
            return BuildPreparationSourceRef.model_validate(value)
        except ValueError:
            return None
    return None


def _apply_resource_guidance(
    entries: list[ResourceBriefEntry], guidance: list[ResourceGuidance]
) -> None:
    by_need = {item.need_id: item for item in guidance}
    for entry in entries:
        picked = by_need.get(entry.need_id)
        if picked is not None:
            entry.primary_candidate_index = picked.primary_candidate_index
            entry.guidance = picked.note


def _apply_component_guidance(
    entries: list[ComponentBriefEntry], guidance: list[ComponentGuidance]
) -> None:
    by_need = {item.need_id: item for item in guidance}
    for entry in entries:
        picked = by_need.get(entry.need_id)
        if picked is not None:
            entry.primary_suggestion_index = picked.primary_suggestion_index
            entry.guidance = picked.note


def _offline_visual_brief(
    resource_index: list[ResourceBriefEntry], component_index: list[ComponentBriefEntry]
) -> VisualBriefOutput:
    """Deterministic fallback used only when no live model call is requested."""
    prose = (
        "## Design language\n\n"
        "Offline fixture run: no model call was made. Use a clear, editorial "
        "treatment with generous whitespace, confident typography, and "
        "restrained motion until a live run supplies real direction.\n\n"
        "## Explicit authority statement\n\n"
        "Code Generator has final authority to adapt, replace, combine, or "
        "ignore any suggestion in this brief."
    )
    return VisualBriefOutput(
        visual_brief_prose=prose,
        resource_guidance=[
            ResourceGuidance(
                need_id=entry.need_id,
                primary_candidate_index=0 if entry.candidates else None,
                note="Offline placeholder guidance; regenerate with a live model call.",
            )
            for entry in resource_index
        ],
        component_guidance=[
            ComponentGuidance(
                need_id=entry.need_id,
                primary_suggestion_index=0 if entry.suggestions else None,
                note="Offline placeholder guidance; regenerate with a live model call.",
            )
            for entry in component_index
        ],
        seo_suggestions={},
        warnings=["This brief was generated offline without a model call."],
        assistant_summary="Offline fixture run.",
    )


class BuildPreparationAgent(Agent):
    key = AgentKey.BUILD_PREPARATION

    def __init__(
        self,
        *,
        model_client: ModelClient | None = None,
        settings: Any,
        live_model: bool = True,
        live_providers: bool = True,
        profile_name: str = "",
        event_sink: Any = None,
    ) -> None:
        self._model_client = model_client
        self._settings = settings
        self._live_model = live_model
        self._live_providers = live_providers
        self._profile_name = profile_name
        self._event_sink = event_sink

    async def run(self, context: AgentContext) -> AgentResult:
        agent_input = context.agent_input
        content_architect = agent_input.get("content_architect") or {}
        visual_design_director = agent_input.get("visual_design_director") or {}
        config = self._settings.build_preparation

        events: list[StageEvent] = []

        stage0 = compile_stage0(
            content_architect,
            visual_design_director,
            source_ref=_source_ref_from_payload(agent_input.get("source_ref")),
            max_routes=int(agent_input.get("max_routes", config.max_routes)),
            editorial_image_budget=int(config.editorial_image_budget),
            visual_component_budget=int(config.visual_component_budget),
            editorial_image_maximum=int(config.editorial_image_maximum),
            visual_component_maximum=int(config.visual_component_maximum),
            auto_derive_visual_resources=bool(
                agent_input.get("auto_derive_visual_resources", config.auto_derive_visual_resources)
            ),
        )
        events.extend(stage0.events)
        await self._emit(events[-1] if events else None)

        discovery = await discover_resources(
            stage0.resource_needs,
            self._settings,
            live_providers=self._live_providers,
            max_candidates_per_role=3,
        )
        discovery_event = _event(
            "resource_research",
            f"Discovered candidates for {len(discovery.resource_index)} resource role(s) "
            f"and {len(discovery.component_index)} component role(s).",
            details={"provider_calls": discovery.provider_calls},
        )
        events.append(discovery_event)
        await self._emit(discovery_event)

        model_calls = 0
        metadata: dict[str, Any] = {}
        prompt_version = "offline"
        if self._live_model:
            if self._model_client is None:
                raise BuildPreparationModelOutputError(
                    "Live mode requires a configured Build Preparation model client."
                )
            visual_output, prompt_version, metadata = await self._compose_visual_brief(
                stage0=stage0,
                visual_design_director=visual_design_director,
                discovery=discovery,
            )
            model_calls = 1
        else:
            visual_output = _offline_visual_brief(
                discovery.resource_index, discovery.component_index
            )

        _apply_resource_guidance(discovery.resource_index, visual_output.resource_guidance)
        _apply_component_guidance(discovery.component_index, visual_output.component_guidance)

        content_brief_markdown = build_content_brief(
            content_architect=content_architect,
            routes=stage0.routes,
            run_id=context.run_id,
            seo_suggestions=visual_output.seo_suggestions,
        )
        all_warnings = [*stage0.warnings, *visual_output.warnings]
        visual_brief_markdown = build_visual_brief(
            routes=stage0.routes,
            resource_index=discovery.resource_index,
            component_index=discovery.component_index,
            visual_brief_prose=visual_output.visual_brief_prose,
            target_contract=str(config.target_contract),
            recommended_dependencies=[],
            visual_input_mode=stage0.visual_input_mode,
            run_id=context.run_id,
            warnings=all_warnings,
        )

        debug_mirror_path = ""
        if bool(agent_input.get("debug_mirror", config.debug_mirror_enabled)):
            resolved_mirror_dir = str(agent_input.get("debug_mirror_dir", "") or "").strip()
            if not resolved_mirror_dir:
                resolved_mirror_dir = resolve_debug_mirror_dir(
                    str(agent_input.get("output_dir", "output")), context.run_id
                )
            debug_mirror_path = write_debug_mirror(
                resolved_mirror_dir,
                content_brief_markdown=content_brief_markdown,
                visual_brief_markdown=visual_brief_markdown,
            )

        complete_event = _event(
            "compose_visual_brief",
            "Composed both Markdown briefs.",
            details={"model_calls": model_calls},
        )
        events.append(complete_event)
        await self._emit(complete_event)

        output = {
            "scope_hash": stage0.scope_hash,
            "routes": [route.model_dump(mode="json") for route in stage0.routes],
            "resource_needs": [need.model_dump(mode="json") for need in stage0.resource_needs],
            "resource_index": [entry.model_dump(mode="json") for entry in discovery.resource_index],
            "component_index": [
                entry.model_dump(mode="json") for entry in discovery.component_index
            ],
            "content_brief_markdown": content_brief_markdown,
            "visual_brief_markdown": visual_brief_markdown,
            "target_contract": str(config.target_contract),
            "recommended_dependencies": [],
            "debug_mirror_path": debug_mirror_path,
            "warnings": all_warnings,
            "events": [event.model_dump(mode="json") for event in events],
            "model_calls": model_calls,
            "provider_calls": discovery.provider_calls,
            "visual_input_mode": stage0.visual_input_mode,
            "assumption_hash": stage0.assumption_hash,
            "assumptions": stage0.assumptions,
        }
        return AgentResult(output=output, prompt_version=prompt_version, model_metadata=metadata)

    async def _compose_visual_brief(
        self,
        *,
        stage0: Stage0Result,
        visual_design_director: dict[str, Any],
        discovery: Any,
    ) -> tuple[VisualBriefOutput, str, dict[str, Any]]:
        packet = {
            "visual_input_mode": stage0.visual_input_mode,
            "routes": [route.model_dump(mode="json") for route in stage0.routes],
            "visual_language": visual_design_director.get("visual_language", {}),
            "shared_visual_systems": visual_design_director.get("shared_visual_systems", {}),
            "motion_system": visual_design_director.get("motion_system", {}),
            "interaction_system": visual_design_director.get("interaction_system", {}),
            "accessibility_and_performance": visual_design_director.get(
                "accessibility_and_performance", {}
            ),
            "pages": visual_design_director.get("pages", []),
            "layout_pattern_needs": [
                need.model_dump(mode="json")
                for need in stage0.resource_needs
                if classify_need(need) == "custom"
            ],
            "resource_roles": [
                {
                    "need_id": entry.need_id,
                    "role_id": entry.role_id,
                    "category": entry.category,
                    "purpose": entry.purpose,
                    "route_ids": entry.route_ids,
                    "candidates": [
                        {"index": index, **candidate.model_dump(mode="json")}
                        for index, candidate in enumerate(entry.candidates)
                    ],
                }
                for entry in discovery.resource_index
            ],
            "component_roles": [
                {
                    "need_id": entry.need_id,
                    "role_id": entry.role_id,
                    "purpose": entry.purpose,
                    "route_ids": entry.route_ids,
                    "suggestions": [
                        {"index": index, **item.model_dump(mode="json")}
                        for index, item in enumerate(entry.suggestions)
                    ],
                }
                for entry in discovery.component_index
            ],
        }
        system_prompt, task_prompt, version, manifest = build_instructions(packet)
        assert self._model_client is not None
        result = await self._model_client.generate_structured(
            operation="compose_visual_brief",
            system_prompt=system_prompt,
            instructions=task_prompt,
            input_payload=packet,
            output_model=VisualBriefOutput,
            model_profile=self._profile_name,
        )
        try:
            output = VisualBriefOutput.model_validate(result.parsed_output)
        except ValueError as exc:
            raise BuildPreparationModelOutputError(
                f"Model output failed the VisualBriefOutput contract: {exc}"
            ) from exc
        need_ids = {need.need_id for need in stage0.resource_needs}
        candidate_counts = {
            entry.need_id: len(entry.candidates) for entry in discovery.resource_index
        }
        suggestion_counts = {
            entry.need_id: len(entry.suggestions) for entry in discovery.component_index
        }
        output = validate_visual_brief_output(
            output,
            need_ids=need_ids,
            candidate_counts=candidate_counts,
            suggestion_counts=suggestion_counts,
        )
        metadata = {
            "provider": result.model,
            "model": result.model,
            "response_id": result.response_id,
            "usage": result.usage,
            "latency_ms": result.latency_ms,
            "finish_reason": result.finish_reason,
            "prompt_modules": manifest,
        }
        return output, version, metadata

    async def _emit(self, event: StageEvent | None) -> None:
        if event is not None and self._event_sink is not None:
            await self._event_sink(event)
