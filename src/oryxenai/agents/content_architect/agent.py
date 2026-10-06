"""Content Architect agent — turns an approved Explorer result into the final,
grounded copy for the one pinned single-page portfolio template.

Runs as a single durable job (`operation == "build"`) whose agent makes up to
three sequential model calls, adaptively:
  1. plan_content        (always): story strategy + grounding, optionally with
                          the full page content inlined already.
  2. write_pages         (only if stage 1 deferred content): the complete page
                          content tree in one call.
  3. integrate_content   (only if the writer flagged inconsistency, or the
                          approval-readiness gate found a repairable defect):
                          consistency/safety pass.

Never more than 3 model calls, never one call per section. The output
contract and deterministic approval-readiness gate are enforced before review.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from oryxenai.agents.content_architect.diagnostics import output_issue_locations
from oryxenai.agents.content_architect.field_paths import normalize_output_field_paths
from oryxenai.agents.content_architect.page_content import (
    atlas_page_errors,
    claim_binding_errors,
    coverage_errors,
    page_completeness_errors,
    page_shape_errors,
)
from oryxenai.agents.content_architect.prompt_builder import build_instructions
from oryxenai.agents.content_architect.schemas import (
    ClaimGrounding,
    ContentArchitectOutput,
    ContentCoverageEntry,
    ContentStoryStrategy,
    PortfolioPageContent,
)
from oryxenai.agents.content_architect.validators import validate_stage_output
from oryxenai.agents.shared.contracts import Agent, AgentContext, AgentKey, AgentResult, ModelClient
from oryxenai.agents.shared.model_cache import (
    StructuredResultCache,
    generate_with_cache,
    prompt_cache_context,
)
from oryxenai.agents.shared.providers.errors import ProviderError
from oryxenai.core.logging import get_logger

logger = get_logger("oryxenai.agents.content_architect")


class ContentArchitectModelOutputError(Exception):
    """Raised when a stage's model output fails the output contract."""

    def __init__(
        self,
        operation: str,
        errors: list[str],
        *,
        issues: list[dict[str, str]] | None = None,
    ) -> None:
        self.operation = operation
        self.errors = errors
        self.issues = issues if issues is not None else output_issue_locations(errors)
        super().__init__(
            f"Content Architect {operation} output failed validation: {'; '.join(errors[:5])}"
        )


class ContentArchitectAgent(Agent):
    """Content Architect agent that uses an injected ModelClient."""

    key = AgentKey.CONTENT_ARCHITECT

    def __init__(
        self,
        model_client: ModelClient,
        profile_name: str = "",
        *,
        result_cache: StructuredResultCache | None = None,
        profile_fingerprint: str = "",
    ) -> None:
        if model_client is None:
            raise ValueError("ContentArchitectAgent requires a model client")
        self._model_client = model_client
        self._profile_name = profile_name
        self._result_cache = result_cache
        self._profile_fingerprint = profile_fingerprint

    async def run(self, context: AgentContext) -> AgentResult:
        operation = context.agent_input.get("operation", "build")
        if operation != "build":
            raise ValueError(f"Unknown Content Architect operation: {operation}")
        return await self._run_build(context)

    async def _run_build(self, context: AgentContext) -> AgentResult:
        agent_input = context.agent_input
        intake = self._intake_from(agent_input)
        # The approved dossier already contains the subject, roles, projects,
        # and facts represented in the legacy profile. Keep the profile only
        # for older sessions that have no dossier.
        model_profile = intake.get("profile", {}) if not intake.get("dossier") else {}
        preferences = dict(agent_input.get("preferences", {}) or {})
        prior_output = dict(agent_input.get("prior_output", {}) or {})
        revision_request = str(agent_input.get("revision_request", "") or "")

        stages_run: list[str] = []
        stages_meta: list[dict[str, Any]] = []

        # ── Stage 1: plan_content (always) ──────────────────────────────
        plan_packet = {
            "selected_theme_id": intake.get("selected_theme_id", ""),
            "allow_illustrative_work": intake.get("allow_illustrative_work", False),
            "approved_brief_title": intake.get("approved_brief_title", ""),
            "user_summary": intake.get("user_summary", ""),
            "profile": model_profile,
            "dossier": intake.get("dossier", {}),
            "open_items": intake.get("open_items", []),
            "preferences": preferences,
            "prior_output": prior_output,
            "revision_request": revision_request,
        }
        parsed_plan, version, meta_plan = await self._call_stage(
            "plan_content", plan_packet, context=context
        )
        stages_run.append("plan_content")
        stages_meta.append(meta_plan)

        user_summary = str(parsed_plan.get("user_summary", "") or "")
        site_story_strategy = dict(parsed_plan.get("site_story_strategy") or {})
        decision_basis = list(parsed_plan.get("decision_basis") or [])
        claim_grounding = list(parsed_plan.get("claim_grounding") or [])
        coverage_ledger = list(parsed_plan.get("coverage_ledger") or [])
        omissions = list(parsed_plan.get("omissions") or [])
        unresolved_issues = list(parsed_plan.get("unresolved_issues") or [])
        privacy_and_confidentiality = list(parsed_plan.get("privacy_and_confidentiality") or [])
        warnings = list(parsed_plan.get("warnings") or [])
        memory_update = dict(parsed_plan.get("memory_update") or {})
        internal_notes = dict(parsed_plan.get("internal_notes") or {})
        page_content = dict(parsed_plan.get("page_content") or {})

        content_included = bool(parsed_plan.get("content_included", False))
        integration_needed = bool(parsed_plan.get("integration_needed", False))

        def absorb(parsed: dict[str, Any]) -> None:
            """Fold a later stage's refreshed page/claims/ledger into the working copy."""
            nonlocal page_content, claim_grounding, coverage_ledger, internal_notes, user_summary
            page_content = dict(parsed.get("page_content") or page_content)
            claim_grounding = list(parsed.get("claim_grounding") or claim_grounding)
            coverage_ledger = list(parsed.get("coverage_ledger") or coverage_ledger)
            internal_notes = {**internal_notes, **dict(parsed.get("internal_notes") or {})}
            warnings.extend(parsed.get("warnings") or [])
            decision_basis.extend(parsed.get("decision_basis") or [])
            memory_update.update(parsed.get("memory_update") or {})
            user_summary = str(parsed.get("user_summary") or user_summary)

        # ── Stage 2: write_pages (only if stage 1 deferred content) ─────
        if not content_included:
            pages_packet = {
                "selected_theme_id": intake.get("selected_theme_id", ""),
                "allow_illustrative_work": intake.get("allow_illustrative_work", False),
                "site_story_strategy": site_story_strategy,
                "claim_grounding": claim_grounding,
                "dossier": intake.get("dossier", {}),
                "profile": model_profile,
                "open_items": intake.get("open_items", []),
                "preferences": preferences,
            }
            parsed_pages, version, meta_pages = await self._call_stage(
                "write_pages",
                pages_packet,
                context=context,
                known_claim_grounding=claim_grounding,
            )
            stages_run.append("write_pages")
            stages_meta.append(meta_pages)
            absorb(parsed_pages)
            if not parsed_pages.get("user_summary"):
                user_summary = (
                    "Your complete portfolio page copy is ready to review. "
                    "Read each section and the evidence notes before approving it."
                )
            integration_needed = integration_needed or bool(
                parsed_pages.get("integration_needed", False)
            )

        # ── Stage 3: integrate_content (only if warranted) ──────────────
        if integration_needed:
            integrate_packet = {
                "selected_theme_id": intake.get("selected_theme_id", ""),
                "allow_illustrative_work": intake.get("allow_illustrative_work", False),
                "page_content": page_content,
                "claim_grounding": claim_grounding,
                "coverage_ledger": coverage_ledger,
                "dossier": intake.get("dossier", {}),
            }
            parsed_integrate, version, meta_integrate = await self._call_stage(
                "integrate_content",
                integrate_packet,
                context=context,
                known_claim_grounding=claim_grounding,
            )
            stages_run.append("integrate_content")
            stages_meta.append(meta_integrate)
            absorb(parsed_integrate)

        # Approval must be a formality after review, never the first place we
        # discover that public content contradicts its own publication gates.
        # Use one of the existing three bounded calls as a corrective
        # integration pass when capacity remains; otherwise fail before the
        # unapprovable output can be presented as ready for review.
        dossier = intake.get("dossier", {})
        readiness_errors = _approval_readiness_errors(
            page_content=page_content,
            claim_grounding=claim_grounding,
            coverage_ledger=coverage_ledger,
            dossier=dossier,
            selected_theme_id=str(intake.get("selected_theme_id", "")),
            allow_illustrative_work=bool(intake.get("allow_illustrative_work", False)),
        )
        if readiness_errors and len(stages_run) < 3:
            repair_packet = {
                "selected_theme_id": intake.get("selected_theme_id", ""),
                "allow_illustrative_work": intake.get("allow_illustrative_work", False),
                "page_content": page_content,
                "claim_grounding": claim_grounding,
                "coverage_ledger": coverage_ledger,
                "approval_readiness_errors": readiness_errors,
                "dossier": dossier,
            }
            parsed_repair, version, meta_repair = await self._call_stage(
                "integrate_content",
                repair_packet,
                context=context,
                known_claim_grounding=claim_grounding,
            )
            stages_run.append("integrate_content")
            stages_meta.append(meta_repair)
            absorb(parsed_repair)
            readiness_errors = _approval_readiness_errors(
                page_content=page_content,
                claim_grounding=claim_grounding,
                coverage_ledger=coverage_ledger,
                dossier=dossier,
                selected_theme_id=str(intake.get("selected_theme_id", "")),
                allow_illustrative_work=bool(intake.get("allow_illustrative_work", False)),
            )
        if readiness_errors:
            issue_locations = _unpopulated_coverage_paths(page_content, coverage_ledger)
            raise ContentArchitectModelOutputError(
                "approval_readiness",
                readiness_errors,
                issues=issue_locations or output_issue_locations(readiness_errors),
            )

        try:
            normalized_strategy = ContentStoryStrategy.model_validate(site_story_strategy)
            normalized_page = PortfolioPageContent.model_validate(page_content)
            normalized_claims = [ClaimGrounding.model_validate(c) for c in claim_grounding]
            normalized_ledger = [ContentCoverageEntry.model_validate(e) for e in coverage_ledger]
        except ValidationError as exc:
            raise ContentArchitectModelOutputError(
                "build", [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:5]]
            ) from exc

        logger.info(
            "content_architect build stages=%s pillars=%d groups=%d",
            stages_run,
            len(normalized_page.systems_practice.pillars),
            len(normalized_page.technical_capabilities.groups),
        )

        return AgentResult(
            output={
                "user_summary": user_summary,
                "site_story_strategy": normalized_strategy.model_dump(mode="json"),
                "decision_basis": decision_basis,
                "page_content": normalized_page.model_dump(mode="json"),
                "claim_grounding": [c.model_dump(mode="json") for c in normalized_claims],
                "coverage_ledger": [e.model_dump(mode="json") for e in normalized_ledger],
                "internal_notes": internal_notes,
                "omissions": omissions,
                "unresolved_issues": unresolved_issues,
                "privacy_and_confidentiality": privacy_and_confidentiality,
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
        context: AgentContext,
        known_claim_grounding: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], str, dict[str, Any]]:
        """Run one model call, validate its output, and return (parsed, version, metadata)."""
        system_prompt, task_prompt, version, manifest = build_instructions(
            operation=operation,
            source_packet=source_packet,
        )

        def validate(parsed: dict[str, Any]) -> None:
            validation = validate_stage_output(
                parsed,
                operation,
                known_claim_grounding=known_claim_grounding,
            )
            if not validation.is_valid:
                raise ContentArchitectModelOutputError(operation, validation.errors)

        try:
            result = await generate_with_cache(
                client=self._model_client,
                result_cache=self._result_cache,
                agent_key=self.key.value,
                operation=operation,
                system_prompt=system_prompt,
                instructions=task_prompt,
                input_payload=source_packet,
                output_model=ContentArchitectOutput,
                model_profile=self._profile_name,
                profile_fingerprint=self._profile_fingerprint,
                request_context=prompt_cache_context(self.key.value, operation, manifest, context),
                strict_schema=False,
                validator=validate,
            )
        except ProviderError as exc:
            exc.details.setdefault("suboperation", operation)
            if isinstance(exc.__cause__, ContentArchitectModelOutputError):
                exc.details["issue_count"] = len(exc.__cause__.errors)
                exc.details["issues"] = exc.__cause__.issues
            raise
        # Cached responses take this same boundary as fresh provider responses.
        # A previous run may have cached a stage-valid output with paths rooted
        # at the JSON property name rather than at the page object.
        parsed = normalize_output_field_paths(_parsed_output(result))
        validate(parsed)
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
            "dossier": raw.get("dossier", {}) or {},
            "open_items": raw.get("open_items", []) or [],
            "selected_theme_id": str(raw.get("selected_theme_id", "") or ""),
            "allow_illustrative_work": bool(raw.get("allow_illustrative_work", False)),
        }


def _approval_readiness_errors(
    *,
    page_content: dict[str, Any],
    claim_grounding: list[dict[str, Any]],
    coverage_ledger: list[dict[str, Any]] | None = None,
    dossier: dict[str, Any] | None = None,
    selected_theme_id: str = "",
    allow_illustrative_work: bool = False,
) -> list[str]:
    """Deterministic gate mirroring what approval will enforce later."""
    return [
        *page_shape_errors(page_content),
        *page_completeness_errors(page_content),
        *(
            atlas_page_errors(page_content, allow_illustrative_work=allow_illustrative_work)
            if selected_theme_id == "cobalt-atlas/v2"
            else []
        ),
        *claim_binding_errors(page_content, claim_grounding),
        *coverage_errors(dossier or {}, coverage_ledger or [], page_content),
    ]


def _unpopulated_coverage_paths(
    page_content: dict[str, Any], coverage_ledger: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """Return bounded, copy-safe path locations without any portfolio copy."""
    from oryxenai.agents.content_architect.page_content import path_is_populated

    issues: list[dict[str, str]] = []
    for entry in coverage_ledger:
        if not isinstance(entry, dict) or entry.get("disposition") not in {"used", "condensed"}:
            continue
        source_id = entry.get("source_id")
        paths = entry.get("field_paths")
        if not isinstance(source_id, str) or not isinstance(paths, list):
            continue
        for path in paths:
            if isinstance(path, str) and not path_is_populated(page_content, path):
                issues.append(
                    {"code": "coverage_path_unpopulated", "source_id": source_id, "path": path}
                )
                if len(issues) >= 12:
                    return issues
                break
    return issues


def _parsed_output(result: Any) -> dict[str, Any]:
    from oryxenai.agents.discovery.schemas import StructuredModelResult

    if isinstance(result, StructuredModelResult):
        return result.parsed_output
    return dict(result.parsed_output)


def _metadata(result: Any, manifest: dict[str, str], operation: str) -> dict[str, Any]:
    return {
        "operation": operation,
        "provider": str(result.telemetry.get("provider", "") or ""),
        "model": result.model,
        "response_id": result.response_id,
        "usage": result.usage,
        "latency_ms": result.latency_ms,
        "finish_reason": result.finish_reason,
        "prompt_modules": manifest,
        "telemetry": result.telemetry,
        "cache": result.cache_metadata,
    }
