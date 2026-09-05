"""Deterministic compilation of portfolio-authored visual tokens."""

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

    def emit(name: str, value: str, *, allow_reference: bool = False) -> None:
        normalized = name.strip().replace("_", "-")
        if not _SAFE_NAME.fullmatch(normalized):
            raise TokenCompilationError(f"unsafe token name: {name}")
        rendered = value.strip()
        if (
            not rendered
            or ("var(" in rendered.casefold() and not allow_reference)
            or ("," in rendered and "cubic-bezier" not in rendered)
        ):
            raise TokenCompilationError(f"token {name} has a fallback or composite value")
        if allow_reference and not re.fullmatch(r"var\(--[a-z0-9_-]+\)", rendered):
            raise TokenCompilationError(f"token {name} has an unsafe alias reference")
        if any(character in rendered for character in ("{", "}", ";", "\n", "\r")):
            raise TokenCompilationError(f"token {name} contains unsafe CSS")
        lines.append(f"  --{normalized}: {rendered};")

    def group_name(group: str, name: str) -> str:
        # A blueprint-authored token name (e.g. a spacing step literally
        # named "space-5") already carrying its own group prefix must not be
        # prefixed a second time: that produced unpredictable emitted names
        # like "--space-space-5" that a model generating source against the
        # blueprint's own token names has no way to anticipate, and its
        # references to the intended "--space-5" then went undefined.
        return name if name == group or name.startswith(f"{group}-") else f"{group}-{name}"

    for color_token in sorted(blueprint.tokens.colors, key=lambda item: item.name):
        emit(group_name("color", color_token.name), color_token.value)
    color_names = {item.name for item in blueprint.tokens.colors}
    invalid_bindings = {
        slot: color_name
        for slot, color_name in blueprint.tokens.shadcn_theme_bindings.items()
        if color_name not in color_names
    }
    if invalid_bindings:
        raise TokenCompilationError(
            "shadcn theme bindings must reference approved color token names: "
            + ", ".join(
                f"{slot}={color_name}" for slot, color_name in sorted(invalid_bindings.items())
            )
        )
    # Live-discovered 2026-09-05: a raw color token and a shadcn theme
    # binding slot both compile to the same "--color-<name>" custom
    # property (group_name is idempotent for an already-prefixed name).
    # Raw colors are emitted first, then binding aliases -- so when a
    # planner names a raw color the same as a semantic slot (e.g. both an
    # "accent" color and an "accent" binding, common since "accent" is a
    # natural name for both), the alias silently overwrites the raw color
    # in the same :root block. This corrupts every derived token (e.g.
    # --color-primary: var(--color-accent) resolving to the wrong value)
    # without any error -- it only surfaced as a whole-site quality-review
    # finding after a full, costly generation pass. Reject it here instead,
    # before any route generation call is made.
    raw_color_property_names = {group_name("color", name) for name in color_names}
    colliding_slots = {
        slot: color_name
        for slot, color_name in blueprint.tokens.shadcn_theme_bindings.items()
        if group_name("color", slot) in raw_color_property_names
    }
    if colliding_slots:
        raise TokenCompilationError(
            "shadcn theme binding slot names collide with existing raw color token names "
            "and would silently overwrite them in the emitted CSS: "
            + ", ".join(
                f"{slot}->{color_name}" for slot, color_name in sorted(colliding_slots.items())
            )
        )
    for slot, color_name in sorted(blueprint.tokens.shadcn_theme_bindings.items()):
        emit(
            group_name("color", slot),
            f"var(--{group_name('color', color_name)})",
            allow_reference=True,
        )
    for group, values in (
        ("space", blueprint.tokens.spacing),
        ("size", blueprint.tokens.sizes),
        ("radius", blueprint.tokens.radii),
    ):
        for length_token in sorted(values, key=lambda item: item.name):
            emit(
                group_name(group, length_token.name),
                f"{length_token.value:g}{length_token.unit}",
            )
    for border_token in sorted(blueprint.tokens.borders, key=lambda item: item.name):
        lines.append(
            f"  --{group_name('border', border_token.name)}: "
            f"{border_token.width.value:g}{border_token.width.unit} "
            f"{border_token.style} var(--{group_name('color', border_token.color_token)});"
        )
    for shadow in sorted(blueprint.tokens.shadows, key=lambda item: item.name):
        lines.append(
            f"  --{group_name('shadow', shadow.name)}: "
            f"{shadow.offset_x.value:g}{shadow.offset_x.unit} "
            f"{shadow.offset_y.value:g}{shadow.offset_y.unit} "
            f"{shadow.blur.value:g}{shadow.blur.unit} "
            f"{shadow.spread.value:g}{shadow.spread.unit} "
            f"var(--{group_name('color', shadow.color_token)});"
        )
    for container in sorted(blueprint.tokens.containers, key=lambda item: item.name):
        emit(
            f"container-{container.name}-max",
            f"{container.maximum.value:g}{container.maximum.unit}",
        )
        emit(
            f"container-{container.name}-padding",
            f"{container.inline_padding.value:g}{container.inline_padding.unit}",
        )
    for motion_token in sorted(blueprint.tokens.motion, key=lambda item: item.name):
        emit(f"motion-{motion_token.name}-duration", f"{motion_token.duration_ms}ms")
        emit(f"motion-{motion_token.name}-easing", motion_token.easing)
    roles = {item.role: item for item in blueprint.tokens.typography_roles}
    body = roles["body"]
    display = roles.get("display", body)
    emit("font-body", f'"{body.family}"')
    emit("font-display", f'"{display.family}"')
    type_step_names = {step.name for step in blueprint.tokens.type_steps}
    emitted_type_names: set[str] = set()
    for role in (body, display):
        if role.role in emitted_type_names or role.role in type_step_names:
            continue
        emit(f"type-{role.role}-min", f"{role.body_min_rem:g}rem")
        emit(f"type-{role.role}-max", f"{role.body_max_rem:g}rem")
        emit(f"type-{role.role}-line-height", f"{role.body_line_height:g}")
        emit(f"type-{role.role}-tracking", f"{role.tracking_em:g}em")
        emitted_type_names.add(role.role)
    for step in sorted(blueprint.tokens.type_steps, key=lambda item: item.name):
        if step.name in emitted_type_names:
            continue
        emit(f"type-{step.name}-min", f"{step.minimum_rem:g}rem")
        emit(f"type-{step.name}-max", f"{step.maximum_rem:g}rem")
        emit(f"type-{step.name}-line-height", f"{step.line_height:g}")
        emit(f"type-{step.name}-tracking", f"{step.tracking_em:g}em")
        emitted_type_names.add(step.name)
    lines.extend(["}", ""])

    emitted_font_faces: set[tuple[str, str, int, str]] = set()
    for typography in blueprint.tokens.typography_roles:
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
                if suffix not in {"woff2", "woff"}:
                    continue
                if ".." in Path(normalized_path).parts or normalized_path.startswith(
                    ("http:", "https:")
                ):
                    raise TokenCompilationError("font binding must point to local material")
                public_path = (
                    f"resources/pack/{normalized_path.removeprefix('resources/')}"
                    if normalized_path.startswith("resources/")
                    else normalized_path.removeprefix("public/")
                )
                weight = _font_weight_for_path(normalized_path, binding, typography.weights)
                # Two typography roles (e.g. body and display) commonly share
                # one approved_font_slot/family. Each role's iteration
                # independently re-matches the same binding, which would
                # otherwise emit that binding's @font-face rules once per
                # role instead of once per actual font file.
                face_key = (family, typography.style, weight, public_path)
                if face_key in emitted_font_faces:
                    continue
                emitted_font_faces.add(face_key)
                lines.extend(
                    [
                        "@font-face {",
                        f'  font-family: "{family}";',
                        f"  font-style: {typography.style};",
                        f"  font-weight: {weight};",
                        f'  src: url("/{public_path}") format("{suffix}");',
                        f"  font-display: {typography.font_display};",
                        "}",
                        "",
                    ]
                )
    return "\n".join(lines)


def _font_weight_for_path(
    normalized_path: str, binding: ExecutionBindingV2, fallback: list[int]
) -> int:
    # Materialized font files are named "{weight}-{style}.{ext}" (e.g.
    # "400-normal.woff2") inside a resource directory, so the weight always
    # sits immediately after a "/" path separator. Matching against the
    # filename alone (not the full path) avoids two failure modes of
    # matching the full path: a "/" left boundary was never recognized by
    # the "-"/"_" boundary class below, so every file in a multi-weight
    # binding silently fell back to the same weight; and a resource-id
    # segment earlier in the path could in principle contain a spurious
    # 3-digit run of its own.
    filename = normalized_path.rsplit("/", 1)[-1]
    match = re.search(r"(?:^|[-_])([1-9][0-9]{2})(?:[-_.]|$)", filename)
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
