"""Validation for deterministic Stage 0 inputs and outputs."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    FetchedResource,
    Stage0Result,
    Stage1QueryPlan,
    Stage2SelectionPlan,
)


class BuildPreparationValidationError(ValueError):
    """Safe validation failure with a stable transport code."""

    code = "BUILD_PREPARATION_INPUT_INVALID"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class VisualIdentityMismatchError(BuildPreparationValidationError):
    """A hard failure when visual direction names a different person."""

    code = "PACK_VISUAL_IDENTITY_MISMATCH"


_PERSON_NAME_RE = re.compile(r"\b([A-Z][a-z]{1,30})\s+([A-Z][a-z]{1,30})\b")
_NON_PERSON_NAME_WORDS = frozenset(
    {
        "accent",
        "architect",
        "background",
        "bengaluru",
        "body",
        "button",
        "card",
        "color",
        "content",
        "design",
        "designer",
        "display",
        "editorial",
        "experience",
        "font",
        "foreground",
        "grotesk",
        "india",
        "interface",
        "karnataka",
        "lead",
        "material",
        "muted",
        "neutral",
        "paper",
        "product",
        "primary",
        "professional",
        "secondary",
        "senior",
        "space",
        "system",
        "technical",
        "text",
        "ui",
        "ux",
        "visual",
    }
)
_NON_PERSON_NAME_LAST_WORDS = _NON_PERSON_NAME_WORDS


def _person_name_candidates(value: Any) -> list[str]:
    """Return conservative two-word proper-name candidates from free text."""

    text = str(value or "")
    candidates: list[str] = []
    for match in _PERSON_NAME_RE.finditer(text):
        first, last = match.groups()
        if first.casefold() in _NON_PERSON_NAME_WORDS or last.casefold() in (
            _NON_PERSON_NAME_LAST_WORDS
        ):
            continue
        candidates.append(f"{first} {last}")
    return candidates


def _walk_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for child in value.values() for text in _walk_text(child)]
    if isinstance(value, list):
        return [text for child in value for text in _walk_text(child)]
    return []


def _approved_fact_statements(content_architect: dict[str, Any]) -> list[str]:
    statements: list[str] = []
    for field in ("claim_grounding", "facts"):
        values = content_architect.get(field)
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            status = item.get("publication_status", "approved")
            status = getattr(status, "value", status)
            if str(status or "approved") != "approved":
                continue
            statement = str(item.get("statement", "") or "").strip()
            if statement:
                statements.append(statement)
    return statements


def _visual_identity_texts(visual_design_director: dict[str, Any]) -> list[str]:
    scope = visual_design_director.get("global")
    if not isinstance(scope, dict):
        scope = visual_design_director
    return [
        text
        for field in ("must_preserve", "visual_language")
        for text in _walk_text(scope.get(field))
    ]


def _count_person_names(values: list[str]) -> tuple[Counter[str], dict[str, str]]:
    counts: Counter[str] = Counter()
    display_names: dict[str, str] = {}
    for value in values:
        for candidate in _person_name_candidates(value):
            key = candidate.casefold()
            counts[key] += 1
            display_names.setdefault(key, candidate)
    return counts, display_names


def _count_name_first_tokens(values: list[str], candidates: dict[str, str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for key in candidates:
        first = key.split(" ", 1)[0]
        pattern = re.compile(rf"\b{re.escape(first)}\b", re.IGNORECASE)
        counts[key] = sum(len(pattern.findall(value)) for value in values)
    return counts


def validate_content_visual_identity_consistency(
    content_architect: dict[str, Any],
    visual_design_director: dict[str, Any],
) -> None:
    """Reject repeated visual-direction names that contradict approved content.

    The check is intentionally narrow: it needs an owner name from approved
    facts and a repeated, two-word proper-name candidate in the visual
    handoff.  A single incidental capitalized phrase is not enough to reject
    a pack, while the common failure mode of copying a different person's
    name into multiple visual constraints is hard-failed.
    """

    if not isinstance(content_architect, dict) or not isinstance(visual_design_director, dict):
        return
    content_counts, content_display_names = _count_person_names(
        _approved_fact_statements(content_architect)
    )
    if not content_counts:
        return
    approved_key, approved_count = content_counts.most_common(1)[0]
    if approved_count < 1:
        return
    visual_texts = _visual_identity_texts(visual_design_director)
    visual_counts, visual_display_names = _count_person_names(visual_texts)
    visual_first_token_counts = _count_name_first_tokens(visual_texts, visual_display_names)
    mismatches = sorted(
        visual_display_names[key]
        for key, count in visual_counts.items()
        if key != approved_key and (count > 1 or visual_first_token_counts.get(key, 0) > 1)
    )
    if mismatches:
        raise VisualIdentityMismatchError(
            "Visual direction repeatedly names a person other than the approved content owner.",
            details={
                "approved_name": content_display_names[approved_key],
                "mismatched_names": ", ".join(mismatches),
            },
        )


def _as_list(value: Any, field: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise BuildPreparationValidationError(f"{field} must be a list.", details={"field": field})
    return value


def validate_visual_input(visual_design_director: dict[str, Any]) -> None:
    if not isinstance(visual_design_director, dict):
        raise BuildPreparationValidationError("Visual Design Director input must be an object.")

    pages = _as_list(visual_design_director.get("pages"), "pages")
    assets = _as_list(visual_design_director.get("asset_briefs"), "asset_briefs")
    resources = _as_list(visual_design_director.get("resource_candidates"), "resource_candidates")

    page_ids: set[str] = set()
    asset_ids: set[str] = set()
    resource_ids: set[str] = set()
    for item in assets:
        if not isinstance(item, dict) or not str(item.get("asset_id", "")):
            raise BuildPreparationValidationError("Every asset brief must have an asset_id.")
        asset_id = str(item["asset_id"])
        if asset_id in asset_ids:
            raise BuildPreparationValidationError(
                "Visual Design Director contains duplicate asset IDs.",
                details={"asset_id": asset_id},
            )
        asset_ids.add(asset_id)
    for item in resources:
        if not isinstance(item, dict) or not str(item.get("resource_id", "")):
            raise BuildPreparationValidationError(
                "Every resource candidate must have a resource_id."
            )
        resource_id = str(item["resource_id"])
        if resource_id in resource_ids:
            raise BuildPreparationValidationError(
                "Visual Design Director contains duplicate resource IDs.",
                details={"resource_id": resource_id},
            )
        resource_ids.add(resource_id)

    for page in pages:
        if not isinstance(page, dict) or not str(page.get("route_id", "")):
            raise BuildPreparationValidationError("Every visual page must have a route_id.")
        route_id = str(page["route_id"])
        if route_id in page_ids:
            raise BuildPreparationValidationError(
                "Visual Design Director contains duplicate route IDs.",
                details={"route_id": route_id},
            )
        page_ids.add(route_id)
        for asset_id in [*(page.get("asset_briefs") or [])]:
            if str(asset_id) not in asset_ids:
                raise BuildPreparationValidationError(
                    "A visual page references an unknown asset brief.",
                    details={"route_id": route_id, "asset_id": str(asset_id)},
                )
        for resource_id in [*(page.get("resource_candidates") or [])]:
            if str(resource_id) not in resource_ids:
                raise BuildPreparationValidationError(
                    "A visual page references an unknown resource candidate.",
                    details={"route_id": route_id, "resource_id": str(resource_id)},
                )
        for scene in _as_list(page.get("scenes"), f"scenes[{route_id}]"):
            if not isinstance(scene, dict) or not str(scene.get("scene_id", "")):
                raise BuildPreparationValidationError(
                    "Every visual scene must have a scene_id.", details={"route_id": route_id}
                )
            for asset_id in [*(scene.get("asset_requirements") or [])]:
                if str(asset_id) not in asset_ids:
                    raise BuildPreparationValidationError(
                        "A visual scene references an unknown asset brief.",
                        details={"scene_id": str(scene["scene_id"]), "asset_id": str(asset_id)},
                    )
            for resource_id in [*(scene.get("resource_candidates") or [])]:
                if str(resource_id) not in resource_ids:
                    raise BuildPreparationValidationError(
                        "A visual scene references an unknown resource candidate.",
                        details={
                            "scene_id": str(scene["scene_id"]),
                            "resource_id": str(resource_id),
                        },
                    )


def validate_stage0_result(result: Stage0Result) -> Stage0Result:
    route_ids = [route.route_id for route in result.routes]
    need_ids = [need.need_id for need in result.resource_needs]
    if len(route_ids) != len(set(route_ids)):
        raise BuildPreparationValidationError("Stage 0 produced duplicate route IDs.")
    if len(need_ids) != len(set(need_ids)):
        raise BuildPreparationValidationError("Stage 0 produced duplicate resource-needs IDs.")
    known_routes = set(route_ids)
    for need in result.resource_needs:
        unknown = set(need.route_ids) - known_routes
        if unknown:
            raise BuildPreparationValidationError(
                "Stage 0 produced a resource need for an unknown route.",
                details={"need_id": need.need_id, "route_ids": sorted(unknown)},
            )
    return result


def validate_query_plan(plan: Stage1QueryPlan, need_ids: set[str]) -> Stage1QueryPlan:
    """Ensure Stage 1 only translates deterministic Stage 0 needs."""
    seen: set[str] = set()
    for query in plan.queries:
        if query.need_id in seen:
            raise BuildPreparationValidationError(
                "Stage 1 produced duplicate need IDs.", details={"need_id": query.need_id}
            )
        if query.need_id not in need_ids:
            raise BuildPreparationValidationError(
                "Stage 1 referenced an unknown Stage 0 need.",
                details={"need_id": query.need_id},
            )
        seen.add(query.need_id)
        if query.kind in {"photo", "component"} and not query.query.strip():
            raise BuildPreparationValidationError(
                "Provider queries must include a non-empty query string.",
                details={"need_id": query.need_id},
            )
        if query.kind == "icon" and not query.icon_name.strip():
            raise BuildPreparationValidationError(
                "Icon queries must include an icon name.", details={"need_id": query.need_id}
            )
    missing = need_ids - seen
    if missing:
        raise BuildPreparationValidationError(
            "Stage 1 did not produce a query for every Stage 0 need.",
            details={"need_ids": sorted(missing)},
        )
    return plan


def validate_fetched_candidates(
    candidates: list[FetchedResource], need_ids: set[str]
) -> list[FetchedResource]:
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.resource_id in seen:
            raise BuildPreparationValidationError(
                "Provider lookup produced duplicate resource IDs.",
                details={"resource_id": candidate.resource_id},
            )
        if candidate.need_id not in need_ids:
            raise BuildPreparationValidationError(
                "Provider lookup returned a candidate for an unknown need.",
                details={"need_id": candidate.need_id},
            )
        if not candidate.provider:
            raise BuildPreparationValidationError(
                "Provider candidates must identify their provider.",
                details={"resource_id": candidate.resource_id},
            )
        seen.add(candidate.resource_id)
    return candidates


def validate_selection_plan(
    plan: Stage2SelectionPlan,
    need_ids: set[str],
    candidates: list[FetchedResource],
) -> Stage2SelectionPlan:
    """Close Stage 2 selections over the exact Stage 1 candidate set."""
    candidate_ids = {candidate.resource_id for candidate in candidates}
    seen: set[str] = set()
    for selection in plan.selections:
        if selection.need_id in seen:
            raise BuildPreparationValidationError(
                "Stage 2 produced duplicate need IDs.", details={"need_id": selection.need_id}
            )
        if selection.need_id not in need_ids:
            raise BuildPreparationValidationError(
                "Stage 2 referenced an unknown need.", details={"need_id": selection.need_id}
            )
        if selection.selected_resource_id and selection.selected_resource_id not in candidate_ids:
            raise BuildPreparationValidationError(
                "Stage 2 selected a resource that providers did not return.",
                details={"resource_id": selection.selected_resource_id},
            )
        unknown_alternates = set(selection.alternate_resource_ids) - candidate_ids
        if unknown_alternates:
            raise BuildPreparationValidationError(
                "Stage 2 ranked an alternate resource that providers did not return.",
                details={"resource_ids": sorted(unknown_alternates)},
            )
        if selection.selected_resource_id in set(selection.alternate_resource_ids):
            raise BuildPreparationValidationError(
                "Stage 2 cannot rank the selected resource as its own alternate.",
                details={"need_id": selection.need_id},
            )
        if not selection.selected_resource_id and not selection.fallback.strip():
            raise BuildPreparationValidationError(
                "A rejected resource selection must include an explicit fallback.",
                details={"need_id": selection.need_id},
            )
        seen.add(selection.need_id)
    missing = need_ids - seen
    if missing:
        raise BuildPreparationValidationError(
            "Stage 2 did not produce a selection for every Stage 0 need.",
            details={"need_ids": sorted(missing)},
        )
    return plan


def validate_build_context(
    context: BuildContextDraft,
    route_ids: set[str],
    selected_resource_ids: set[str],
) -> BuildContextDraft:
    """Reject dangling route/resource references from Stage 3 or 4."""
    seen_routes: set[str] = set()
    for route in context.routes:
        if route.route_id in seen_routes:
            raise BuildPreparationValidationError(
                "Build context contains duplicate route IDs.",
                details={"route_id": route.route_id},
            )
        if route.route_id not in route_ids:
            raise BuildPreparationValidationError(
                "Build context referenced an unknown route.",
                details={"route_id": route.route_id},
            )
        unknown_resources = set(route.resource_ids) - selected_resource_ids
        if unknown_resources:
            raise BuildPreparationValidationError(
                "Build context referenced an unselected resource.",
                details={"resource_ids": sorted(unknown_resources)},
            )
        if not route.brief_markdown.strip():
            raise BuildPreparationValidationError(
                "Every build-context route must contain a non-empty brief.",
                details={"route_id": route.route_id},
            )
        seen_routes.add(route.route_id)
    missing_routes = route_ids - seen_routes
    if missing_routes:
        raise BuildPreparationValidationError(
            "Build context did not cover every approved route.",
            details={"route_ids": sorted(missing_routes)},
        )
    if not context.overview_markdown.strip():
        raise BuildPreparationValidationError("Build context overview must not be empty.")
    return context


def validate_phase2_contracts(
    query_plan: Stage1QueryPlan,
    candidates: list[FetchedResource],
    selection_plan: Stage2SelectionPlan,
    context: BuildContextDraft,
    *,
    need_ids: set[str],
    route_ids: set[str],
) -> None:
    validate_query_plan(query_plan, need_ids)
    validate_fetched_candidates(candidates, need_ids)
    validate_selection_plan(selection_plan, need_ids, candidates)
    validate_build_context(
        context,
        route_ids,
        {
            selection.selected_resource_id
            for selection in selection_plan.selections
            if selection.selected_resource_id
        },
    )
