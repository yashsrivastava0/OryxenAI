"""Post-promotion export of the complete generated portfolio.

After a run reaches READY, the full portfolio is copied to the configured
export root as both the source project (without disposables) and the built
static site, plus a metadata manifest. Export is advisory: a failure here is
logged as an event and never fails a promoted run.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import UTC, datetime, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from oryxenai.agents.code_generator.core import fs_safe
from oryxenai.agents.code_generator.core.workspace import repository_root

DEFAULT_EXPORT_ROOT = "output/code-gen-output"
DEFAULT_EXPORT_TIMEZONE = "Asia/Kolkata"

_DOCKER_ARTIFACT_NAMES = {
    "dockerfile",
    ".dockerignore",
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
}
_DISPOSABLE_SOURCE_NAMES = {"node_modules", "dist", ".workspace", ".git"}


def _is_docker_artifact(name: str) -> bool:
    lowered = name.casefold()
    return lowered in _DOCKER_ARTIFACT_NAMES or lowered.startswith("dockerfile.")


def _export_ignore(root: Path, excluded: list[str]) -> Callable[[str, list[str]], set[str]]:
    def ignore(path: str, names: list[str]) -> set[str]:
        current = Path(path)
        ignored: set[str] = set()
        for name in names:
            if name in _DISPOSABLE_SOURCE_NAMES or _is_docker_artifact(name):
                ignored.add(name)
                relative = (current / name).relative_to(root).as_posix()
                excluded.append(relative)
        return ignored

    return ignore


def _export_timestamp(config: Any) -> tuple[datetime, str]:
    timezone_name = str(getattr(config, "export_timezone", DEFAULT_EXPORT_TIMEZONE) or "")
    timezone: tzinfo
    try:
        timezone = ZoneInfo(timezone_name or DEFAULT_EXPORT_TIMEZONE)
    except Exception:
        # Windows development images may not ship the optional tzdata package.
        # Use the machine's configured local timezone rather than failing an
        # otherwise advisory export.
        timezone = datetime.now().astimezone().tzinfo or UTC
        timezone_name = "system-local"
    return datetime.now(timezone), timezone_name


def export_portfolio(
    *,
    settings: Any,
    run_id: str,
    repo_dir: Path,
    metadata: dict[str, Any],
) -> Path:
    config = settings.code_generator_verification
    root = Path(str(getattr(config, "export_root", DEFAULT_EXPORT_ROOT)))
    if not root.is_absolute():
        root = repository_root() / root
    exported_at, timezone_name = _export_timestamp(config)
    short_id = run_id.replace("-", "")[:8] or "run"
    folder_name = f"{exported_at:%H-%M-%d-%m-%Y}-{short_id}"
    target = root / folder_name
    # UUID prefixes are collision-safe for normal runs. If a caller reuses a
    # short synthetic ID, preserve the existing export instead of deleting it.
    if target.exists():
        existing_metadata = target / "portfolio.json"
        if existing_metadata.is_file():
            try:
                existing = json.loads(existing_metadata.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                existing = {}
            if str(existing.get("run_id", "")) != run_id:
                target = root / f"{folder_name}-{run_id[:12]}"
        if target.exists():
            fs_safe.remove_tree(target, required=False)

    excluded: list[str] = []
    shutil.copytree(
        repo_dir,
        target / "source",
        symlinks=False,
        ignore=_export_ignore(repo_dir, excluded),
    )
    dist_dir = repo_dir / "dist"
    if dist_dir.is_dir():
        shutil.copytree(
            dist_dir,
            target / "dist",
            symlinks=False,
            ignore=_export_ignore(dist_dir, excluded),
        )

    payload = {
        "schema_version": "oryxenai-portfolio-export-v1",
        "run_id": run_id,
        "exported_at": exported_at.astimezone(UTC).isoformat(),
        "export_timezone": timezone_name,
        "export_folder": target.name,
        **metadata,
        "runtime": {
            "kind": "static-vite",
            "docker": False,
            "preview": "shared-static-gateway",
            "entrypoint": "dist/index.html",
        },
        "excluded_source_artifacts": sorted(set(excluded)),
    }
    fs_safe.write_text_atomic(
        target / "portfolio.json",
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )
    return target


__all__ = ["DEFAULT_EXPORT_ROOT", "DEFAULT_EXPORT_TIMEZONE", "export_portfolio"]
