"""Deterministic compilation of portfolio-authored v3 visual tokens."""

from __future__ import annotations

import re
from pathlib import Path

from oryxenai.agents.code_generator.core.development_schemas import (
    ExecutionBindingV2,
    ExperienceBlueprintV3,
)


class TokenCompilationError(ValueError):
    pass


_SAFE_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")


def compile_generated_tokens(
    blueprint: ExperienceBlueprintV3,
    bindings: list[ExecutionBindingV2] | tuple[ExecutionBindingV2, ...] = (),
) -> str:
    """Return stable CSS with no scaffold palette or token fallback values."""

    lines = [
        "/* Generated from the admitted ExperienceBlueprintV3. Do not edit. */",
        ":root {",
    ]
    for group in sorted(blueprint.tokens.token_groups, key=lambda item: item.group_id):
        for name, value in sorted(group.values.items()):
            normalized = str(name).strip().replace("_", "-")
            if not _SAFE_NAME.fullmatch(normalized):
                raise TokenCompilationError(f"unsafe token name: {name}")
            rendered = str(value).strip()
            lowered = rendered.casefold()
            if (
                not rendered
                or ("var(" in rendered and "," in rendered)
                or any(character in rendered for character in ("{", "}", ";", "\n", "\r"))
                or "url(" in lowered
                or "@import" in lowered
                or "http:" in lowered
                or "https:" in lowered
            ):
                raise TokenCompilationError(f"token {group.group_id}.{name} has a fallback value")
            lines.append(f"  --{group.group_id}-{normalized}: {rendered};")
    lines.extend(
        [
            "}",
            "",
        ]
    )
    typography = blueprint.tokens.typography
    matching = [
        item
        for item in bindings
        if item.resource_slot_id == typography.resource_slot_id and item.local_paths
    ]
    for binding in sorted(matching, key=lambda item: item.resource_slot_id):
        family = binding.font_family or typography.family
        if not family.strip() or any(character in family for character in ('"', "\n", "\r", ";")):
            raise TokenCompilationError("font binding has no family")
        for path in sorted(binding.local_paths):
            normalized_path = path.replace("\\", "/").lstrip("/")
            if ".." in Path(normalized_path).parts or normalized_path.startswith(
                ("http:", "https:")
            ):
                raise TokenCompilationError("font binding must point to local material")
            lines.extend(
                [
                    "@font-face {",
                    f'  font-family: "{family}";',
                    f'  src: url("/{normalized_path}") format("woff2");',
                    "  font-display: swap;",
                    "}",
                    "",
                ]
            )
    return "\n".join(lines)


def write_generated_tokens(
    repo_dir: Path,
    blueprint: ExperienceBlueprintV3,
    bindings: list[ExecutionBindingV2] | tuple[ExecutionBindingV2, ...] = (),
) -> Path:
    target = repo_dir / "src" / "design" / "generated-tokens.css"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(compile_generated_tokens(blueprint, bindings), encoding="utf-8")
    return target
