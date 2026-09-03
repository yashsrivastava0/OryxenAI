"""Trusted prompt assembly for Build Preparation's single structured stage."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from oryxenai.agents.build_preparation.schemas import VisualBriefOutput

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_PROMPT_VERSION = "build_preparation.compose_visual_brief.v1"


def _load(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


def _hash16(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def build_instructions(source_packet: dict[str, Any]) -> tuple[str, str, str, dict[str, str]]:
    """Return trusted system text, task text, version, and prompt manifest."""
    schema = VisualBriefOutput.model_json_schema()
    schema_text = json.dumps(schema, ensure_ascii=False, indent=2)
    system = _load("system.md")
    operation_prompt = _load("compose_visual_brief.md")
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
        "compose_visual_brief.md": _hash16(operation_prompt),
        "schema": _hash16(schema_text),
    }
    return system, task, _PROMPT_VERSION, manifest
