"""Deterministic generated-source manifests and pack projection materialization."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

from oryxenai.agents.code_generator.core.development_schemas import ExperienceBlueprintV4
from oryxenai.agents.code_generator.core.path_policy import semantic_segment
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace
from oryxenai.agents.shared.image_retrieval import generate_responsive_renditions


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def materialize_trusted_manifests(
    workspace: GenerationWorkspace,
    projections: dict[str, dict[str, Any]],
    plan: Any,
    acquisition_ledger: dict[str, Any] | None = None,
    acquisition_materials_root: Path | None = None,
    settings: Any | None = None,
) -> dict[str, Any]:
    site = projections["site/contract.json"]
    visual = projections["design/visual-direction.json"]
    target = projections["provenance/targets.json"].get("target", {})
    execution = projections["execution/contract.json"]
    copied_resources = workspace.materialize_pack_resources()
    acquired_resources = (
        workspace.materialize_acquisition_resources(acquisition_ledger, acquisition_materials_root)
        if acquisition_ledger is not None and acquisition_materials_root is not None
        else []
    )
    image_assets = _materialize_image_assets(
        workspace,
        execution=execution,
        copied_resources=copied_resources,
        acquired_resources=acquired_resources,
        plan=plan,
        settings=settings,
    )
    route_entries = []
    for route in site.get("routes", []):
        if not isinstance(route, dict):
            continue
        route_id = str(route.get("route_id", ""))
        storage_key = _route_storage_key(
            str(route.get("storage_key") or route_id),
            semantic=isinstance(getattr(plan, "experience_blueprint", None), ExperienceBlueprintV4),
        )
        route_entries.append(
            {
                "route_id": route_id,
                "path": str(route.get("path", "")),
                "storage_key": storage_key,
                "title": str(route.get("title", route_id)),
                "purpose": str(route.get("purpose", "")),
                "component_path": f"../routes/{storage_key}/index",
            }
        )

    public_data = {
        "site": site,
        "visual_direction": visual,
        "target": target,
    }
    content_manifest = {
        "routes": site.get("routes", []),
        "public_content": site.get("public_content", []),
        "public_content_manifest": site.get("public_content_manifest", {}),
    }
    resource_manifest = {
        "pack_resources": copied_resources,
        "pack_bindings": [
            {
                "path": path,
                "usage": "module" if path.startswith("src/generated/resources/") else "url",
                "reference": (path.removeprefix("public/") if path.startswith("public/") else path),
            }
            for path in copied_resources
        ],
        "acquired_resources": acquired_resources,
        "image_assets": image_assets,
        "execution_slots": execution.get("slots", []),
        "resource_ledger": projections["resources/ledger.json"],
    }
    interaction_map = {
        "interactions": _json_values(getattr(plan, "interactions", []) or []),
    }
    acceptance_map = {
        "criteria": site.get("criteria", []),
        "coverage": _json_values(getattr(plan, "acceptance_coverage", []) or []),
    }
    _write_ts(workspace.repo_dir / "src/content/public-data.ts", "PUBLIC_SITE", public_data)
    _write_ts(
        workspace.repo_dir / "src/generated/content-manifest.ts",
        "CONTENT_MANIFEST",
        content_manifest,
    )
    _write_ts(
        workspace.repo_dir / "src/generated/resource-manifest.ts",
        "RESOURCE_MANIFEST",
        resource_manifest,
    )
    _write_ts(
        workspace.repo_dir / "src/generated/interaction-map.ts", "INTERACTION_MAP", interaction_map
    )
    _write_ts(
        workspace.repo_dir / "src/generated/acceptance-map.ts", "ACCEPTANCE_MAP", acceptance_map
    )
    _write_ts(
        workspace.repo_dir / "src/generated/contract-meta.ts",
        "CONTRACT_META",
        {
            "pipeline_contract_version": (
                "code-generator-v4"
                if isinstance(getattr(plan, "experience_blueprint", None), ExperienceBlueprintV4)
                else "code-generator-v3"
            )
        },
    )
    _write_route_registry(workspace, route_entries)

    for route in route_entries:
        route_dir = workspace.repo_dir / "src" / "routes" / route["storage_key"]
        route_dir.mkdir(parents=True, exist_ok=True)
        route_file = route_dir / "index.tsx"
        if not route_file.exists():
            route_file.write_text(
                _default_route_component(route["route_id"], route["title"]),
                encoding="utf-8",
                newline="\n",
            )
        css_file = route_dir / "route.css"
        if not css_file.exists():
            css_file.write_text(".route-page { display: grid; gap: 1.5rem; }\n", encoding="utf-8")

    manifest = build_source_manifest(workspace.repo_dir)
    manifest_hash = digest(manifest)
    manifest_path = workspace.ledger_dir / "source-manifest.json"
    workspace.write_json(manifest_path, {"files": manifest, "manifest_hash": manifest_hash})
    return {"files": manifest, "manifest_hash": manifest_hash, "resource_paths": copied_resources}


def _materialize_image_assets(
    workspace: GenerationWorkspace,
    *,
    execution: dict[str, Any],
    copied_resources: list[str],
    acquired_resources: list[dict[str, Any]],
    plan: Any,
    settings: Any | None,
) -> list[dict[str, Any]]:
    placement_by_slot: dict[str, Any] = {}
    blueprint = getattr(plan, "experience_blueprint", None)
    if isinstance(blueprint, ExperienceBlueprintV4):
        placement_by_slot = {item.resource_slot_id: item for item in blueprint.resource_placements}
    assets: list[dict[str, Any]] = []
    copied = set(copied_resources)
    for slot in execution.get("slots", []) if isinstance(execution, dict) else []:
        if not isinstance(slot, dict):
            continue
        category = str(slot.get("category", "")).casefold()
        if not any(token in category for token in ("image", "photo", "illustration", "texture")):
            continue
        slot_id = str(slot.get("resource_slot_id", ""))
        resolution = slot.get("resolution", {})
        local_paths = resolution.get("local_paths", []) if isinstance(resolution, dict) else []
        sources: list[dict[str, Any]] = []
        for value in local_paths:
            normalized = str(value).replace("\\", "/").lstrip("/")
            public_path = (
                f"public/resources/pack/{normalized.removeprefix('resources/')}"
                if normalized.startswith("resources/")
                else normalized
            )
            if public_path not in copied:
                continue
            source = workspace.repo_dir / public_path
            sources.extend(
                _pack_image_renditions(
                    workspace,
                    slot_id=slot_id,
                    source=source,
                    settings=settings,
                )
            )
        if sources:
            assets.append(
                _image_asset(
                    slot_id,
                    str(slot.get("route_id", "")),
                    [str(item) for item in slot.get("section_ids", [])],
                    sources,
                    placement_by_slot.get(slot_id),
                )
            )
    acquired_by_id: dict[str, list[dict[str, Any]]] = {}
    slot_ids = {
        str(item.get("resource_slot_id", ""))
        for item in execution.get("slots", [])
        if isinstance(item, dict)
    }
    for item in acquired_resources:
        if str(item.get("category", "")).casefold() not in {"image", "texture", "illustration"}:
            continue
        request_id = str(item.get("request_id", ""))
        possible_slot = request_id.removeprefix("request-")
        resource_id = possible_slot if possible_slot in slot_ids else request_id
        acquired_by_id.setdefault(resource_id, []).append(item)
    for resource_id, entries in acquired_by_id.items():
        placement = entries[0].get("placement", {})
        acquired_sources: list[dict[str, Any]] = []
        if len(entries) == 1:
            # A single acquired original still needs the same responsive
            # contract as a pack image. Generate local renditions from the
            # receipt-bound bytes; never ask the browser to resize a remote
            # URL or to fetch a provider asset at runtime.
            source_path = workspace.repo_dir / str(entries[0].get("local_path", ""))
            generated = _pack_image_renditions(
                workspace,
                slot_id=resource_id,
                source=source_path,
                settings=settings,
            )
            if generated:
                acquired_sources.extend(generated)
        if not acquired_sources:
            acquired_sources = [
                {
                    "path": str(item.get("local_path", "")).removeprefix("public/"),
                    "width": int(item.get("inspection", {}).get("pixel_width", 0) or 0),
                    "height": int(item.get("inspection", {}).get("pixel_height", 0) or 0),
                    "format": str(item.get("inspection", {}).get("rendition_format", "")),
                    "media_type": str(item.get("media_type", "")),
                    "sha256": str(item.get("sha256", "")),
                }
                for item in entries
                if int(item.get("inspection", {}).get("pixel_width", 0) or 0) > 0
            ]
        if acquired_sources:
            assets.append(
                _image_asset(
                    resource_id,
                    str(placement.get("route_id", "")),
                    [str(placement.get("section_id", ""))] if placement.get("section_id") else [],
                    acquired_sources,
                    placement_by_slot.get(resource_id),
                )
            )
    return sorted(assets, key=lambda item: item["resource_id"])


def _pack_image_renditions(
    workspace: GenerationWorkspace,
    *,
    slot_id: str,
    source: Path,
    settings: Any | None,
) -> list[dict[str, Any]]:
    if not source.is_file():
        return []
    data = source.read_bytes()
    image_config = getattr(settings, "image_retrieval", None) if settings is not None else None
    widths = list(getattr(image_config, "responsive_widths", []))
    formats = list(getattr(image_config, "responsive_formats", []))
    if not widths or not formats:
        try:
            with Image.open(source) as image:
                width, height = image.size
                image_format = str(image.format or source.suffix.lstrip(".")).casefold()
        except Exception:
            return []
        return [
            {
                "path": source.relative_to(workspace.repo_dir).as_posix().removeprefix("public/"),
                "width": width,
                "height": height,
                "format": image_format,
                "media_type": f"image/{'jpeg' if image_format in {'jpg', 'jpeg'} else image_format}",
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        ]
    renditions = generate_responsive_renditions(
        data,
        widths=widths,
        formats=formats,
        quality=int(getattr(image_config, "responsive_quality", 84)),
    )
    target_root = (
        workspace.repo_dir / "public" / "resources" / "renditions" / semantic_segment(slot_id)
    )
    target_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for payload, metadata in renditions:
        digest_value = hashlib.sha256(payload).hexdigest()
        image_format = str(metadata["rendition_format"])
        suffix = "jpg" if image_format == "jpeg" else image_format
        target = target_root / f"{digest_value}-{metadata['pixel_width']}w.{suffix}"
        target.write_bytes(payload)
        results.append(
            {
                "path": target.relative_to(workspace.repo_dir).as_posix().removeprefix("public/"),
                "width": int(metadata["pixel_width"]),
                "height": int(metadata["pixel_height"]),
                "format": image_format,
                "media_type": str(metadata["media_type"]),
                "sha256": digest_value,
            }
        )
    return results


def _image_asset(
    resource_id: str,
    route_id: str,
    section_ids: list[str],
    sources: list[dict[str, Any]],
    placement: Any | None,
) -> dict[str, Any]:
    ordered = sorted(sources, key=lambda item: (item["format"], item["width"]))
    largest = max(ordered, key=lambda item: int(item["width"]))
    return {
        "resource_id": resource_id,
        "route_id": route_id,
        "section_ids": section_ids,
        "alt_policy": str(getattr(placement, "alt_policy", "contextual_description")),
        "loading": str(getattr(placement, "loading", "lazy")),
        "sizes": str(getattr(placement, "sizes", "100vw")),
        "fit": str(getattr(placement, "fit", "cover")),
        "focal_position": str(getattr(placement, "focal_position", "center")),
        "width": int(largest["width"]),
        "height": int(largest["height"]),
        "sources": ordered,
    }


def build_source_manifest(repo_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(repo_dir.rglob("*")):
        if not path.is_file() or any(part in {"node_modules", "dist"} for part in path.parts):
            continue
        relative = path.relative_to(repo_dir).as_posix()
        data = path.read_bytes()
        entries.append(
            {
                "path": relative,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return entries


def _write_ts(path: Path, export_name: str, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    path.write_text(f"export const {export_name} = {serialized} as const;\n", encoding="utf-8")


def _json_values(values: list[Any]) -> list[Any]:
    """Convert typed plan contracts to the JSON written into generated manifests."""

    return [
        value.model_dump(mode="json") if hasattr(value, "model_dump") else value for value in values
    ]


def _write_route_registry(workspace: GenerationWorkspace, routes: list[dict[str, str]]) -> None:
    lines = [
        'import type { ComponentType } from "react";',
        "",
    ]
    for index, route in enumerate(routes):
        lines.append(f'import Route{index} from "{route["component_path"]}";')
    lines.extend(["", "export const ROUTES = ["])
    for index, route in enumerate(routes):
        lines.append(
            f"  {{ routeId: {json.dumps(route['route_id'])}, path: {json.dumps(route['path'])}, title: {json.dumps(route['title'])}, component: Route{index} }},"
        )
    lines.extend(
        [
            "] as const satisfies readonly { routeId: string; path: string; title: string; component: ComponentType }[];",
            "",
        ]
    )
    path = workspace.repo_dir / "src/generated/route-registry.ts"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def _route_storage_key(value: str, *, semantic: bool = False) -> str:
    normalized = value.replace("\\", "/").strip("/")
    if normalized.startswith("routes/"):
        normalized = normalized.removeprefix("routes/")
    normalized = normalized or "route"
    return semantic_segment(normalized) if semantic else normalized


def _default_route_component(route_id: str, title: str) -> str:
    safe_title = json.dumps(title, ensure_ascii=False)
    return (
        'import "./route.css";\n\n'
        f"export default function RoutePage() {{\n"
        f'  return <main className="route-page" data-route-id={json.dumps(route_id)}>\n'
        f"    <h1>{{{safe_title}}}</h1>\n"
        "  </main>;\n"
        "}\n"
    )
