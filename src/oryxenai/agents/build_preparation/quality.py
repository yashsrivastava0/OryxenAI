"""Deterministic admission checks for provider resources and agent handoff."""

from __future__ import annotations

import re
from typing import Any

from oryxenai.agents.build_preparation.materializer import dependencies_allowed
from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    BuildPreparationSourceRef,
    CandidateQualification,
    FetchedResource,
    HandoffIssue,
    HandoffQualityReport,
    MaterializationResult,
    ResourceNeed,
    ResourceSelection,
    RouteScope,
)

_CUSTOM_CATEGORIES = frozenset({"hero_pattern", "background_system", "diagram_primitive"})
_GENERIC_TERMS = frozenset(
    {
        "adapt",
        "background",
        "component",
        "composition",
        "custom",
        "diagram",
        "image",
        "pattern",
        "resource",
        "static",
        "text",
        "visual",
    }
)
_PROHIBITED_IMAGE_TERMS = frozenset(
    {
        "dashboard",
        "face",
        "laptop screen",
        "logo",
        "portrait",
        "screenshot",
        "smartphone",
        "user interface",
    }
)


def normalize_query_plan(plan: Any, needs: list[ResourceNeed]) -> Any:
    """Keep model query intent inside the fixed visual and provider policy."""
    by_id = {need.need_id: need for need in needs}
    queries = []
    for query in plan.queries:
        need = by_id[query.need_id]
        update: dict[str, Any] = {
            "required_for_handoff": need.required_for_handoff,
            "allowed_providers": ["pexels"] if need.required_for_handoff else [],
        }
        photo_need = need.kind == "asset" and any(
            token in f"{need.category} {need.purpose}".lower()
            for token in ("editorial", "image", "photo", "portrait")
        )
        if need.required_for_handoff or photo_need:
            update["kind"] = "photo"
            update["orientation"] = str(need.details.get("orientation", "landscape") or "landscape")
            update["allowed_providers"] = (
                ["pexels"] if need.required_for_handoff else ["pexels", "unsplash"]
            )
        elif need.category in _CUSTOM_CATEGORIES:
            update["kind"] = "custom"
            update["allowed_providers"] = []
        queries.append(query.model_copy(update=update))
    return plan.model_copy(update={"queries": queries})


def qualify_candidates(
    needs: list[ResourceNeed], candidates: list[FetchedResource]
) -> list[CandidateQualification]:
    """Admit only candidates that can actually satisfy this static-client handoff."""
    need_by_id = {need.need_id: need for need in needs}
    return [_qualify(need_by_id[candidate.need_id], candidate) for candidate in candidates]


def _qualify(need: ResourceNeed, candidate: FetchedResource) -> CandidateQualification:
    reasons: list[str] = []
    codes: list[str] = []
    policy_status = "approved"
    technical_status = "approved"
    relevance = 70
    quality = 70

    if candidate.kind == "photo":
        if candidate.provider != "pexels" and need.required_for_handoff:
            technical_status = "rejected"
            codes.append("REMOTE_ASSET_NOT_ALLOWED")
            reasons.append("Required images must be materialized locally for the static target.")
        if candidate.width < 1200 or candidate.height < 700:
            quality = 0
            codes.append("IMAGE_RESOLUTION_TOO_LOW")
            reasons.append("Image dimensions are below the 1200x700 handoff minimum.")
        if candidate.provider == "unsplash" and candidate.hotlink_url.startswith("https://"):
            technical_status = "rejected"
            codes.append("REMOTE_ASSET_NOT_ALLOWED")
            reasons.append(
                "Unsplash hotlinking conflicts with the static target's no-remote-runtime-assets contract."
            )
        elif not candidate.image_url.startswith("https://"):
            technical_status = "rejected"
            codes.append("IMAGE_SOURCE_MISSING")
            reasons.append("The provider did not supply a downloadable image source.")
        searchable = " ".join(
            [candidate.title, candidate.description, candidate.source_reference]
        ).lower()
        if any(term in searchable for term in _PROHIBITED_IMAGE_TERMS):
            policy_status = "rejected"
            codes.append("IMAGE_POLICY_REJECTED")
            reasons.append("The candidate may depict prohibited evidence-like or portrait content.")
        meaningful_terms = {
            token
            for token in re.findall(r"[a-z0-9]+", " ".join(need.query_terms).lower())
            if len(token) > 3 and token not in _GENERIC_TERMS
        }
        matched_terms = sum(1 for token in meaningful_terms if token in searchable)
        if meaningful_terms and matched_terms == 0:
            relevance = 55
            reasons.append(
                "Metadata has no direct subject match; visual review is required before use."
            )
        elif meaningful_terms:
            relevance = min(100, 75 + (matched_terms * 10))
        if not candidate.photographer or not candidate.attribution_url:
            quality = min(quality, 55)
            codes.append("IMAGE_ATTRIBUTION_INCOMPLETE")
            reasons.append("Photographer attribution is incomplete.")
    elif candidate.kind == "component":
        source_text = " ".join(
            [candidate.title, candidate.description, candidate.provider_asset_id]
        ).lower()
        terms = {
            token
            for token in re.findall(r"[a-z0-9]+", " ".join(need.query_terms).lower())
            if len(token) > 3 and token not in _GENERIC_TERMS
        }
        matches = sum(1 for token in terms if token in source_text)
        if matches < 2:
            relevance = 0
            codes.append("COMPONENT_NOT_RELEVANT")
            reasons.append(
                "The registry component does not match the requested interaction or layout intent."
            )
        else:
            relevance = min(100, 70 + matches * 10)
        if not candidate.source_files:
            technical_status = "rejected"
            codes.append("COMPONENT_SOURCE_MISSING")
            reasons.append("The registry candidate has no source files to materialize.")
        if not dependencies_allowed(candidate.dependencies):
            technical_status = "rejected"
            codes.append("COMPONENT_DEPENDENCY_NOT_ALLOWED")
            reasons.append(
                "The registry candidate requires dependencies outside the target contract."
            )
        if not candidate.license.strip():
            technical_status = "rejected"
            codes.append("COMPONENT_LICENSE_UNKNOWN")
            reasons.append("The registry candidate does not provide a license record.")
    elif candidate.kind == "icon":
        if not candidate.icon_name:
            technical_status = "rejected"
            codes.append("ICON_NAME_MISSING")
            reasons.append("The icon candidate has no importable Lucide name.")

    eligible = (
        relevance >= 70
        and quality >= 70
        and policy_status == "approved"
        and technical_status == "approved"
    )
    if not eligible and not reasons:
        reasons.append("Candidate did not satisfy the handoff quality threshold.")
    return CandidateQualification(
        resource_id=candidate.resource_id,
        need_id=need.need_id,
        eligible=eligible,
        relevance_score=relevance,
        quality_score=quality,
        policy_status=policy_status,
        technical_status=technical_status,
        reasons=reasons,
        issue_codes=codes,
    )


def select_required_candidates(
    selections: list[ResourceSelection],
    needs: list[ResourceNeed],
    qualifications: list[CandidateQualification],
) -> tuple[list[ResourceSelection], list[str]]:
    """Prevent a weak model response from silently dropping a required good candidate."""
    need_by_id = {need.need_id: need for need in needs}
    best_by_need: dict[str, CandidateQualification] = {}
    for item in qualifications:
        if not item.eligible:
            continue
        current = best_by_need.get(item.need_id)
        if current is None or (item.relevance_score, item.quality_score) > (
            current.relevance_score,
            current.quality_score,
        ):
            best_by_need[item.need_id] = item
    warnings: list[str] = []
    normalized: list[ResourceSelection] = []
    qualification_by_id = {item.resource_id: item for item in qualifications}
    for selection in selections:
        need = need_by_id[selection.need_id]
        chosen = qualification_by_id.get(selection.selected_resource_id or "")
        if chosen is not None and not chosen.eligible:
            selection = selection.model_copy(
                update={
                    "selected_resource_id": None,
                    "fallback": selection.fallback or need.fallback,
                    "adaptation_notes": "Rejected by deterministic quality and policy admission checks.",
                }
            )
            warnings.append(f"Rejected ineligible candidate for need '{need.source_id}'.")
        if need.required_for_handoff and not selection.selected_resource_id:
            best = best_by_need.get(need.need_id)
            if best is not None:
                selection = selection.model_copy(
                    update={
                        "selected_resource_id": best.resource_id,
                        "why_selected": "Highest-quality policy-compliant provider candidate selected for a required handoff asset.",
                        "adaptation_notes": "Use only as a non-evidentiary editorial visual with the supplied attribution.",
                    }
                )
                warnings.append(
                    f"Selected the highest-qualified required resource for '{need.source_id}'."
                )
        normalized.append(selection)
    return normalized, warnings


def build_handoff_report(
    *,
    source_ref: BuildPreparationSourceRef,
    routes: list[RouteScope],
    build_context: BuildContextDraft,
    content_architect: dict[str, Any],
    needs: list[ResourceNeed],
    selections: list[ResourceSelection],
    qualifications: list[CandidateQualification],
    materialization: MaterializationResult,
) -> HandoffQualityReport:
    """Apply the final non-bypassable Code Generator admission gate."""
    selected_ids = {
        selection.need_id: selection.selected_resource_id
        for selection in selections
        if selection.selected_resource_id
    }
    materialized = {
        str(entry.get("id", ""))
        for entry in materialization.resources
        if isinstance(entry, dict)
        and (
            str(entry.get("local_path", ""))
            or str(entry.get("local_directory", ""))
            or str(entry.get("disposition", "")) == "adaptable_source"
        )
    }
    issues: list[HandoffIssue] = []
    approval_verified = bool(
        source_ref.content_architect_content_hash
        and source_ref.visual_design_director_direction_hash
    )
    if not approval_verified:
        issues.append(
            HandoffIssue(
                code="UPSTREAM_APPROVAL_UNVERIFIED",
                message=(
                    "The package does not contain both approved Content Architect and Visual "
                    "Design Director hashes, so it is review-only and cannot be handed to Code Generator."
                ),
                next_action=(
                    "Approve both upstream stages and regenerate through the production session flow, "
                    "or provide fixture projections that include both approval hashes."
                ),
            )
        )
    if not routes:
        issues.append(
            HandoffIssue(
                code="PUBLIC_ROUTE_SCOPE_EMPTY",
                message="The approved package contains no public compilable route.",
                next_action="Return to Content Architect and approve at least one public route.",
            )
        )
    context_by_route = {route.route_id: route for route in build_context.routes}
    content_by_route = {
        str(pack.get("route_id", "")): pack
        for pack in content_architect.get("page_content_packs", []) or []
        if isinstance(pack, dict) and pack.get("route_id")
    }
    for route in routes:
        route_context = context_by_route.get(route.route_id)
        if route_context is None or not route_context.brief_markdown.strip():
            issues.append(
                HandoffIssue(
                    code="ROUTE_BUILD_BRIEF_MISSING",
                    message=f"Route '{route.route_id}' has no usable Code Generator build brief.",
                    next_action="Regenerate Build Preparation from the approved visual direction.",
                )
            )
        content_pack = content_by_route.get(route.route_id)
        sections = content_pack.get("sections", []) if isinstance(content_pack, dict) else []
        if not isinstance(sections, list) or not sections:
            issues.append(
                HandoffIssue(
                    code="ROUTE_PUBLIC_CONTENT_MISSING",
                    message=f"Route '{route.route_id}' has no approved public section content.",
                    next_action="Return to Content Architect and approve grounded content for this route.",
                )
            )
    required_ids = [need.need_id for need in needs if need.required_for_handoff]
    for need in needs:
        if not need.required_for_handoff:
            continue
        resource_id = selected_ids.get(need.need_id)
        if not resource_id:
            issues.append(
                HandoffIssue(
                    code="REQUIRED_RESOURCE_UNRESOLVED",
                    need_id=need.need_id,
                    message=f"Required resource '{need.source_id}' has no eligible provider selection.",
                    next_action="Configure PEXELS_API_KEY or refine the approved editorial asset policy, then rerun.",
                )
            )
        elif resource_id not in materialized:
            issues.append(
                HandoffIssue(
                    code="REQUIRED_RESOURCE_NOT_MATERIALIZED",
                    need_id=need.need_id,
                    message=f"Required resource '{need.source_id}' was selected but is not a local usable file.",
                    next_action="Review provider download, image inspection, and attribution diagnostics, then rerun.",
                )
            )
    eligible = not issues
    return HandoffQualityReport(
        handoff_eligible=eligible,
        upstream_approval_verified=approval_verified,
        status="ready_for_handoff" if eligible else "needs_attention",
        summary=(
            "Approved upstream references, public route content, and required resources passed deterministic handoff admission."
            if eligible
            else "The package is available for review but is blocked from Code Generator handoff."
        ),
        required_need_ids=required_ids,
        selected_resource_ids=sorted(selected_ids.values()),
        materialized_resource_ids=sorted(materialized),
        qualifications=qualifications,
        issues=issues,
    )
