"""Deterministic materialization into a disposable build-context staging tree."""

from __future__ import annotations

import hashlib
import io
import json
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, cast

from PIL import Image

from oryxenai.agents.build_preparation.providers import (
    download_pexels,
    trigger_unsplash_download,
)
from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    FetchedResource,
    MaterializationResult,
    MaterializedFile,
    ResourceNeed,
    ResourceSelection,
    RouteScope,
)

DownloadImage = Callable[[FetchedResource], Awaitable[bytes]]
TriggerDownload = Callable[[FetchedResource], Awaitable[None]]

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


def _target_package_files(target: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
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
    lock = {
        "name": package["name"],
        "version": package["version"],
        "lockfileVersion": 3,
        "requires": True,
        "packages": {
            "": {
                "name": package["name"],
                "version": package["version"],
                "dependencies": package["dependencies"],
            }
        },
    }
    return package, lock


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
    download_image: DownloadImage | None = None,
    trigger_download: TriggerDownload | None = None,
    root_override: str | Path | None = None,
) -> MaterializationResult:
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
    }
    files.append(_write(root, "target/target-contract.json", _json_bytes(target), "text"))
    package, lock = _target_package_files(target)
    files.append(_write(root, "target/package.json", _json_bytes(package), "text"))
    files.append(_write(root, "target/package-lock.json", _json_bytes(lock), "text"))

    selected_ids: list[str] = []
    for route in routes:
        route_context = next(
            (item for item in context.routes if item.route_id == route.route_id), None
        )
        if route_context is None:
            continue
        route_name = _safe_name(route.route_id)
        files.append(
            _write(
                root,
                f"routes/{route_name}/brief.md",
                _route_brief_text(route_context).encode("utf-8"),
                "text",
            )
        )
        files.append(
            _write(
                root,
                f"routes/{route_name}/data.json",
                _json_bytes(_route_data(content_architect, route.route_id)),
                "text",
            )
        )
        route_selected: list[str] = []
        for need_id in [need.need_id for need in needs if route.route_id in need.route_ids]:
            selection = selection_by_need.get(need_id)
            if selection and selection.selected_resource_id:
                route_selected.append(selection.selected_resource_id)
                selected_ids.append(selection.selected_resource_id)
        route_selected = list(dict.fromkeys(route_selected))
        files.append(
            _write(
                root,
                f"routes/{route_name}/resources.json",
                _json_bytes({"route_id": route.route_id, "resource_ids": route_selected}),
                "text",
            )
        )

    resource_manifest: list[dict[str, Any]] = []
    icon_names: list[str] = []
    seen_selected: set[str] = set()
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
            "dependencies": candidate.dependencies,
            "license": candidate.license,
        }
        if candidate.kind == "photo" and candidate.provider == "pexels":
            try:
                downloader = download_image or (lambda item: download_pexels(item, settings))
                image_bytes = await downloader(candidate)
                try:
                    with Image.open(io.BytesIO(image_bytes)) as image:
                        image.verify()
                except Exception as exc:
                    raise ValueError("image bytes failed verification") from exc
                extension = "jpg"
                if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
                    extension = "png"
                image_path = f"resources/images/{resource_id}.{extension}"
                files.append(_write(root, image_path, image_bytes, "image"))
                metadata = {
                    "resource_id": resource_id,
                    "alt_text": candidate.title,
                    "focal_point": need.details.get("focal_point", "") if need else "",
                    "source": candidate.source_reference,
                    "photographer": candidate.photographer,
                    "photographer_url": candidate.photographer_url,
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
                base_entry.update({"local_path": image_path, "inspection_level": "pixel_inspected"})
            except Exception as exc:
                warnings.append(f"Could not materialize Pexels resource {resource_id}: {exc}")
                base_entry.update(
                    {"fallback": selection.fallback or (need.fallback if need else "")}
                )
        elif candidate.kind == "photo" and candidate.provider == "unsplash":
            try:
                tracker = trigger_download or (
                    lambda item: trigger_unsplash_download(item, settings)
                )
                await tracker(candidate)
            except Exception as exc:
                warnings.append(f"Unsplash tracking failed for {resource_id}: {exc}")
            metadata = {
                "resource_id": resource_id,
                "hotlink_url": candidate.hotlink_url,
                "source": candidate.source_reference,
                "photographer": candidate.photographer,
                "photographer_url": candidate.photographer_url,
                "attribution_url": candidate.attribution_url,
                "inspection_level": "metadata_only",
                "local_path": "",
            }
            files.append(
                _write(
                    root, f"resources/images/{resource_id}.json", _json_bytes(metadata), "metadata"
                )
            )
            base_entry.update(
                {"hotlink_url": candidate.hotlink_url, "inspection_level": "metadata_only"}
            )
        elif candidate.kind == "component":
            component_root = f"resources/components/{_safe_name(candidate.provider)}/{resource_id}"
            dependencies_allowed = set(candidate.dependencies).issubset(TARGET_ALLOWED_DEPENDENCIES)
            if not dependencies_allowed:
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
                for source_path, content in candidate.source_files.items():
                    relative = (
                        f"{component_root}/{_safe_name(source_path, 'source')}-"
                        f"{_safe_name(Path(source_path).stem, 'file')}{Path(source_path).suffix}"
                    )
                    files.append(_write(root, relative, content.encode("utf-8"), "text"))
                base_entry.update(
                    {
                        "dependencies_allowed": True,
                        "local_directory": component_root,
                        "disposition": "adaptable_source",
                    }
                )
        elif candidate.kind == "icon":
            icon_names.append(candidate.icon_name)
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
                "source_reference": entry.get("source_reference", ""),
            }
        )
    files.append(_write(root, "provenance/licenses.json", _json_bytes(licenses), "text"))
    manifest = {
        "phase": "phase3",
        "run_id": run_id,
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
        resources=resource_manifest,
    )
