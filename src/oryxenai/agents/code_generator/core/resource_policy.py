"""Shared host-owned resource classification for Code Generator.

Build Preparation uses editorial names such as ``editorial_photo`` and
``abstract systems illustration``.  The generator must normalize those names
without losing the original value, and it must never classify a declared
component slot as an image merely because a purpose string mentions visuals.
"""

from __future__ import annotations

import re

IMAGE_CATEGORIES = frozenset({"image", "photo", "editorial_photo", "illustration", "texture"})
COMPONENT_CATEGORIES = frozenset(
    {"component", "component_source", "visual_component", "registry_component"}
)
FONT_CATEGORIES = frozenset({"font", "typography", "typography_system"})


def normalize_resource_category(value: object) -> str:
    """Map an upstream category to the executable acquisition category."""

    raw = " ".join(str(value or "").casefold().replace("_", " ").split())
    if raw in {"photo", "editorial photo", "image", "images"}:
        return "image"
    if raw in {"illustration", "illustrations", "abstract illustration", "abstract systems illustration"}:
        return "illustration"
    if raw in {"texture", "textures", "surface texture"}:
        return "texture"
    if raw in {"font", "typography", "typography system", "type system"}:
        return "font"
    if raw in {"component", "component source", "visual component", "registry component"}:
        return "component_source"
    if raw in {"icon", "icons"}:
        return "icon"
    if raw in {"style", "style primitive", "pattern", "token preset", "helper"}:
        return "style_primitive"
    return raw.replace(" ", "_")


def is_image_category(value: object) -> bool:
    """Return whether a category is an image-like browser asset."""

    normalized = normalize_resource_category(value)
    return normalized in {"image", "illustration", "texture"}


def is_component_category(value: object) -> bool:
    return normalize_resource_category(value) == "component_source"


def is_font_category(value: object) -> bool:
    return normalize_resource_category(value) == "font"


def category_words(value: object) -> set[str]:
    """Expose stable words for the one remaining emergent-resource matcher."""

    return {word for word in re.findall(r"[a-z0-9]+", str(value or "").casefold()) if word}


__all__ = [
    "category_words",
    "is_component_category",
    "is_font_category",
    "is_image_category",
    "normalize_resource_category",
]
