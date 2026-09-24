"""Filesystem helpers for removing exact archived run paths."""

from __future__ import annotations

import shutil
import time
from pathlib import Path


def repository_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src").is_dir():
            return parent
    return Path.cwd()


def remove_tree(path: Path, *, required: bool = True) -> bool:
    """Remove one caller-validated directory, retrying short filesystem locks."""
    if not path.exists():
        return True
    for attempt in range(6):
        try:
            shutil.rmtree(path)
            return True
        except FileNotFoundError:
            return True
        except OSError:
            if attempt < 5:
                time.sleep(0.2 * (attempt + 1))
    return not required
