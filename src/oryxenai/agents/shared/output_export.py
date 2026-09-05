"""Best-effort local exports for completed first-four-agent runs."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from oryxenai.core.logging import get_logger

logger = get_logger("oryxenai.agents.shared.output_export")

_EXCLUDED_METADATA_KEYS = frozenset(
    {
        "cache_key",
        "input_fingerprint",
        "profile_fingerprint",
        "prompt_fingerprint",
    }
)


def export_agent_result(
    settings: Any,
    *,
    agent_key: str,
    run_id: UUID | str,
    output: Mapping[str, Any],
    model_metadata: Mapping[str, Any],
) -> str | None:
    """Atomically export a pure result and safe metadata under ``output``.

    Exports are deliberately best effort. A read-only or unavailable local
    output mount must never turn an already-committed portfolio run into a
    failed run. Raw prompts, resumes, cache keys, and database state are not
    copied into these files.
    """

    config = getattr(settings, "model_cache", None)
    if config is None or not bool(getattr(config, "export_enabled", True)):
        return None

    root = Path(str(getattr(config, "output_root", "output") or "output"))
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[4] / root
    slug = _safe_slug(agent_key)
    run_slug = _safe_slug(str(run_id))
    destination = root / slug / run_slug

    try:
        destination.mkdir(parents=True, exist_ok=True)
        _atomic_json(destination / "result.json", dict(output))
        _atomic_json(
            destination / "run-metadata.json",
            {
                "agent_key": agent_key,
                "run_id": str(run_id),
                "exported_at": datetime.now(UTC).isoformat(),
                "model_metadata": _safe_export_metadata(model_metadata),
            },
        )
        _export_markdown_files(destination, output)
    except OSError as exc:
        logger.warning(
            "local result export skipped agent=%s run=%s error=%s",
            slug,
            run_slug,
            type(exc).__name__,
        )
        return None
    return str(destination)


def _export_markdown_files(destination: Path, output: Mapping[str, Any]) -> None:
    for key in ("content_brief_markdown", "visual_brief_markdown"):
        value = output.get(key)
        if isinstance(value, str) and value:
            filename = f"{key.replace('_markdown', '')}.md"
            _atomic_text(destination / filename, value)


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    _atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


def _atomic_text(path: Path, value: str) -> None:
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        with suppress(OSError):
            os.unlink(temporary_name)
        raise


def _safe_export_metadata(value: Any) -> Any:
    """Keep useful receipts while excluding cache identity material."""

    if isinstance(value, Mapping):
        return {
            str(key): _safe_export_metadata(item)
            for key, item in value.items()
            if str(key).casefold() not in _EXCLUDED_METADATA_KEYS
        }
    if isinstance(value, list):
        return [_safe_export_metadata(item) for item in value]
    return value


def _safe_slug(value: str) -> str:
    allowed = {"-", "_", "."}
    result = "".join(char if char.isalnum() or char in allowed else "-" for char in value)
    return result.strip("-.") or "unknown"
