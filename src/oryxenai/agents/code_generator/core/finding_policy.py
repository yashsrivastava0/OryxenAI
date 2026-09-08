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
    "approved requirement",
    "must preserve",
    "must include",
    "required interaction",
    "required asset",
    "approved content",
)
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


def effective_finding_severity(finding: Any) -> str:
    """Return ``blocking`` or ``advisory`` using code/evidence semantics."""

    code = str(getattr(finding, "code", "") or "").casefold()
    evidence = " ".join(
        str(getattr(finding, field, "") or "") for field in ("evidence", "requested_outcome")
    ).casefold()
    if str(getattr(finding, "code", "") or "") in _ADVISORY_RUNTIME_CODES:
        return "advisory"
    # A clearly functional/approved requirement wins over a visual adjective
    # in the same finding (for example, an explicit required interaction with
    # a spacing symptom).
    if any(term in code for term in _BLOCKING_TERMS):
        return "blocking"
    if any(term in code for term in _ADVISORY_TERMS):
        if any(phrase in evidence for phrase in _EXPLICIT_REQUIREMENT_PHRASES):
            return "blocking"
        return "advisory"
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
