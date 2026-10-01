"""Shared builders for Content Architect unit tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from tests.conftest import _CA_PAGE_CONTENT


def valid_page() -> dict[str, Any]:
    """A complete, template-ready page_content dict (fresh copy per call)."""
    return deepcopy(_CA_PAGE_CONTENT)


def claim(
    claim_id: str = "claim:one",
    *,
    publication_status: str = "approved",
    field_paths: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "statement": "A supplied statement.",
        "source_reference": "profile.projects[0]",
        "evidence_status": "verified",
        "ownership": "individual",
        "publication_status": publication_status,
        "field_paths": field_paths or [],
    }


def plan_payload(
    *, content_included: bool = True, integration_needed: bool = False
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "mode": "STRATEGY_AND_CONTENT" if content_included else "STRATEGY_ONLY",
        "content_included": content_included,
        "integration_needed": integration_needed,
        "site_story_strategy": {"positioning": "x"},
        "claim_grounding": [],
    }
    if content_included:
        payload["page_content"] = valid_page()
    return payload


def pages_payload(*, integration_needed: bool = False) -> dict[str, Any]:
    return {
        "mode": "PAGES_READY",
        "content_included": False,
        "integration_needed": integration_needed,
        "page_content": valid_page(),
        "claim_grounding": [],
    }


def integrate_payload(page: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "mode": "INTEGRATED",
        "content_included": False,
        "page_content": page if page is not None else valid_page(),
    }
