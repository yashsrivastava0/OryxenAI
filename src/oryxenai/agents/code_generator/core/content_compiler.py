"""Materialize approved public copy as a typed, receipt-bound TS module."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


def compile_content_index(
    public_content: list[dict[str, Any]],
    facts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Flatten approved leaf values into collision-safe, stable import keys."""

    entries: list[dict[str, Any]] = []
    for route in public_content:
        if not isinstance(route, dict):
            continue
        route_id = str(route.get("route_id", ""))
        for section in route.get("sections", []):
            if not isinstance(section, dict):
                continue
            section_id = str(section.get("section_id", ""))
            for path, value in _leaf_values(section.get("content", {})):
                entries.append(
                    {
                        "content_id": _content_id(route_id, section_id, path),
                        "route_id": route_id,
                        "section_id": section_id,
                        "path": path,
                        "value": value,
                    }
                )
    for fact in facts or []:
        if not isinstance(fact, dict):
            continue
        fact_id = str(fact.get("fact_id", ""))
        statement = fact.get("statement")
        if fact_id and isinstance(statement, str):
            entries.append(
                {
                    "content_id": f"fact:{fact_id}",
                    "route_id": "",
                    "section_id": "",
                    "path": "statement",
                    "value": statement,
                }
            )
    ids = [str(item["content_id"]) for item in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("approved content keys collided after normalization")
    return entries


def content_ids_by_section(
    public_content: list[dict[str, Any]], facts: list[dict[str, Any]] | None = None
) -> dict[tuple[str, str], list[str]]:
    grouped: dict[tuple[str, str], list[str]] = {}
    for item in compile_content_index(public_content, facts):
        route_id = str(item.get("route_id", ""))
        section_id = str(item.get("section_id", ""))
        if route_id and section_id:
            grouped.setdefault((route_id, section_id), []).append(str(item["content_id"]))
    return grouped


def compile_content_module(
    public_content: list[dict[str, Any]], facts: list[dict[str, Any]] | None = None
) -> str:
    payload = json.dumps(public_content, ensure_ascii=False, sort_keys=True, indent=2)
    index = json.dumps(
        compile_content_index(public_content, facts), ensure_ascii=False, sort_keys=True, indent=2
    )
    return (
        "/* Generated from approved public content. Do not retype copy in route components. */\n"
        "export type PublicContentPack = typeof PUBLIC_CONTENT[number];\n"
        f"export const PUBLIC_CONTENT = {payload} as const;\n\n"
        f"export const CONTENT_INDEX = {index} as const;\n\n"
        'export type ApprovedContentId = typeof CONTENT_INDEX[number]["content_id"];\n'
        "export function contentForRoute(routeId: string): PublicContentPack | undefined {\n"
        "  return PUBLIC_CONTENT.find((item) => item.route_id === routeId);\n"
        "}\n\n"
        "export function sectionForRoute(routeId: string, sectionId: string) {\n"
        "  return contentForRoute(routeId)?.sections.find((item) => item.section_id === sectionId);\n"
        "}\n\n"
        "export function contentValue(contentId: ApprovedContentId): string {\n"
        "  const entry = CONTENT_INDEX.find((item) => item.content_id === contentId);\n"
        '  if (!entry || typeof entry.value !== "string") throw new Error(`Unknown approved content key: ${contentId}`);\n'
        "  return entry.value;\n"
        "}\n"
    )


def write_content_module(
    repo_dir: Path,
    public_content: list[dict[str, Any]],
    facts: list[dict[str, Any]] | None = None,
) -> Path:
    target = repo_dir / "src" / "content" / "generated-content.ts"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(compile_content_module(public_content, facts), encoding="utf-8")
    return target


def _leaf_values(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(prefix or "value", value)]
    if isinstance(value, dict):
        result: list[tuple[str, str]] = []
        for key in sorted(value):
            child = f"{prefix}.{key}" if prefix else str(key)
            result.extend(_leaf_values(value[key], child))
        return result
    if isinstance(value, list):
        result = []
        for index, item in enumerate(value):
            child = f"{prefix}.{index}" if prefix else str(index)
            result.extend(_leaf_values(item, child))
        return result
    return []


def _content_id(route_id: str, section_id: str, path: str) -> str:
    normalized = unicodedata.normalize("NFKC", path).casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "value"
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:8]
    return f"content:{route_id}:{section_id}:{slug}-{digest}"


__all__ = [
    "compile_content_index",
    "compile_content_module",
    "content_ids_by_section",
    "write_content_module",
]
