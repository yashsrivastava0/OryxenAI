"""Deterministic validators for Content Architect OUTPUTS only.

Transport-level validation: the response must be parseable, required
envelope keys must exist, mode must be known and consistent with the
operation, and the page content tree must have the right JSON types. Free-text
copy is NOT business-validated — the model decides how to phrase things.
Template completeness (exactly four pillars, a hero name, ...) is checked
separately by the agent's approval-readiness gate so one bounded repair call
can fix it instead of failing the whole run.

Two checks here go beyond pure shape and are deliberate structural backstops
(not content judgment): a BLOCKED claim can never be bound to a public field,
and a small set of internal-review key names can never appear inside page
copy. Both were observed to leak through in real live-model output despite
prompt instructions saying otherwise — prompts alone are not a sufficient
enforcement mechanism for "never happens", so these are enforced here and
trigger a bounded retry (ContentArchitectModelOutputError) instead of
silently persisting.

The real provider adapter returns raw parsed JSON with no schema
pre-validation (see providers/opencode_go.py), so every check here must be
defensive — never assume a field has the "right" type before checking it.
"""

from __future__ import annotations

from typing import Any

from oryxenai.agents.content_architect.page_content import (
    model_errors,
    page_model_errors,
    page_shape_errors,
)
from oryxenai.agents.content_architect.schemas import (
    ClaimGrounding,
    ContentCoverageEntry,
    ContentPlanMode,
    ContentStoryStrategy,
    DecisionBasis,
    DecisionRecord,
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
    known_claim_grounding: list[dict[str, Any]] | None = None,
) -> ValidationOutcome:
    """Validate one internal model call's output for the given operation.

    `operation` is one of "plan_content", "write_pages", "integrate_content".
    `known_claim_grounding` carries stage 1's already-validated claims forward
    for stages that do not re-emit them, so blocked-claim checks still apply.
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

    claim_grounding = data.get("claim_grounding")
    if claim_grounding is not None and not isinstance(claim_grounding, list):
        errors.append("'claim_grounding' must be a list when present")
        claim_grounding = []
    errors.extend(_validate_claim_grounding(claim_grounding or []))
    for index, claim in enumerate(claim_grounding or []):
        if isinstance(claim, dict):
            errors.extend(model_errors(f"claim_grounding[{index}]", ClaimGrounding, claim))

    coverage_ledger = data.get("coverage_ledger")
    if coverage_ledger is not None and not isinstance(coverage_ledger, list):
        errors.append("'coverage_ledger' must be a list when present")
    for index, entry in enumerate(coverage_ledger if isinstance(coverage_ledger, list) else []):
        if isinstance(entry, dict):
            errors.extend(model_errors(f"coverage_ledger[{index}]", ContentCoverageEntry, entry))

    strategy = data.get("site_story_strategy")
    if operation == "plan_content" and not _is_nonempty_dict(strategy):
        errors.append("'site_story_strategy' must not be empty for plan_content")
    elif strategy is not None:
        errors.extend(model_errors("site_story_strategy", ContentStoryStrategy, strategy))

    decision_basis = data.get("decision_basis")
    if decision_basis is not None and not isinstance(decision_basis, list):
        errors.append("'decision_basis' must be a list when present")
        decision_basis = []
    errors.extend(_validate_decision_basis(decision_basis or []))
    for index, record in enumerate(decision_basis or []):
        if isinstance(record, dict):
            errors.extend(model_errors(f"decision_basis[{index}]", DecisionRecord, record))

    content_required = (operation == "plan_content" and bool(content_included)) or operation in {
        "write_pages",
        "integrate_content",
    }
    page_content = data.get("page_content")
    if content_required and not _is_nonempty_dict(page_content):
        errors.append(f"'page_content' must not be empty for {operation}")
    elif page_content is not None:
        shape_errors = page_shape_errors(page_content)
        errors.extend(shape_errors)
        if not shape_errors:
            errors.extend(page_model_errors(page_content))

    effective_claims = claim_grounding or known_claim_grounding or []
    for claim in effective_claims:
        if (
            isinstance(claim, dict)
            and claim.get("publication_status") == PublicationStatus.BLOCKED.value
            and claim.get("field_paths")
        ):
            errors.append(
                f"blocked claim {str(claim.get('claim_id', '')).strip()!r} is bound to public "
                "field(s) — blocked claims must not appear in public output"
            )

    for list_field in ("omissions", "unresolved_issues", "privacy_and_confidentiality", "warnings"):
        value = data.get(list_field)
        if value is not None and not isinstance(value, list):
            errors.append(f"'{list_field}' must be a list when present")

    for dict_field in ("memory_update", "internal_notes"):
        value = data.get(dict_field)
        if value is not None and not isinstance(value, dict):
            errors.append(f"'{dict_field}' must be a dict when present")

    return ValidationOutcome(len(errors) == 0, errors)


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

        field_paths = claim.get("field_paths")
        if field_paths is not None and (
            not isinstance(field_paths, list) or any(not isinstance(p, str) for p in field_paths)
        ):
            errors.append(
                f"Claim {index} ({claim_id or index}) field_paths must be a list of strings"
            )
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


def _is_nonempty_dict(value: Any) -> bool:
    return isinstance(value, dict) and len(value) > 0
