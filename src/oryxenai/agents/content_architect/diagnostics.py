"""Small, content-free issue locations for Content Architect failures."""

from __future__ import annotations

import re

_PAGE_FIELD = re.compile(
    r"^(?:page_content\.)?(?:hero|metadata|marquee_keywords|systems_practice|"
    r"technical_capabilities|professional_context|connect|atlas)"
    r"(?:\.[A-Za-z_][A-Za-z0-9_]*|\[\d+\])*"
)


def output_issue_locations(errors: list[str]) -> list[dict[str, str]]:
    """Identify our schema field without copying a model value or error text."""
    issues: list[dict[str, str]] = []
    for error in errors[:12]:
        match = _PAGE_FIELD.match(error)
        if match:
            path = match.group(0).removeprefix("page_content.")
        elif error.startswith(("'mode'", "mode")):
            path = "mode"
        elif error.startswith("'content_included'"):
            path = "content_included"
        elif error.startswith("Claim ") or error.startswith("claim_grounding"):
            path = "claim_grounding"
        elif error.startswith("Coverage ledger ") or error.startswith("coverage_ledger"):
            path = "coverage_ledger"
        else:
            continue
        issue = {"code": "invalid_output_field", "path": path}
        if issue not in issues:
            issues.append(issue)
    return issues
