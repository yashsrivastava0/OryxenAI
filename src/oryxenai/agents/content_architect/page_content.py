"""Deterministic rules for the single-page content tree.

Pure functions over plain dicts so the agent's readiness gate, the output
validator, the approval state machine, and the service all share one
definition of "a complete, safe page" without importing each other.
Everything here is defensive: model output arrives as unvalidated JSON.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ValidationError

from oryxenai.agents.content_architect.schemas import CoverageDisposition, PortfolioPageContent

PILLAR_COUNT = 4
_SAFE_URL_PREFIXES = ("https://", "http://", "mailto:")
_PUBLIC_DISPOSITIONS = {CoverageDisposition.USED.value, CoverageDisposition.CONDENSED.value}
_ALL_DISPOSITIONS = {item.value for item in CoverageDisposition}

# Internal review/QA annotation keys that must live in internal_notes, never
# inside visitor-facing page copy.
INTERNAL_NOTE_KEYS = frozenset(
    {
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
)

_CHUNK = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)?((?:\[\d+\])*)")
_MISSING = object()


# ── Field paths ─────────────────────────────────────────────────────────────


def parse_field_path(path: Any) -> list[str | int] | None:
    """Parse "a.b[0].c" (or "a.b.0.c") into segments; None when malformed."""
    if not isinstance(path, str) or not path.strip():
        return None
    parts: list[str | int] = []
    for chunk in path.strip().split("."):
        if chunk.isdigit():
            parts.append(int(chunk))
            continue
        match = _CHUNK.fullmatch(chunk)
        if not chunk or match is None:
            return None
        if match.group(1):
            parts.append(match.group(1))
        parts.extend(int(index) for index in re.findall(r"\[(\d+)\]", match.group(2)))
    return parts or None


def resolve_field_path(page: Any, path: Any) -> Any:
    """Return the value at `path` inside `page`, or the module sentinel when absent."""
    segments = parse_field_path(path)
    if segments is None:
        return _MISSING
    current = page
    for segment in segments:
        if isinstance(segment, int):
            if not isinstance(current, list) or segment >= len(current):
                return _MISSING
            current = current[segment]
        else:
            if not isinstance(current, dict) or segment not in current:
                return _MISSING
            current = current[segment]
    return current


def path_is_populated(page: Any, path: Any) -> bool:
    value = resolve_field_path(page, path)
    return value is not _MISSING and _is_populated(value)


def _is_populated(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        return any(_is_populated(child) for child in value.values())
    if isinstance(value, list):
        return any(_is_populated(child) for child in value)
    return value is not None


# ── Shape (type safety on raw model JSON) ───────────────────────────────────

_REGION_KEYS = (
    "hero",
    "metadata",
    "systems_practice",
    "technical_capabilities",
    "professional_context",
    "connect",
)


def page_shape_errors(page: Any) -> list[str]:
    """Reject wrong JSON types and internal-review key leakage; not completeness."""
    if not isinstance(page, dict):
        return ["'page_content' must be an object"]
    errors: list[str] = []
    for key in _REGION_KEYS:
        value = page.get(key)
        if value is not None and not isinstance(value, dict):
            errors.append(f"page_content.{key} must be an object")
    if not _is_string_list(page.get("marquee_keywords")):
        errors.append("page_content.marquee_keywords must be a list of strings")

    systems = _region(page, "systems_practice")
    pillars = systems.get("pillars")
    if pillars is not None and not _is_object_list(pillars):
        errors.append("page_content.systems_practice.pillars must be a list of objects")

    capabilities = _region(page, "technical_capabilities")
    groups = capabilities.get("groups")
    if groups is not None and not _is_object_list(groups):
        errors.append("page_content.technical_capabilities.groups must be a list of objects")
    else:
        for index, group in enumerate(groups or []):
            if not _is_string_list(group.get("items")):
                errors.append(
                    f"page_content.technical_capabilities.groups[{index}].items "
                    "must be a list of strings"
                )

    context = _region(page, "professional_context")
    if not _is_string_list(context.get("organizations")):
        errors.append("page_content.professional_context.organizations must be a list of strings")

    destinations = _region(page, "connect").get("destinations")
    if destinations is not None and not _is_object_list(destinations):
        errors.append("page_content.connect.destinations must be a list of objects")

    leaked = find_internal_note_keys(page)
    if leaked:
        errors.append(
            f"page_content contains internal-review key(s) {sorted(leaked)} — "
            "move these into internal_notes instead"
        )
    return errors


def model_errors(label: str, model: type[BaseModel], value: Any) -> list[str]:
    """Report Pydantic type errors for `value` against `model`, bounded and readable."""
    try:
        model.model_validate(value)
    except ValidationError as exc:
        return [
            f"{label}.{'.'.join(str(part) for part in item['loc'])}: {item['msg']}".replace(
                f"{label}.:", f"{label}:"
            )
            for item in exc.errors()[:5]
        ]
    return []


def page_model_errors(page: Any) -> list[str]:
    return model_errors("page_content", PortfolioPageContent, page)


def find_internal_note_keys(content: Any, *, depth: int = 0) -> set[str]:
    """Recursively (bounded depth) find internal-review key names inside content."""
    found: set[str] = set()
    if depth > 6:
        return found
    if isinstance(content, dict):
        for key, value in content.items():
            if key in INTERNAL_NOTE_KEYS:
                found.add(key)
            found |= find_internal_note_keys(value, depth=depth + 1)
    elif isinstance(content, list):
        for item in content:
            found |= find_internal_note_keys(item, depth=depth + 1)
    return found


# ── Completeness (what the pinned template needs to render) ─────────────────


def page_completeness_errors(page: Any) -> list[str]:
    """Return what is missing for the pinned template to render without gaps.

    Organizations, destinations, and marquee keywords may legitimately be empty
    (a profile can name no employer or public link); an invented entry would be
    worse than an empty list, so only structural slots are required here.
    """
    if not isinstance(page, dict):
        return ["page_content is missing"]
    errors: list[str] = []

    hero = _region(page, "hero")
    if not _text(hero.get("name")):
        errors.append("hero.name is required")
    if not (_text(hero.get("headline_prefix")) or _text(hero.get("headline_emphasis"))):
        errors.append("hero needs headline_prefix and/or headline_emphasis")
    if not _text(hero.get("intro")):
        errors.append("hero.intro is required")

    metadata = _region(page, "metadata")
    for key in ("title", "description"):
        if not _text(metadata.get(key)):
            errors.append(f"metadata.{key} is required")

    errors.extend(_section_errors(page, "systems_practice"))
    pillars = list(_as_list(_region(page, "systems_practice").get("pillars")))
    if len(pillars) != PILLAR_COUNT:
        errors.append(
            f"systems_practice.pillars must have exactly {PILLAR_COUNT} entries; found {len(pillars)}"
        )
    for index, pillar in enumerate(pillars):
        if not isinstance(pillar, dict) or not _text(pillar.get("title")):
            errors.append(f"systems_practice.pillars[{index}].title is required")
        if not isinstance(pillar, dict) or not _text(pillar.get("description")):
            errors.append(f"systems_practice.pillars[{index}].description is required")

    errors.extend(_section_errors(page, "technical_capabilities"))
    groups = _as_list(_region(page, "technical_capabilities").get("groups"))
    if not groups:
        errors.append("technical_capabilities.groups needs at least one group")
    for index, group in enumerate(groups):
        if not isinstance(group, dict) or not _text(group.get("heading")):
            errors.append(f"technical_capabilities.groups[{index}].heading is required")
        elif not [i for i in _as_list(group.get("items")) if _text(i)]:
            errors.append(f"technical_capabilities.groups[{index}].items needs at least one item")

    errors.extend(_section_errors(page, "professional_context"))

    errors.extend(_section_errors(page, "connect"))
    destinations = _as_list(_region(page, "connect").get("destinations"))
    for index, destination in enumerate(destinations):
        if not isinstance(destination, dict) or not _text(destination.get("label")):
            errors.append(f"connect.destinations[{index}].label is required")
            continue
        url = _text(destination.get("url"))
        if not url.lower().startswith(_SAFE_URL_PREFIXES):
            errors.append(f"connect.destinations[{index}].url must be an http(s) or mailto link")
    return errors


def atlas_page_errors(page: Any, *, allow_illustrative_work: bool) -> list[str]:
    """Additional content rules for the optional Cobalt Atlas v2 pages."""
    if not isinstance(page, dict) or not isinstance(page.get("atlas"), dict):
        return ["page_content.atlas is required for Cobalt Atlas v2"]
    atlas = page["atlas"]
    errors: list[str] = []
    for field in ("about_heading", "about_intro"):
        if not _text(atlas.get(field)):
            errors.append(f"atlas.{field} is required")
    for field in ("experience", "education", "statistics", "projects"):
        if not isinstance(atlas.get(field), list):
            errors.append(f"atlas.{field} must be a list")
    for field, maximum in (("about_heading", 160), ("about_intro", 1400), ("about_quote", 500)):
        if len(_text(atlas.get(field))) > maximum:
            errors.append(f"atlas.{field} exceeds {maximum} characters")
    for field, maximum in (("experience", 12), ("education", 8), ("statistics", 4)):
        rows = atlas.get(field)
        if isinstance(rows, list):
            if len(rows) > maximum:
                errors.append(f"atlas.{field} has at most {maximum} entries")
            for index, row in enumerate(rows):
                if isinstance(row, dict):
                    for key, value in row.items():
                        if isinstance(value, str) and len(value.strip()) > 900:
                            errors.append(f"atlas.{field}[{index}].{key} exceeds 900 characters")
    projects = atlas.get("projects") if isinstance(atlas.get("projects"), list) else []
    if len(projects) > 3:
        errors.append("atlas.projects has at most three featured entries")
    illustrative = 0
    real = 0
    for index, project in enumerate(projects):
        if not isinstance(project, dict):
            errors.append(f"atlas.projects[{index}] must be an object")
            continue
        kind = project.get("kind", "real")
        if kind == "real":
            real += 1
        elif kind == "illustrative":
            illustrative += 1
            if _text(project.get("outcome")):
                errors.append(f"atlas.projects[{index}].outcome must be empty for illustration")
        else:
            errors.append(f"atlas.projects[{index}].kind is invalid")
        if not _text(project.get("title")) or not _text(project.get("summary")):
            errors.append(f"atlas.projects[{index}] needs title and summary")
        for field, maximum in (
            ("title", 160),
            ("summary", 600),
            ("problem", 1400),
            ("approach", 1400),
            ("outcome", 700),
        ):
            if len(_text(project.get(field))) > maximum:
                errors.append(f"atlas.projects[{index}].{field} exceeds {maximum} characters")
        url = _text(project.get("external_url"))
        if url and not url.lower().startswith(("https://", "http://")):
            errors.append(f"atlas.projects[{index}].external_url must be http(s)")
    if illustrative and (not allow_illustrative_work or real or illustrative > 1):
        errors.append("atlas illustrative work needs explicit opt-in and no real project")
    return errors


def _section_errors(page: dict[str, Any], key: str) -> list[str]:
    region = _region(page, key)
    return [
        f"{key}.{field} is required"
        for field in ("eyebrow", "heading")
        if not _text(region.get(field))
    ]


# ── Claim and coverage binding ──────────────────────────────────────────────


def claim_binding_errors(page: Any, claims: list[dict[str, Any]]) -> list[str]:
    """Non-approved claims must not reach public copy; approved ones must resolve."""
    errors: list[str] = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim.get("claim_id", "") or "")
        paths = claim.get("field_paths") or []
        if not isinstance(paths, list):
            errors.append(f"Claim {claim_id!r} field_paths must be a list")
            continue
        status = claim.get("publication_status", "pending")
        if status != "approved":
            if paths:
                errors.append(
                    f"Claim {claim_id!r} is {status!r} but is bound to public field(s) "
                    f"{[str(p) for p in paths[:3]]}; omit or neutralize that copy"
                )
            continue
        for path in paths:
            if not path_is_populated(page, path):
                errors.append(f"Claim {claim_id!r} field_path {path!r} has no populated copy")
    return errors


def coverage_errors(dossier: dict[str, Any], ledger: list[Any], page: Any) -> list[str]:
    """Require a disposition for every fact/entity in a new Discovery dossier."""
    if dossier.get("contract_version") != "DiscoveryDossier/v1":
        return []  # Existing approved sessions may predate dossier production.
    expected = {
        f"{kind}/{item['id']}"
        for field, kind in (
            ("facts", "fact"),
            ("roles", "role"),
            ("projects", "project"),
            ("other_evidence", "evidence"),
        )
        for item in dossier.get(field, [])
        if isinstance(item, dict) and item.get("id")
    }
    errors: list[str] = []
    seen: set[str] = set()
    for index, entry in enumerate(ledger):
        if not isinstance(entry, dict):
            errors.append(f"Coverage ledger entry {index} is not an object")
            continue
        source_id = str(entry.get("source_id", "") or "")
        disposition = entry.get("disposition")
        paths = entry.get("field_paths", [])
        if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
            errors.append(f"Coverage ledger {source_id!r} has invalid field_paths")
            paths = []
        if source_id not in expected:
            errors.append(f"Coverage ledger has unknown source_id {source_id!r}")
        if source_id in seen:
            errors.append(f"Coverage ledger repeats source_id {source_id!r}")
        seen.add(source_id)
        if disposition not in _ALL_DISPOSITIONS:
            errors.append(f"Coverage ledger {source_id!r} has invalid disposition")
        elif disposition in _PUBLIC_DISPOSITIONS:
            if not paths or any(not path_is_populated(page, path) for path in paths):
                errors.append(
                    f"Coverage ledger {source_id!r} needs field_paths with populated copy"
                )
        elif paths or not str(entry.get("reason", "") or "").strip():
            errors.append(f"Coverage ledger {source_id!r} needs a reason and no field_paths")
    missing = sorted(expected - seen)
    if missing:
        errors.append(f"Coverage ledger is missing dossier items: {', '.join(missing[:10])}")
    return errors


# ── Small helpers ───────────────────────────────────────────────────────────


def _region(page: dict[str, Any], key: str) -> dict[str, Any]:
    value = page.get(key)
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _is_string_list(value: Any) -> bool:
    return value is None or (isinstance(value, list) and all(isinstance(v, str) for v in value))


def _is_object_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, dict) for v in value)
