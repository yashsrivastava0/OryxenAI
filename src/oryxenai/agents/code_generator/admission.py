"""Content admission: refuse content the pinned template cannot render, up front.

Content Architect enforces structure, not size. A page with hundreds of items or
paragraphs of text would blow the model's output limit and fail late and
expensively, so the host checks counts and lengths **before any model call** and
reports the exact field. Completeness reuses Content Architect's own rules.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from oryxenai.agents.content_architect.page_content import (
    atlas_page_errors,
    page_completeness_errors,
    page_shape_errors,
)
from oryxenai.themes import uses_atlas_content
from oryxenai.themes.issues import Issue

# field -> max characters
TEXT_LIMITS: dict[str, int] = {
    "hero.name": 120,
    "hero.eyebrow_primary": 120,
    "hero.eyebrow_secondary": 120,
    "hero.headline_prefix": 220,
    "hero.headline_emphasis": 160,
    "hero.intro": 1400,
    "hero.location": 120,
    "hero.primary_cta_label": 80,
    "hero.secondary_cta_label": 80,
    "metadata.title": 160,
    "metadata.description": 420,
}
SECTION_LIMITS = {"eyebrow": 60, "heading": 220, "intro": 900}
MAX_MARQUEE_KEYWORDS = 20
MAX_KEYWORD_CHARS = 60
MAX_PILLAR_TITLE = 120
MAX_PILLAR_DESCRIPTION = 420
MAX_GROUPS = 8
MAX_ITEMS_PER_GROUP = 60
MAX_TOTAL_ITEMS = 240
MAX_ITEM_CHARS = 120
MAX_GROUP_HEADING = 120
MAX_ORGANIZATIONS = 30
MAX_ORGANIZATION_CHARS = 160
MAX_DESTINATIONS = 12
MAX_LABEL_CHARS = 80
MAX_URL_CHARS = 500

_PATH_PREFIX = re.compile(r"^(?:page_content\.)?([A-Za-z_][\w.\[\]]*)")


def _issue(
    code: str, message: str, path: str, *, expected: str | None = None, found: str | None = None
) -> Issue:
    return Issue(code, "error", message, path=path, expected=expected, found=found)


def _too_long(path: str, value: Any, limit: int) -> Issue | None:
    if isinstance(value, str) and len(value.strip()) > limit:
        return _issue(
            "CONTENT_LIMIT_EXCEEDED",
            f"{path} is {len(value.strip())} characters; this template fits at most {limit}.",
            path,
            expected=f"<= {limit} characters",
            found=f"{len(value.strip())} characters",
        )
    return None


def content_admission_issues(
    page_content: Mapping[str, Any],
    *,
    theme_id: str = "",
    allow_illustrative_work: bool = False,
) -> list[Issue]:
    """Everything wrong with ``page_content`` for building a page (empty = buildable)."""
    content = dict(page_content)
    issues: list[Issue] = []
    atlas_errors = (
        atlas_page_errors(content, allow_illustrative_work=allow_illustrative_work)
        if uses_atlas_content(theme_id)
        else []
    )
    for message in [*page_shape_errors(content), *page_completeness_errors(content), *atlas_errors]:
        match = _PATH_PREFIX.match(message)
        issues.append(
            Issue(
                "CONTENT_INCOMPLETE",
                "error",
                message,
                path=match.group(1) if match else None,
            )
        )
    if issues:
        return issues

    def region(key: str) -> Mapping[str, Any]:
        value = content.get(key)
        return value if isinstance(value, Mapping) else {}

    def check(path: str, value: Any, limit: int) -> None:
        found = _too_long(path, value, limit)
        if found is not None:
            issues.append(found)

    for path, limit in TEXT_LIMITS.items():
        group, _, field = path.partition(".")
        check(path, region(group).get(field), limit)
    for key in ("systems_practice", "technical_capabilities", "professional_context", "connect"):
        for field, limit in SECTION_LIMITS.items():
            check(f"{key}.{field}", region(key).get(field), limit)

    keywords = content.get("marquee_keywords")
    if isinstance(keywords, list):
        if len(keywords) > MAX_MARQUEE_KEYWORDS:
            issues.append(
                _issue(
                    "CONTENT_LIMIT_EXCEEDED",
                    f"marquee_keywords has {len(keywords)} entries; at most {MAX_MARQUEE_KEYWORDS} fit.",
                    "marquee_keywords",
                    expected=f"<= {MAX_MARQUEE_KEYWORDS}",
                    found=str(len(keywords)),
                )
            )
        for index, keyword in enumerate(keywords):
            check(f"marquee_keywords[{index}]", keyword, MAX_KEYWORD_CHARS)

    pillars = region("systems_practice").get("pillars")
    for index, pillar in enumerate(pillars if isinstance(pillars, list) else []):
        if isinstance(pillar, Mapping):
            check(f"systems_practice.pillars[{index}].title", pillar.get("title"), MAX_PILLAR_TITLE)
            check(
                f"systems_practice.pillars[{index}].description",
                pillar.get("description"),
                MAX_PILLAR_DESCRIPTION,
            )

    groups = region("technical_capabilities").get("groups")
    group_list = groups if isinstance(groups, list) else []
    if len(group_list) > MAX_GROUPS:
        issues.append(
            _issue(
                "CONTENT_LIMIT_EXCEEDED",
                f"technical_capabilities.groups has {len(group_list)} groups; at most {MAX_GROUPS} fit.",
                "technical_capabilities.groups",
                expected=f"<= {MAX_GROUPS}",
                found=str(len(group_list)),
            )
        )
    total = 0
    for index, group in enumerate(group_list):
        if not isinstance(group, Mapping):
            continue
        base = f"technical_capabilities.groups[{index}]"
        check(f"{base}.heading", group.get("heading"), MAX_GROUP_HEADING)
        items = group.get("items")
        item_list = items if isinstance(items, list) else []
        total += len(item_list)
        if len(item_list) > MAX_ITEMS_PER_GROUP:
            issues.append(
                _issue(
                    "CONTENT_LIMIT_EXCEEDED",
                    f"{base}.items has {len(item_list)} entries; at most {MAX_ITEMS_PER_GROUP} fit in one group.",
                    f"{base}.items",
                    expected=f"<= {MAX_ITEMS_PER_GROUP}",
                    found=str(len(item_list)),
                )
            )
        for position, item in enumerate(item_list):
            check(f"{base}.items[{position}]", item, MAX_ITEM_CHARS)
    if total > MAX_TOTAL_ITEMS:
        issues.append(
            _issue(
                "CONTENT_LIMIT_EXCEEDED",
                f"The capability groups hold {total} items in total; at most {MAX_TOTAL_ITEMS} fit.",
                "technical_capabilities.groups",
                expected=f"<= {MAX_TOTAL_ITEMS}",
                found=str(total),
            )
        )

    organizations = region("professional_context").get("organizations")
    org_list = organizations if isinstance(organizations, list) else []
    if len(org_list) > MAX_ORGANIZATIONS:
        issues.append(
            _issue(
                "CONTENT_LIMIT_EXCEEDED",
                f"professional_context.organizations has {len(org_list)} entries; at most {MAX_ORGANIZATIONS} fit.",
                "professional_context.organizations",
                expected=f"<= {MAX_ORGANIZATIONS}",
                found=str(len(org_list)),
            )
        )
    for index, organization in enumerate(org_list):
        check(f"professional_context.organizations[{index}]", organization, MAX_ORGANIZATION_CHARS)

    destinations = region("connect").get("destinations")
    destination_list = destinations if isinstance(destinations, list) else []
    if len(destination_list) > MAX_DESTINATIONS:
        issues.append(
            _issue(
                "CONTENT_LIMIT_EXCEEDED",
                f"connect.destinations has {len(destination_list)} links; at most {MAX_DESTINATIONS} fit.",
                "connect.destinations",
                expected=f"<= {MAX_DESTINATIONS}",
                found=str(len(destination_list)),
            )
        )
    for index, destination in enumerate(destination_list):
        if isinstance(destination, Mapping):
            check(f"connect.destinations[{index}].label", destination.get("label"), MAX_LABEL_CHARS)
            check(f"connect.destinations[{index}].url", destination.get("url"), MAX_URL_CHARS)
    return issues
