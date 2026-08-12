"""Trusted prompt assembly for Build Preparation's structured stages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

_PROMPT_FILES = {
    "compose_resource_queries": "compose_resource_queries.md",
    "select_resources": "select_resources.md",
    "write_build_context": "write_build_context.md",
    "integrate_cross_route": "integrate_cross_route.md",
    "review_handoff_quality": "review_handoff_quality.md",
}

_PROMPT_VERSIONS = {
    "compose_resource_queries": "build_preparation.compose_resource_queries.v1",
    "select_resources": "build_preparation.select_resources.v1",
    "write_build_context": "build_preparation.write_build_context.v1",
    "integrate_cross_route": "build_preparation.integrate_cross_route.v1",
    "review_handoff_quality": "build_preparation.review_handoff_quality.v1",
}


def _load(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


def _hash16(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def output_model_for(operation: str) -> type[Any]:
    from oryxenai.agents.build_preparation.schemas import (
        Stage1QueryPlan,
        Stage2SelectionPlan,
        Stage3BuildContextResult,
        Stage4IntegratedContextResult,
        Stage5HandoffReview,
    )

    models: dict[str, type[Any]] = {
        "compose_resource_queries": Stage1QueryPlan,
        "select_resources": Stage2SelectionPlan,
        "write_build_context": Stage3BuildContextResult,
        "integrate_cross_route": Stage4IntegratedContextResult,
        "review_handoff_quality": Stage5HandoffReview,
    }
    try:
        return models[operation]
    except KeyError as exc:
        raise ValueError(f"Unknown Build Preparation operation: {operation}") from exc


def build_instructions(
    operation: str, source_packet: dict[str, Any]
) -> tuple[str, str, str, dict[str, str]]:
    """Return trusted system text, task text, version, and prompt manifest."""
    if operation not in _PROMPT_FILES:
        raise ValueError(f"Unknown Build Preparation operation: {operation}")
    schema = output_model_for(operation).model_json_schema()
    schema_text = json.dumps(schema, ensure_ascii=False, indent=2)
    system = _load("system.md")
    operation_prompt = _load(_PROMPT_FILES[operation])
    serialized = json.dumps(source_packet, ensure_ascii=False, default=str)
    escaped = serialized.replace("]]", "]]>]]<![CDATA[")
    task = (
        f"{operation_prompt}\n\n"
        f"## Output JSON schema\n```json\n{schema_text}\n```\n\n"
        '<user_input trust="untrusted" encoding="json">\n'
        f"<![CDATA[\n{escaped}\n]]>\n"
        "</user_input>\n\n"
        "Return exactly one complete JSON object matching the schema."
    )
    manifest = {
        "system.md": _hash16(system),
        _PROMPT_FILES[operation]: _hash16(operation_prompt),
        "schema": _hash16(schema_text),
    }
    return system, task, _PROMPT_VERSIONS[operation], manifest
