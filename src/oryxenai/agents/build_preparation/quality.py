"""Deterministic admission checks for provider resources and agent handoff."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from oryxenai.agents.build_preparation.materializer import (
    _meaningful_component_source,
    dependencies_allowed,
)
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
from oryxenai.agents.build_preparation.visual_input import component_provider_terms

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


_CONTEXT_VALUE_KEYS = frozenset(
    {
        "title",
        "heading",
        "label",
        "purpose",
        "summary",
        "description",
        "narrative_goal",
        "background_intent",
        "content",
        "body",
        "text",
        "public_content",
        "visual_goal",
        "interaction_class",
        "interaction_outcome",
        "placement",
        "provider_terms",
        "style",
        "palette",
        "typography",
        "responsive",
        "responsive_behavior",
        "reduced_motion",
        "reduced_motion_behavior",
        "accessibility",
        "accessibility_requirements",
        "performance_choices",
    }
)
_CONTEXT_EXCLUDED_KEYS = frozenset(
    {
        "route_id",
        "scene_id",
        "section_id",
        "role_id",
        "need_id",
        "source_id",
        "resource_id",
        "provider_id",
        "provider_asset_id",
        "url",
        "urls",
        "source_url",
        "source_reference",
        "source_files",
        "dependencies",
        "registry_dependencies",
        "expected_exports",
        "local_path",
        "path",
        "code",
        "html",
        "css",
        "javascript",
        "typescript",
    }
)


def _context_terms(value: Any, *, key: str = "") -> list[str]:
    """Extract bounded, human-facing semantic terms from approved context."""
    if isinstance(value, dict):
        terms: list[str] = []
        for child_key, child_value in value.items():
            normalized_key = str(child_key).casefold()
            if normalized_key in _CONTEXT_EXCLUDED_KEYS:
                continue
            if normalized_key in _CONTEXT_VALUE_KEYS or isinstance(child_value, (dict, list)):
                terms.extend(_context_terms(child_value, key=normalized_key))
        return terms
    if isinstance(value, (list, tuple, set)):
        terms: list[str] = []
        for item in value:
            terms.extend(_context_terms(item, key=key))
        return terms
    if not isinstance(value, (str, int, float)):
        return []
    text = str(value).strip()
    if not text or len(text) > 240 or key in _CONTEXT_EXCLUDED_KEYS:
        return []
    if re.search(r"(?:https?://|www\.|<[^>]+>|\b(?:import|export)\b)", text, re.I):
        return []
    # Keep query terms concrete and provider-safe; source code and URLs are
    # excluded before this point, and punctuation is normalized for matching.
    return [
        token
        for token in re.findall(r"[a-z0-9][a-z0-9'-]*", text.casefold())
        if len(token) > 2 and token not in _GENERIC_TERMS
    ]


def _dedupe_terms(values: list[Any], *, limit: int = 32) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        for token in _context_terms(value):
            normalized = str(token).strip().casefold()
            if len(normalized) <= 2 or normalized in _GENERIC_TERMS or normalized in seen:
                continue
            seen.add(normalized)
            terms.append(normalized)
            if len(terms) >= limit:
                return terms
    return terms


def _context_for_need(need: ResourceNeed, context: dict[str, Any] | None) -> list[str]:
    if not isinstance(context, dict):
        return []
    route_ids = {str(item) for item in need.route_ids if str(item).strip()}
    scene_ids = {str(item) for item in need.scene_ids if str(item).strip()}
    section_ids = {str(item) for item in need.section_ids if str(item).strip()}
    role_id = need.component_intent.role_id if need.component_intent else ""
    selected: list[Any] = [context.get("semantic_subject_terms", [])]

    for item in context.get("approved_route_context", []) or []:
        if not isinstance(item, dict) or (
            route_ids and str(item.get("route_id", "")) not in route_ids
        ):
            continue
        selected.append({"title": item.get("title", ""), "purpose": item.get("purpose", "")})
    for item in context.get("approved_section_context", []) or []:
        if not isinstance(item, dict):
            continue
        section = item.get("section", {})
        if not isinstance(section, dict):
            continue
        if route_ids and str(item.get("route_id", "")) not in route_ids:
            continue
        if section_ids and str(section.get("section_id", "")) not in section_ids:
            continue
        selected.append(section)
    for item in context.get("approved_scene_context", []) or []:
        if not isinstance(item, dict):
            continue
        scene = item.get("scene", {})
        if not isinstance(scene, dict):
            continue
        if route_ids and str(item.get("route_id", "")) not in route_ids:
            continue
        if scene_ids and str(scene.get("scene_id", "")) not in scene_ids:
            continue
        selected.append(scene)
    for item in context.get("public_content_context", []) or []:
        if not isinstance(item, dict) or (
            route_ids and str(item.get("route_id", "")) not in route_ids
        ):
            continue
        selected.append(item)
    for item in context.get("interaction_context", []) or []:
        if not isinstance(item, dict) or (role_id and str(item.get("role_id", "")) != role_id):
            continue
        selected.append(item)
    selected.extend(
        [
            context.get("responsive_context", {}),
            context.get("reduced_motion_context", {}),
        ]
    )
    return _dedupe_terms(selected, limit=40)


def normalize_query_plan(
    plan: Any,
    needs: list[ResourceNeed],
    settings: Any = None,
    context: dict[str, Any] | None = None,
) -> Any:
    """Keep model query intent inside the fixed visual and provider policy."""
    by_id = {need.need_id: need for need in needs}
    image_config = getattr(settings, "image_retrieval", None)
    image_providers = list(getattr(image_config, "provider_order", ["pexels", "pixabay"]))
    image_providers = [
        provider for provider in image_providers if provider in {"pexels", "pixabay", "unsplash"}
    ]
    if not image_providers:
        image_providers = ["pexels", "pixabay"]
    if (
        image_config is not None
        and bool(getattr(image_config, "unsplash_enabled", False))
        and bool(getattr(image_config, "unsplash_local_vendoring_authorized", False))
        and "unsplash" in list(getattr(image_config, "provider_order", []))
    ):
        image_providers.append("unsplash")
    queries = []
    for query in plan.queries:
        need = by_id[query.need_id]
        details = need.details if isinstance(need.details, dict) else {}
        contextual_terms = _context_for_need(need, context)
        semantic_terms = _dedupe_terms(
            [*need.query_terms, need.purpose, *contextual_terms], limit=40
        )
        merged_query_terms = _dedupe_terms(
            [query.query, *semantic_terms],
            limit=48,
        )
        contextual_negative = [
            *(
                details.get("negative_concepts", [])
                if isinstance(details.get("negative_concepts", []), list)
                else []
            ),
            *(
                context.get("forbidden_concepts", [])
                if isinstance(context, dict)
                and isinstance(context.get("forbidden_concepts", []), list)
                else []
            ),
        ]
        query = query.model_copy(
            update={
                "query": " ".join(merged_query_terms).strip(),
                "purpose": query.purpose or need.purpose,
                "subject": query.subject or " ".join(semantic_terms),
                "style_mood": query.style_mood or str(details.get("mood", "") or ""),
                "theme_colors": query.theme_colors
                or (
                    [str(item) for item in details.get("theme_colors", []) if str(item).strip()]
                    if isinstance(details.get("theme_colors", []), list)
                    else []
                ),
                "orientation": query.orientation or str(details.get("orientation", "") or ""),
                "aspect_ratio": query.aspect_ratio
                or str(details.get("aspect_ratio_need", "") or ""),
                "category": query.category or need.category,
                "negative_concepts": list(
                    dict.fromkeys(
                        [
                            *query.negative_concepts,
                            *[str(item) for item in contextual_negative if str(item).strip()],
                        ]
                    )
                ),
                "important": query.important
                or any(
                    token in f"{need.purpose} {need.importance}".casefold()
                    for token in ("hero", "banner", "showcase", "critical")
                ),
            }
        )
        if need.category.casefold() in {"visual_component", "component", "registry_component"}:
            configured_registry_order = list(
                getattr(
                    getattr(settings, "resource_providers", None),
                    "registry_order",
                    ["shadcn", "magicui", "smoothui", "cultui"],
                )
            )
            configured_registry_order = [
                provider
                for provider in configured_registry_order
                if provider in {"shadcn", "magicui", "smoothui", "cultui"}
            ]
            registry_order = [
                str(value)
                for value in getattr(query, "allowed_providers", [])
                if str(value) in configured_registry_order
            ] or configured_registry_order
            role_id = (
                need.component_intent.role_id
                if need.component_intent is not None
                else str(details.get("interaction_role", "") or "")
            )
            canonical_terms = [
                str(item) for item in details.get("provider_terms", []) or [] if str(item).strip()
            ]
            typed_terms = (
                [str(item) for item in need.component_intent.provider_terms if str(item).strip()]
                if need.component_intent
                else []
            )
            interaction_terms = [
                str(details.get(key, "") or "")
                for key in ("interaction_class", "interaction_outcome", "placement")
                if str(details.get(key, "") or "").strip()
            ]
            provider_terms = list(
                dict.fromkeys(
                    [
                        *query.provider_terms,
                        *canonical_terms,
                        *typed_terms,
                        *component_provider_terms(role_id),
                        *interaction_terms,
                        *contextual_terms,
                    ]
                )
            )
            query_text = " ".join(
                dict.fromkeys(
                    [
                        *str(query.query or "").split(),
                        *provider_terms,
                        *semantic_terms,
                    ]
                )
            ).strip()
            queries.append(
                query.model_copy(
                    update={
                        "kind": "component",
                        "query": query_text,
                        "provider_terms": provider_terms[:24],
                        "allowed_providers": registry_order,
                        "required_for_handoff": need.required_for_handoff,
                        "interaction_class": (
                            query.interaction_class
                            or (
                                need.component_intent.interaction_class
                                if need.component_intent
                                else ""
                            )
                        ),
                        "interaction_outcome": (
                            query.interaction_outcome
                            or (
                                need.component_intent.interaction_outcome
                                if need.component_intent
                                else ""
                            )
                        ),
                        "placement": query.placement or str(details.get("placement", "") or ""),
                        "expected_exports": query.expected_exports
                        or (
                            need.component_intent.expected_exports if need.component_intent else []
                        ),
                    }
                )
            )
            continue
        if need.source_policy != "optional_external_acquisition":
            if need.category.casefold() in {"font", "typography", "type_system"}:
                queries.append(
                    query.model_copy(
                        update={
                            "kind": "font",
                            "allowed_providers": ["fontsource"],
                            "required_for_handoff": need.required_for_handoff,
                        }
                    )
                )
                continue
            queries.append(
                query.model_copy(
                    update={
                        "kind": "custom",
                        "allowed_providers": [],
                        "required_for_handoff": False,
                    }
                )
            )
            continue
        if need.source_status != "needs_acquisition":
            queries.append(
                query.model_copy(
                    update={
                        "kind": "custom",
                        "allowed_providers": [],
                        "required_for_handoff": False,
                    }
                )
            )
            continue
        update: dict[str, Any] = {
            "required_for_handoff": need.required_for_handoff,
            "allowed_providers": image_providers if need.required_for_handoff else [],
        }
        if need.category.casefold() in {"font", "typography", "type_system"}:
            update.update({"kind": "font", "allowed_providers": ["fontsource"]})
            queries.append(query.model_copy(update=update))
            continue
        photo_need = need.kind == "asset" and any(
            token in f"{need.category} {need.purpose}".lower()
            for token in ("editorial", "image", "photo", "portrait")
        )
        if need.required_for_handoff or photo_need:
            update["kind"] = "photo"
            update["orientation"] = str(need.details.get("orientation", "landscape") or "landscape")
            update["allowed_providers"] = image_providers
            update["minimum_width"] = int(
                details.get("minimum_width")
                or (
                    getattr(image_config, "minimum_width", 1200)
                    if image_config is not None
                    else 1200
                )
            )
            update["minimum_height"] = int(
                details.get("minimum_height")
                or (
                    getattr(image_config, "minimum_height", 700)
                    if image_config is not None
                    else 700
                )
            )
        elif need.category in _CUSTOM_CATEGORIES:
            update["kind"] = "custom"
            update["allowed_providers"] = []
        queries.append(query.model_copy(update=update))
    return plan.model_copy(update={"queries": queries})


def qualify_candidates(
    needs: list[ResourceNeed],
    candidates: list[FetchedResource],
    *,
    source_required: bool = True,
    query_terms_by_need: dict[str, list[str]] | None = None,
) -> list[CandidateQualification]:
    """Admit candidates, optionally before the selected source is fetched."""
    need_by_id = {need.need_id: need for need in needs}
    return [
        _qualify(
            need_by_id[candidate.need_id],
            candidate,
            source_required=source_required,
            query_terms=(query_terms_by_need or {}).get(candidate.need_id, []),
        )
        for candidate in candidates
    ]


def _qualify(
    need: ResourceNeed,
    candidate: FetchedResource,
    *,
    source_required: bool = True,
    query_terms: list[str] | None = None,
) -> CandidateQualification:
    reasons: list[str] = []
    codes: list[str] = []
    policy_status = "approved"
    technical_status = "approved"
    relevance = 70
    quality = 70

    if candidate.kind == "photo":
        minimum_width = int(need.details.get("minimum_width", 1200) or 1200)
        minimum_height = int(need.details.get("minimum_height", 700) or 700)
        if (
            candidate.provider == "generated-local"
            or candidate.provider_asset_id.casefold().startswith(("mock-", "generated-"))
            or "/mock/" in candidate.image_url.casefold()
        ):
            technical_status = "rejected"
            codes.append("SYNTHETIC_IMAGE_CANDIDATE")
            reasons.append(
                "Synthetic, mock, or generated image candidates are never handoff material."
            )
        if candidate.provider not in {"pexels", "pixabay"} and need.required_for_handoff:
            technical_status = "rejected"
            codes.append("REMOTE_ASSET_NOT_ALLOWED")
            reasons.append("Required images must be materialized locally for the static target.")
        if candidate.width < minimum_width or candidate.height < minimum_height:
            quality = 0
            codes.append("IMAGE_RESOLUTION_TOO_LOW")
            reasons.append(
                f"Image dimensions are below the {minimum_width}x{minimum_height} handoff minimum."
            )
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
            for token in re.findall(
                r"[a-z0-9]+", " ".join([*need.query_terms, *(query_terms or [])]).lower()
            )
            if len(token) > 3 and token not in _GENERIC_TERMS
        }
        matched_terms = sum(1 for token in meaningful_terms if token in searchable)
        if meaningful_terms and matched_terms == 0:
            relevance = 55
            reasons.append("Metadata has no direct subject match for the approved visual need.")
        elif meaningful_terms:
            relevance = min(100, 75 + (matched_terms * 10))
        if not candidate.photographer or not candidate.attribution_url:
            quality = min(quality, 55)
            codes.append("IMAGE_ATTRIBUTION_INCOMPLETE")
            reasons.append("Photographer attribution is incomplete.")
        if not candidate.license.strip() or not candidate.license_reference.strip():
            technical_status = "rejected"
            codes.append("IMAGE_LICENSE_INCOMPLETE")
            reasons.append("Image licence provenance is incomplete.")
    elif candidate.kind == "component":
        if candidate.provider == "generated-local":
            technical_status = "rejected"
            codes.append("SYNTHETIC_COMPONENT_CANDIDATE")
            reasons.append("Generated-local component source is not a real registry handoff.")
        source_text = " ".join(
            [
                candidate.title,
                candidate.description,
                candidate.provider_asset_id,
                " ".join(str(item) for item in candidate.retrieval_metadata.get("tags", [])),
            ]
        ).lower()
        intent = need.component_intent
        forbidden = {
            token
            for token in re.findall(
                r"[a-z0-9]+",
                " ".join(
                    [
                        *(intent.negative_concepts if intent else []),
                        *(intent.prohibitions if intent else []),
                    ]
                ).lower(),
            )
            if len(token) > 3
        }
        if forbidden.intersection(set(re.findall(r"[a-z0-9]+", source_text))):
            policy_status = "rejected"
            codes.append("COMPONENT_POLICY_REJECTED")
            reasons.append("The candidate metadata contains a prohibited concept for this role.")
        terms = {
            token
            for token in re.findall(
                r"[a-z0-9]+",
                " ".join(
                    [
                        *need.query_terms,
                        *(query_terms or []),
                        *(intent.provider_terms if intent else []),
                        *candidate.retrieval_metadata.get("provider_terms", []),
                    ]
                ).lower(),
            )
            if len(token) > 3 and token not in _GENERIC_TERMS
        }
        matches = sum(1 for token in terms if token in source_text)
        if matches < 1:
            relevance = 0
            codes.append("COMPONENT_NOT_RELEVANT")
            reasons.append(
                "The registry component does not match the requested interaction or layout intent."
            )
        else:
            relevance = min(100, 70 + matches * 10)
        if source_required and not candidate.source_files:
            technical_status = "rejected"
            codes.append("COMPONENT_SOURCE_MISSING")
            reasons.append("The registry candidate has no source files to materialize.")
        elif source_required and not _meaningful_component_source(candidate.source_files):
            technical_status = "rejected"
            codes.append("COMPONENT_SOURCE_PLACEHOLDER")
            reasons.append("The registry candidate contains only empty or placeholder source.")
        if not dependencies_allowed(candidate.dependencies):
            technical_status = "rejected"
            codes.append("COMPONENT_DEPENDENCY_NOT_ALLOWED")
            reasons.append(
                "The registry candidate requires dependencies outside the target contract."
            )
        if not candidate.license.strip() or not candidate.license_reference.strip():
            technical_status = "rejected"
            codes.append("COMPONENT_LICENSE_UNKNOWN")
            reasons.append("The registry candidate does not provide a license record.")
    elif candidate.kind == "icon":
        if not candidate.icon_name:
            technical_status = "rejected"
            codes.append("ICON_NAME_MISSING")
            reasons.append("The icon candidate has no importable Lucide name.")
    elif candidate.kind == "font":
        if candidate.provider != "fontsource" or not candidate.font_family:
            technical_status = "rejected"
            codes.append("FONT_METADATA_MISSING")
            reasons.append("The font candidate has no approved Fontsource metadata.")
        if not candidate.font_urls:
            technical_status = "rejected"
            codes.append("FONT_SOURCE_MISSING")
            reasons.append("The font candidate has no downloadable local font files.")

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
    visual_input_mode: str = "approved_vdd",
    assumption_hash: str = "",
    image_target: int = 0,
    component_target: int = 0,
    provider_calls: int = 0,
    cache_hits: int = 0,
    rate_limit_events: int = 0,
    deferred_optional_roles: list[str] | None = None,
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
    materialized_by_id = {
        str(entry.get("id", "")): entry
        for entry in materialization.resources
        if isinstance(entry, dict)
    }
    issues: list[HandoffIssue] = []
    approval_verified = bool(
        source_ref.content_architect_content_hash
        and (
            source_ref.visual_design_director_direction_hash
            or (
                source_ref.visual_input_mode in {"assumed_from_content", "merged_vdd_assumptions"}
                and source_ref.assumption_hash
                and source_ref.producer_provenance_hash
            )
        )
    )
    if not approval_verified:
        issues.append(
            HandoffIssue(
                code="UPSTREAM_APPROVAL_UNVERIFIED",
                message=(
                    "The package does not contain both approved Content Architect and Visual "
                    "Design Director approval or Build Preparation assumption provenance, so it is review-only and cannot be handed to Code Generator."
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
    visual_categories = {
        "image",
        "photo",
        "editorial_photo",
        "portrait",
        "component",
        "visual_component",
        "registry_component",
    }
    required_ids = [
        need.need_id
        for need in needs
        if need.required_for_handoff or need.category.casefold() in visual_categories
    ]
    image_need_ids = {
        need.need_id
        for need in needs
        if need.category.casefold() in {"image", "photo", "editorial_photo", "portrait"}
    }
    component_need_ids = {
        need.need_id
        for need in needs
        if need.category.casefold() in {"component", "visual_component", "registry_component"}
    }
    materialized_by_need = {
        str(entry.get("need_id", "")): entry
        for entry in materialization.resources
        if isinstance(entry, dict)
    }
    for need in needs:
        if need.need_id not in materialized_by_need:
            selected_id = selected_ids.get(need.need_id)
            if selected_id and selected_id in materialized_by_id:
                materialized_by_need[need.need_id] = materialized_by_id[selected_id]

    def materialized_disposition(entry: dict[str, Any]) -> str:
        disposition = str(entry.get("disposition", "") or "")
        if disposition:
            return disposition
        if str(entry.get("local_path", "") or ""):
            return "local_file"
        if str(entry.get("local_directory", "") or "") or entry.get("source_files"):
            return "adaptable_source"
        return ""

    for need in needs:
        selected_resource = materialized_by_id.get(selected_ids.get(need.need_id, ""), {})
        if (
            need.source_policy in {"curated_local", "generated_local_visual"}
            and selected_ids.get(need.need_id)
            and str(selected_resource.get("provider", "")) != "generated-local"
        ):
            issues.append(
                HandoffIssue(
                    code="SOURCE_POLICY_STOCK_FORBIDDEN",
                    need_id=need.need_id,
                    message=f"'{need.source_id}' is approved for local fabrication only and cannot use stock acquisition.",
                    next_action="Use the approved local resource or its declared fallback.",
                )
            )
        if need.source_policy == "approved_user_media":
            resource_id = selected_ids.get(need.need_id)
            if resource_id and resource_id not in materialized:
                issues.append(
                    HandoffIssue(
                        code="APPROVED_USER_MEDIA_NOT_LOCAL",
                        need_id=need.need_id,
                        message=f"Approved user media '{need.source_id}' was not locally verified.",
                        next_action="Supply the verified local media or use the declared fallback honestly.",
                    )
                )
        is_image_role = need.category.casefold() in {
            "image",
            "photo",
            "editorial_photo",
            "portrait",
        }
        is_component_role = need.category.casefold() in {
            "component",
            "visual_component",
            "registry_component",
        }
        if is_image_role or is_component_role:
            usable_dispositions = {"local_file", "adaptable_source"}
            disposition = materialized_disposition(materialized_by_need.get(need.need_id, {}))
            if not selected_ids.get(need.need_id) or disposition not in usable_dispositions:
                role_label = "image" if is_image_role else "component"
                issues.append(
                    HandoffIssue(
                        code=(
                            "REQUIRED_RESOURCE_UNRESOLVED"
                            if need.required_for_handoff and not selected_ids.get(need.need_id)
                            else "REQUIRED_RESOURCE_NOT_MATERIALIZED"
                            if need.required_for_handoff
                            else "IMAGE_ROLE_UNRESOLVED"
                            if is_image_role
                            else "COMPONENT_ROLE_UNRESOLVED"
                        ),
                        need_id=need.need_id,
                        message=(
                            f"Known {role_label} role '{need.source_id}' did not materialize as local validated material."
                        ),
                        next_action=(
                            "Retry the bounded provider/source attempts and inspect the materialization receipt, "
                            "or explicitly remove the role upstream before rerunning."
                        ),
                    )
                )
            continue
        if not need.required_for_handoff:
            continue
        resource_id = selected_ids.get(need.need_id)
        if not resource_id:
            issues.append(
                HandoffIssue(
                    code="REQUIRED_RESOURCE_UNRESOLVED",
                    need_id=need.need_id,
                    message=f"Required resource '{need.source_id}' has no eligible provider selection.",
                    next_action="Configure PEXELS_API_KEY or PIXABAY_API_KEY, or refine the approved editorial asset policy, then rerun.",
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
    slot_ids = [slot.resource_slot_id for slot in materialization.execution_slots]
    known_need_slots = {
        source_id for slot in materialization.execution_slots for source_id in slot.source_ids
    }
    readiness = {
        "slot_count": len(slot_ids),
        "local_materialized": sum(
            slot.resolution.resolution_type == "local_materialized"
            for slot in materialization.execution_slots
        ),
        "target_package_binding": sum(
            slot.resolution.resolution_type == "target_package_binding"
            for slot in materialization.execution_slots
        ),
        "local_recipe": sum(
            slot.resolution.resolution_type == "local_recipe"
            for slot in materialization.execution_slots
        ),
        "execution_gap": len(materialization.execution_gaps),
    }
    if (
        materialization.pack_version == "build-preparation-pack-v3"
        and materialization.execution_contract_path
    ):
        if not slot_ids or len(slot_ids) != len(set(slot_ids)):
            issues.append(
                HandoffIssue(
                    code="EXECUTION_SLOT_INVALID",
                    message="The v3 pack does not contain one unique execution slot per prepared decision.",
                    next_action="Regenerate Build Preparation after correcting the execution compiler.",
                )
            )
        missing_needs = sorted({need.source_id for need in needs} - known_need_slots)
        if missing_needs:
            issues.append(
                HandoffIssue(
                    code="EXECUTION_SLOT_COVERAGE_MISSING",
                    message="Known prepared resource needs are absent from the v3 execution inventory.",
                    next_action="Regenerate Build Preparation; known needs cannot defer to Code Generator.",
                )
            )
        recipe_ids = {recipe.recipe_id for recipe in materialization.local_recipes}
        root = Path(materialization.root_path)
        for slot in materialization.execution_slots:
            resolution = slot.resolution
            if resolution.resolution_type == "local_recipe":
                if resolution.recipe_id not in recipe_ids:
                    issues.append(
                        HandoffIssue(
                            code="EXECUTION_RECIPE_DANGLING",
                            message=f"Execution slot '{slot.resource_slot_id}' has no local recipe.",
                            next_action="Regenerate Build Preparation from approved direction.",
                        )
                    )
            elif resolution.resolution_type == "local_materialized":
                if not resolution.local_paths or any(
                    not (root / path).is_file() and not (root / path).is_dir()
                    for path in resolution.local_paths
                ):
                    issues.append(
                        HandoffIssue(
                            code="EXECUTION_LOCAL_PATH_INVALID",
                            message=f"Execution slot '{slot.resource_slot_id}' references unavailable local material.",
                            next_action="Regenerate the local materialization before handoff.",
                        )
                    )
            elif resolution.resolution_type == "target_package_binding":
                if not resolution.package_name or not resolution.expected_exports:
                    issues.append(
                        HandoffIssue(
                            code="EXECUTION_PACKAGE_BINDING_INVALID",
                            message=f"Execution slot '{slot.resource_slot_id}' lacks a usable package binding.",
                            next_action="Use a configured target dependency or a typed local recipe.",
                        )
                    )
            elif resolution.resolution_type == "execution_gap":
                # The structured gap below supplies the route/scene-specific
                # revision instruction; this issue makes eligibility visibly false.
                issues.append(
                    HandoffIssue(
                        code="VDD_EXECUTION_GAP",
                        message=f"Execution slot '{slot.resource_slot_id}' is blocked by upstream direction.",
                        next_action="Revise and explicitly re-approve Visual Design Director output.",
                    )
                )
        for resource in materialization.resources:
            if not isinstance(resource, dict):
                continue
            if resource.get("provider") and not (
                str(resource.get("license", "") or "").strip()
                and str(resource.get("license_reference", "") or "").strip()
            ):
                issues.append(
                    HandoffIssue(
                        code="EXECUTION_LICENSE_INCOMPLETE",
                        message="A materialized resource has incomplete licence provenance.",
                        next_action="Use an approved source with a recorded licence before handoff.",
                    )
                )
        seen_hashes: dict[str, str] = {}
        for resource in materialization.resources:
            if not isinstance(resource, dict):
                continue
            content_hash = str(resource.get("content_hash", "") or "")
            if not content_hash:
                continue
            previous = seen_hashes.get(content_hash)
            if previous and previous != str(resource.get("id", "")):
                issues.append(
                    HandoffIssue(
                        code="DUPLICATE_IMAGE_MATERIAL",
                        message="Two image roles resolve to the same local content hash.",
                        next_action="Select distinct provider assets or revise the visual roles before handoff.",
                    )
                )
            seen_hashes[content_hash] = str(resource.get("id", ""))
        for resource in materialization.resources:
            if not isinstance(resource, dict):
                continue
            local_values = [
                str(resource.get("local_path", "") or ""),
                str(resource.get("local_directory", "") or ""),
            ]
            if any(value.startswith(("http://", "https://")) for value in local_values):
                issues.append(
                    HandoffIssue(
                        code="REMOTE_RUNTIME_ASSET",
                        message="A resource usage contract points at a remote runtime asset.",
                        next_action="Materialize the selected bytes/source into the pack before handoff.",
                    )
                )
    image_materialized_count = sum(
        1
        for need_id in image_need_ids
        if materialized_disposition(materialized_by_need.get(need_id, {})) == "local_file"
    )
    component_materialized_count = sum(
        1
        for need_id in component_need_ids
        if materialized_disposition(materialized_by_need.get(need_id, {}))
        in {"adaptable_source", "local_file"}
    )
    visual_role_count = len(image_need_ids) + len(component_need_ids)
    unresolved_visual_roles = sorted(
        [
            need.need_id
            for need in needs
            if need.category.casefold() in visual_categories
            and materialized_disposition(materialized_by_need.get(need.need_id, {}))
            not in {"local_file", "adaptable_source"}
        ]
    )
    total_enrichment_failure = bool(
        visual_role_count and not image_materialized_count and not component_materialized_count
    )
    partial_enrichment_failure = bool(unresolved_visual_roles and not total_enrichment_failure)
    if image_need_ids and not image_materialized_count:
        issues.append(
            HandoffIssue(
                code="IMAGE_ENRICHMENT_EMPTY",
                message="Approved image roles exist, but no image materialized locally.",
                next_action="Retry approved image providers and validate at least one local image before handoff.",
            )
        )
    if component_need_ids and not component_materialized_count:
        issues.append(
            HandoffIssue(
                code="COMPONENT_ENRICHMENT_EMPTY",
                message="Approved component roles exist, but no component source materialized locally.",
                next_action="Retry configured registries and validate at least one local component source before handoff.",
            )
        )
    if total_enrichment_failure:
        issues.append(
            HandoffIssue(
                code="TOTAL_ENRICHMENT_FAILURE",
                message="Approved image/component enrichment produced no local material at all.",
                next_action="Resolve at least one approved image or component locally, or revise the upstream roles explicitly.",
            )
        )
    role_statuses = []
    for need in needs:
        if need.category.casefold() not in visual_categories:
            continue
        entry = materialized_by_need.get(need.need_id, {})
        role_statuses.append(
            {
                "need_id": need.need_id,
                "role": "image"
                if need.category.casefold() in {"image", "photo", "editorial_photo", "portrait"}
                else "component",
                "route_ids": list(need.route_ids),
                "scene_ids": list(need.scene_ids),
                "section_ids": list(need.section_ids),
                "attempts": list(entry.get("materialization_attempts", []))
                if isinstance(entry.get("materialization_attempts", []), list)
                else [],
                "final_classification": materialized_disposition(entry) or "unresolved",
                "selected_provider": str(entry.get("provider", "") or ""),
                "selected_resource_id": str(entry.get("id", "") or ""),
            }
        )
    handoff_summary = {
        "image_target": int(image_target),
        "image_materialized": image_materialized_count,
        "semantic_image_need_count": len(image_need_ids),
        "component_target": int(component_target),
        "component_materialized": component_materialized_count,
        "semantic_component_need_count": len(component_need_ids),
        "font_materialized": sum(
            1
            for entry in materialization.resources
            if isinstance(entry, dict)
            and entry.get("kind") == "font"
            and entry.get("disposition") == "local_file"
        ),
        "provider_calls": int(provider_calls),
        "cache_hits": int(cache_hits),
        "rate_limit_events": int(rate_limit_events),
        "deferred_optional_roles": list(deferred_optional_roles or []),
        "unresolved_visual_roles": unresolved_visual_roles,
        "role_statuses": role_statuses,
        "total_enrichment_failure": total_enrichment_failure,
        "partial_enrichment_failure": partial_enrichment_failure,
        "execution_gaps": len(materialization.execution_gaps),
        "visual_input_mode": visual_input_mode,
        "assumption_hash": assumption_hash,
    }
    eligible = not issues
    handoff_summary["code_generator_eligible"] = eligible
    return HandoffQualityReport(
        projection_hashes=dict(materialization.projection_hashes),
        readiness=readiness,
        execution_gaps=materialization.execution_gaps,
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
        handoff_summary=handoff_summary,
    )
