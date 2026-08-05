"""Prompt builder for Discovery agent.

Loads static prompt files, serializes dynamic input safely, and returns
typed instructions and input payloads for model consumption.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PROMPT_DIR = Path(__file__).resolve().parent / "prompts"

PROMPT_VERSION_SYSTEM = "discovery.system.v1"
PROMPT_VERSION_PREPARE_QUESTIONS = "discovery.prepare_questions.v1"
PROMPT_VERSION_BUILD_BRIEF = "discovery.build_brief.v1"
PROMPT_VERSION_REPAIR = "discovery.repair.v1"

OPERATION_VERSION_MAP = {
    "prepare_questions": PROMPT_VERSION_PREPARE_QUESTIONS,
    "build_brief": PROMPT_VERSION_BUILD_BRIEF,
    "repair": PROMPT_VERSION_REPAIR,
}


def load_system_prompt() -> str:
    return _load_text("system.md")


def load_operation_prompt(operation: str) -> str:
    filename_map = {
        "prepare_questions": "prepare_questions.md",
        "build_brief": "build_brief.md",
        "repair": "repair_output.md",
    }
    filename = filename_map.get(operation)
    if filename is None:
        raise ValueError(f"Unknown Discovery operation: {operation}")
    return _load_text(filename)


def get_prompt_version(operation: str) -> str:
    return OPERATION_VERSION_MAP.get(operation, "discovery.unknown")


def build_instructions(
    operation: str,
    source_packet: dict[str, Any],
    config: dict[str, Any] | None = None,
    output_language: str = "en",
) -> tuple[str, str, str]:
    """Build instructions for a Discovery model call.

    Returns (system_prompt, task_prompt, prompt_version).
    Dynamic input is serialized as JSON within safe XML boundaries.
    """
    system = load_system_prompt()
    task = load_operation_prompt(operation)
    version = get_prompt_version(operation)

    serialized_input = _serialize_source_packet(source_packet, config, output_language)
    full_task = f"{task}\n\n{serialized_input}"

    return system, full_task, version


def build_repair_instructions(
    original_output: dict[str, Any],
    validation_errors: list[str],
    config: dict[str, Any] | None = None,
) -> tuple[str, str, str]:
    """Build repair instructions for a failed validation."""
    operation = "repair"
    system = load_system_prompt()
    task = load_operation_prompt(operation)
    version = get_prompt_version(operation)

    repair_input = {
        "original_output": original_output,
        "validation_errors": validation_errors,
    }
    serialized = _serialize_source_packet(repair_input, config)
    full_task = f"{task}\n\n{serialized}"

    return system, full_task, version


def _load_text(filename: str) -> str:
    path = _PROMPT_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def _serialize_source_packet(
    data: dict[str, Any],
    config: dict[str, Any] | None = None,
    output_language: str = "en",
) -> str:
    payload = {
        "data": data,
        "output_language": output_language,
    }
    if config:
        payload["constraints"] = config

    serialized = json.dumps(payload, ensure_ascii=False, default=str)
    escaped = serialized.replace("]]", "]]>]]<![CDATA[")
    return (
        f'<source_packet trust="untrusted" encoding="json">\n'
        f"<![CDATA[\n{escaped}\n]]>\n"
        f"</source_packet>"
    )
