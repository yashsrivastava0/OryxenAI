"""Visual Design Director agent — converts an approved Content Architect
output into a complete visual-experience direction.

Runs as a single durable job (`operation == "build"`) whose agent makes up to
three sequential model calls, adaptively:
  1. establish_visual_language  (always): site-wide visual language + shared
                                 systems, optionally with full per-route
                                 direction inlined already.
  2. direct_page_experience     (only if stage 1 deferred pages): batched
                                 final direction for every route in one call.
  3. integrate_site_experience  (only if warranted): cross-page
                                 reconciliation pass.

Never more than 3 model calls, never one call per page/scene. The output
contract is the only validation gate, enforced by validators.py. Mirrors
Content Architect's agent.py architecture exactly.
"""

from __future__ import annotations

from typing import Any

from oryxenai.agents.shared.contracts import Agent, AgentContext, AgentKey, AgentResult, ModelClient
from oryxenai.agents.visual_design_director.prompt_builder import build_instructions
from oryxenai.agents.visual_design_director.resource_catalogue import find_candidates
from oryxenai.agents.visual_design_director.schemas import VisualDesignDirectorOutput
from oryxenai.agents.visual_design_director.validators import validate_stage_output
from oryxenai.core.logging import get_logger
from oryxenai.core.settings import get_settings

logger = get_logger("oryxenai.agents.visual_design_director")

_INTEGRATION_ROUTE_THRESHOLD = 2


class VisualDesignDirectorModelOutputError(Exception):
    """Raised when a stage's model output fails the output contract."""

    def __init__(self, operation: str, errors: list[str]) -> None:
        self.operation = operation
        self.errors = errors
        super().__init__(
            f"Visual Design Director {operation} output failed validation: {'; '.join(errors[:5])}"
        )


class VisualDesignDirectorAgent(Agent):
    """Visual Design Director agent that uses an injected ModelClient."""

    key = AgentKey.VISUAL_DESIGN_DIRECTOR

    def __init__(self, model_client: ModelClient, profile_name: str = "") -> None:
        if model_client is None:
            raise ValueError("VisualDesignDirectorAgent requires a model client")
        self._model_client = model_client
        self._config = get_settings().visual_design_director
        self._profile_name = profile_name

    async def run(self, context: AgentContext) -> AgentResult:
        operation = context.agent_input.get("operation", "build")
        if operation != "build":
            raise ValueError(f"Unknown Visual Design Director operation: {operation}")
        return await self._run_build(context)

    async def _run_build(self, context: AgentContext) -> AgentResult:
        agent_input = context.agent_input
        intake = self._intake_from(agent_input)
        preferences = dict(agent_input.get("preferences", {}) or {})
        prior_output = dict(agent_input.get("prior_output", {}) or {})
        revision_request = str(agent_input.get("revision_request", "") or "")

        route_plan = list(intake.get("route_plan", []) or [])

        # Resource catalogue shortlist is computed ONCE, before stage 1, and
        # reused unchanged across every stage of this run — a resource_id a
        # model picks in an earlier stage must still be valid when a later
        # stage's validator checks it.
        catalogue_shortlist = find_candidates(
            _collect_catalogue_tags(intake), limit=self._config.max_catalogue_candidates
        )
        known_resource_ids = {
            str(entry.get("resource_id", ""))
            for entry in catalogue_shortlist
            if entry.get("resource_id")
        }
        catalogue_for_prompt = [
            {key: value for key, value in entry.items() if key != "tags"}
            for entry in catalogue_shortlist
        ]

        stages_run: list[str] = []
        stages_meta: list[dict[str, Any]] = []

        # ── Stage 1: establish_visual_language (always) ─────────────────
        language_packet = {
            "presentation_mode": intake.get("presentation_mode", ""),
            "site_story_strategy": intake.get("site_story_strategy", {}),
            "route_plan": route_plan,
            "page_content_packs": intake.get("page_content_packs", []),
            "public_content_manifest": intake.get("public_content_manifest", {}),
            "media_status": intake.get("media_status", {}),
            "visual_director_handoff": intake.get("visual_director_handoff", {}),
            "privacy_and_confidentiality": intake.get("privacy_and_confidentiality", []),
            "preferences": preferences,
            "resource_catalogue_shortlist": catalogue_for_prompt,
            "prior_output": prior_output,
            "revision_request": revision_request,
        }
        parsed_language, version, meta_language = await self._call_stage(
            "establish_visual_language",
            language_packet,
            known_route_plan=route_plan,
            known_resource_ids=known_resource_ids,
        )
        stages_run.append("establish_visual_language")
        stages_meta.append(meta_language)

        user_summary = str(parsed_language.get("user_summary", "") or "")
        meta = dict(parsed_language.get("meta") or {})
        visual_language = dict(parsed_language.get("visual_language") or {})
        shared_visual_systems = dict(parsed_language.get("shared_visual_systems") or {})
        navigation_direction = dict(parsed_language.get("navigation_direction") or {})
        motion_system = dict(parsed_language.get("motion_system") or {})
        interaction_system = dict(parsed_language.get("interaction_system") or {})
        accessibility_and_performance = dict(
            parsed_language.get("accessibility_and_performance") or {}
        )
        must_preserve = list(parsed_language.get("must_preserve") or [])
        must_not_fabricate = list(parsed_language.get("must_not_fabricate") or [])
        conflicts = list(parsed_language.get("conflicts") or [])
        warnings = list(parsed_language.get("warnings") or [])
        memory_update = dict(parsed_language.get("memory_update") or {})
        pages = list(parsed_language.get("pages") or [])
        asset_briefs = list(parsed_language.get("asset_briefs") or [])
        resource_candidates = list(parsed_language.get("resource_candidates") or [])
        compiler_handoff = dict(parsed_language.get("compiler_handoff") or {})

        pages_included = bool(parsed_language.get("pages_included", False))
        integration_needed = bool(parsed_language.get("integration_needed", False))

        # ── Stage 2: direct_page_experience (only if stage 1 deferred pages) ──
        if not pages_included:
            pages_packet = {
                "visual_language": visual_language,
                "shared_visual_systems": shared_visual_systems,
                "route_plan": route_plan,
                "page_content_packs": intake.get("page_content_packs", []),
                "media_status": intake.get("media_status", {}),
                "visual_director_handoff": intake.get("visual_director_handoff", {}),
                "preferences": preferences,
                "resource_catalogue_shortlist": catalogue_for_prompt,
                "prior_output": prior_output,
                "revision_request": revision_request,
            }
            parsed_pages, version, meta_pages = await self._call_stage(
                "direct_page_experience",
                pages_packet,
                known_route_plan=route_plan,
                known_resource_ids=known_resource_ids,
            )
            stages_run.append("direct_page_experience")
            stages_meta.append(meta_pages)

            pages = list(parsed_pages.get("pages") or [])
            asset_briefs = list(parsed_pages.get("asset_briefs") or [])
            resource_candidates = list(parsed_pages.get("resource_candidates") or [])
            if parsed_pages.get("shared_visual_systems"):
                shared_visual_systems = dict(parsed_pages.get("shared_visual_systems") or {})
            if parsed_pages.get("navigation_direction"):
                navigation_direction = dict(parsed_pages.get("navigation_direction") or {})
            if parsed_pages.get("motion_system"):
                motion_system = dict(parsed_pages.get("motion_system") or {})
            if parsed_pages.get("user_summary"):
                # Stage 1's user_summary may have correctly described a
                # deferral ("route direction isn't ready yet"); once stage 2
                # actually produces the pages, that claim is stale — prefer
                # stage 2's own description of what it actually produced.
                user_summary = str(parsed_pages.get("user_summary") or user_summary)
            warnings.extend(parsed_pages.get("warnings") or [])
            conflicts.extend(parsed_pages.get("conflicts") or [])
            memory_update.update(parsed_pages.get("memory_update") or {})
            integration_needed = integration_needed or bool(
                parsed_pages.get("integration_needed", False)
            )

        if len(route_plan) > _INTEGRATION_ROUTE_THRESHOLD:
            integration_needed = True
        # Never integrate a literal single route — nothing to reconcile
        # against, even if a stage mistakenly flagged integration_needed.
        run_integration = integration_needed and len(route_plan) > 1

        # ── Stage 3: integrate_site_experience (only if warranted) ──────
        if run_integration:
            integrate_packet = {
                "visual_language": visual_language,
                "shared_visual_systems": shared_visual_systems,
                "navigation_direction": navigation_direction,
                "motion_system": motion_system,
                "pages": pages,
                "asset_briefs": asset_briefs,
                "resource_candidates": resource_candidates,
                "resource_catalogue_shortlist": catalogue_for_prompt,
            }
            parsed_integrate, version, meta_integrate = await self._call_stage(
                "integrate_site_experience",
                integrate_packet,
                known_route_plan=route_plan,
                known_resource_ids=known_resource_ids,
            )
            stages_run.append("integrate_site_experience")
            stages_meta.append(meta_integrate)

            pages = list(parsed_integrate.get("pages") or pages)
            asset_briefs = list(parsed_integrate.get("asset_briefs") or asset_briefs)
            resource_candidates = list(
                parsed_integrate.get("resource_candidates") or resource_candidates
            )
            if parsed_integrate.get("shared_visual_systems"):
                shared_visual_systems = dict(parsed_integrate.get("shared_visual_systems") or {})
            if parsed_integrate.get("navigation_direction"):
                navigation_direction = dict(parsed_integrate.get("navigation_direction") or {})
            if parsed_integrate.get("motion_system"):
                motion_system = dict(parsed_integrate.get("motion_system") or {})
            if parsed_integrate.get("user_summary"):
                user_summary = str(parsed_integrate.get("user_summary") or user_summary)
            conflicts.extend(parsed_integrate.get("conflicts") or [])
            warnings.extend(parsed_integrate.get("warnings") or [])
            memory_update.update(parsed_integrate.get("memory_update") or {})
            compiler_handoff = dict(parsed_integrate.get("compiler_handoff") or compiler_handoff)

        max_pages = self._config.max_pages
        if len(pages) > max_pages:
            pages = pages[:max_pages]

        # Every field set below is deterministically owned by agent.py, never
        # trusted from the model — this is what closes the class of bug where
        # a stage's free-text narrative (user_summary/meta/compiler_handoff)
        # goes stale once a LATER stage actually produces the pages an
        # earlier stage deferred. publication_status/compilable in
        # particular are the authoritative signal a future Blueprint
        # Compiler must gate on instead of trusting prose.
        pages, page_compilability = _stamp_page_compilability(pages, route_plan)
        resource_candidates = _stamp_resource_candidates(resource_candidates)

        compiler_handoff = dict(compiler_handoff)
        compiler_handoff["pages_compilable"] = page_compilability

        meta = dict(meta)
        meta["final_operation"] = stages_run[-1] if stages_run else ""
        meta["stages_run"] = list(stages_run)
        meta["model_profile"] = self._profile_name
        meta["prompt_version"] = version

        # source_refs is always deterministically overwritten here, never
        # trusted from the model — see schemas.py's VisualDesignDirectorOutput
        # docstring for why this differs from the persisted source_ref.
        source_refs = {
            "content_architect_content_hash": intake.get("content_architect_content_hash", ""),
            "content_architect_session_revision": intake.get(
                "content_architect_session_revision", 0
            ),
            "route_ids_covered": [
                page.get("route_id", "") for page in pages if isinstance(page, dict)
            ],
        }

        logger.info(
            "visual_design_director build stages=%s pages=%d assets=%d resources=%d",
            stages_run,
            len(pages),
            len(asset_briefs),
            len(resource_candidates),
        )

        return AgentResult(
            output={
                "user_summary": user_summary,
                "meta": meta,
                "source_refs": source_refs,
                "visual_language": visual_language,
                "shared_visual_systems": shared_visual_systems,
                "navigation_direction": navigation_direction,
                "motion_system": motion_system,
                "interaction_system": interaction_system,
                "pages": pages,
                "asset_briefs": asset_briefs,
                "resource_candidates": resource_candidates,
                "accessibility_and_performance": accessibility_and_performance,
                "must_preserve": must_preserve,
                "must_not_fabricate": must_not_fabricate,
                "conflicts": conflicts,
                "warnings": warnings,
                "compiler_handoff": compiler_handoff,
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
        known_resource_ids: set[str] | None = None,
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
            output_model=VisualDesignDirectorOutput,
            model_profile=self._profile_name,
        )
        parsed = _parsed_output(result)
        validation = validate_stage_output(
            parsed,
            operation,
            known_route_plan=known_route_plan,
            known_resource_ids=known_resource_ids,
        )
        if not validation.is_valid:
            raise VisualDesignDirectorModelOutputError(operation, validation.errors)
        return parsed, version, _metadata(result, manifest, operation)

    @staticmethod
    def _intake_from(agent_input: dict[str, Any]) -> dict[str, Any]:
        raw = agent_input.get("intake", {})
        if not isinstance(raw, dict):
            return {}
        return {
            "content_architect_content_hash": str(
                raw.get("content_architect_content_hash", "") or ""
            ),
            "content_architect_session_revision": int(
                raw.get("content_architect_session_revision", 0) or 0
            ),
            "presentation_mode": str(raw.get("presentation_mode", "") or ""),
            "site_story_strategy": raw.get("site_story_strategy", {}) or {},
            "route_plan": raw.get("route_plan", []) or [],
            "page_content_packs": raw.get("page_content_packs", []) or [],
            "public_content_manifest": raw.get("public_content_manifest", {}) or {},
            "media_status": raw.get("media_status", {}) or {},
            "visual_director_handoff": raw.get("visual_director_handoff", {}) or {},
            "privacy_and_confidentiality": raw.get("privacy_and_confidentiality", []) or [],
        }


def _stamp_page_compilability(
    pages: list[Any], route_plan: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, bool]]:
    """Deterministically stamp publication_status/compilable onto every page
    from the known Content Architect route_plan — never trusting the model
    to describe this itself. A page for a route CA marked "pending" keeps
    its full scene-level content (mirrors CA's own precedent of planning
    pending content, just gated) but is marked compilable=False. Returns the
    stamped pages plus a route_id -> compilable map for compiler_handoff.
    """
    status_by_route: dict[str, str] = {}
    for route in route_plan:
        if isinstance(route, dict):
            route_id = str(route.get("route_id", "") or "")
            if route_id:
                status_by_route[route_id] = str(
                    route.get("publication_status", "approved") or "approved"
                )

    stamped: list[dict[str, Any]] = []
    compilability: dict[str, bool] = {}
    for page in pages:
        if not isinstance(page, dict):
            stamped.append(page)
            continue
        route_id = str(page.get("route_id", "") or "")
        status = status_by_route.get(route_id, "approved")
        if status not in {"approved", "pending"}:
            # "blocked" routes never reach this point (validators.py hard-
            # rejects them first); anything else unrecognized is treated as
            # not-yet-compilable rather than silently assumed approved.
            status = "pending"
        new_page = dict(page)
        new_page["publication_status"] = status
        new_page["compilable"] = status == "approved"
        stamped.append(new_page)
        if route_id:
            compilability[route_id] = new_page["compilable"]
    return stamped, compilability


def _stamp_resource_candidates(resource_candidates: list[Any]) -> list[dict[str, Any]]:
    """Deterministically attach catalogue provenance to every resource
    candidate that survived validation — never model-authored. By
    construction every candidate here already passed validators.py's
    known_resource_ids check, so lookup_status is "verified" whenever the
    catalogue lookup succeeds (the "unverified" branch is defensive only).
    """
    from oryxenai.agents.visual_design_director.resource_catalogue import (
        catalogue_version,
        get_entry,
    )

    version = catalogue_version()
    stamped: list[dict[str, Any]] = []
    for candidate in resource_candidates:
        if not isinstance(candidate, dict):
            stamped.append(candidate)
            continue
        resource_id = str(candidate.get("resource_id", "") or "")
        entry = get_entry(resource_id) if resource_id else None
        new_candidate = dict(candidate)
        new_candidate["category"] = str(entry.get("category", "")) if entry else ""
        new_candidate["resource_library_version"] = version
        new_candidate["lookup_status"] = "verified" if entry else "unverified"
        stamped.append(new_candidate)
    return stamped


def _collect_catalogue_tags(intake: dict[str, Any]) -> list[str]:
    """Deterministic tag set for the resource-catalogue shortlist, built only
    from structural facts already present in the intake — never free-text
    parsing.
    """
    tags: list[str] = []
    presentation_mode = str(intake.get("presentation_mode", "") or "")
    if presentation_mode:
        tags.append(presentation_mode)

    handoff = intake.get("visual_director_handoff", {}) or {}
    if handoff.get("unavailable_media"):
        tags.append("no-media")
    if handoff.get("diagram_opportunities"):
        tags.append("diagram")
    if handoff.get("storytelling_opportunities"):
        tags.append("narrative")

    for route in intake.get("route_plan", []) or []:
        if isinstance(route, dict):
            density = str(route.get("content_density", "") or "")
            if density and density not in tags:
                tags.append(density)

    return tags


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
