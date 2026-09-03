"""Validation for deterministic Stage 0 inputs/outputs and the model's brief output."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from oryxenai.agents.build_preparation.schemas import Stage0Result, VisualBriefOutput


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


def validate_visual_brief_output(
    output: VisualBriefOutput,
    *,
    need_ids: set[str],
    candidate_counts: dict[str, int],
    suggestion_counts: dict[str, int],
) -> VisualBriefOutput:
    """Reject any model pick that isn't a real index into the given candidates.

    This is the whole enforcement mechanism for "never invent a resource": the
    model can only choose ``None`` or an in-range index into the candidate
    list Build Preparation's own deterministic discovery step already found.
    """
    if not output.visual_brief_prose.strip():
        raise BuildPreparationValidationError("The visual brief prose must not be empty.")
    seen: set[str] = set()
    for guidance in output.resource_guidance:
        if guidance.need_id in seen:
            raise BuildPreparationValidationError(
                "The model returned duplicate resource guidance for one need.",
                details={"need_id": guidance.need_id},
            )
        seen.add(guidance.need_id)
        if guidance.need_id not in need_ids:
            raise BuildPreparationValidationError(
                "The model returned guidance for an unknown resource need.",
                details={"need_id": guidance.need_id},
            )
        available = candidate_counts.get(guidance.need_id, 0)
        if guidance.primary_candidate_index is not None and not (
            0 <= guidance.primary_candidate_index < available
        ):
            raise BuildPreparationValidationError(
                "The model picked a resource candidate index that was not in the "
                "discovered candidate list.",
                details={"need_id": guidance.need_id, "index": guidance.primary_candidate_index},
            )
    seen = set()
    for component_guidance in output.component_guidance:
        if component_guidance.need_id in seen:
            raise BuildPreparationValidationError(
                "The model returned duplicate component guidance for one need.",
                details={"need_id": component_guidance.need_id},
            )
        seen.add(component_guidance.need_id)
        if component_guidance.need_id not in need_ids:
            raise BuildPreparationValidationError(
                "The model returned guidance for an unknown component need.",
                details={"need_id": component_guidance.need_id},
            )
        available = suggestion_counts.get(component_guidance.need_id, 0)
        if component_guidance.primary_suggestion_index is not None and not (
            0 <= component_guidance.primary_suggestion_index < available
        ):
            raise BuildPreparationValidationError(
                "The model picked a component suggestion index that was not in the "
                "discovered suggestion list.",
                details={
                    "need_id": component_guidance.need_id,
                    "index": component_guidance.primary_suggestion_index,
                },
            )
    return output
