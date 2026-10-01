"""Versioned, immutable portfolio themes.

A theme package is a directory: the pre-built stylesheet, local assets, a
``manifest.json`` pinning every file by SHA-256, and an executable markup
contract. A released theme version is never edited; a change ships as a new
version. Generated pages pin ``theme_id`` and the stylesheet hash, so an old
page keeps rendering with the exact bytes it was verified against.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from oryxenai.themes.contract import ThemeContract

DEFAULT_THEME_ID = "editorial-forest/v1"

# theme id -> module exposing ``load() -> ThemePackage``
_THEME_MODULES: dict[str, str] = {
    "editorial-forest/v1": "oryxenai.themes.editorial_forest.v1",
}

_MEDIA_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".woff2": "font/woff2",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".js": "text/javascript; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".json": "application/json",
}


class ThemeError(Exception):
    """A theme is unknown or its files do not match its manifest."""


@dataclass(frozen=True, slots=True)
class ThemeFile:
    path: str
    media_type: str
    sha256: str
    size: int
    data: bytes


@dataclass(frozen=True, slots=True)
class ThemePackage:
    theme_id: str
    manifest: Mapping[str, Any]
    files: Mapping[str, ThemeFile]
    contract: ThemeContract

    @property
    def stylesheet(self) -> ThemeFile:
        return self.files[str(self.manifest["stylesheet"])]

    @property
    def css_sha256(self) -> str:
        return self.stylesheet.sha256

    def file(self, path: str) -> ThemeFile | None:
        return self.files.get(path)

    def manifest_entries(self) -> list[dict[str, object]]:
        """Bundle manifest rows for the theme-owned files (hash, size, type)."""
        return [
            {"path": item.path, "sha256": item.sha256, "bytes": item.size, "source": "theme"}
            for item in sorted(self.files.values(), key=lambda entry: entry.path)
        ]


def media_type_for(path: str) -> str:
    return _MEDIA_TYPES.get(Path(path).suffix.lower(), "application/octet-stream")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_manifest_files(root: Path, relative_paths: list[str]) -> list[dict[str, object]]:
    """Hash theme files for ``manifest.json`` (used by tests and the dev tool)."""
    rows: list[dict[str, object]] = []
    for relative in sorted(relative_paths):
        data = (root / relative).read_bytes()
        rows.append(
            {
                "path": relative,
                "sha256": sha256_hex(data),
                "bytes": len(data),
                "media_type": media_type_for(relative),
            }
        )
    return rows


def load_package(root: Path, contract: ThemeContract) -> ThemePackage:
    """Load a theme directory and verify every file against its manifest."""
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    files: dict[str, ThemeFile] = {}
    for entry in manifest["files"]:
        relative = str(entry["path"])
        target = (root / relative).resolve()
        if root.resolve() not in target.parents:
            raise ThemeError(f"Theme file escapes its package: {relative}")
        try:
            data = target.read_bytes()
        except OSError as exc:
            raise ThemeError(f"Theme file is missing: {relative}") from exc
        digest = sha256_hex(data)
        if digest != entry["sha256"] or len(data) != int(entry["bytes"]):
            raise ThemeError(
                f"Theme file {relative} does not match manifest.json "
                f"(expected {entry['sha256']}, found {digest}). Released theme versions are immutable."
            )
        files[relative] = ThemeFile(relative, str(entry["media_type"]), digest, len(data), data)
    if str(manifest["stylesheet"]) not in files:
        raise ThemeError("The manifest does not list its stylesheet.")
    return ThemePackage(str(manifest["theme_id"]), manifest, files, contract)


@lru_cache(maxsize=8)
def get_theme(theme_id: str = DEFAULT_THEME_ID) -> ThemePackage:
    module_name = _THEME_MODULES.get(theme_id)
    if module_name is None:
        raise ThemeError(f"Unknown theme '{theme_id}'.")
    module = importlib.import_module(module_name)
    package: ThemePackage = module.load()
    if package.theme_id != theme_id:
        raise ThemeError(f"Theme module {module_name} reports id '{package.theme_id}'.")
    return package


def list_theme_ids() -> tuple[str, ...]:
    return tuple(sorted(_THEME_MODULES))
