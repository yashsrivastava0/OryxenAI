"""One host-owned release policy for generated-site findings.

Model severity is evidence, not authority.  Functional failures and explicit
contract violations remain blocking; subjective visual polish is retained in
the receipt as an advisory note so it cannot consume the repair budget or
hide an otherwise usable preview.
"""

from __future__ import annotations

from typing import Any

_BLOCKING_TERMS = (
    "build",
    "type",
    "runtime",
    "exception",
    "error",
    "missing",
    "broken",
    "navigation",
    "interaction",
    "accessibility",
    "asset",
    "overflow",
    "clip",
    "hidden",
    "unsafe",
    "network",
    "required",
    "coverage",
)
_EXPLICIT_REQUIREMENT_PHRASES = (
    "must preserve",
    "must include",
    "required interaction",
    "required asset",
    "explicitly required",
)
_ADVISORY_FUNCTIONAL_REQUIREMENT_PHRASES = (
    "required interaction",
    "required asset",
    "explicitly required",
)
_BLOCKING_MODEL_CODES = {
    # These findings describe an observable product contract or an approved
    # interaction.  Their severity is independent of the provider's declared
    # value and of any visual language in the evidence.
    "interaction-hidden-approved-content",
    "interaction-state-missing",
}
_ADVISORY_MODEL_CODES = {
    # These are whole-site aesthetic observations.  In particular, the
    # ``missing`` and ``coverage`` words in these identifiers must not turn a
    # subjective review into a functional release blocker.
    "blueprint-distinctive-move-missing",
    "composition-missing-section-rail",
    "motion-grouping-mismatch",
    "typography-role-coverage",
    # ``columns_*`` are abstract design-grid spans; a legitimate two-track
    # realization must not be treated as a failed functional contract merely
    # because the provider compares the span with CSS track count.
    "blueprint-desktop-column-mismatch",
    "blueprint-resource-role-mismatch",
    "generic-disclosure-label",
    "noninformative-disclosure",
    "redundant-disclosure-control",
    "active-navigation-state",
}
_ADVISORY_TERMS = (
    "visual",
    "composition",
    "spacing",
    "ratio",
    "decorative",
    "aesthetic",
    "polish",
    "motion",
    "similarity",
    "typography",
    "layout",
)
_ADVISORY_RUNTIME_CODES = {
    "RUNTIME_REGION_WIDTH_RATIO",
    "RUNTIME_REGION_COLUMN_COUNT",
    "RUNTIME_REGION_GAP",
    "RUNTIME_REGION_MEASURE",
    "RUNTIME_DISTINCTIVE_RELATIONSHIP",
    "RUNTIME_SECTION_GAP_EXCESSIVE",
}
_BLOCKING_RUNTIME_CODES = {
    "RUNTIME_ANCHOR_TARGET_MISSING",
    "RUNTIME_ASSERTION_FAILED",
    "RUNTIME_ASSET_FAILED",
    "RUNTIME_CONSOLE_ERROR",
    "RUNTIME_CONTENT_OUT_OF_VIEWPORT",
    "RUNTIME_CSP_VIOLATION",
    "RUNTIME_DOM_ID_DUPLICATE",
    "RUNTIME_EMPTY_SHELL",
    "RUNTIME_FONT_LOAD_FAILED",
    "RUNTIME_FONT_SELECTOR",
    "RUNTIME_GEOMETRY_INVALID",
    "RUNTIME_H1_COUNT_INVALID",
    "RUNTIME_IMAGE_DECODE_FAILED",
    "RUNTIME_INTERACTION_ID_DUPLICATE",
    "RUNTIME_INTERACTION_SELECTOR",
    "RUNTIME_INTERACTION_STATE_ATTRIBUTE",
    "RUNTIME_INTERNAL_ROUTE_UNRESOLVED",
    "RUNTIME_LAYOUT_RECIPE_EMPTY_TRACK",
    "RUNTIME_LAYOUT_RECIPE_PROPERTY_MISSING",
    "RUNTIME_MAIN_COUNT_INVALID",
    "RUNTIME_MAIN_GEOMETRY_INVALID",
    "RUNTIME_MOTION_REDUCED_CONTENT_HIDDEN",
    "RUNTIME_MOTION_SELECTOR",
    "RUNTIME_MOTION_STATE_MISMATCH",
    "RUNTIME_MOTION_STATE_UNCHANGED",
    "RUNTIME_OUTBOUND_REQUEST",
    "RUNTIME_PAGE_ERROR",
    "RUNTIME_REALIZATION_INVALID",
    "RUNTIME_REDUCED_MOTION_UNSAFE",
    "RUNTIME_REGION_OVERLAP",
    "RUNTIME_REGION_SECTION_SELECTOR",
    "RUNTIME_REGION_SELECTOR",
    "RUNTIME_REGION_STICKY_UNAUTHORIZED",
    "RUNTIME_RESOURCE_ANCESTOR_HIDDEN",
    "RUNTIME_RESOURCE_ANCESTOR_OPACITY",
    "RUNTIME_RESOURCE_ASPECT_RATIO",
    "RUNTIME_RESOURCE_CLIPPED",
    "RUNTIME_RESOURCE_DECODE",
    "RUNTIME_RESOURCE_DIMENSIONS_MISSING",
    "RUNTIME_RESOURCE_LOADING_POLICY",
    "RUNTIME_RESOURCE_NOT_VISIBLE",
    "RUNTIME_RESOURCE_OCCLUDED",
    "RUNTIME_RESOURCE_PATH_MISMATCH",
    "RUNTIME_RESOURCE_SELECTOR",
    "RUNTIME_RESOURCE_SRCSET_MISSING",
    "RUNTIME_RESOURCE_VISIBLE_USE",
    "RUNTIME_SECTION_COLLAPSED",
    "RUNTIME_SECTION_COLLISION",
    "RUNTIME_SECTION_ORDER",
    "RUNTIME_SECTION_ORDER_INVALID",
    "RUNTIME_TEXT_CLIPPED",
    "RUNTIME_TEXT_TOO_SMALL",
    "RUNTIME_TOUCH_TARGET_TOO_SMALL",
}


def effective_finding_severity(finding: Any) -> str:
    """Return ``blocking`` or ``advisory`` using code/evidence semantics."""

    code = str(getattr(finding, "code", "") or "").casefold()
    normalized_code = str(getattr(finding, "code", "") or "")
    evidence = " ".join(
        str(getattr(finding, field, "") or "") for field in ("evidence", "requested_outcome")
    ).casefold()
    if normalized_code in _ADVISORY_RUNTIME_CODES:
        return "advisory"
    if normalized_code in _BLOCKING_RUNTIME_CODES:
        return "blocking"
    if code in _BLOCKING_MODEL_CODES:
        return "blocking"
    if code in _ADVISORY_MODEL_CODES:
        # Keep known visual observations advisory even when their prose uses
        # generic words such as "must" or "approved".  Only a disclosure/nav
        # observation that explicitly names a required interaction/asset is a
        # functional failure; a wrong crop, span, or polish suggestion needs a
        # separate concrete contract code to become blocking.
        if code in {
            "noninformative-disclosure",
            "generic-disclosure-label",
            "redundant-disclosure-control",
            "active-navigation-state",
        } and any(phrase in evidence for phrase in _ADVISORY_FUNCTIONAL_REQUIREMENT_PHRASES):
            return "blocking"
        return "advisory"
    # Evidence that names an explicit contract wins over an otherwise unknown
    # finding.  Generic "approved" wording deliberately is not sufficient.
    if any(phrase in evidence for phrase in _EXPLICIT_REQUIREMENT_PHRASES):
        return "blocking"
    # Subjective visual evidence is advisory by default.  This check comes
    # before generic words such as ``missing`` and ``coverage`` so a code such
    # as ``missing-visual-balance`` cannot become a functional blocker merely
    # because of its vocabulary.
    if any(term in code or term in evidence for term in _ADVISORY_TERMS):
        return "advisory"
    # Unknown findings without an explicitly visual signal stay conservative;
    # known functional codes above remain explicit rather than relying on
    # substring guesses.
    if any(term in code for term in _BLOCKING_TERMS):
        return "blocking"
    if any(term in evidence for term in _BLOCKING_TERMS):
        return "blocking"
    # Unknown findings stay visible and conservative.  Their declared
    # severity is not allowed to disappear merely because this policy does not
    # yet know their vocabulary.
    return "blocking" if getattr(finding, "severity", "blocking") == "blocking" else "advisory"


def normalize_findings(findings: list[Any]) -> list[Any]:
    """Copy findings with their host-derived effective severity."""

    normalized: list[Any] = []
    for finding in findings:
        severity = effective_finding_severity(finding)
        if getattr(finding, "severity", None) == severity:
            normalized.append(finding)
        elif hasattr(finding, "model_copy"):
            normalized.append(finding.model_copy(update={"severity": severity}))
        else:
            normalized.append(finding)
    return normalized


def has_blocking_findings(findings: list[Any]) -> bool:
    return any(effective_finding_severity(item) == "blocking" for item in findings)


__all__ = [
    "effective_finding_severity",
    "has_blocking_findings",
    "normalize_findings",
]
