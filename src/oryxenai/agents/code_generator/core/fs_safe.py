"""Windows-tolerant filesystem primitives for the Code Generator.

Every directory swap, tree deletion, and atomic file write in the generation,
checkpoint, build, and preview paths routes through this module so transient
OS-level handle locks (antivirus real-time scans, search indexing, orphaned
node processes on Windows) degrade into bounded retries instead of failing a
durable run mid-flight.
"""

from __future__ import annotations

import contextlib
import os
import random
import shutil
import stat
import sys
import time
from pathlib import Path
from typing import Any

# Total worst-case wait is ~10s per operation: enough for antivirus/indexer
# scan windows on freshly written trees while staying inside job time budgets.
_RETRY_DELAYS_SECONDS = (0.3, 0.6, 1.0, 1.5, 2.5, 4.0)

# Subtrees that never carry irreplaceable state; locked entries inside them
# are cleared best-effort before a strict removal of the parent.
_DISPOSABLE_NAMES = {"node_modules", "dist"}


class FsSafeError(OSError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _sleep_before_retry(attempt: int) -> None:
    delay = _RETRY_DELAYS_SECONDS[min(attempt, len(_RETRY_DELAYS_SECONDS) - 1)]
    # Uniform jitter only de-synchronizes retries; it is not used for
    # anything cryptographic.
    time.sleep(delay + random.uniform(0.0, 0.2))  # noqa: S311


def _extended(path: Path) -> Path:
    """Use the Windows extended-length prefix so deep trees (node_modules)
    cannot exceed MAX_PATH during removal."""

    if sys.platform != "win32":
        return path
    resolved = str(path.resolve())
    if resolved.startswith("\\\\?\\"):
        return Path(resolved)
    return Path(f"\\\\?\\{resolved}")


def _on_remove_error(function: Any, target: str, excinfo: BaseException) -> None:
    # Read-only files (npm/git artifacts) block rmtree on Windows; make them
    # writable and retry the single failed operation. Any failure here raises
    # its own OSError, which the outer retry loop handles.
    os.chmod(target, stat.S_IWRITE)
    function(target)


def _rmtree_retry(path: Path, *, required: bool) -> bool:
    if not path.exists() and not path.is_symlink():
        return True
    last_error: OSError | None = None
    for attempt in range(len(_RETRY_DELAYS_SECONDS) + 1):
        try:
            shutil.rmtree(_extended(path), onexc=_on_remove_error)
        except OSError as exc:
            last_error = exc
            if attempt < len(_RETRY_DELAYS_SECONDS):
                _sleep_before_retry(attempt)
                continue
        if not path.exists():
            return True
        if not required:
            return False
    raise FsSafeError(
        "FS_REMOVE_FAILED",
        f"The tree could not be removed after retries: {path} ({last_error})",
    )


def remove_tree(path: Path, *, required: bool = True) -> bool:
    """Remove a directory tree with bounded lock retries.

    Disposable subtrees (node_modules/dist) directly under `path` are cleared
    best-effort first so a locked build artifact never blocks removal of the
    source tree that contains it. Returns False when a best-effort removal
    left the tree in place; raises FsSafeError when `required` and it failed.
    """

    if not path.exists():
        return True
    for child in sorted(path.iterdir()):
        if child.name in _DISPOSABLE_NAMES and child.is_dir() and not child.is_symlink():
            _rmtree_retry(child, required=False)
    return _rmtree_retry(path, required=required)


def rename_dir_with_retry(source: Path, target: Path) -> None:
    """Rename `source` onto `target` (which must not exist), retrying through
    transient Windows handle locks on the freshly written source tree."""

    if target.exists():
        raise FsSafeError("FS_TARGET_EXISTS", f"The rename destination already exists: {target}")
    last_error: OSError | None = None
    for attempt in range(len(_RETRY_DELAYS_SECONDS) + 1):
        try:
            os.replace(source, target)
            return
        except PermissionError as exc:
            last_error = exc
            if attempt < len(_RETRY_DELAYS_SECONDS):
                _sleep_before_retry(attempt)
                continue
            break
        except OSError as exc:
            raise FsSafeError("FS_RENAME_FAILED", f"Directory rename failed: {exc}") from exc
    raise FsSafeError(
        "FS_RENAME_FAILED",
        f"Directory rename stayed locked after retries: {source} ({last_error})",
    )


def write_text_atomic(path: Path, text: str) -> None:
    """Write text through a partial file plus a retried atomic replace."""

    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial")
    partial.write_text(text, encoding="utf-8", newline="\n")
    error: OSError | None = None
    for attempt in range(len(_RETRY_DELAYS_SECONDS) + 1):
        try:
            os.replace(partial, path)
            return
        except PermissionError as exc:
            error = exc
            if attempt < len(_RETRY_DELAYS_SECONDS):
                _sleep_before_retry(attempt)
                continue
            break
    with contextlib.suppress(OSError):
        partial.unlink(missing_ok=True)
    raise FsSafeError("FS_WRITE_FAILED", f"Atomic write failed for: {path}") from error


def copy_file_with_retry(source: Path, target: Path) -> None:
    """Copy one file, retrying through transient locks on the source."""

    target.parent.mkdir(parents=True, exist_ok=True)
    error: OSError | None = None
    for attempt in range(len(_RETRY_DELAYS_SECONDS) + 1):
        try:
            shutil.copyfile(source, target)
            return
        except PermissionError as exc:
            error = exc
            if attempt < len(_RETRY_DELAYS_SECONDS):
                _sleep_before_retry(attempt)
                continue
            break
    raise FsSafeError("FS_COPY_FAILED", f"File copy stayed locked: {source}") from error
