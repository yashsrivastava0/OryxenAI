"""Deterministic validators for Content Architect OUTPUTS only.

Transport-level validation: the response must be parseable, required
envelope keys must exist, mode must be known and consistent with the
operation, route/claim entries must carry usable stable IDs. Free-text
content (site_story_strategy prose, section content blocks, public_content_manifest
copy, visual_director_handoff notes) is NOT business-validated — the model
decides how to phrase things; only the envelope shape is checked, mirroring
how Discovery never business-validates brief_markdown.

Two checks here go beyond pure shape and are deliberate structural backstops
(not content judgment): a BLOCKED route/claim can never be referenced from
public output, and a small set of internal-review key names can never appear
inside a section's visitor-facing `content`. Both were observed to leak
through in real live-model output despite prompt instructions saying
otherwise — prompts alone are not a sufficient enforcement mechanism for
"never happens", so these are enforced here and trigger a bounded retry
(ContentArchitectModelOutputError) instead of silently persisting.

The real provider adapter returns raw parsed JSON with no schema
pre-validation (see providers/opencode_go.py), so every check here must be
defensive — never assume a field has the "right" type before checking it.
"""

from __future__ import annotations

from typing import Any

from oryxenai.agents.content_architect.schemas import (
    ContentPlanMode,
    DecisionBasis,
    EvidenceStatus,
    Ownership,
    PublicationStatus,
)

_PLAN_CONTENT_MODES = {
    ContentPlanMode.STRATEGY_ONLY.value,
    ContentPlanMode.STRATEGY_AND_CONTENT.value,
}
_WRITE_PAGES_MODES = {ContentPlanMode.PAGES_READY.value}
_INTEGRATE_MODES = {ContentPlanMode.INTEGRATED.value}

_OPERATION_MODES = {
    "plan_content": _PLAN_CONTENT_MODES,
    "write_pages": _WRITE_PAGES_MODES,
    "integrate_content": _INTEGRATE_MODES,
}

_GROUNDED_STATUSES = {EvidenceStatus.VERIFIED.value}
_VALID_EVIDENCE_STATUSES = {item.value for item in EvidenceStatus}
_VALID_OWNERSHIP = {item.value for item in Ownership}
_VALID_PUBLICATION_STATUSES = {item.value for item in PublicationStatus}
_VALID_DECISION_BASIS = {item.value for item in DecisionBasis}

# Internal review/QA annotation keys that must live in a page pack's
# internal_notes, never inside a section's visitor-facing content.
_INTERNAL_NOTE_KEYS = {
    "status_note",
    "evidence_status",
    "publication_check",
    "publication_status",
    "verification_status",
    "ownership",
    "internal_note",
    "internal_notes",
    "review_note",
    "review_notes",
    "qa_note",
    "confidence_or_warning",
    "needs_confirmation",
}


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
    known_claim_grounding: list[dict[str, Any]] | None = None,
) -> ValidationOutcome:
    """Validate one internal model call's output for the given operation.

    `operation` is one of "plan_content", "write_pages", "integrate_content".
    `known_route_plan`/`known_claim_grounding` carry stage 1's already-validated
    lists forward for stages that don't re-emit them (write_pages,
    integrate_content) so blocked-entity cross-checks still apply.
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

    content_included = data.get("content_included")
    if not isinstance(content_included, bool):
        errors.append("'content_included' must be a boolean")
    if operation == "plan_content" and isinstance(content_included, bool) and mode in valid_modes:
        expected_mode = (
            ContentPlanMode.STRATEGY_AND_CONTENT.value
            if content_included
            else ContentPlanMode.STRATEGY_ONLY.value
        )
        if mode != expected_mode:
            errors.append(
                f"'mode' ({mode!r}) is inconsistent with content_included={content_included!r}"
            )

    # Route count is NOT validated here (truncate, never reject — a genuinely
    # large senior profile is a fact about the input, not a model mistake;
    # see ContentArchitectAgent's post-validation truncation to max_routes,
    # mirroring Discovery's validate_brief_output/max_projects precedent).
    route_plan = data.get("route_plan")
    if route_plan is not None and not isinstance(route_plan, list):
        errors.append("'route_plan' must be a list when present")
        route_plan = []
    route_plan = route_plan or []
    if operation == "plan_content" and not route_plan:
        errors.append("'route_plan' must not be empty for plan_content")
    errors.extend(_validate_route_plan(route_plan))

    claim_grounding = data.get("claim_grounding")
    if claim_grounding is not None and not isinstance(claim_grounding, list):
        errors.append("'claim_grounding' must be a list when present")
        claim_grounding = []
    errors.extend(_validate_claim_grounding(claim_grounding or []))

    if operation == "plan_content" and not _is_nonempty_dict(data.get("site_story_strategy")):
        errors.append("'site_story_strategy' must not be empty for plan_content")

    decision_basis = data.get("decision_basis")
    if decision_basis is not None and not isinstance(decision_basis, list):
        errors.append("'decision_basis' must be a list when present")
        decision_basis = []
    errors.extend(_validate_decision_basis(decision_basis or []))

    content_required = (operation == "plan_content" and bool(content_included)) or operation in {
        "write_pages",
        "integrate_content",
    }
    page_content_packs = data.get("page_content_packs")
    if page_content_packs is not None and not isinstance(page_content_packs, list):
        errors.append("'page_content_packs' must be a list when present")
        page_content_packs = []
    if content_required:
        if not page_content_packs:
            errors.append(f"'page_content_packs' must not be empty for {operation}")
        if not _is_nonempty_dict(data.get("public_content_manifest")):
            errors.append(f"'public_content_manifest' must not be empty for {operation}")

    effective_route_plan = route_plan or known_route_plan or []
    effective_claim_grounding = claim_grounding or known_claim_grounding or []
    errors.extend(
        _validate_page_content_packs(
            page_content_packs or [], effective_route_plan, effective_claim_grounding
        )
    )

    if operation == "integrate_content" and not _is_nonempty_dict(
        data.get("visual_director_handoff")
    ):
        errors.append("'visual_director_handoff' must not be empty for integrate_content")

    for list_field in ("omissions", "unresolved_issues", "privacy_and_confidentiality", "warnings"):
        value = data.get(list_field)
        if value is not None and not isinstance(value, list):
            errors.append(f"'{list_field}' must be a list when present")

    memory_update = data.get("memory_update")
    if memory_update is not None and not isinstance(memory_update, dict):
        errors.append("'memory_update' must be a dict when present")

    return ValidationOutcome(len(errors) == 0, errors)


def _validate_route_plan(route_plan: list[Any]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, route in enumerate(route_plan):
        if not isinstance(route, dict):
            errors.append(f"Route {index} is not an object")
            continue
        route_id = str(route.get("route_id", "") or "").strip()
        path = str(route.get("path", "") or "").strip()
        purpose = str(route.get("purpose", "") or "").strip()
        if not route_id:
            errors.append(f"Route {index} has no route_id")
        elif route_id in seen:
            errors.append(f"Duplicate route_id: {route_id}")
        else:
            seen.add(route_id)
        if not path:
            errors.append(f"Route {index} ({route_id or index}) has no path")
        if not purpose:
            errors.append(f"Route {index} ({route_id or index}) has no purpose")
        publication_status = route.get("publication_status")
        if publication_status is not None and publication_status not in _VALID_PUBLICATION_STATUSES:
            errors.append(f"Route {index} ({route_id or index}) has invalid publication_status")
    return errors


def _validate_claim_grounding(claim_grounding: list[Any]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, claim in enumerate(claim_grounding):
        if not isinstance(claim, dict):
            errors.append(f"Claim {index} is not an object")
            continue
        claim_id = str(claim.get("claim_id", "") or "").strip()
        if not claim_id:
            errors.append(f"Claim {index} has no claim_id")
        elif claim_id in seen:
            errors.append(f"Duplicate claim_id: {claim_id}")
        else:
            seen.add(claim_id)

        evidence_status = claim.get("evidence_status", EvidenceStatus.UNRESOLVED.value)
        if evidence_status not in _VALID_EVIDENCE_STATUSES:
            errors.append(f"Claim {index} ({claim_id or index}) has invalid evidence_status")
        elif (
            evidence_status in _GROUNDED_STATUSES
            and not str(claim.get("source_reference", "") or "").strip()
        ):
            errors.append(
                f"Claim {index} ({claim_id or index}) is {evidence_status!r} but has no source_reference"
            )

        ownership = claim.get("ownership")
        if ownership is not None and ownership not in _VALID_OWNERSHIP:
            errors.append(f"Claim {index} ({claim_id or index}) has invalid ownership")

        publication_status = claim.get("publication_status")
        if publication_status is not None and publication_status not in _VALID_PUBLICATION_STATUSES:
            errors.append(f"Claim {index} ({claim_id or index}) has invalid publication_status")
    return errors


def _validate_decision_basis(decision_basis: list[Any]) -> list[str]:
    errors: list[str] = []
    for index, record in enumerate(decision_basis):
        if not isinstance(record, dict):
            errors.append(f"Decision record {index} is not an object")
            continue
        if not str(record.get("decision", "") or "").strip():
            errors.append(f"Decision record {index} has no 'decision' name")
        basis = record.get("basis")
        if basis not in _VALID_DECISION_BASIS:
            errors.append(f"Decision record {index} has invalid 'basis': {basis!r}")
    return errors


def _validate_page_content_packs(
    page_content_packs: list[Any],
    route_plan: list[Any],
    claim_grounding: list[Any],
) -> list[str]:
    errors: list[str] = []

    known_route_ids = {
        str(r.get("route_id", "")).strip() for r in route_plan if isinstance(r, dict)
    }
    blocked_route_ids = {
        str(r.get("route_id", "")).strip()
        for r in route_plan
        if isinstance(r, dict) and r.get("publication_status") == PublicationStatus.BLOCKED.value
    }
    known_claim_ids = {
        str(c.get("claim_id", "")).strip() for c in claim_grounding if isinstance(c, dict)
    }
    blocked_claim_ids = {
        str(c.get("claim_id", "")).strip()
        for c in claim_grounding
        if isinstance(c, dict) and c.get("publication_status") == PublicationStatus.BLOCKED.value
    }

    for pack_index, pack in enumerate(page_content_packs):
        if not isinstance(pack, dict):
            errors.append(f"Page content pack {pack_index} is not an object")
            continue
        route_id = str(pack.get("route_id", "") or "").strip()
        if not route_id:
            errors.append(f"Page content pack {pack_index} has no route_id")
        elif known_route_ids and route_id not in known_route_ids:
            errors.append(
                f"Page content pack {pack_index} references unknown route_id {route_id!r}"
            )
        elif route_id in blocked_route_ids:
            errors.append(
                f"Page content pack {pack_index} references blocked route_id {route_id!r} — "
                "blocked routes must not appear in public output"
            )

        sections = pack.get("sections")
        if not isinstance(sections, list):
            errors.append(
                f"Page content pack {pack_index} ({route_id or pack_index}) 'sections' must be a list"
            )
            continue

        section_ids: set[str] = set()
        for section_index, section in enumerate(sections):
            label = f"pack {pack_index} section {section_index}"
            if not isinstance(section, dict):
                errors.append(f"{label} is not an object")
                continue
            section_id = str(section.get("section_id", "") or "").strip()
            if not section_id:
                errors.append(f"{label} has no section_id")
            elif section_id in section_ids:
                errors.append(f"{label} has duplicate section_id {section_id!r} within its pack")
            else:
                section_ids.add(section_id)

            claim_ids = section.get("claim_ids")
            if claim_ids is not None and not isinstance(claim_ids, list):
                errors.append(f"{label} 'claim_ids' must be a list when present")
                claim_ids = []
            for claim_id in claim_ids or []:
                claim_id = str(claim_id).strip()
                if claim_id in blocked_claim_ids:
                    errors.append(
                        f"{label} references blocked claim_id {claim_id!r} — "
                        "blocked claims must not appear in public output"
                    )
                elif known_claim_ids and claim_id not in known_claim_ids:
                    errors.append(f"{label} references unknown claim_id {claim_id!r}")

            content = section.get("content")
            if content is not None and not isinstance(content, dict):
                errors.append(f"{label} 'content' must be an object when present")
            elif isinstance(content, dict):
                leaked = _find_internal_note_keys(content)
                if leaked:
                    errors.append(
                        f"{label} content contains internal-review key(s) {sorted(leaked)} — "
                        "move these into the page pack's internal_notes instead"
                    )

        internal_notes = pack.get("internal_notes")
        if internal_notes is not None and not isinstance(internal_notes, dict):
            errors.append(
                f"Page content pack {pack_index} 'internal_notes' must be an object when present"
            )

    return errors


def _find_internal_note_keys(content: dict[str, Any], *, depth: int = 0) -> set[str]:
    """Recursively (bounded depth) find internal-review key names inside content."""
    found: set[str] = set()
    if depth > 3:
        return found
    for key, value in content.items():
        if key in _INTERNAL_NOTE_KEYS:
            found.add(key)
        if isinstance(value, dict):
            found |= _find_internal_note_keys(value, depth=depth + 1)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    found |= _find_internal_note_keys(item, depth=depth + 1)
    return found


def _is_nonempty_dict(value: Any) -> bool:
    return isinstance(value, dict) and len(value) > 0
