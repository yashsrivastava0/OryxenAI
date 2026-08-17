"""Receipt-bound prompt assembly for Code Generator source operations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from oryxenai.agents.code_generator.core.development_schemas import (
    GenerationContextReceipt,
    GenerationResult,
)
from oryxenai.agents.code_generator.core.generation_contract import (
    render_contract_instructions,
)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_VERSIONS = {
    "planner": "code_generator.planner.v6",
    "foundation": "code_generator.foundation.v5",
    "route_batch": "code_generator.route_batch.v5",
    "route_compose": "code_generator.route_compose.v4",
    "integrate": "code_generator.integrate.v5",
    "repair": "code_generator.repair.v5",
}
_FILES = {
    "planner": "planner.md",
    "foundation": "foundation.md",
    "route_batch": "route_batch.md",
    "route_compose": "route_compose.md",
    "integrate": "integrate.md",
    "repair": "repair_source.md",
}


def build_instructions(
    operation: str,
    context: dict[str, Any],
    *,
    output_model: type[BaseModel] = GenerationResult,
) -> tuple[str, str, GenerationContextReceipt]:
    if operation not in _FILES:
        raise ValueError(f"Unknown Code Generator operation: {operation}")
    system = _read("system.md")
    operation_prompt = _read(_FILES[operation])
    contract = context.get("generation_contract")
    contract_block = (
        render_contract_instructions(contract) if isinstance(contract, dict) and contract else ""
    )
    schema = json.dumps(output_model.model_json_schema(), ensure_ascii=False, sort_keys=True)
    serialized = json.dumps(context, ensure_ascii=False, sort_keys=True, default=str)
    task = (
        f"{operation_prompt}\n\n"
        + (f"{contract_block}\n\n" if contract_block else "")
        + "Return exactly one JSON object. The transport enforces the declared output schema; "
        "do not include prose, Markdown, or reasoning outside that object.\n"
        "Copy the input's context_receipt_hash value EXACTLY, unchanged, into "
        "based_on_context_receipt.\n"
        "Set mode to exactly one of changes/requests/cannot_complete; the two payload "
        "fields that do not match your mode MUST be null."
    )
    context_hash = _hash(context)
    schema_hash = hashlib.sha256(schema.encode("utf-8")).hexdigest()
    receipt = GenerationContextReceipt(
        receipt_id=f"context-{context_hash[:20]}",
        operation_id=operation,
        role_profile=str(context.get("role_profile", "")),
        prompt_versions={
            "system": "code_generator.system.v3",
            "operation": _VERSIONS[operation],
            "system_hash": _hash(system),
            # Hash the full composed instructions so a changed contract block
            # invalidates cached model calls, not just a changed prompt file.
            "operation_hash": _hash(task),
        },
        output_schema_hash=schema_hash,
        ordered_input_hashes=[str(value) for value in context.get("input_hashes", [])],
        owned_paths=[str(value) for value in context.get("owned_paths", [])],
        context_hash=context_hash,
        context_estimate=len(serialized),
        output_ceiling=int(context.get("output_ceiling", 0) or 0),
    )
    return system, task, receipt


def _read(name: str) -> str:
    path = _PROMPTS_DIR / name
    if not path.is_file():
        raise ValueError(f"Code Generator prompt is missing: {name}")
    return path.read_text(encoding="utf-8").strip()


def _hash(value: object) -> str:
    if isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


__all__ = ["build_instructions"]
