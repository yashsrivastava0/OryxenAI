"""Placeholder content for theme exemplars.

The exemplar a model sees must never contain literal sample copy: the model copies
it. Render the exemplar from ``placeholderize(sample)`` so every string reads as
"put the value of this field here", using the same path syntax as ``data-field``.
"""

from __future__ import annotations

from typing import Any


def placeholderize(value: Any, path: str = "") -> Any:
    """Replace each non-empty string leaf with ``{path}``; empty strings stay empty."""
    if isinstance(value, str):
        return f"{{{path}}}" if value.strip() else ""
    if isinstance(value, dict):
        return {
            key: placeholderize(child, f"{path}.{key}" if path else str(key))
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [placeholderize(child, f"{path}[{index}]") for index, child in enumerate(value)]
    return value
