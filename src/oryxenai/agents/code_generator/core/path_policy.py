"""Cross-platform generated-path normalization and collision checks."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import PurePosixPath, PureWindowsPath

_WINDOWS_RESERVED = {
    "aux",
    "clock$",
    "con",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


def semantic_segment(value: str) -> str:
    """Return a readable segment plus a stable hash so lossy slugs cannot collide."""

    normalized = unicodedata.normalize("NFKC", value).strip()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.casefold()).strip("-") or "item"
    if slug.split(".", 1)[0] in _WINDOWS_RESERVED:
        slug = f"item-{slug}"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]
    return f"{slug[:72]}-{digest}"


def validate_generated_paths(paths: list[str]) -> None:
    """Reject unsafe, case-only, and Unicode-normalization path collisions."""

    identities: dict[str, str] = {}
    for value in paths:
        path = PurePosixPath(value.replace("\\", "/"))
        if (
            not value
            or path.is_absolute()
            or bool(PureWindowsPath(value).drive)
            or ".." in path.parts
            or any(not part or part.rstrip(" .") != part for part in path.parts)
            or any(part.split(".", 1)[0].casefold() in _WINDOWS_RESERVED for part in path.parts)
        ):
            raise ValueError(f"unsafe generated path: {value}")
        identity = unicodedata.normalize("NFKC", path.as_posix()).casefold()
        prior = identities.get(identity)
        if prior is not None and prior != path.as_posix():
            raise ValueError(f"generated paths collide across platforms: {prior} and {value}")
        identities[identity] = path.as_posix()


__all__ = ["semantic_segment", "validate_generated_paths"]
