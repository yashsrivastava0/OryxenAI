"""Materialize approved public copy as a typed, receipt-bound TS module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def compile_content_module(public_content: list[dict[str, Any]]) -> str:
    payload = json.dumps(public_content, ensure_ascii=False, sort_keys=True, indent=2)
    return (
        "/* Generated from approved public content. Do not retype copy in route components. */\n"
        "export type PublicContentPack = typeof PUBLIC_CONTENT[number];\n"
        f"export const PUBLIC_CONTENT = {payload} as const;\n\n"
        "export function contentForRoute(routeId: string): PublicContentPack | undefined {\n"
        "  return PUBLIC_CONTENT.find((item) => item.route_id === routeId);\n"
        "}\n"
    )


def write_content_module(repo_dir: Path, public_content: list[dict[str, Any]]) -> Path:
    target = repo_dir / "src" / "content" / "generated-content.ts"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(compile_content_module(public_content), encoding="utf-8")
    return target
