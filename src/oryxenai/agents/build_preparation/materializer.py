"""Deterministic materialization into a disposable build-context staging tree."""

from __future__ import annotations

import hashlib
import io
import json
import re
from collections.abc import Awaitable, Callable
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, cast

from PIL import Image, ImageStat

from oryxenai.agents.build_preparation.contracts import (
    PACK_VERSION,
    compile_v3_projections,
    projection_hash,
    validate_execution_contract_shape,
)
from oryxenai.agents.build_preparation.execution import compile_execution_contract
from oryxenai.agents.build_preparation.providers import download_font
from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    FetchedResource,
    MaterializationResult,
    MaterializedFile,
    ResourceNeed,
    ResourceSelection,
    RouteScope,
)
from oryxenai.agents.shared.image_retrieval import intent_from_values, prepare_image_bytes

DownloadImage = Callable[[FetchedResource], Awaitable[bytes]]
TriggerDownload = Callable[[FetchedResource], Awaitable[None]]
DownloadFont = Callable[[FetchedResource], Awaitable[dict[str, bytes]]]

TARGET_ALLOWED_DEPENDENCIES = frozenset(
    {
        "react",
        "react-dom",
        "vite",
        "typescript",
        "@vitejs/plugin-react",
        "tailwindcss",
        "@tailwindcss/vite",
        "motion",
        "lucide-react",
        "clsx",
        "tailwind-merge",
        "class-variance-authority",
        "tw-animate-css",
        "@radix-ui/react-accordion",
        "@radix-ui/react-dialog",
        "@radix-ui/react-dropdown-menu",
        "@radix-ui/react-navigation-menu",
        "@radix-ui/react-separator",
        "@radix-ui/react-slot",
        "@radix-ui/react-tabs",
        "@radix-ui/react-tooltip",
        "@radix-ui/react-visually-hidden",
    }
)


def _dependency_name(value: str) -> str:
    dependency = value.strip()
    if dependency.startswith("@"):
        slash = dependency.find("/")
        version_at = dependency.find("@", slash + 1) if slash >= 0 else -1
        return dependency[:version_at] if version_at > 0 else dependency
    return dependency.split("@", 1)[0]


def dependencies_allowed(values: list[str]) -> bool:
    for value in values:
        dependency = value.strip()
        name = _dependency_name(dependency)
        if not name or name not in TARGET_ALLOWED_DEPENDENCIES:
            return False
        specifier = dependency[len(name) :].removeprefix("@").lower()
        if specifier and (
            any(
                token in specifier
                for token in ("npm:", "file:", "git+", "://", "workspace:", "link:")
            )
            or any(character.isspace() for character in specifier)
        ):
            return False
    return True


def _safe_name(value: str, fallback: str = "route") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return cleaned[:80] or fallback


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _write(root: Path, relative: str, content: bytes, kind: str) -> MaterializedFile:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return MaterializedFile(
        relative_path=relative.replace("\\", "/"),
        kind=kind,  # type: ignore[arg-type]
        size_bytes=len(content),
        sha256=_hash_bytes(content),
    )


_PRIVATE_MARKERS = {"private", "pending", "draft", "rejected", "internal", "confidential"}


def _public_value(value: Any) -> Any:
    """Keep only approved/public content in the prepared route data."""
    if isinstance(value, list):
        return [item for item in (_public_value(item) for item in value) if item is not None]
    if not isinstance(value, dict):
        return value
    status_values = [
        str(value.get(key, "") or "").strip().lower()
        for key in ("publication_status", "visibility", "status")
    ]
    if any(status in _PRIVATE_MARKERS for status in status_values if status):
        return None
    return {
        key: cleaned
        for key, item in value.items()
        if key not in {"internal_notes", "private_notes"}
        and (cleaned := _public_value(item)) is not None
    }


def _route_data(content: dict[str, Any], route_id: str) -> dict[str, Any]:
    packs = content.get("page_content_packs") or []
    pack = next(
        (
            item
            for item in packs
            if isinstance(item, dict) and str(item.get("route_id", "")) == route_id
        ),
        {},
    )
    return cast(
        dict[str, Any],
        _public_value(
            {
                "route_id": route_id,
                "sections": pack.get("sections", []) if isinstance(pack, dict) else [],
                "public_content_manifest": content.get("public_content_manifest", {}),
            }
        ),
    )


def _target_package_file(target: dict[str, Any]) -> dict[str, Any]:
    versions = {
        "react": "^19.0.0",
        "react-dom": "^19.0.0",
        "vite": "^7.0.0",
        "typescript": "^5.0.0",
        "@vitejs/plugin-react": "^5.0.0",
        "tailwindcss": "^4.0.0",
        "@tailwindcss/vite": "^4.0.0",
        "motion": "^12.0.0",
        "lucide-react": "^0.500.0",
        "clsx": "^2.1.1",
        "tailwind-merge": "^3.0.0",
        "class-variance-authority": "^0.7.1",
        "tw-animate-css": "^1.3.0",
    }
    package = {
        "name": "oryxenai-prepared-portfolio",
        "private": True,
        "version": "0.0.0",
        "type": "module",
        "scripts": {"build": "vite build", "typecheck": "tsc --noEmit"},
        "dependencies": {
            name: versions[name] for name in target["allowed_dependencies"] if name in versions
        },
    }
    return package


def _safe_component_source_path(value: str) -> str:
    raw = value.replace("\\", "/")
    if raw.startswith("/") or PureWindowsPath(value).drive:
        raise ValueError("component source path must be relative")
    normalized = raw.strip("/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError("component source path is unsafe")
    return path.as_posix()


def _meaningful_component_source(source_files: dict[str, str]) -> bool:
    """Reject wrappers/comments that only look like a component on disk.

    Registry source must contain executable UI structure, not an empty export,
    a single ``return null`` wrapper, or a prose/comment marker.  The checks
    are intentionally structural and provider-agnostic; relevance remains a
    separate quality decision.
    """
    combined = "\n".join(str(value or "") for value in source_files.values())
    normalized = re.sub(r"/\*.*?\*/|//[^\n]*|<!--[\s\S]*?-->", "", combined, flags=re.S)
    compact = re.sub(r"\s+", " ", normalized).strip()
    if len(compact) < 150 or "return null" in compact.replace(" ", "").casefold():
        return False
    has_export = bool(re.search(r"\bexport\s+(?:default\s+)?(?:function|const|class)\b", compact))
    markup_count = len(re.findall(r"</?[A-Za-z][^>]*>", compact))
    ui_signals = sum(
        token in compact.casefold()
        for token in ("classname", "aria-", "data-", "onclick", "onchange", "motion", "ref=")
    )
    return has_export and markup_count >= 2 and ui_signals >= 1


def _component_exports(source_files: dict[str, str]) -> list[str]:
    names: list[str] = []
    for source in source_files.values():
        names.extend(
            re.findall(
                r"\bexport\s+(?:default\s+)?(?:const|function|class|type|interface)\s+([A-Za-z_$][\w$]*)",
                source,
            )
        )
        for group in re.findall(r"\bexport\s*\{([^}]*)\}", source):
            names.extend(
                item.strip().split(" as ")[-1] for item in group.split(",") if item.strip()
            )
    return sorted({name for name in names if name})


def _later_fetch_providers(settings: Any, need: ResourceNeed) -> list[str]:
    if need.kind != "resource":
        return []
    category = f"{need.category} {need.purpose}".lower()
    if "icon" in category:
        return ["lucide"]
    if not bool(getattr(settings.resource_providers, "registries_enabled", True)):
        return []
    providers: list[str] = []
    for provider in getattr(settings.resource_providers, "registry_order", []):
        if provider == "shadcn" or bool(
            getattr(settings.resource_providers, f"{provider}_enabled", False)
        ):
            providers.append(str(provider))
    return list(dict.fromkeys(providers))


def _resource_plan(
    *,
    needs: list[ResourceNeed],
    selections: list[ResourceSelection],
    candidates: list[FetchedResource],
    materialized_resources: list[dict[str, Any]],
    settings: Any,
) -> dict[str, Any]:
    selection_by_need = {selection.need_id: selection for selection in selections}
    candidate_by_id = {candidate.resource_id: candidate for candidate in candidates}
    materialized_by_id = {
        str(entry.get("id", "")): entry for entry in materialized_resources if entry.get("id")
    }
    usable_dispositions = {"adaptable_source", "local_file", "package_import"}
    entries: list[dict[str, Any]] = []
    for need in needs:
        selection = selection_by_need.get(need.need_id)
        selected_id = selection.selected_resource_id if selection else None
        materialized = materialized_by_id.get(selected_id or "", {})
        candidate = candidate_by_id.get(selected_id or "")
        disposition = str(
            materialized.get(
                "disposition",
                "selected_not_materialized" if selected_id else "custom_fallback",
            )
        )
        selected_is_usable = disposition in usable_dispositions
        # v2 allowed known needs to escape upstream as a vague later-fetch
        # instruction.  v3 resolves each one into a local item, dependency
        # binding, typed recipe, or explicit execution gap instead.
        later_providers = [] if selected_is_usable else _later_fetch_providers(settings, need)
        entries.append(
            {
                "need_id": need.need_id,
                "source_id": need.source_id,
                "kind": need.kind,
                "category": need.category,
                "purpose": need.purpose,
                "importance": need.importance,
                "required_for_handoff": need.required_for_handoff,
                "route_ids": need.route_ids,
                "scene_ids": need.scene_ids,
                "source_status": need.source_status,
                "source_policy": need.source_policy,
                "disposition": disposition,
                "selected_resource_id": selected_id,
                "selected_provider": candidate.provider if candidate else "",
                "why_selected": selection.why_selected if selection else "",
                "adaptation_notes": selection.adaptation_notes if selection else "",
                "fallback": (
                    selection.fallback if selection and selection.fallback else need.fallback
                ),
                "legacy_provider_diagnostics": later_providers,
            }
        )
    return {
        "schema_version": "build-preparation-resource-ledger-v3",
        "pack_version": PACK_VERSION,
        "policy": {
            "runtime_network_fetch_allowed": False,
            "known_needs_require_execution_slot_coverage": True,
            "unlisted_resource_ids_are_forbidden": True,
        },
        "resource_decisions": entries,
    }


def _overview_text(context: BuildContextDraft) -> str:
    sections = [context.overview_markdown.strip()]
    if context.fixed_facts:
        sections.append(
            "## Fixed facts\n\n" + "\n".join(f"- {item}" for item in context.fixed_facts)
        )
    if context.freedoms:
        sections.append(
            "## Free to change\n\n" + "\n".join(f"- {item}" for item in context.freedoms)
        )
    if context.runtime_requirements:
        sections.append(
            "## Runtime requirements\n\n```json\n"
            + json.dumps(context.runtime_requirements, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n```"
        )
    return "\n\n".join(section for section in sections if section) + "\n"


def _route_brief_text(route_context: Any) -> str:
    sections = [route_context.brief_markdown.strip()]
    if route_context.acceptance_criteria:
        sections.append(
            "## Acceptance criteria\n\n"
            + "\n".join(f"- {item}" for item in route_context.acceptance_criteria)
        )
    if route_context.free_to_change:
        sections.append(
            "## Free to change\n\n"
            + "\n".join(f"- {item}" for item in route_context.free_to_change)
        )
    return "\n\n".join(section for section in sections if section) + "\n"


def _synthetic_visual_direction(routes: list[RouteScope]) -> dict[str, Any]:
    """Compatibility projection for direct materializer callers only.

    Live Build Preparation always supplies the approved VDD output.  This
    small fallback preserves the isolated materializer utility while keeping
    its synthetic origin obvious in the resulting projection.
    """
    return {
        "approved": {"visual_direction_hash": "materializer-compatibility-only"},
        "pages": [
            {
                "route_id": route.route_id,
                "path": route.path or "/",
                "publication_status": "approved",
                "compilable": True,
            }
            for route in routes
        ],
        "asset_briefs": [],
        "resource_candidates": [],
    }


async def materialize_build_context(
    *,
    output_dir: str | Path,
    run_id: str,
    routes: list[RouteScope],
    needs: list[ResourceNeed],
    selections: list[ResourceSelection],
    candidates: list[FetchedResource],
    context: BuildContextDraft,
    content_architect: dict[str, Any],
    settings: Any,
    visual_design_director: dict[str, Any] | None = None,
    legacy_route_layout: bool = False,
    download_image: DownloadImage | None = None,
    download_font_files: DownloadFont | None = None,
    trigger_download: TriggerDownload | None = None,
    root_override: str | Path | None = None,
) -> MaterializationResult:
    compatibility_mode = visual_design_director is None or (
        legacy_route_layout and not content_architect.get("route_plan")
    )
    legacy_content = content_architect
    if compatibility_mode:
        route_contexts = {item.route_id: item for item in context.routes}
        route_briefs = {
            route_id: route_context.brief_markdown
            for route_id, route_context in route_contexts.items()
        }
        compatibility_packs = []
        for route in routes:
            raw = _route_data(content_architect, route.route_id)
            sections = []
            for index, section in enumerate(raw.get("sections", []) or []):
                if isinstance(section, dict):
                    sections.append(
                        {
                            **section,
                            "section_id": str(
                                section.get("section_id")
                                or section.get("id")
                                or f"compatibility-{index}"
                            ),
                        }
                    )
            compatibility_packs.append({"route_id": route.route_id, "sections": sections})
        content_architect = {
            **content_architect,
            "approved": content_architect.get("approved")
            or {"content_hash": "materializer-compatibility-only"},
            "route_plan": content_architect.get("route_plan")
            or [
                {
                    "route_id": route.route_id,
                    "path": route.path or "/",
                    "title": route.title,
                    "publication_status": "approved",
                }
                for route in routes
            ],
            "page_content_packs": compatibility_packs
            or [
                {
                    "route_id": route.route_id,
                    "sections": [
                        {
                            "section_id": "compatibility",
                            "purpose": route_briefs.get(route.route_id, ""),
                            "content": {},
                        }
                    ],
                }
                for route in routes
            ],
        }
    root = (
        Path(root_override)
        if root_override is not None
        else Path(output_dir) / "build-preparation" / _safe_name(run_id, "run") / "build-context"
    )
    root.mkdir(parents=True, exist_ok=True)
    files: list[MaterializedFile] = []
    warnings: list[str] = []
    licenses: list[dict[str, Any]] = []
    candidate_by_id = {candidate.resource_id: candidate for candidate in candidates}
    selection_by_need = {selection.need_id: selection for selection in selections}
    need_by_id = {need.need_id: need for need in needs}

    files.append(_write(root, "overview.md", _overview_text(context).encode("utf-8"), "text"))
    target = {
        "target_id": settings.build_preparation.target_contract,
        "runtime": "static-client",
        "framework": "react",
        "language": "typescript",
        "bundler": "vite",
        "styling": "tailwind",
        "allowed_dependencies": sorted(TARGET_ALLOWED_DEPENDENCIES),
        "forbidden_runtime_capabilities": [
            "server-runtime",
            "remote-fonts",
            "remote-runtime-assets",
            "package-installation",
            "secret-environment-access",
        ],
        "dependency_resolution": {
            "allowed_dependency_set_is_ceiling": True,
            "code_generator_must_generate_lockfile": True,
            "installation_phase": "code_generation_build_only",
            "lockfile_included": False,
            "merge_selected_resource_dependencies": True,
            "package_manifest_is_starter": True,
            "runtime_installation_allowed": False,
        },
        "visual_resource_policy": {
            "image_target_count": settings.build_preparation.editorial_image_budget,
            "image_maximum": settings.build_preparation.editorial_image_maximum,
            "component_target_count": settings.build_preparation.visual_component_budget,
            "component_maximum": settings.build_preparation.visual_component_maximum,
            "require_real_local_material": settings.build_preparation.require_live_visual_resources,
            "generated_visuals_allowed": False,
        },
    }
    declared_policy = (visual_design_director or {}).get("resource_policy")
    if isinstance(declared_policy, dict):
        target["visual_resource_policy"] = {
            **target["visual_resource_policy"],
            **{
                key: declared_policy[key]
                for key in (
                    "image_target_count",
                    "image_maximum",
                    "component_target_count",
                    "component_maximum",
                    "require_real_local_material",
                )
                if key in declared_policy
            },
        }
    files.append(_write(root, "target/target-contract.json", _json_bytes(target), "text"))
    package = _target_package_file(target)
    files.append(_write(root, "target/package.json", _json_bytes(package), "text"))

    projections = compile_v3_projections(
        content_architect=content_architect,
        visual_design_director=(
            _synthetic_visual_direction(routes)
            if compatibility_mode
            else visual_design_director or _synthetic_visual_direction(routes)
        ),
        source_ref=(content_architect.get("_build_preparation_source_ref") or {}),
        target_contract=target,
        max_routes=int(settings.build_preparation.max_routes),
    )
    projection_hashes = {name: projection_hash(value) for name, value in projections.items()}
    files.append(_write(root, "site/contract.json", _json_bytes(projections["site"]), "text"))
    files.append(
        _write(root, "design/visual-direction.json", _json_bytes(projections["visual"]), "text")
    )
    files.append(
        _write(root, "provenance/approvals.json", _json_bytes(projections["approvals"]), "text")
    )
    files.append(
        _write(root, "provenance/targets.json", _json_bytes(projections["targets"]), "text")
    )
    contract_routes = {item["route_id"]: item for item in projections["site"]["routes"]}
    contract_content = {item["route_id"]: item for item in projections["site"]["public_content"]}

    selected_ids: list[str] = []
    for route in routes:
        route_context = next(
            (item for item in context.routes if item.route_id == route.route_id), None
        )
        if route_context is None:
            continue
        route_name = (
            _safe_name(route.route_id)
            if compatibility_mode
            else str(contract_routes[route.route_id]["storage_key"]).removeprefix("routes/")
        )
        files.append(
            _write(
                root,
                f"routes/{route_name}/brief.md",
                _route_brief_text(route_context).encode("utf-8"),
                "text",
            )
        )
        if legacy_route_layout:
            legacy_name = _safe_name(route.route_id)
            files.append(
                _write(
                    root,
                    f"routes/{legacy_name}/data.json",
                    _json_bytes(_route_data(content_architect, route.route_id)),
                    "text",
                )
            )
        files.append(
            _write(
                root,
                f"routes/{route_name}/data.json",
                _json_bytes(
                    _route_data(legacy_content, route.route_id)
                    if compatibility_mode
                    else {
                        "route_id": route.route_id,
                        "sections": contract_content[route.route_id]["sections"],
                        "public_content_manifest": projections["site"]["public_content_manifest"],
                    }
                ),
                "text",
            )
        )
        route_selected: list[str] = []
        route_need_ids = [need.need_id for need in needs if route.route_id in need.route_ids]
        for need_id in route_need_ids:
            selection = selection_by_need.get(need_id)
            if selection and selection.selected_resource_id:
                route_selected.append(selection.selected_resource_id)
                selected_ids.append(selection.selected_resource_id)
        route_selected = list(dict.fromkeys(route_selected))
        files.append(
            _write(
                root,
                f"routes/{route_name}/resources.json",
                _json_bytes(
                    {
                        "route_id": route.route_id,
                        "need_ids": route_need_ids,
                        "resource_ids": route_selected,
                    }
                ),
                "text",
            )
        )
        if legacy_route_layout:
            files.append(
                _write(
                    root,
                    f"routes/{_safe_name(route.route_id)}/resources.json",
                    _json_bytes(
                        {
                            "route_id": route.route_id,
                            "need_ids": route_need_ids,
                            "resource_ids": route_selected,
                        }
                    ),
                    "text",
                )
            )

    resource_manifest: list[dict[str, Any]] = []
    icon_names: list[str] = []
    seen_selected: set[str] = set()
    image_by_hash: dict[str, str] = {}
    for selection in selections:
        resource_id = selection.selected_resource_id
        if not resource_id or resource_id in seen_selected:
            continue
        seen_selected.add(resource_id)
        candidate = candidate_by_id.get(resource_id)
        if candidate is None:
            warnings.append(f"Selected resource {resource_id} was not returned by providers.")
            continue
        need = need_by_id.get(selection.need_id)
        base_entry: dict[str, Any] = {
            "id": resource_id,
            "need_id": selection.need_id,
            "kind": candidate.kind,
            "provider": candidate.provider,
            "provider_asset_id": candidate.provider_asset_id,
            "source_reference": candidate.source_reference,
            "why_selected": selection.why_selected,
            "fallback": selection.fallback or candidate.fallback,
            "dependencies": list(candidate.dependencies),
            "registry_dependencies": list(candidate.registry_dependencies),
            "source_version": candidate.source_version,
            "provider_receipt": dict(candidate.retrieval_metadata.get("provider_receipt", {})),
            "license": candidate.license,
            "license_reference": candidate.license_reference,
            "required_for_handoff": bool(need.required_for_handoff) if need else False,
            "placement": str(need.details.get("placement", "")) if need else "",
            "disposition": "selected_not_materialized",
            "usage_contract": {
                "route_ids": list(need.route_ids) if need else [],
                "scene_ids": list(need.scene_ids) if need else [],
                "section_ids": list(need.section_ids) if need else [],
                "placement": str(need.details.get("placement", "")) if need else "",
                "responsive_behavior": str(need.details.get("responsive_behavior", "") or "")
                if need
                else "",
                "alt_or_decorative_treatment": (
                    "decorative; use empty alt unless the final approved composition gives it meaning"
                    if candidate.kind == "photo"
                    else "preserve semantic labels and keyboard/focus behavior"
                ),
                "attribution": {
                    "source_reference": candidate.source_reference,
                    "attribution_url": candidate.attribution_url,
                    "license": candidate.license,
                    "license_reference": candidate.license_reference,
                },
                "dependencies": list(candidate.dependencies),
                "registry_dependencies": list(candidate.registry_dependencies),
                "source_version": candidate.source_version,
                "expected_exports": list(
                    need.component_intent.expected_exports
                    if need and need.component_intent
                    else candidate.retrieval_metadata.get("expected_exports", [])
                ),
                "reduced_motion_behavior": str(
                    need.details.get("reduced_motion_behavior", "") or "static equivalent"
                )
                if need
                else "static equivalent",
                "fallback": selection.fallback or (need.fallback if need else ""),
                "provider_receipt": dict(candidate.retrieval_metadata),
            },
        }
        if candidate.kind == "photo" and candidate.provider in {
            "pexels",
            "pixabay",
            "unsplash",
        }:
            try:
                if download_image is None:
                    raise ValueError(
                        "live provider download is required; offline image bytes are not admissible"
                    )
                downloader = download_image
                image_bytes = await downloader(candidate)
                details = need.details if need else {}
                intent = intent_from_values(
                    purpose=need.purpose if need else candidate.title,
                    subject=candidate.title or candidate.description,
                    style_mood=str(details.get("style_mood", "") or ""),
                    orientation=candidate.orientation,
                    aspect_ratio=str(details.get("aspect_ratio", "") or ""),
                    minimum_width=1200 if need and need.required_for_handoff else 0,
                    minimum_height=700 if need and need.required_for_handoff else 0,
                    queries=[candidate.title or candidate.description],
                )
                image_bytes, image_info = prepare_image_bytes(
                    image_bytes,
                    intent,
                    max_dimension=int(
                        getattr(
                            getattr(settings, "image_retrieval", None),
                            "max_dimension",
                            2400,
                        )
                    ),
                )
                try:
                    with Image.open(io.BytesIO(image_bytes)) as image:
                        image.load()
                        pixel_width, pixel_height = image.size
                        sample = image.convert("RGB").resize((64, 64))
                        colors = sample.getcolors(maxcolors=4096)
                        channel_spread = sum(ImageStat.Stat(sample).stddev)
                        if colors is None or len(colors) < 8 or channel_spread < 6.0:
                            raise ValueError("image pixels are flat or insufficiently varied")
                    if (
                        need
                        and need.required_for_handoff
                        and (pixel_width < 1200 or pixel_height < 700)
                    ):
                        raise ValueError("image dimensions are below the 1200x700 handoff minimum")
                except Exception as exc:
                    raise ValueError("image bytes failed verification") from exc
                extension = "jpg"
                if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
                    extension = "png"
                content_hash = str(image_info["sha256"])
                image_path = image_by_hash.get(content_hash, "")
                if not image_path:
                    image_path = f"resources/images/{resource_id}.{extension}"
                    files.append(_write(root, image_path, image_bytes, "image"))
                    image_by_hash[content_hash] = image_path
                metadata = {
                    "resource_id": resource_id,
                    "alt_text": candidate.title,
                    "focal_point": need.details.get("focal_point", "") if need else "",
                    "source": candidate.source_reference,
                    "photographer": candidate.photographer,
                    "photographer_url": candidate.photographer_url,
                    "attribution_url": candidate.attribution_url,
                    "license": candidate.license,
                    "license_reference": candidate.license_reference,
                    "placement": need.details.get("placement", "") if need else "",
                    "decorative": True,
                    "pixel_width": pixel_width,
                    "pixel_height": pixel_height,
                    "original_width": image_info["original_width"],
                    "original_height": image_info["original_height"],
                    "content_hash": content_hash,
                    "inspection_level": "pixel_inspected",
                    "local_path": image_path,
                }
                files.append(
                    _write(
                        root,
                        f"resources/images/{resource_id}.json",
                        _json_bytes(metadata),
                        "metadata",
                    )
                )
                base_entry.update(
                    {
                        "local_path": image_path,
                        "inspection_level": "pixel_inspected",
                        "pixel_width": pixel_width,
                        "pixel_height": pixel_height,
                        "attribution_url": candidate.attribution_url,
                        "disposition": "local_file",
                    }
                )
                base_entry["content_hash"] = content_hash
                base_entry["usage_contract"].update(
                    {"local_path": image_path, "sha256": content_hash}
                )
            except Exception as exc:
                warnings.append(
                    f"Could not materialize {candidate.provider} resource {resource_id}: {exc}"
                )
                base_entry.update(
                    {
                        "disposition": "custom_implementation_required",
                        "fallback": selection.fallback or (need.fallback if need else ""),
                    }
                )
        elif candidate.kind == "photo":
            warnings.append(
                f"Image {resource_id} uses provider '{candidate.provider}', which is not approved for local handoff."
            )
            base_entry.update({"disposition": "custom_implementation_required"})
        elif candidate.kind == "font" and candidate.provider == "fontsource":
            try:
                downloader = download_font_files or (lambda item: download_font(item, settings))
                font_files = await downloader(candidate)
                font_root = f"resources/fonts/{resource_id}"
                source_entries: list[dict[str, Any]] = []
                for variant, font_bytes in sorted(font_files.items()):
                    extension = str(
                        getattr(settings.resource_providers, "fontsource_format", "woff2")
                    )
                    font_path = f"{font_root}/{_safe_name(variant)}.{extension}"
                    item = _write(root, font_path, font_bytes, "font")
                    source_entries.append(
                        {"variant": variant, "local_path": font_path, "sha256": item.sha256}
                    )
                    files.append(item)
                if not source_entries:
                    raise ValueError("Fontsource returned no font files")
                files.append(
                    _write(
                        root,
                        f"{font_root}/font.json",
                        _json_bytes(
                            {
                                "resource_id": resource_id,
                                "family": candidate.font_family,
                                "weights": candidate.font_weights,
                                "license": candidate.license,
                                "license_reference": candidate.license_reference,
                                "files": source_entries,
                            }
                        ),
                        "metadata",
                    )
                )
                base_entry.update(
                    {
                        "font_family": candidate.font_family,
                        "font_weights": candidate.font_weights,
                        "local_directory": font_root,
                        "source_files": source_entries,
                        "disposition": "local_file",
                    }
                )
            except Exception as exc:
                warnings.append(f"Could not materialize Fontsource resource {resource_id}: {exc}")
                base_entry.update(
                    {
                        "font_family": candidate.font_family,
                        "font_weights": candidate.font_weights,
                        "disposition": "custom_implementation_required",
                    }
                )
        elif candidate.kind == "component":
            component_root = f"resources/components/{_safe_name(candidate.provider)}/{resource_id}"
            component_dependencies_allowed = dependencies_allowed(candidate.dependencies)
            if not component_dependencies_allowed:
                warnings.append(
                    f"Component {resource_id} has dependencies outside the target contract."
                )
                base_entry.update(
                    {
                        "dependencies_allowed": False,
                        "local_directory": "",
                        "disposition": "custom_implementation_required",
                    }
                )
            else:
                resolved_sources: list[tuple[str, str, str]] = []
                seen_paths: set[str] = set()
                try:
                    for source_path, content in candidate.source_files.items():
                        safe_source_path = _safe_component_source_path(source_path)
                        collision_key = safe_source_path.lower()
                        if collision_key in seen_paths:
                            raise ValueError("component source paths collide after extraction")
                        seen_paths.add(collision_key)
                        relative = f"{component_root}/source/{safe_source_path}"
                        resolved_sources.append((source_path, relative, content))
                except ValueError as exc:
                    warnings.append(f"Component {resource_id} has unsafe source paths: {exc}.")
                    base_entry.update(
                        {
                            "dependencies_allowed": True,
                            "local_directory": "",
                            "disposition": "custom_implementation_required",
                        }
                    )
                else:
                    source_map = {
                        source_path: content for source_path, _, content in resolved_sources
                    }
                    if not resolved_sources or not _meaningful_component_source(source_map):
                        warnings.append(
                            f"Component {resource_id} is empty or placeholder source and cannot be handed off."
                        )
                        base_entry.update(
                            {
                                "dependencies_allowed": True,
                                "local_directory": "",
                                "disposition": "custom_implementation_required",
                            }
                        )
                        resource_manifest.append(base_entry)
                        continue
                    source_entries: list[dict[str, Any]] = []
                    for source_path, relative, content in resolved_sources:
                        item = _write(root, relative, content.encode("utf-8"), "text")
                        files.append(item)
                        source_entries.append(
                            {
                                "original_path": source_path,
                                "local_path": relative,
                                "sha256": item.sha256,
                            }
                        )
                    base_entry.update(
                        {
                            "dependencies_allowed": True,
                            "local_directory": f"{component_root}/source",
                            "source_files": source_entries,
                            "disposition": "adaptable_source",
                            "release_pin": candidate.source_version,
                        }
                    )
                    source_hashes = [str(item.get("sha256", "")) for item in source_entries]
                    explicit_exports = [
                        str(item)
                        for item in (
                            need.component_intent.expected_exports
                            if need and need.component_intent
                            else candidate.retrieval_metadata.get("expected_exports", [])
                        )
                        if str(item).strip()
                    ]
                    export_names = explicit_exports or _component_exports(source_map)
                    base_entry["usage_contract"].update(
                        {
                            "local_directory": f"{component_root}/source",
                            "local_paths": [item["local_path"] for item in source_entries],
                            "expected_exports": export_names,
                            "export_name": export_names[0] if export_names else "",
                            "sha256": source_hashes,
                            "source_hashes": source_hashes,
                            "import_path": f"./{component_root}/source",
                        }
                    )
                    base_entry["expected_exports"] = export_names
        elif candidate.kind == "icon":
            icon_names.append(candidate.icon_name)
            base_entry.update(
                {
                    "disposition": "package_import",
                    "package_import": f"lucide-react:{candidate.icon_name}",
                }
            )
        resource_manifest.append(base_entry)
    if icon_names:
        files.append(
            _write(
                root,
                "resources/icons/icons.json",
                _json_bytes({"icons": sorted(set(icon_names)), "package": "lucide-react"}),
                "text",
            )
        )

    for entry in resource_manifest:
        licenses.append(
            {
                "resource_id": entry["id"],
                "provider": entry["provider"],
                "license": entry.get("license", ""),
                "license_reference": entry.get("license_reference", ""),
                "source_reference": entry.get("source_reference", ""),
            }
        )
    files.append(_write(root, "provenance/licenses.json", _json_bytes(licenses), "text"))
    # Direct utility callers without an approved VDD projection retain the
    # historical diagnostic plan name.  Production materialization writes the
    # v3 ledger and is the only form Code Generator can admit.
    resource_plan_path = "resources/plan.json" if compatibility_mode else "resources/ledger.json"
    ledger = _resource_plan(
        needs=needs,
        selections=selections,
        candidates=candidates,
        materialized_resources=resource_manifest,
        settings=settings,
    )
    if compatibility_mode:
        # Direct utility callers are diagnostic-only and keep the legacy
        # shape so their tests and old fixture review tooling remain useful.
        # This tree is emitted as phase3 and is never a v3 admission input.
        legacy_needs = ledger["resource_decisions"]
        for entry in legacy_needs:
            providers = list(entry.pop("legacy_provider_diagnostics", []))
            usable = entry.get("disposition") in {
                "adaptable_source",
                "local_file",
                "package_import",
            }
            entry["later_fetch"] = {
                "allowed": bool(providers) and not bool(entry.get("required_for_handoff")),
                "phase": "code_generation_only"
                if providers and not entry.get("required_for_handoff")
                else "not_allowed",
                "providers": providers,
                "must_replace_not_duplicate": True,
                "requirements": [] if usable else ["Diagnostic-only legacy fallback."],
            }
        ledger = {
            "schema_version": "build-preparation-resource-plan-v1",
            "policy": {
                "runtime_network_fetch_allowed": False,
                "selected_resource_and_fallback_are_exclusive": True,
                "unlisted_resource_ids_are_forbidden": True,
            },
            "needs": legacy_needs,
        }
    execution_contract, local_recipes, execution_slots, execution_gaps = compile_execution_contract(
        routes=routes,
        needs=needs,
        materialized_resources=resource_manifest,
        site=projections["site"],
        visual=projections["visual"],
        target=target,
    )
    slot_ids_by_route: dict[str, list[str]] = {}
    for slot in execution_slots:
        if slot.route_id:
            slot_ids_by_route.setdefault(slot.route_id, []).append(slot.resource_slot_id)
    for recipe in local_recipes:
        files.append(
            _write(root, recipe.local_path, _json_bytes(recipe.model_dump(mode="json")), "text")
        )
    recipe_manifest = {
        "schema_version": "build-preparation-recipe-manifest-v1",
        "pack_version": PACK_VERSION,
        "recipes": [recipe.model_dump(mode="json") for recipe in local_recipes],
    }
    files.append(
        _write(
            root,
            "resources/recipes/manifest.json",
            _json_bytes(recipe_manifest),
            "text",
        )
    )
    if not compatibility_mode:
        # Rewrite the canonical resource maps after deriving the final slot
        # inventory.  There are no legacy route aliases in a v3 tree.
        for route in routes:
            route_name = str(contract_routes[route.route_id]["storage_key"]).removeprefix("routes/")
            route_need_ids = [need.need_id for need in needs if route.route_id in need.route_ids]
            route_resource_ids = [
                str(resource.get("id", ""))
                for resource in resource_manifest
                if str(resource.get("need_id", "")) in route_need_ids
                and str(resource.get("id", ""))
            ]
            files.append(
                _write(
                    root,
                    f"routes/{route_name}/resources.json",
                    _json_bytes(
                        {
                            "route_id": route.route_id,
                            "need_ids": route_need_ids,
                            "resource_ids": sorted(set(route_resource_ids)),
                            "slot_ids": sorted(slot_ids_by_route.get(route.route_id, [])),
                        }
                    ),
                    "text",
                )
            )
        ledger["slots"] = [slot.model_dump(mode="json") for slot in execution_slots]
        ledger["execution_contract_path"] = "execution/contract.json"
    files.append(_write(root, resource_plan_path, _json_bytes(ledger), "text"))
    projection_hashes["ledger"] = projection_hash(ledger)
    projection_hashes["recipes"] = projection_hash(recipe_manifest)
    resource_projection = {
        "schema_version": projections["site"]["schema_version"],
        "pack_version": PACK_VERSION,
        "resources": resource_manifest,
        "resource_needs": [need.model_dump(mode="json") for need in needs],
    }
    projection_hashes["resources"] = projection_hash(resource_projection)
    files.append(
        _write(root, "resources/projection.json", _json_bytes(resource_projection), "text")
    )
    projection_hashes["execution"] = projection_hash(execution_contract)
    execution_contract_path = "execution/contract.json"
    if not compatibility_mode:
        validate_execution_contract_shape(
            execution=execution_contract,
            ledger=ledger,
            recipe_manifest=recipe_manifest,
            site=projections["site"],
            package_paths={item.relative_path for item in files} | {execution_contract_path},
            allowed_dependencies=set(target.get("allowed_dependencies", []) or []),
        )
    files.append(_write(root, execution_contract_path, _json_bytes(execution_contract), "text"))
    manifest = {
        "phase": "pack-v3" if not compatibility_mode else "diagnostic-phase3",
        "pack_version": PACK_VERSION,
        "run_id": run_id,
        "plan_path": resource_plan_path,
        "resources": resource_manifest,
        "files": [item.model_dump(mode="json") for item in files],
        "warnings": warnings,
    }
    files.append(_write(root, "resources/manifest.json", _json_bytes(manifest), "text"))
    relative_root = (
        str(root.relative_to(Path.cwd())) if root.is_relative_to(Path.cwd()) else str(root)
    )
    return MaterializationResult(
        root_path=str(root),
        relative_root=relative_root.replace("\\", "/"),
        files=files,
        resource_ids=list(dict.fromkeys(selected_ids)),
        warnings=warnings,
        licenses=licenses,
        manifest_path="resources/manifest.json",
        resource_plan_path=resource_plan_path,
        resources=resource_manifest,
        pack_version=PACK_VERSION if not compatibility_mode else "phase3",
        projection_hashes=projection_hashes,
        execution_slots=execution_slots,
        local_recipes=local_recipes,
        execution_gaps=execution_gaps,
        execution_contract_path=execution_contract_path,
        resource_ledger_path=(resource_plan_path if not compatibility_mode else ""),
    )


def materialize_handoff_report(
    root: Path,
    materialization: MaterializationResult,
    report: dict[str, Any],
) -> MaterializationResult:
    """Write the Code Generator admission decision into the staged tree."""
    relative = "handoff-report.json"
    item = _write(root, relative, _json_bytes(report), "metadata")
    analysis = report.get("run_analysis")
    analysis_item: MaterializedFile | None = None
    analysis_hash = ""
    if isinstance(analysis, dict):
        analysis_bytes = _json_bytes(analysis)
        analysis_hash = _hash_bytes(analysis_bytes)
        analysis_item = _write(root, "handoff-analysis.json", analysis_bytes, "metadata")
    return materialization.model_copy(
        update={
            "files": [
                *materialization.files,
                item,
                *([analysis_item] if analysis_item is not None else []),
            ],
            "handoff_report_path": relative,
            "analysis_path": "handoff-analysis.json" if analysis_item is not None else "",
            "analysis_hash": analysis_hash,
        }
    )
