"""Dependency-free structural audit for generated TypeScript/JSX source.

The generator deliberately does not depend on a parser package at runtime.  This
audit is therefore a conservative lexical pass over the small set of source
constructs that form the portfolio contract: local module edges, route shell
landmarks, section anchors, interaction markers, and exported shared systems.
It is supplemental to the build/typecheck gate, never a replacement for it.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, cast

from oryxenai.agents.code_generator.core.development_schemas import (
    Diagnostic,
    ExperienceBlueprintV3,
    ExperienceBlueprintV4,
    SitePlan,
)
from oryxenai.agents.code_generator.core.source_lexing import (
    static_jsx_attribute_values,
    strip_source_comments,
)

_IMPORT_RE = re.compile(
    r"(?:import\s+(?P<bindings>[\s\S]*?)\s+from\s+|export\s+[\s\S]*?\s+from\s+|import\s*\()"
    r"[\"'](?P<module>[^\"']+)[\"']"
)
_ID_RE = re.compile(r"(?<![\w-])id\s*=\s*[\"']([^\"']+)[\"']")
_INTERACTION_RE = re.compile(r"data-interaction-id\s*=\s*[\"']([^\"']+)[\"']")
_CONTENT_RE = re.compile(r"data-content-id\s*=\s*[\"']([^\"']+)[\"']")
_EXPORT_DECL_RE = re.compile(
    r"\bexport\s+(?:declare\s+)?(?:const|let|var|function|class|type|interface|enum)\s+"
    r"([A-Za-z_$][\w$]*)"
)
_EXPORT_LIST_RE = re.compile(r"\bexport\s*\{([^}]*)\}")
_IMPORT_BINDING_RE = re.compile(
    r"^\s*(?:(?P<default>[A-Za-z_$][\w$]*)\s*,\s*)?"
    r"(?:\{(?P<named>[^}]*)\}|(?P<namespace>\*\s+as\s+[A-Za-z_$][\w$]*))?"
    r"\s*$"
)
_GENERIC_CLASS_RE = re.compile(
    r"(?:class(?:Name)?\s*=\s*[\"'`]([^\"'`]+)[\"'`]|\.(card|surface|grid|reveal|stagger)\b)"
)
_NETWORK_RE = re.compile(
    r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(|\b(?:axios|ky)\s*\("
)
_FRAGMENT_RE = re.compile(r"href\s*=\s*[\"']#([^\"']+)[\"']")


def _without_comments(value: str) -> str:
    return strip_source_comments(value)


def _diagnostic(
    code: str,
    message: str,
    *,
    file: str = "",
    route_id: str = "",
    symbol: str = "",
    expected: str = "",
    observed: str = "",
) -> Diagnostic:
    fingerprint = hashlib.sha256(
        f"{code}:{file}:{route_id}:{symbol}:{message}:{expected}:{observed}".encode()
    ).hexdigest()[:24]
    return Diagnostic(
        diagnostic_id=f"diagnostic-{fingerprint}",
        group="source_contract",
        code=code,
        phase="source_contract",
        route_id=route_id,
        normalized_message=message,
        file=file,
        symbol=symbol,
        expected=expected,
        observed=observed,
        fingerprint=fingerprint,
    )


def _resolve_local(repo_dir: Path, source_path: Path, imported: str) -> Path | None:
    target = (
        (repo_dir / imported.lstrip("/")).resolve()
        if imported.startswith("/")
        else (source_path.parent / imported).resolve()
    )
    if not target.is_relative_to(repo_dir.resolve()):
        return None
    if target.is_file():
        return target
    for suffix in (".ts", ".tsx", ".css", ".json"):
        candidate = target.with_suffix(suffix)
        if candidate.is_file():
            return candidate
    for suffix in ("index.ts", "index.tsx"):
        candidate = target / suffix
        if candidate.is_file():
            return candidate
    return None


def _exports(source: str) -> set[str]:
    clean = _without_comments(source)
    values = set(_EXPORT_DECL_RE.findall(clean))
    for group in _EXPORT_LIST_RE.findall(clean):
        for item in group.split(","):
            name = item.strip().split(" as ", 1)[-1].strip()
            if name:
                values.add(name)
    if re.search(r"\bexport\s+default\b", clean):
        values.add("default")
    return values


def _named_imports(bindings: str) -> tuple[set[str], bool]:
    match = _IMPORT_BINDING_RE.match(bindings.strip())
    if not match:
        return set(), False
    names: set[str] = set()
    if match.group("default"):
        names.add("default")
    named = match.group("named") or ""
    for item in named.split(","):
        item = item.strip()
        if not item:
            continue
        names.add(item.split(" as ", 1)[0].strip())
    return names, bool(match.group("namespace"))


def _route_source_path(route: dict[str, Any], *, semantic: bool = False) -> str:
    storage_key = str(route.get("storage_key") or route.get("route_id", ""))
    storage_key = storage_key.replace("\\", "/").strip("/")
    if storage_key.startswith("routes/"):
        storage_key = storage_key.removeprefix("routes/")
    # The planner already stores a collision-safe route directory in
    # ``storage_key``. Re-semanticizing that value would append a second hash
    # and make the validator look for a route file the generator never wrote.
    if semantic and not route.get("storage_key"):
        from oryxenai.agents.code_generator.core.path_policy import semantic_segment

        storage_key = semantic_segment(storage_key or str(route.get("route_id", "")))
    return f"src/routes/{storage_key}/index.tsx"


def _route_ids_in_source(route: dict[str, Any], source: str) -> str:
    route_id = str(route.get("route_id", ""))
    return route_id if route_id in source else ""


def _literal_selector_positions(source: str, selector: str) -> list[int] | None:
    """Return source positions for simple planner selectors, if provable."""

    value = selector.strip()
    id_match = re.fullmatch(r"#([A-Za-z_][\w-]*)", value)
    if id_match:
        return [
            position
            for position, attribute_value in static_jsx_attribute_values(source, "id")
            if attribute_value == id_match.group(1)
        ]
    attribute_match = re.fullmatch(
        r"\[\s*([A-Za-z_:][\w:.-]*)\s*=\s*([\"'])(.*?)\2\s*\]",
        value,
    )
    if attribute_match:
        name, _, expected = attribute_match.groups()
        return [
            position
            for position, attribute_value in static_jsx_attribute_values(source, name)
            if attribute_value == expected
        ]
    class_match = re.fullmatch(r"\.([A-Za-z_][\w-]*)", value)
    if class_match:
        expected = class_match.group(1)
        return [
            position
            for name in ("class", "className")
            for position, attribute_value in static_jsx_attribute_values(source, name)
            if expected in attribute_value.split()
        ]
    return None


def audit_typescript_source(
    repo_dir: Path,
    *,
    files: dict[str, str],
    plan: SitePlan,
    projections: dict[str, dict[str, Any]] | None = None,
) -> list[Diagnostic]:
    """Return blocking diagnostics for the V3 source contract.

    V2 generation remains supported for compatibility; the stricter route and
    token contract is intentionally activated only for an admitted V3 plan.
    """

    if not isinstance(plan.experience_blueprint, (ExperienceBlueprintV3, ExperienceBlueprintV4)):
        return []
    diagnostics: list[Diagnostic] = []
    clean_files = {
        path: _without_comments(text)
        for path, text in files.items()
        if path.endswith((".ts", ".tsx"))
    }

    blueprint_v4 = isinstance(plan.experience_blueprint, ExperienceBlueprintV4)
    v4_blueprint = cast(ExperienceBlueprintV4, plan.experience_blueprint)
    v4_section_selectors = (
        {
            (region.route_id, region.section_id): region.section_selector
            for region in v4_blueprint.section_regions
        }
        if blueprint_v4
        else {}
    )
    route_css = {
        path: _without_comments(text)
        for path, text in files.items()
        if path.startswith("src/routes/") and path.endswith(".css")
    }
    if blueprint_v4:
        # V4 route code must use the trusted shell, not merely coexist with an
        # unused SharedSystems module in the candidate tree.
        for route in plan.routes:
            route_file = _route_source_path(route.model_dump(mode="json"), semantic=blueprint_v4)
            route_source = clean_files.get(route_file, "")
            if not re.search(r"\bRouteShell\b", route_source) or not re.search(
                r"import\s+\{[^}]*\bRouteShell\b[^}]*\}\s+from\s+[\"'](?:(?:\.\.?/)+components/generated/SharedSystems|@/components/generated/SharedSystems)",
                route_source,
            ):
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_ROUTE_SHELL_UNUSED",
                        "Every v4 route must import and render the trusted RouteShell.",
                        file=route_file,
                        route_id=str(route.route_id),
                    )
                )
        token_values = {
            item.value.casefold() for item in v4_blueprint.tokens.colors if item.value.strip()
        }
        for path, css in route_css.items():
            if re.search(r"var\([^)]*,", css):
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_CSS_TOKEN_FALLBACK",
                        "Generated route CSS may not hide an unbound token behind a fallback.",
                        file=path,
                    )
                )
            for literal in sorted(token_values):
                if css.casefold().count(literal) > 0:
                    diagnostics.append(
                        _diagnostic(
                            "SOURCE_RAW_PALETTE_LITERAL",
                            "Generated route CSS must reference canonical color tokens instead of raw palette literals.",
                            file=path,
                            symbol=literal,
                        )
                    )

    shared_path = "src/components/generated/SharedSystems.tsx"
    shared = clean_files.get(shared_path, "")
    if not shared:
        diagnostics.append(
            _diagnostic(
                "SOURCE_SHARED_SYSTEMS_MISSING",
                "The trusted generated SharedSystems module is missing.",
                file=shared_path,
            )
        )
    else:
        required_exports: tuple[str, ...] = (
            "RouteShell",
            "SectionAnchor",
            "useDisclosure",
            "Disclosure",
        )
        if blueprint_v4:
            required_exports += ("LocalImage",)
        for export_name in required_exports:
            if export_name not in _exports(shared):
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_SHARED_EXPORT_MISSING",
                        f"SharedSystems does not export the required {export_name} API.",
                        file=shared_path,
                        symbol=export_name,
                    )
                )
        for required_literal in ("<main", "publicSectionUrl", "aria-expanded", "Escape"):
            if required_literal not in shared:
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_SHARED_SYSTEM_INCOMPLETE",
                        "The trusted SharedSystems implementation is missing a required behavior primitive.",
                        file=shared_path,
                        symbol=required_literal,
                    )
                )

    for path, source in clean_files.items():
        if not path.startswith("src/"):
            continue
        network_match = _NETWORK_RE.search(source)
        if network_match:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_FORBIDDEN_NETWORK_CODE",
                    "Generated source contains a runtime network API outside the trusted local preview boundary.",
                    file=path,
                    symbol=network_match.group(0).strip(),
                )
            )
        for match in _IMPORT_RE.finditer(source):
            module = match.group("module")
            if not module.startswith((".", "/")):
                continue
            target = _resolve_local(repo_dir, repo_dir / path, module)
            if target is None:
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_LOCAL_MODULE_MISSING",
                        "A local import or re-export does not resolve to a checked-in module.",
                        file=path,
                        symbol=module,
                    )
                )
                continue
            bindings = match.group("bindings") or ""
            imported_names, namespace = _named_imports(bindings)
            if namespace or not imported_names:
                continue
            target_relative = target.relative_to(repo_dir).as_posix()
            exported = _exports(clean_files.get(target_relative, ""))
            for imported_name in sorted(imported_names):
                if imported_name not in exported:
                    diagnostics.append(
                        _diagnostic(
                            "SOURCE_LOCAL_EXPORT_MISSING",
                            "A local import names an export that its target module does not provide.",
                            file=path,
                            symbol=imported_name,
                            expected=target_relative,
                        )
                    )

    for route in plan.routes:
        route_data = route.model_dump(mode="json")
        route_id = str(route_data.get("route_id", ""))
        route_file = _route_source_path(route_data, semantic=blueprint_v4)
        # Reuse the exact path selected by _route_source_path. The planner's
        # storage_key is already collision-safe; semanticizing it again here
        # would point the route-wide audit at a different directory than the
        # generator wrote.
        route_prefix = f"{route_file.rsplit('/', 1)[0]}/"
        route_source = clean_files.get(route_file, "")
        if not route_source:
            continue
        route_source_with_shell = f"{shared}\n{route_source}"
        route_section_sources = {
            path: source
            for path, source in clean_files.items()
            if path.startswith(f"{route_prefix}sections/") and path.endswith(".tsx")
        }
        route_files_source = "\n".join(
            [route_source, *[route_section_sources[path] for path in sorted(route_section_sources)]]
        )
        # V4 section batches own their executable anchors. The composer only
        # renders those components; requiring duplicate anchors in index.tsx
        # would create duplicate DOM IDs. Include the completed route modules
        # in route-level checks while keeping shell checks scoped to the
        # composer and trusted shell.
        route_contract_source = route_files_source if blueprint_v4 else route_source
        if _route_ids_in_source(route_data, route_source_with_shell) != route_id:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_ID_MISSING",
                    "The V3 route source does not carry its authoritative route ID.",
                    file=route_file,
                    route_id=route_id,
                )
            )
        main_count = len(re.findall(r"<main\b", route_source_with_shell))
        h1_count = len(
            re.findall(
                r"<h1\b",
                f"{shared}\n{route_contract_source}" if blueprint_v4 else route_source_with_shell,
            )
        )
        if main_count != 1:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_MAIN_COUNT_INVALID",
                    "Every route must render exactly one main landmark through RouteShell.",
                    file=route_file,
                    route_id=route_id,
                    expected="1",
                    observed=str(main_count),
                )
            )
        if h1_count != 1:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_ROUTE_H1_COUNT_INVALID",
                    "Every route must render exactly one h1 heading.",
                    file=route_file,
                    route_id=route_id,
                    expected="1",
                    observed=str(h1_count),
                )
            )
        for landmark, maximum in (("nav", 1), ("header", 1), ("footer", 1)):
            count = len(re.findall(rf"<{landmark}\b", route_source_with_shell))
            if count > maximum:
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_UNOWNED_LANDMARK_DUPLICATE",
                        f"The route contains more than one {landmark} landmark.",
                        file=route_file,
                        route_id=route_id,
                        symbol=landmark,
                        expected=str(maximum),
                        observed=str(count),
                    )
                )

        for fragment in _FRAGMENT_RE.findall(route_contract_source):
            if not re.search(
                rf"(?<![\w-])id\s*=\s*[\"']{re.escape(fragment)}[\"']",
                route_contract_source,
            ):
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_INTERNAL_FRAGMENT_UNRESOLVED",
                        "A literal internal fragment does not resolve to a route DOM ID.",
                        file=route_file,
                        route_id=route_id,
                        symbol=fragment,
                    )
                )

        route_sections = list(route_data.get("section_order", []))
        if not route_sections:
            route_sections = [str(item) for item in route_data.get("section_ids", [])]
        positions: list[int] = []
        section_owner_paths: dict[str, str] = {}
        section_anchor_source = route_contract_source if blueprint_v4 else route_source
        for section_id in route_sections:
            matches = list(
                re.finditer(
                    rf"data-content-id\s*=\s*[\"']{re.escape(section_id)}[\"']",
                    section_anchor_source,
                )
            )
            if len(matches) != 1:
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_SECTION_ANCHOR_COUNT_INVALID",
                        "Each approved route section must have exactly one source content anchor.",
                        file=route_file,
                        route_id=route_id,
                        symbol=section_id,
                        expected="1",
                        observed=str(len(matches)),
                    )
                )
            section_selector = v4_section_selectors.get((route_id, section_id), f"#{section_id}")
            selector_matches = _literal_selector_positions(section_anchor_source, section_selector)
            if selector_matches is not None and len(selector_matches) != 1:
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_SECTION_DOM_ID_MISSING",
                        "Each approved section must implement its exact compiler-supplied "
                        "section selector once.",
                        file=route_file,
                        route_id=route_id,
                        symbol=section_selector,
                        expected="1",
                        observed=str(len(selector_matches)),
                    )
                )
            if blueprint_v4:
                owners = [
                    path
                    for path, source in route_section_sources.items()
                    if re.search(
                        rf"data-content-id\s*=\s*[\"']{re.escape(section_id)}[\"']",
                        source,
                    )
                ]
                if len(owners) == 1:
                    section_owner_paths[section_id] = owners[0]
            elif matches:
                positions.append(matches[0].start())
        if blueprint_v4:
            # For a composer, import order is the source-level representation
            # of rendered section order because the anchors live in children.
            for section_id in route_sections:
                owner = section_owner_paths.get(section_id)
                if owner is not None:
                    positions.append(route_source.find(Path(owner).stem))
        if positions != sorted(positions):
            diagnostics.append(
                _diagnostic(
                    "SOURCE_SECTION_ORDER_INVALID",
                    "Rendered section anchors do not follow the approved route section order.",
                    file=route_file,
                    route_id=route_id,
                )
            )

        for attr, code, label in (
            (_ID_RE, "SOURCE_DOM_ID_DUPLICATE", "DOM ID"),
            (_INTERACTION_RE, "SOURCE_INTERACTION_ID_DUPLICATE", "interaction ID"),
        ):
            values = attr.findall(route_source)
            duplicates = sorted({value for value in values if values.count(value) > 1})
            for value in duplicates:
                diagnostics.append(
                    _diagnostic(
                        code,
                        f"The route contains a duplicate {label}; identifiers must be unique per route.",
                        file=route_file,
                        route_id=route_id,
                        symbol=value,
                    )
                )
        generic = _GENERIC_CLASS_RE.search(route_source)
        if generic:
            value = generic.group(1) or generic.group(2) or ""
            if any(
                token in value.split() for token in ("card", "surface", "grid", "reveal", "stagger")
            ):
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_GENERIC_SCAFFOLD_CLASS",
                        "The route uses a generic scaffold class instead of a blueprint-owned composition.",
                        file=route_file,
                        route_id=route_id,
                        symbol=value,
                    )
                )

        route_moves = [
            move
            for move in plan.experience_blueprint.distinctive_moves
            if move.route_id == route_id
        ]
        for move in route_moves:
            marker = (
                str(getattr(move, "runtime_marker", ""))
                if blueprint_v4
                else f'data-distinctive-move-id="{move.move_id}"'
            )
            owner_file = section_owner_paths.get(getattr(move, "section_id", ""), route_file)
            if marker not in route_files_source:
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_BLUEPRINT_MOVE_UNUSED",
                        "A blueprint distinctive move has no traceable route implementation marker.",
                        file=owner_file,
                        route_id=route_id,
                        symbol=move.move_id,
                    )
                )
            elif blueprint_v4:
                v4_move = next(
                    item for item in v4_blueprint.distinctive_moves if item.move_id == move.move_id
                )
                scoped_css = "\n".join(
                    value for path, value in route_css.items() if path.startswith(route_prefix)
                )
                declarations = _selector_declarations(
                    scoped_css,
                    v4_move.source_selector,
                    runtime_marker=marker,
                )
                missing_properties = [
                    property_name
                    for property_name in v4_move.required_css_properties
                    if property_name.casefold() not in declarations
                ]
                if not declarations or missing_properties:
                    diagnostics.append(
                        _diagnostic(
                            "SOURCE_BLUEPRINT_MOVE_MARKER_ONLY",
                            "A distinctive-move marker is present without selector-scoped CSS evidence.",
                            file=owner_file,
                            route_id=route_id,
                            symbol=(
                                f"{move.move_id}:{','.join(missing_properties)}"
                                if missing_properties
                                else move.move_id
                            ),
                        )
                    )

        if blueprint_v4:
            for beat in v4_blueprint.motion_beats:
                if beat.route_id != route_id:
                    continue
                marker_present = beat.target_marker in route_files_source
                owner_file = section_owner_paths.get(beat.section_id, route_file)
                scoped_css = "\n".join(
                    value for path, value in route_css.items() if path.startswith(route_prefix)
                )
                declarations = _selector_declarations(scoped_css, beat.target_selector)
                expected_properties = {
                    item.property_name.casefold() for item in beat.changed_properties
                }
                motion_present = bool(
                    expected_properties.intersection(declarations)
                    and any(
                        name == "animation" or name.startswith(("animation-", "transition"))
                        for name in declarations
                    )
                )
                reduced_present = _selector_has_reduced_motion(scoped_css, beat.target_selector)
                if not marker_present or not motion_present:
                    diagnostics.append(
                        _diagnostic(
                            "SOURCE_MOTION_BEAT_UNIMPLEMENTED",
                            "Every v4 motion beat needs a target marker and executable source behavior.",
                            file=owner_file,
                            route_id=route_id,
                            symbol=beat.motion_id,
                        )
                    )
                if not reduced_present:
                    diagnostics.append(
                        _diagnostic(
                            "SOURCE_MOTION_REDUCED_MOTION_MISSING",
                            "Every v4 motion beat needs a prefers-reduced-motion replacement.",
                            file=owner_file,
                            route_id=route_id,
                            symbol=beat.motion_id,
                        )
                    )
            for assignment in v4_blueprint.interactions:
                if assignment.route_id != route_id:
                    continue
                if assignment.literal_marker not in route_files_source or not re.search(
                    r"(?:onClick|onKeyDown|href=|download=)", route_files_source
                ):
                    diagnostics.append(
                        _diagnostic(
                            "SOURCE_INTERACTION_UNIMPLEMENTED",
                            "Every v4 interaction assignment needs a literal marker and state/navigation behavior.",
                            file=route_file,
                            route_id=route_id,
                            symbol=assignment.interaction_id,
                        )
                    )
            diagnostics.extend(
                _audit_v4_anti_slop(
                    route_id=route_id,
                    route_file=route_file,
                    route_prefix=route_prefix,
                    files=files,
                    visual_direction=(projections or {}).get("design/visual-direction.json", {}),
                )
            )

    if blueprint_v4:
        diagnostics.extend(
            _audit_v4_cross_route_sameness(
                routes=[route.model_dump(mode="json") for route in plan.routes],
                files=clean_files,
            )
        )
    return _dedupe(diagnostics)


def _dedupe(values: list[Diagnostic]) -> list[Diagnostic]:
    seen: set[str] = set()
    result: list[Diagnostic] = []
    for value in values:
        if value.fingerprint not in seen:
            seen.add(value.fingerprint)
            result.append(value)
    return result


def _selector_declarations(
    css: str,
    selector: str,
    *,
    runtime_marker: str = "",
) -> set[str]:
    """Return declarations from the exact selector block, never unrelated CSS."""

    if not selector.strip():
        return set()
    accepted_selectors = [selector]
    if runtime_marker.strip():
        accepted_selectors.append(f"{selector.strip()}[{runtime_marker.strip()}]")
    blocks: list[str] = []
    for match in re.finditer(r"(?P<selectors>[^{}]+)\{(?P<body>[^{}]*)\}", css, re.DOTALL):
        selectors = [item.strip() for item in match.group("selectors").split(",")]
        if any(
            _selector_targets_contract(item, expected)
            for item in selectors
            for expected in accepted_selectors
        ):
            blocks.append(match.group("body"))
    return {
        match.group(1).casefold()
        for body in blocks
        for match in re.finditer(r"(?:^|;)\s*([a-z-]+)\s*:", body, re.IGNORECASE)
    }


_MOTION_STATE_QUALIFIER_RE = re.compile(
    r'\[data-motion-(?:ready|state)(?:\s*=\s*["\'][^"\']*["\'])?\]',
    re.IGNORECASE,
)


def _selector_targets_contract(candidate: str, expected: str) -> bool:
    """Allow runtime motion state qualifiers without changing the target."""

    normalized_candidate = " ".join(candidate.strip().split())
    normalized_expected = " ".join(expected.strip().split())
    if normalized_candidate == normalized_expected:
        return True
    without_runtime_state = _MOTION_STATE_QUALIFIER_RE.sub("", normalized_candidate)
    return " ".join(without_runtime_state.split()) == normalized_expected


def _selector_has_reduced_motion(css: str, selector: str) -> bool:
    """Require the reduced-motion rule to target the declared selector."""

    for match in re.finditer(
        r"@media[^{}]*prefers-reduced-motion\s*:\s*reduce[^{}]*"
        r"\{(?P<body>[^{}]*(?:\{[^{}]*\}[^{}]*)*)\}",
        css,
        re.IGNORECASE | re.DOTALL,
    ):
        if _selector_declarations(match.group("body"), selector):
            return True
    return False


_V4_SECTION_STRUCTURE_RE = re.compile(
    r"<(?:section|div|article|aside|header|footer)\b|"
    r"className\s*=\s*[\"'][^\"']+[\"']",
    re.IGNORECASE,
)


def _v4_section_structure_signature(source: str) -> tuple[str, ...]:
    return tuple(_V4_SECTION_STRUCTURE_RE.findall(_without_comments(source)))


def _v4_route_section_signature(
    *, files: dict[str, str], route_prefix: str
) -> tuple[tuple[str, ...], ...] | None:
    section_paths = sorted(
        path
        for path in files
        if path.startswith(f"{route_prefix}sections/") and path.endswith(".tsx")
    )
    if len(section_paths) < 3:
        return None
    return tuple(_v4_section_structure_signature(files[path]) for path in section_paths)


def _audit_v4_cross_route_sameness(
    *, routes: list[dict[str, Any]], files: dict[str, str]
) -> list[Diagnostic]:
    """Reject identical section-shell sequences across distinct v4 routes."""

    seen: dict[tuple[tuple[str, ...], ...], tuple[str, str]] = {}
    diagnostics: list[Diagnostic] = []
    for route in routes:
        route_id = str(route.get("route_id", ""))
        route_file = _route_source_path(route, semantic=True)
        route_prefix = f"{route_file.rsplit('/', 1)[0]}/"
        signature = _v4_route_section_signature(files=files, route_prefix=route_prefix)
        if signature is None:
            continue
        previous = seen.get(signature)
        if previous is not None:
            previous_route_id, previous_route_file = previous
            diagnostics.append(
                _diagnostic(
                    "SOURCE_CROSS_ROUTE_SAMENESS",
                    "Two or more v4 routes use an identical structural section sequence.",
                    file=route_file,
                    route_id=route_id,
                    symbol="section-shell-sequence",
                    expected=f"distinct from route {previous_route_id}",
                    observed=f"same structural signature as {previous_route_file}",
                )
            )
        else:
            seen[signature] = (route_id, route_file)
    return diagnostics


def _audit_v4_anti_slop(
    *,
    route_id: str,
    route_file: str,
    route_prefix: str,
    files: dict[str, str],
    visual_direction: dict[str, Any],
) -> list[Diagnostic]:
    signature = _v4_route_section_signature(files=files, route_prefix=route_prefix)
    if signature is None:
        return []
    section_sources = [
        files[path]
        for path in sorted(files)
        if path.startswith(f"{route_prefix}sections/") and path.endswith(".tsx")
    ]
    diagnostics: list[Diagnostic] = []
    signatures = list(signature)
    repeated = max((signatures.count(item) for item in signatures), default=0)
    if repeated >= 3:
        diagnostics.append(
            _diagnostic(
                "SOURCE_REPEATED_SECTION_SHELL",
                "Three or more v4 sections use an identical structural shell.",
                file=route_file,
                route_id=route_id,
            )
        )
    route_css = "\n".join(
        text
        for path, text in files.items()
        if path.startswith(route_prefix) and path.endswith(".css")
    ).casefold()
    direction_text = json.dumps(visual_direction, ensure_ascii=False).casefold()
    for token, pattern in (
        ("gradient", r"(?:linear|radial|conic)-gradient\("),
        ("glass", r"backdrop-filter\s*:|backdrop-blur"),
        ("pill", r"border-radius\s*:\s*(?:999|100%|50rem)"),
        ("blob", r"border-radius\s*:[^;]*(?:%[^;]*){2,}"),
    ):
        if len(re.findall(pattern, route_css, re.IGNORECASE)) >= 3 and token not in direction_text:
            diagnostics.append(
                _diagnostic(
                    "SOURCE_UNAUTHORIZED_EFFECT_REPETITION",
                    f"The route repeats an unauthorized {token} treatment across sections.",
                    file=route_file,
                    route_id=route_id,
                    symbol=token,
                )
            )
    centered = len(re.findall(r"text-align\s*:\s*center", route_css))
    if centered >= max(3, len(section_sources) - 1):
        diagnostics.append(
            _diagnostic(
                "SOURCE_UNIFORM_SECTION_CENTERING",
                "Most v4 sections use the same centered composition.",
                file=route_file,
                route_id=route_id,
            )
        )
    section_css = [
        text.casefold()
        for path, text in files.items()
        if path.startswith(f"{route_prefix}sections/") and path.endswith(".css")
    ]
    reveal_sections = sum(
        bool(
            re.search(
                r"opacity\s*:\s*0|"
                r"transform\s*:[^;]*translate[xy]?\(\s*(?!0(?:\.0+)?(?:[a-z%]+)?\s*\))",
                text,
            )
        )
        for text in section_css
    )
    if reveal_sections >= max(3, len(section_sources) - 1) and "blanket" not in direction_text:
        diagnostics.append(
            _diagnostic(
                "SOURCE_BLANKET_REVEAL_MOTION",
                "The route applies repeated fade or translate reveals across most sections.",
                file=route_file,
                route_id=route_id,
            )
        )
    return diagnostics
