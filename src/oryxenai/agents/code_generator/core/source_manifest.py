"""Deterministic generated-source manifests and pack projection materialization."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace


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
    route_entries = []
    for route in site.get("routes", []):
        if not isinstance(route, dict):
            continue
        route_id = str(route.get("route_id", ""))
        storage_key = _route_storage_key(str(route.get("storage_key", route_id)))
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
        "acquired_resources": acquired_resources,
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


def _route_storage_key(value: str) -> str:
    normalized = value.replace("\\", "/").strip("/")
    if normalized.startswith("routes/"):
        normalized = normalized.removeprefix("routes/")
    return normalized or "route"


def _default_route_component(route_id: str, title: str) -> str:
    safe_title = json.dumps(title, ensure_ascii=False)
    return (
        'import "./route.css";\n\n'
        f"export default function RoutePage() {{\n"
        f'  return <main className="route-page" data-route-id={json.dumps(route_id)}>\n'
        f"    <h1>{safe_title}</h1>\n"
        "  </main>;\n"
        "}\n"
    )
