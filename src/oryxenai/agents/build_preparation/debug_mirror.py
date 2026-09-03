"""Local debug mirror for Build Preparation's two Markdown briefs.

A courtesy copy for developer inspection -- never the source of truth (that
is the session's persisted state, or the fixture's returned payload). Writes
are best-effort with a bounded retry for the same transient Windows
file-lock behavior Code Generator's own fs_safe layer works around; a mirror
failure never fails the run.
"""

from __future__ import annotations

import random
import re
import time
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_INDIA_TIME = timezone(timedelta(hours=5, minutes=30), name="IST")
_FS_RETRY_DELAYS_SECONDS = (0.3, 0.6, 1.0, 1.5, 2.5, 4.0)


class DebugMirrorError(Exception):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


def _sleep_before_retry(attempt: int) -> None:
    delay = _FS_RETRY_DELAYS_SECONDS[min(attempt, len(_FS_RETRY_DELAYS_SECONDS) - 1)]
    time.sleep(delay + random.uniform(0.0, 0.2))  # noqa: S311


def _mkdir_with_retry(path: Path) -> None:
    last_error: OSError | None = None
    for attempt in range(len(_FS_RETRY_DELAYS_SECONDS) + 1):
        try:
            path.mkdir(parents=True, exist_ok=True)
            return
        except PermissionError as exc:
            last_error = exc
            if attempt < len(_FS_RETRY_DELAYS_SECONDS):
                _sleep_before_retry(attempt)
                continue
            break
    raise DebugMirrorError(
        f"Directory creation stayed locked after retries: {path}",
        details={"error": str(last_error)},
    )


def _write_text_with_retry(path: Path, text: str) -> None:
    last_error: OSError | None = None
    for attempt in range(len(_FS_RETRY_DELAYS_SECONDS) + 1):
        try:
            path.write_text(text, encoding="utf-8")
            return
        except PermissionError as exc:
            last_error = exc
            if attempt < len(_FS_RETRY_DELAYS_SECONDS):
                _sleep_before_retry(attempt)
                continue
            break
    raise DebugMirrorError(
        f"File write stayed locked after retries: {path}",
        details={"error": str(last_error)},
    )


def _safe_segment(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return cleaned[:100] or fallback


def resolve_debug_mirror_dir(output_dir: str, run_id: str) -> str:
    """Build a per-run, collision-free debug-mirror directory under a stable base."""
    timestamp = datetime.now(_INDIA_TIME).strftime("%H-%M-%d-%m")
    run_prefix = _safe_segment(run_id[:8] if run_id else "", "run")
    base = Path(output_dir) / "build-preparation" / f"{timestamp}-{run_prefix}"
    destination = base
    suffix = 0
    while destination.exists():
        suffix += 1
        destination = base.parent / f"{base.name}-{suffix}"
    return str(destination)


def write_debug_mirror(
    directory: str,
    *,
    content_brief_markdown: str,
    visual_brief_markdown: str,
) -> str:
    """Write both briefs directly into ``directory`` (created if needed).

    The caller is responsible for making ``directory`` collision-free across
    runs (see :func:`resolve_debug_mirror_dir`). Returns the folder's path
    relative to the working directory, or "" if the mirror could not be
    written -- a mirror failure is advisory only and never fails the run.
    """
    try:
        destination = Path(directory)
        _mkdir_with_retry(destination)
        _write_text_with_retry(
            destination / "content-and-narrative-brief.md", content_brief_markdown
        )
        _write_text_with_retry(destination / "visual-and-build-brief.md", visual_brief_markdown)
        _write_text_with_retry(
            destination / "generated-at.txt", datetime.now(UTC).isoformat() + "\n"
        )
        try:
            return str(destination.relative_to(Path.cwd())).replace("\\", "/")
        except ValueError:
            return str(destination)
    except DebugMirrorError:
        return ""
