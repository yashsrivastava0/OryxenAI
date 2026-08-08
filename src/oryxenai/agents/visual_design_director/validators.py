"""Deterministic validators for Visual Design Director OUTPUTS only.

Transport-level validation: the response must be parseable, required
envelope keys must exist, mode must be known and consistent with the
operation, page/scene/asset/resource entries must carry usable stable IDs.
Free-text/free-dict direction (visual_language, shared_visual_systems,
storyboard, layout_intent, motion_intent, compiler_handoff, ...) is NOT
business-validated — the model decides how to phrase things; only the
envelope shape is checked, mirroring Content Architect's exact philosophy.

Per DECISIONS.md D-002, this stays strictly envelope/structural — no
synthesized "subjective quality" warnings (excessive motion, long copy,
density, ...). Those are prompt-carried self-reporting instructions instead
(see prompts/system.md's self_report_rule); nothing here computes them.

Two checks here go beyond pure shape and are deliberate structural
backstops, mirroring Content Architect's own precedent (a BLOCKED route can
never be referenced from public output; there, that was added because real
model output was observed leaking blocked content despite prompt
instructions saying not to): a BLOCKED Content Architect route can never be
referenced from visual output, and a resource_id can only ever be one that
was actually offered to the model in this call's catalogue shortlist —
closed-set selection, never model-invented, per DECISIONS.md D-001.

The real provider adapter returns raw parsed JSON with no schema
pre-validation (see agents/shared/providers/opencode_go.py), so every check
here must be defensive — never assume a field has the "right" type before
checking it.
"""

from __future__ import annotations

from typing import Any

from oryxenai.agents.visual_design_director.schemas import AssetImportance, VisualPlanMode

_VISUAL_LANGUAGE_MODES = {
    VisualPlanMode.VISUAL_LANGUAGE_ONLY.value,
    VisualPlanMode.VISUAL_LANGUAGE_AND_PAGES.value,
}
_DIRECT_PAGES_MODES = {VisualPlanMode.PAGES_READY.value}
_INTEGRATE_MODES = {VisualPlanMode.INTEGRATED.value}

_OPERATION_MODES = {
    "establish_visual_language": _VISUAL_LANGUAGE_MODES,
    "direct_page_experience": _DIRECT_PAGES_MODES,
    "integrate_site_experience": _INTEGRATE_MODES,
}

_VALID_IMPORTANCE = {item.value for item in AssetImportance}


class ValidationOutcome:
    """Immutable result of a validation run."""

    def __init__(self, is_valid: bool, errors: list[str]) -> None:
        self.is_valid = is_valid
        self.errors = errors

    def __bool__(self) -> bool:
        return self.is_valid


def validate_stage_output(
    data: dict[str, Any],
    operation: str,
    *,
    known_route_plan: list[dict[str, Any]] | None = None,
    known_resource_ids: set[str] | None = None,
) -> ValidationOutcome:
    """Validate one internal model call's output for the given operation.

    `operation` is one of "establish_visual_language", "direct_page_experience",
    "integrate_site_experience". `known_route_plan` carries Content Architect's
    route entries (route_id/publication_status) for cross-checking;
    `known_resource_ids` is the exact catalogue shortlist given to this call.
    """
    errors: list[str] = []
    if not isinstance(data, dict):
        return ValidationOutcome(False, ["output is not a JSON object"])

    valid_modes = _OPERATION_MODES.get(operation)
    if valid_modes is None:
        return ValidationOutcome(False, [f"unknown operation: {operation!r}"])

    mode = data.get("mode")
    if mode not in valid_modes:
        errors.append(f"'mode' must be one of {sorted(valid_modes)} for {operation}; got {mode!r}")

    pages_included = data.get("pages_included")
    if not isinstance(pages_included, bool):
        errors.append("'pages_included' must be a boolean")
    if (
        operation == "establish_visual_language"
        and isinstance(pages_included, bool)
        and mode in valid_modes
    ):
        expected_mode = (
            VisualPlanMode.VISUAL_LANGUAGE_AND_PAGES.value
            if pages_included
            else VisualPlanMode.VISUAL_LANGUAGE_ONLY.value
        )
        if mode != expected_mode:
            errors.append(
                f"'mode' ({mode!r}) is inconsistent with pages_included={pages_included!r}"
            )

    if operation == "establish_visual_language":
        if not _is_nonempty_dict(data.get("visual_language")):
            errors.append("'visual_language' must not be empty for establish_visual_language")
        if not _is_nonempty_dict(data.get("shared_visual_systems")):
            errors.append("'shared_visual_systems' must not be empty for establish_visual_language")

    pages = data.get("pages")
    if pages is not None and not isinstance(pages, list):
        errors.append("'pages' must be a list when present")
        pages = []
    pages = pages or []

    pages_required = (operation == "establish_visual_language" and bool(pages_included)) or (
        operation in {"direct_page_experience", "integrate_site_experience"}
    )
    if pages_required and not pages:
        errors.append(f"'pages' must not be empty for {operation}")

    known_route_ids: set[str] = set()
    blocked_route_ids: set[str] = set()
    if known_route_plan:
        for route in known_route_plan:
            if not isinstance(route, dict):
                continue
            route_id = str(route.get("route_id", "") or "").strip()
            if not route_id:
                continue
            known_route_ids.add(route_id)
            if route.get("publication_status") == "blocked":
                blocked_route_ids.add(route_id)

    page_errors, page_route_ids, scene_ids, referenced_resource_ids = _validate_pages(
        pages, known_route_ids, blocked_route_ids
    )
    errors.extend(page_errors)

    if operation in {"direct_page_experience", "integrate_site_experience"} and known_route_ids:
        expected_coverage = known_route_ids - blocked_route_ids
        missing = expected_coverage - page_route_ids
        for route_id in sorted(missing):
            errors.append(f"route_id {route_id!r} has no visual direction (missing from 'pages')")

    asset_briefs = data.get("asset_briefs")
    if asset_briefs is not None and not isinstance(asset_briefs, list):
        errors.append("'asset_briefs' must be a list when present")
        asset_briefs = []
    asset_brief_errors, asset_ids = _validate_asset_briefs(asset_briefs or [])
    errors.extend(asset_brief_errors)

    resource_candidates = data.get("resource_candidates")
    if resource_candidates is not None and not isinstance(resource_candidates, list):
        errors.append("'resource_candidates' must be a list when present")
        resource_candidates = []
    resource_errors, resource_ids = _validate_resource_candidates(resource_candidates or [])
    errors.extend(resource_errors)

    for id_label, ids in (
        ("scene_id", scene_ids),
        ("asset_id", asset_ids),
        ("resource_id", resource_ids),
    ):
        duplicates = _find_duplicates(ids)
        if duplicates:
            errors.append(f"Duplicate {id_label} value(s): {sorted(duplicates)}")

    if known_resource_ids is not None:
        all_referenced_resource_ids = referenced_resource_ids | set(resource_ids)
        unknown = {rid for rid in all_referenced_resource_ids if rid} - known_resource_ids
        if unknown:
            errors.append(
                f"resource_id(s) {sorted(unknown)} were not in the catalogue shortlist given to this call"
            )

    if operation == "integrate_site_experience":
        if not _is_nonempty_dict(data.get("compiler_handoff")):
            errors.append("'compiler_handoff' must not be empty for integrate_site_experience")
    elif _is_nonempty_dict(data.get("compiler_handoff")):
        # compiler_handoff summarizes the FINAL, fully-reconciled state —
        # only integrate_site_experience has that. A stage 1 or stage 2
        # response that writes premature compiler guidance was observed
        # going stale the moment a later stage actually produced the pages
        # it claimed were deferred (e.g. "do not compile route X" persisting
        # after route X's full scene direction was written) — hard reject
        # here rather than trust prompt discipline alone, mirroring Content
        # Architect's own precedent for narrative fields that were observed
        # contradicting the structured output around them.
        errors.append(
            f"'compiler_handoff' must be empty for {operation} — only "
            "integrate_site_experience may populate it"
        )

    for list_field in ("must_preserve", "must_not_fabricate", "conflicts", "warnings"):
        value = data.get(list_field)
        if value is not None and not isinstance(value, list):
            errors.append(f"'{list_field}' must be a list when present")

    memory_update = data.get("memory_update")
    if memory_update is not None and not isinstance(memory_update, dict):
        errors.append("'memory_update' must be a dict when present")

    return ValidationOutcome(len(errors) == 0, errors)


def _validate_pages(
    pages: list[Any],
    known_route_ids: set[str],
    blocked_route_ids: set[str],
) -> tuple[list[str], set[str], list[str], set[str]]:
    errors: list[str] = []
    seen_route_ids: set[str] = set()
    scene_ids: list[str] = []
    referenced_resource_ids: set[str] = set()

    for page_index, page in enumerate(pages):
        if not isinstance(page, dict):
            errors.append(f"Page {page_index} is not an object")
            continue
        route_id = str(page.get("route_id", "") or "").strip()
        if not route_id:
            errors.append(f"Page {page_index} has no route_id")
        elif route_id in seen_route_ids:
            errors.append(f"Duplicate page route_id: {route_id}")
        else:
            seen_route_ids.add(route_id)

        if route_id:
            if known_route_ids and route_id not in known_route_ids:
                errors.append(f"Page {page_index} references unknown route_id {route_id!r}")
            elif route_id in blocked_route_ids:
                errors.append(
                    f"Page {page_index} references blocked route_id {route_id!r} — "
                    "blocked routes must not appear in visual output"
                )

        for resource_id in page.get("resource_candidates") or []:
            referenced_resource_ids.add(str(resource_id))

        scenes = page.get("scenes")
        if scenes is not None and not isinstance(scenes, list):
            errors.append(f"Page {page_index} ({route_id or page_index}) 'scenes' must be a list")
            continue

        for scene_index, scene in enumerate(scenes or []):
            label = f"page {page_index} scene {scene_index}"
            if not isinstance(scene, dict):
                errors.append(f"{label} is not an object")
                continue

            scene_id = str(scene.get("scene_id", "") or "").strip()
            if not scene_id:
                errors.append(f"{label} has no scene_id")
            else:
                scene_ids.append(scene_id)

            responsive_behavior = scene.get("responsive_behavior")
            if not str(responsive_behavior or "").strip():
                errors.append(f"{label} ({scene_id or scene_index}) has no responsive_behavior")

            motion_intent = scene.get("motion_intent")
            if motion_intent is not None and not isinstance(motion_intent, dict):
                errors.append(f"{label} 'motion_intent' must be an object when present")
            elif _is_nonempty_dict(motion_intent):
                reduced_motion_behavior = scene.get("reduced_motion_behavior")
                if not str(reduced_motion_behavior or "").strip():
                    errors.append(
                        f"{label} ({scene_id or scene_index}) has non-trivial motion_intent "
                        "but no reduced_motion_behavior"
                    )

            for resource_id in scene.get("resource_candidates") or []:
                referenced_resource_ids.add(str(resource_id))

    return errors, seen_route_ids, scene_ids, referenced_resource_ids


def _validate_asset_briefs(asset_briefs: list[Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    asset_ids: list[str] = []
    for index, asset in enumerate(asset_briefs):
        if not isinstance(asset, dict):
            errors.append(f"Asset brief {index} is not an object")
            continue
        asset_id = str(asset.get("asset_id", "") or "").strip()
        if not asset_id:
            errors.append(f"Asset brief {index} has no asset_id")
        else:
            asset_ids.append(asset_id)

        importance = asset.get("importance", AssetImportance.OPTIONAL.value)
        if importance not in _VALID_IMPORTANCE:
            errors.append(f"Asset brief {index} ({asset_id or index}) has invalid importance")
        elif importance != AssetImportance.OPTIONAL.value:
            source_status = str(asset.get("source_status", "") or "").strip()
            fallback_strategy = str(asset.get("fallback_strategy", "") or "").strip()
            if not source_status:
                errors.append(
                    f"Asset brief {index} ({asset_id or index}) has importance={importance!r} "
                    "but no source_status"
                )
            if not fallback_strategy:
                errors.append(
                    f"Asset brief {index} ({asset_id or index}) has importance={importance!r} "
                    "but no fallback_strategy"
                )
    return errors, asset_ids


def _validate_resource_candidates(resource_candidates: list[Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    resource_ids: list[str] = []
    for index, resource in enumerate(resource_candidates):
        if not isinstance(resource, dict):
            errors.append(f"Resource candidate {index} is not an object")
            continue
        resource_id = str(resource.get("resource_id", "") or "").strip()
        if not resource_id:
            errors.append(f"Resource candidate {index} has no resource_id")
        else:
            resource_ids.append(resource_id)
    return errors, resource_ids


def _find_duplicates(ids: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in ids:
        if not value:
            continue
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return duplicates


def _is_nonempty_dict(value: Any) -> bool:
    return isinstance(value, dict) and len(value) > 0
