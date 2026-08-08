"""Content Architect agent — turns an approved Discovery result into final,
grounded portfolio content and a site/route architecture.

Runs as a single durable job (`operation == "build"`) whose agent makes up to
three sequential model calls, adaptively:
  1. plan_content        (always): site strategy + route plan + grounding,
                          optionally with full content inlined already.
  2. write_pages         (only if stage 1 deferred content): batched final
                          content for every route in one call.
  3. integrate_content   (only if cross-route reconciliation is warranted):
                          terminology/nav consistency pass.

Never more than 3 model calls, never one call per page/section. The output
contract is the only validation gate, enforced by validators.py.
"""

from __future__ import annotations

from typing import Any

from oryxenai.agents.content_architect.prompt_builder import build_instructions
from oryxenai.agents.content_architect.schemas import ContentArchitectOutput
from oryxenai.agents.content_architect.validators import validate_stage_output
from oryxenai.agents.shared.contracts import Agent, AgentContext, AgentKey, AgentResult, ModelClient
from oryxenai.core.logging import get_logger
from oryxenai.core.settings import get_settings

logger = get_logger("oryxenai.agents.content_architect")

_INTEGRATION_ROUTE_THRESHOLD = 2


class ContentArchitectModelOutputError(Exception):
    """Raised when a stage's model output fails the output contract."""

    def __init__(self, operation: str, errors: list[str]) -> None:
        self.operation = operation
        self.errors = errors
        super().__init__(
            f"Content Architect {operation} output failed validation: {'; '.join(errors[:5])}"
        )


class ContentArchitectAgent(Agent):
    """Content Architect agent that uses an injected ModelClient."""

    key = AgentKey.CONTENT_ARCHITECT

    def __init__(self, model_client: ModelClient, profile_name: str = "") -> None:
        if model_client is None:
            raise ValueError("ContentArchitectAgent requires a model client")
        self._model_client = model_client
        self._config = get_settings().content_architect
        self._profile_name = profile_name

    async def run(self, context: AgentContext) -> AgentResult:
        operation = context.agent_input.get("operation", "build")
        if operation != "build":
            raise ValueError(f"Unknown Content Architect operation: {operation}")
        return await self._run_build(context)

    async def _run_build(self, context: AgentContext) -> AgentResult:
        agent_input = context.agent_input
        intake = self._intake_from(agent_input)
        preferences = dict(agent_input.get("preferences", {}) or {})
        prior_output = dict(agent_input.get("prior_output", {}) or {})
        revision_request = str(agent_input.get("revision_request", "") or "")

        stages_run: list[str] = []
        stages_meta: list[dict[str, Any]] = []

        # ── Stage 1: plan_content (always) ──────────────────────────────
        plan_packet = {
            "approved_brief_title": intake.get("approved_brief_title", ""),
            "user_summary": intake.get("user_summary", ""),
            "profile": intake.get("profile", {}),
            "open_items": intake.get("open_items", []),
            "preferences": preferences,
            "prior_output": prior_output,
            "revision_request": revision_request,
        }
        parsed_plan, version, meta_plan = await self._call_stage("plan_content", plan_packet)
        stages_run.append("plan_content")
        stages_meta.append(meta_plan)

        user_summary = str(parsed_plan.get("user_summary", "") or "")
        site_story_strategy = dict(parsed_plan.get("site_story_strategy") or {})
        decision_basis = list(parsed_plan.get("decision_basis") or [])
        route_plan = list(parsed_plan.get("route_plan") or [])
        claim_grounding = list(parsed_plan.get("claim_grounding") or [])
        omissions = list(parsed_plan.get("omissions") or [])
        unresolved_issues = list(parsed_plan.get("unresolved_issues") or [])
        privacy_and_confidentiality = list(parsed_plan.get("privacy_and_confidentiality") or [])
        media_status = dict(parsed_plan.get("media_status") or {})
        warnings = list(parsed_plan.get("warnings") or [])
        memory_update = dict(parsed_plan.get("memory_update") or {})
        page_content_packs = list(parsed_plan.get("page_content_packs") or [])
        public_content_manifest = dict(parsed_plan.get("public_content_manifest") or {})
        visual_director_handoff = dict(parsed_plan.get("visual_director_handoff") or {})

        content_included = bool(parsed_plan.get("content_included", False))
        integration_needed = bool(parsed_plan.get("integration_needed", False))

        # ── Stage 2: write_pages (only if stage 1 deferred content) ─────
        if not content_included:
            pages_packet = {
                "site_story_strategy": site_story_strategy,
                "route_plan": route_plan,
                "claim_grounding": claim_grounding,
                "preferences": preferences,
            }
            parsed_pages, version, meta_pages = await self._call_stage(
                "write_pages",
                pages_packet,
                known_route_plan=route_plan,
                known_claim_grounding=claim_grounding,
            )
            stages_run.append("write_pages")
            stages_meta.append(meta_pages)

            page_content_packs = list(parsed_pages.get("page_content_packs") or [])
            public_content_manifest = dict(parsed_pages.get("public_content_manifest") or {})
            if parsed_pages.get("visual_director_handoff"):
                visual_director_handoff = dict(parsed_pages.get("visual_director_handoff") or {})
            warnings.extend(parsed_pages.get("warnings") or [])
            decision_basis.extend(parsed_pages.get("decision_basis") or [])
            memory_update.update(parsed_pages.get("memory_update") or {})
            integration_needed = integration_needed or bool(
                parsed_pages.get("integration_needed", False)
            )

        if len(route_plan) > _INTEGRATION_ROUTE_THRESHOLD:
            integration_needed = True

        # ── Stage 3: integrate_content (only if warranted) ──────────────
        if integration_needed:
            integrate_packet = {
                "route_plan": route_plan,
                "claim_grounding": claim_grounding,
                "page_content_packs": page_content_packs,
                "public_content_manifest": public_content_manifest,
            }
            parsed_integrate, version, meta_integrate = await self._call_stage(
                "integrate_content",
                integrate_packet,
                known_route_plan=route_plan,
                known_claim_grounding=claim_grounding,
            )
            stages_run.append("integrate_content")
            stages_meta.append(meta_integrate)

            page_content_packs = list(
                parsed_integrate.get("page_content_packs") or page_content_packs
            )
            public_content_manifest = dict(
                parsed_integrate.get("public_content_manifest") or public_content_manifest
            )
            visual_director_handoff = dict(
                parsed_integrate.get("visual_director_handoff") or visual_director_handoff
            )
            warnings.extend(parsed_integrate.get("warnings") or [])
            decision_basis.extend(parsed_integrate.get("decision_basis") or [])
            memory_update.update(parsed_integrate.get("memory_update") or {})

        max_routes = self._config.max_routes
        if len(route_plan) > max_routes:
            route_plan = route_plan[:max_routes]
        if len(page_content_packs) > max_routes:
            page_content_packs = page_content_packs[:max_routes]

        logger.info(
            "content_architect build stages=%s routes=%d pages=%d",
            stages_run,
            len(route_plan),
            len(page_content_packs),
        )

        return AgentResult(
            output={
                "user_summary": user_summary,
                "site_story_strategy": site_story_strategy,
                "decision_basis": decision_basis,
                "route_plan": route_plan,
                "claim_grounding": claim_grounding,
                "page_content_packs": page_content_packs,
                "public_content_manifest": public_content_manifest,
                "omissions": omissions,
                "unresolved_issues": unresolved_issues,
                "privacy_and_confidentiality": privacy_and_confidentiality,
                "media_status": media_status,
                "visual_director_handoff": visual_director_handoff,
                "warnings": warnings,
                "stages_run": stages_run,
                "memory_update": memory_update,
            },
            prompt_version=version,
            model_metadata={"stages": stages_meta},
        )

    async def _call_stage(
        self,
        operation: str,
        source_packet: dict[str, Any],
        *,
        known_route_plan: list[dict[str, Any]] | None = None,
        known_claim_grounding: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], str, dict[str, Any]]:
        """Run one model call, validate its output, and return (parsed, version, metadata)."""
        system_prompt, task_prompt, version, manifest = build_instructions(
            operation=operation,
            source_packet=source_packet,
        )
        result = await self._model_client.generate_structured(
            operation=operation,
            system_prompt=system_prompt,
            instructions=task_prompt,
            input_payload=source_packet,
            output_model=ContentArchitectOutput,
            model_profile=self._profile_name,
        )
        parsed = _parsed_output(result)
        validation = validate_stage_output(
            parsed,
            operation,
            known_route_plan=known_route_plan,
            known_claim_grounding=known_claim_grounding,
        )
        if not validation.is_valid:
            raise ContentArchitectModelOutputError(operation, validation.errors)
        return parsed, version, _metadata(result, manifest, operation)

    @staticmethod
    def _intake_from(agent_input: dict[str, Any]) -> dict[str, Any]:
        raw = agent_input.get("intake", {})
        if not isinstance(raw, dict):
            return {}
        return {
            "approved_brief_title": str(raw.get("approved_brief_title", "") or ""),
            "user_summary": str(raw.get("user_summary", "") or ""),
            "profile": raw.get("profile", {}) or {},
            "open_items": raw.get("open_items", []) or [],
        }


def _parsed_output(result: Any) -> dict[str, Any]:
    from oryxenai.agents.discovery.schemas import StructuredModelResult

    if isinstance(result, StructuredModelResult):
        return result.parsed_output
    return dict(result.parsed_output)


def _metadata(result: Any, manifest: dict[str, str], operation: str) -> dict[str, Any]:
    return {
        "operation": operation,
        "provider": result.model,
        "model": result.model,
        "response_id": result.response_id,
        "usage": result.usage,
        "latency_ms": result.latency_ms,
        "finish_reason": result.finish_reason,
        "prompt_modules": manifest,
    }
