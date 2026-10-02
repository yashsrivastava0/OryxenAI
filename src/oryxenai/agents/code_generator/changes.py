"""Typed content edits: what a chat request is allowed to change, and how it is applied.

The interpreter proposes small operations on the site's ``page_content``; the host
applies them to a copy through a whitelist of paths and types, then re-checks the
result with the same admission rules a first build uses. Nothing here touches the
page markup: a change is always "new content -> normal pipeline".

Path grammar: ``section.field`` with optional list indexes, e.g.
``systems_practice.pillars[2].title`` or ``technical_capabilities.groups[0].items``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import ValidationError

from oryxenai.agents.code_generator.admission import content_admission_issues
from oryxenai.agents.code_generator.schemas import ChangeIntent, ChangeOperation, ChangePlanEnvelope
from oryxenai.agents.content_architect.schemas import PortfolioPageContent

_STEP = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)((?:\[\d+\])*)$")

_OPTIONAL_TEXT = ("eyebrow", "heading", "intro")
_SECTIONS = ("systems_practice", "technical_capabilities", "professional_context", "connect")

# normalized path (indexes -> "[]") -> kind
_TEXT_PATHS: frozenset[str] = frozenset(
    {
        *(
            f"hero.{name}"
            for name in (
                "name",
                "eyebrow_primary",
                "eyebrow_secondary",
                "headline_prefix",
                "headline_emphasis",
                "intro",
                "location",
                "primary_cta_label",
                "secondary_cta_label",
            )
        ),
        "metadata.title",
        "metadata.description",
        *(f"{section}.{field}" for section in _SECTIONS for field in _OPTIONAL_TEXT),
        "systems_practice.pillars[].title",
        "systems_practice.pillars[].description",
        "technical_capabilities.groups[].heading",
        "marquee_keywords[]",
        "technical_capabilities.groups[].items[]",
        "professional_context.organizations[]",
        "connect.destinations[].label",
        "connect.destinations[].url",
    }
)
_STRING_LISTS: frozenset[str] = frozenset(
    {
        "marquee_keywords",
        "technical_capabilities.groups[].items",
        "professional_context.organizations",
    }
)
_BOOL_PATHS: frozenset[str] = frozenset({"connect.destinations[].featured"})
_OBJECT_LISTS: frozenset[str] = frozenset({"technical_capabilities.groups", "connect.destinations"})
_APPENDABLE: frozenset[str] = _STRING_LISTS | _OBJECT_LISTS
_REMOVABLE: frozenset[str] = frozenset(
    {
        "marquee_keywords[]",
        "technical_capabilities.groups[]",
        "technical_capabilities.groups[].items[]",
        "professional_context.organizations[]",
        "connect.destinations[]",
    }
)

EDITABLE_PATHS_HELP = (
    "hero.{name,eyebrow_primary,eyebrow_secondary,headline_prefix,headline_emphasis,intro,"
    "location,primary_cta_label,secondary_cta_label}; metadata.{title,description}; "
    "marquee_keywords (set list | append str | remove [i]); "
    "{systems_practice,technical_capabilities,professional_context,connect}.{eyebrow,heading,intro}; "
    "systems_practice.pillars[i].{title,description} (exactly four pillars: edit, never add or remove); "
    "technical_capabilities.groups (append {heading,items} | remove [i]), "
    "technical_capabilities.groups[i].heading, groups[i].items (set list | append str | remove [j]); "
    "professional_context.organizations (set list | append str | remove [i]); "
    "connect.destinations (append {label,url,featured} | remove [i]), "
    "connect.destinations[i].{label,url,featured}"
)


class ChangeError(Exception):
    """A proposed edit cannot be applied; ``message`` says exactly which and why."""

    def __init__(self, message: str, *, path: str = "") -> None:
        self.message = message
        self.path = path
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class _Step:
    key: str
    indexes: tuple[int, ...]


def _parse(path: str) -> tuple[list[_Step], str]:
    """Split a path into steps and its normalized form (indexes replaced by ``[]``)."""
    steps: list[_Step] = []
    normalized: list[str] = []
    if not isinstance(path, str) or not path.strip() or len(path) > 160:
        raise ChangeError("An edit has an empty or oversized path.", path=str(path)[:80])
    for raw in path.strip().split("."):
        match = _STEP.match(raw)
        if match is None:
            raise ChangeError(f"'{path}' is not a valid content path.", path=path)
        indexes = tuple(int(item) for item in re.findall(r"\[(\d+)\]", match.group(2)))
        steps.append(_Step(match.group(1), indexes))
        normalized.append(match.group(1) + "[]" * len(indexes))
    return steps, ".".join(normalized)


def _child(container: Any, key: str, path: str) -> Any:
    if not isinstance(container, dict) or key not in container:
        raise ChangeError(f"'{path}' does not exist on this page.", path=path)
    return container[key]


def _index(items: Any, position: int, path: str) -> Any:
    if not isinstance(items, list) or position >= len(items):
        count = len(items) if isinstance(items, list) else 0
        raise ChangeError(
            f"'{path}' points past the end of the list ({count} item{'s' if count != 1 else ''}).",
            path=path,
        )
    return items[position]


def _walk(
    root: Any, steps: Sequence[_Step], path: str, *, stop_before_last: bool
) -> tuple[Any, Any]:
    """Resolve to the parent container and the final key (str or int)."""
    node = root
    flat: list[str | int] = []
    for step in steps:
        flat.append(step.key)
        flat.extend(step.indexes)
    for position, part in enumerate(flat):
        last = position == len(flat) - 1
        if last and stop_before_last:
            return node, part
        node = _child(node, part, path) if isinstance(part, str) else _index(node, part, path)
    return node, None


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise ChangeError(f"'{path}' needs text.", path=path)
    return value.strip()


def _string_list(value: Any, path: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ChangeError(f"'{path}' needs a list of text values.", path=path)
    return [item.strip() for item in value]


def _object(value: Any, normalized: str, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ChangeError(f"Adding to '{path}' needs an object.", path=path)
    if normalized == "technical_capabilities.groups":
        heading = _text(value.get("heading"), f"{path}.heading")
        return {"heading": heading, "items": _string_list(value.get("items", []), f"{path}.items")}
    label = _text(value.get("label"), f"{path}.label")
    url = _text(value.get("url"), f"{path}.url")
    featured = value.get("featured", False)
    if not isinstance(featured, bool):
        raise ChangeError(f"'{path}.featured' must be true or false.", path=path)
    return {"label": label, "url": url, "featured": featured}


def apply_operation(content: dict[str, Any], operation: ChangeOperation) -> None:
    """Apply one edit in place; raise :class:`ChangeError` if it is not allowed."""
    steps, normalized = _parse(operation.path)
    path = operation.path.strip()
    verb = operation.op
    if verb == "set":
        if normalized in _TEXT_PATHS:
            parent, key = _walk(content, steps, path, stop_before_last=True)
            _child_exists(parent, key, path)
            parent[key] = _text(operation.value, path)
        elif normalized in _STRING_LISTS:
            parent, key = _walk(content, steps, path, stop_before_last=True)
            _child_exists(parent, key, path)
            parent[key] = _string_list(operation.value, path)
        elif normalized in _BOOL_PATHS:
            if not isinstance(operation.value, bool):
                raise ChangeError(f"'{path}' must be true or false.", path=path)
            parent, key = _walk(content, steps, path, stop_before_last=True)
            _child_exists(parent, key, path)
            parent[key] = operation.value
        else:
            raise ChangeError(f"'{path}' cannot be changed from chat.", path=path)
    elif verb == "append":
        if normalized not in _APPENDABLE:
            raise ChangeError(f"Nothing can be added to '{path}'.", path=path)
        target, _ = _walk(content, steps, path, stop_before_last=False)
        if not isinstance(target, list):
            raise ChangeError(f"'{path}' is not a list.", path=path)
        if normalized in _STRING_LISTS:
            target.append(_text(operation.value, path))
        else:
            target.append(_object(operation.value, normalized, path))
    elif verb == "remove":
        if normalized not in _REMOVABLE:
            raise ChangeError(f"'{path}' cannot be removed from chat.", path=path)
        parent, key = _walk(content, steps, path, stop_before_last=True)
        if not isinstance(parent, list) or not isinstance(key, int) or key >= len(parent):
            raise ChangeError(f"'{path}' points past the end of the list.", path=path)
        del parent[key]
    else:  # pragma: no cover - the schema only allows the three verbs
        raise ChangeError(f"Unknown edit '{verb}'.", path=path)


def _child_exists(parent: Any, key: Any, path: str) -> None:
    if isinstance(key, int):
        _index(parent, key, path)
    elif not isinstance(parent, dict) or key not in parent:
        raise ChangeError(f"'{path}' does not exist on this page.", path=path)


def apply_operations(
    content: Mapping[str, Any], operations: Iterable[ChangeOperation]
) -> dict[str, Any]:
    """Apply every edit to a deep copy of ``content`` (all-or-nothing)."""
    updated: dict[str, Any] = copy.deepcopy(dict(content))
    for operation in operations:
        apply_operation(updated, operation)
    return updated


def leaf_strings(value: Any) -> set[str]:
    """Every non-trivial string in a content tree."""
    found: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, str):
            if len(node.strip()) >= 3:
                found.add(node.strip())
        elif isinstance(node, Mapping):
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return found


def leaf_paths(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    """(path, text) for every string in a content tree, in document order."""
    found: list[tuple[str, str]] = []
    if isinstance(value, str):
        found.append((prefix, value))
    elif isinstance(value, Mapping):
        for key, child in value.items():
            found.extend(leaf_paths(child, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, list):
        for position, child in enumerate(value):
            found.extend(leaf_paths(child, f"{prefix}[{position}]"))
    return found


def remaining_mentions(content: Mapping[str, Any], removed: Iterable[str]) -> list[tuple[str, str]]:
    """Where text the person asked to hide still appears inside other fields."""
    needles = sorted({item for item in removed if len(item) >= 4}, key=len, reverse=True)
    hits: list[tuple[str, str]] = []
    for path, text in leaf_paths(dict(content)):
        lowered = text.lower()
        for needle in needles:
            if needle.lower() in lowered:
                hits.append((path, needle))
                break
    return hits


def removed_strings(before: Mapping[str, Any], after: Mapping[str, Any]) -> set[str]:
    """Text that was on the page before and is gone now (for privacy restriction)."""
    return leaf_strings(before) - leaf_strings(after)


def content_sha256(page_content: Mapping[str, Any]) -> str:
    """Stable fingerprint of a content tree (pins what a version was built from)."""
    material = json.dumps(
        dict(page_content), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


# ── deciding what a chat message does ─────────────────────────────────────────

_MAX_REPLY_CHARS = 600


def clean_reply(text: str, fallback: str = "") -> str:
    """Model-written chat text: single paragraph, no control characters, bounded."""
    cleaned = "".join(ch if ch.isprintable() or ch in "\n\t" else " " for ch in str(text or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return fallback
    return (
        cleaned if len(cleaned) <= _MAX_REPLY_CHARS else cleaned[: _MAX_REPLY_CHARS - 1] + "\u2026"
    )


@dataclass(frozen=True, slots=True)
class ChangeDecision:
    """``reply``: answer in chat, build nothing. ``build``: regenerate from ``new_content``."""

    kind: Literal["reply", "build"]
    reply: str
    new_content: dict[str, Any] | None = None
    removed: frozenset[str] = frozenset()


def decide_change(base_content: Mapping[str, Any], plan: ChangePlanEnvelope) -> ChangeDecision:
    """Turn the interpreter's plan into a build, or into the reply the person should read."""
    reply = clean_reply(plan.reply)
    if plan.intent is ChangeIntent.NEEDS_CLARIFICATION:
        question = clean_reply(plan.clarification, reply)
        return ChangeDecision(
            "reply", question or "Could you say a little more about what you would like changed?"
        )
    if plan.intent is ChangeIntent.STYLE_REQUEST:
        return ChangeDecision(
            "reply",
            reply
            or "Styling and layout cannot be changed from chat yet. I can change the wording and content of your page.",
        )
    if plan.intent is ChangeIntent.UNSUPPORTED:
        return ChangeDecision(
            "reply", reply or "That is outside what I can change on this page from chat."
        )
    if plan.intent is ChangeIntent.CHAT_ONLY:
        return ChangeDecision(
            "reply",
            reply
            or "I can change the wording and content of your page. What would you like to change?",
        )
    if not plan.ops:
        return ChangeDecision(
            "reply", reply or "I could not find anything to change in that request."
        )

    try:
        updated = apply_operations(base_content, plan.ops)
        shaped = PortfolioPageContent.model_validate(updated).model_dump(mode="json")
    except ChangeError as exc:
        return ChangeDecision("reply", f"I could not make that change: {exc.message}")
    except ValidationError:
        return ChangeDecision(
            "reply", "I could not make that change because it would break the page structure."
        )
    issues = content_admission_issues(shaped)
    if issues:
        return ChangeDecision("reply", f"I could not make that change: {issues[0].message}")
    if shaped == PortfolioPageContent.model_validate(dict(base_content)).model_dump(mode="json"):
        return ChangeDecision("reply", "That is already how the page reads, so nothing changed.")
    removed = removed_strings(base_content, shaped) if plan.privacy_sensitive else set()
    message = reply or "I updated your page."
    leftovers = remaining_mentions(shaped, removed)
    if leftovers:
        places = ", ".join(sorted({path for path, _ in leftovers})[:3])
        message = clean_reply(
            f"{message} Note: that detail still appears in {places}. Tell me how to reword it and I will remove it there too."
        )
    return ChangeDecision(
        "build",
        message,
        new_content=shaped,
        removed=frozenset(removed),
    )
