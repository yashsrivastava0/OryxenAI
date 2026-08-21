"""Dependency-free structural audit for generated TypeScript/JSX source.

The generator deliberately does not depend on a parser package at runtime.  This
audit is therefore a conservative lexical pass over the small set of source
constructs that form the portfolio contract: local module edges, route shell
landmarks, section anchors, interaction markers, and exported shared systems.
It is supplemental to the build/typecheck gate, never a replacement for it.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, cast

from oryxenai.agents.code_generator.core.development_schemas import (
    Diagnostic,
    ExperienceBlueprintV3,
    ExperienceBlueprintV4,
    SitePlan,
)

_COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\r\n]*|<!--[\s\S]*?-->", re.DOTALL)
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
    return _COMMENT_RE.sub(" ", value)


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


def _route_source_path(route: dict[str, Any]) -> str:
    storage_key = str(route.get("storage_key", route.get("route_id", "")))
    storage_key = storage_key.replace("\\", "/").strip("/")
    if storage_key.startswith("routes/"):
        storage_key = storage_key.removeprefix("routes/")
    return f"src/routes/{storage_key}/index.tsx"


def _route_ids_in_source(route: dict[str, Any], source: str) -> str:
    route_id = str(route.get("route_id", ""))
    return route_id if route_id in source else ""


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
    route_css = {
        path: _without_comments(text)
        for path, text in files.items()
        if path.startswith("src/routes/") and path.endswith(".css")
    }
    if blueprint_v4:
        # V4 route code must use the trusted shell, not merely coexist with an
        # unused SharedSystems module in the candidate tree.
        for route in plan.routes:
            route_file = _route_source_path(route.model_dump(mode="json"))
            route_source = clean_files.get(route_file, "")
            if not re.search(r"\bRouteShell\b", route_source) or not re.search(
                r"import\s+\{[^}]*\bRouteShell\b[^}]*\}\s+from\s+[\"'](?:\.\.?/)+components/generated/SharedSystems",
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
        for export_name in ("RouteShell", "SectionAnchor", "useDisclosure", "Disclosure"):
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
        route_file = _route_source_path(route_data)
        route_storage_key = (
            str(route_data.get("storage_key", route_id)).replace("\\", "/").strip("/")
        )
        if route_storage_key.startswith("routes/"):
            route_storage_key = route_storage_key.removeprefix("routes/")
        route_prefix = f"src/routes/{route_storage_key}/"
        route_source = clean_files.get(route_file, "")
        if not route_source:
            continue
        route_source_with_shell = f"{shared}\n{route_source}"
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
        h1_count = len(re.findall(r"<h1\b", route_source_with_shell))
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

        for fragment in _FRAGMENT_RE.findall(route_source_with_shell):
            if not re.search(
                rf"(?<![\w-])id\s*=\s*[\"']{re.escape(fragment)}[\"']",
                route_source_with_shell,
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
        for section_id in route_sections:
            matches = list(
                re.finditer(
                    rf"data-content-id\s*=\s*[\"']{re.escape(section_id)}[\"']",
                    route_source,
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
            dom_id_matches = list(
                re.finditer(
                    rf"(?<![\w-])id\s*=\s*[\"']{re.escape(section_id)}[\"']",
                    route_source,
                )
            )
            if len(dom_id_matches) != 1:
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_SECTION_DOM_ID_MISSING",
                        "Each approved section must expose its compiler-supplied DOM ID exactly once.",
                        file=route_file,
                        route_id=route_id,
                        symbol=section_id,
                        expected="1",
                        observed=str(len(dom_id_matches)),
                    )
                )
            if matches:
                positions.append(matches[0].start())
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
            marker = f'data-distinctive-move-id="{move.move_id}"'
            route_files_source = "\n".join(
                value for path, value in clean_files.items() if path.startswith(route_prefix)
            )
            if marker not in route_files_source:
                diagnostics.append(
                    _diagnostic(
                        "SOURCE_BLUEPRINT_MOVE_UNUSED",
                        "A blueprint distinctive move has no traceable route implementation marker.",
                        file=route_file,
                        route_id=route_id,
                        symbol=move.move_id,
                    )
                )
            elif blueprint_v4:
                evidence = "\n".join(route_css.values()) + "\n" + route_files_source
                if not re.search(
                    r"(?:grid|flex|width|margin|padding|position|sticky|transform|gap|align-items|justify-content)",
                    evidence,
                    re.IGNORECASE,
                ):
                    diagnostics.append(
                        _diagnostic(
                            "SOURCE_BLUEPRINT_MOVE_MARKER_ONLY",
                            "A distinctive-move marker is present without executable layout or behavior evidence.",
                            file=route_file,
                            route_id=route_id,
                            symbol=move.move_id,
                        )
                    )

        if blueprint_v4:
            for beat in v4_blueprint.motion_beats:
                if beat.route_id != route_id:
                    continue
                route_files_source = "\n".join(
                    value for path, value in clean_files.items() if path.startswith(route_prefix)
                )
                marker_present = beat.target_marker in route_files_source
                motion_present = bool(
                    re.search(r"(?:transition|animation|transform)", route_files_source, re.I)
                )
                reduced_present = bool(
                    re.search(r"prefers-reduced-motion", "\n".join(route_css.values()), re.I)
                )
                if not marker_present or not motion_present:
                    diagnostics.append(
                        _diagnostic(
                            "SOURCE_MOTION_BEAT_UNIMPLEMENTED",
                            "Every v4 motion beat needs a target marker and executable source behavior.",
                            file=route_file,
                            route_id=route_id,
                            symbol=beat.motion_id,
                        )
                    )
                if not reduced_present:
                    diagnostics.append(
                        _diagnostic(
                            "SOURCE_MOTION_REDUCED_MOTION_MISSING",
                            "Every v4 motion beat needs a prefers-reduced-motion replacement.",
                            file=route_file,
                            route_id=route_id,
                            symbol=beat.motion_id,
                        )
                    )
            for assignment in v4_blueprint.interactions:
                if assignment.route_id != route_id:
                    continue
                route_files_source = "\n".join(
                    value for path, value in clean_files.items() if path.startswith(route_prefix)
                )
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

    return _dedupe(diagnostics)


def _dedupe(values: list[Diagnostic]) -> list[Diagnostic]:
    seen: set[str] = set()
    result: list[Diagnostic] = []
    for value in values:
        if value.fingerprint not in seen:
            seen.add(value.fingerprint)
            result.append(value)
    return result
