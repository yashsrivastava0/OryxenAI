"""Provider-wire schema checks for bounded native structured outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SchemaCompatibilityError(ValueError):
    """Raised when a DTO exceeds the provider's native schema subset."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("; ".join(self.issues) or "schema is not provider-compatible")


def schema_compatibility_issues(output_model: type[BaseModel]) -> list[str]:
    """Return deterministic, safe reasons a schema is too complex on the wire.

    Pydantic's ``$defs``/``$ref`` nodes are valid JSON Schema and are retained
    in trusted prompts.  The checks target the problematic constructs: union
    composition, arbitrary object maps, and unconstrained arrays.
    """

    schema = output_model.model_json_schema()
    issues: list[str] = []

    def visit(value: Any, path: str = "root") -> None:
        if isinstance(value, dict):
            if any(key in value for key in ("anyOf", "oneOf", "allOf")):
                issues.append(f"{path}:union-composition")
            additional = value.get("additionalProperties")
            if additional is True or isinstance(additional, dict):
                issues.append(f"{path}:arbitrary-object-map")
            if value.get("type") == "array" and "items" not in value:
                issues.append(f"{path}:untyped-array")
            for key, child in value.items():
                visit(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(schema)
    return list(dict.fromkeys(issues))


def ensure_schema_compatible(output_model: type[BaseModel]) -> None:
    issues = schema_compatibility_issues(output_model)
    if issues:
        raise SchemaCompatibilityError(issues)


__all__ = [
    "SchemaCompatibilityError",
    "ensure_schema_compatible",
    "schema_compatibility_issues",
]
