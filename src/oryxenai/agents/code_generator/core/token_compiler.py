"""Deterministic compilation of portfolio-authored v3 visual tokens."""

from __future__ import annotations

import re
from pathlib import Path

from oryxenai.agents.code_generator.core.development_schemas import (
    ExecutionBindingV2,
    ExperienceBlueprintV3,
    ExperienceBlueprintV4,
)


class TokenCompilationError(ValueError):
    pass


# The group prefix makes the emitted custom property safe even when a token
# suffix follows a conventional scale name such as ``2xl``.
_SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_FONT_FILE_SUFFIXES = frozenset({".otf", ".ttf", ".woff", ".woff2"})


def compile_generated_tokens(
    blueprint: ExperienceBlueprintV3 | ExperienceBlueprintV4,
    bindings: list[ExecutionBindingV2] | tuple[ExecutionBindingV2, ...] = (),
) -> str:
    """Return stable CSS with no scaffold palette or token fallback values."""

    if isinstance(blueprint, ExperienceBlueprintV4):
        return _compile_v4_tokens(blueprint, bindings)

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
    font_style = str(getattr(typography, "style", "normal") or "normal")
    matching = [
        item
        for item in bindings
        if item.resource_slot_id == typography.resource_slot_id and item.local_paths
    ]
    for binding in sorted(matching, key=lambda item: item.resource_slot_id):
        family = binding.font_family or typography.family
        if not family.strip() or any(character in family for character in ('"', "\n", "\r", ";")):
            raise TokenCompilationError("font binding has no family")
        # Resource receipts may include the materialized directory as a
        # convenient import root alongside its files.  Only emit actual font
        # files into @font-face; a directory URL passes source checks but is a
        # missing production artifact reference after bundling.
        for path in sorted(binding.local_paths):
            normalized_path = path.replace("\\", "/").lstrip("/")
            if ".." in Path(normalized_path).parts or normalized_path.startswith(
                ("http:", "https:")
            ):
                raise TokenCompilationError("font binding must point to local material")
            if Path(normalized_path).suffix.casefold() not in _FONT_FILE_SUFFIXES:
                continue
            if normalized_path.startswith("resources/"):
                public_path = f"resources/pack/{normalized_path.removeprefix('resources/')}"
            else:
                public_path = normalized_path
            weight = _font_weight_for_path(normalized_path, binding, typography.weights)
            font_format = Path(normalized_path).suffix.casefold().lstrip(".")
            if font_format not in {"woff2", "woff", "ttf", "otf"}:
                continue
            lines.extend(
                [
                    "@font-face {",
                    f'  font-family: "{family}";',
                    f"  font-style: {font_style};",
                    f"  font-weight: {weight};",
                    f'  src: url("/{public_path}") format("{font_format}");',
                    "  font-display: swap;",
                    "}",
                    "",
                ]
            )
    return "\n".join(lines)


def _compile_v4_tokens(
    blueprint: ExperienceBlueprintV4,
    bindings: list[ExecutionBindingV2] | tuple[ExecutionBindingV2, ...],
) -> str:
    lines = [
        "/* Generated from the admitted ExperienceBlueprintV4. Do not edit. */",
        ":root {",
    ]

    def emit(name: str, value: str) -> None:
        normalized = name.strip().replace("_", "-")
        if not _SAFE_NAME.fullmatch(normalized):
            raise TokenCompilationError(f"unsafe token name: {name}")
        rendered = value.strip()
        if (
            not rendered
            or "var(" in rendered.casefold()
            or ("," in rendered and "cubic-bezier" not in rendered)
        ):
            raise TokenCompilationError(f"token {name} has a fallback or composite value")
        if any(character in rendered for character in ("{", "}", ";", "\n", "\r")):
            raise TokenCompilationError(f"token {name} contains unsafe CSS")
        lines.append(f"  --{normalized}: {rendered};")

    for color_token in sorted(blueprint.tokens.colors, key=lambda item: item.name):
        emit(f"color-{color_token.name}", color_token.value)
    for group, values in (
        ("space", blueprint.tokens.spacing),
        ("size", blueprint.tokens.sizes),
        ("radius", blueprint.tokens.radii),
    ):
        for length_token in sorted(values, key=lambda item: item.name):
            emit(
                f"{group}-{length_token.name}",
                f"{length_token.value:g}{length_token.unit}",
            )
    for border_token in sorted(blueprint.tokens.borders, key=lambda item: item.name):
        emit(
            f"border-{border_token.name}",
            f"{border_token.width.value:g}{border_token.width.unit} {border_token.style} var(--color-{border_token.color_token})",
        )
    for motion_token in sorted(blueprint.tokens.motion, key=lambda item: item.name):
        emit(f"motion-{motion_token.name}-duration", f"{motion_token.duration_ms}ms")
        emit(f"motion-{motion_token.name}-easing", motion_token.easing)
    typography = blueprint.tokens.typography
    emit("font-body", f'"{typography.family}"')
    emit("font-display", f'"{typography.family}"')
    emit("type-body-min", f"{typography.body_min_rem:g}rem")
    emit("type-body-max", f"{typography.body_max_rem:g}rem")
    emit("type-heading-ratio", f"{typography.heading_ratio:g}")
    emit("type-body-line-height", f"{typography.body_line_height:g}")
    lines.extend(["}", ""])

    matching = [
        item
        for item in bindings
        if item.resource_slot_id == typography.approved_font_slot and item.local_paths
    ]
    for binding in sorted(matching, key=lambda item: item.resource_slot_id):
        family = binding.font_family or typography.family
        for path in sorted(binding.local_paths):
            normalized_path = path.replace("\\", "/").lstrip("/")
            suffix = Path(normalized_path).suffix.casefold().lstrip(".")
            if suffix not in {"woff2", "woff", "ttf", "otf"}:
                continue
            if ".." in Path(normalized_path).parts or normalized_path.startswith(
                ("http:", "https:")
            ):
                raise TokenCompilationError("font binding must point to local material")
            public_path = (
                f"resources/pack/{normalized_path.removeprefix('resources/')}"
                if normalized_path.startswith("resources/")
                else normalized_path
            )
            weight = _font_weight_for_path(normalized_path, binding, typography.weights)
            lines.extend(
                [
                    "@font-face {",
                    f'  font-family: "{family}";',
                    f"  font-style: {typography.style};",
                    f"  font-weight: {weight};",
                    f'  src: url("/{public_path}") format("{suffix}");',
                    "  font-display: swap;",
                    "}",
                    "",
                ]
            )
    return "\n".join(lines)


def _font_weight_for_path(
    normalized_path: str, binding: ExecutionBindingV2, fallback: list[int]
) -> int:
    match = re.search(r"(?:^|[-_])([1-9][0-9]{2})(?:[-_.]|$)", normalized_path)
    if match is not None:
        return int(match.group(1))
    weights = [int(value) for value in binding.font_weights if str(value).isdigit()]
    return weights[0] if weights else (fallback[0] if fallback else 400)


def write_generated_tokens(
    repo_dir: Path,
    blueprint: ExperienceBlueprintV3 | ExperienceBlueprintV4,
    bindings: list[ExecutionBindingV2] | tuple[ExecutionBindingV2, ...] = (),
) -> Path:
    target = repo_dir / "src" / "design" / "generated-tokens.css"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(compile_generated_tokens(blueprint, bindings), encoding="utf-8")
    return target
