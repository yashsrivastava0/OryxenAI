"""Local resource catalogue and deterministic fallback resolver.

The checked-in VDD catalogue is conceptual, so this module intentionally
does not pretend those IDs are source files. It emits verified local/system
resources and explicit custom implementation opportunities.
"""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path

from oryxenai.build_preparation.fingerprints import sha256_json
from oryxenai.build_preparation.providers import (
    PexelsClient,
    ProviderUnavailable,
    ShadcnRegistryProvider,
    choose_photo,
    registry_entry,
)
from oryxenai.build_preparation.schemas import (
    ResourceManifest,
    ResourceManifestEntry,
    ResourceRequirement,
)


class ResourceResolutionError(ValueError):
    pass


def deduplicate_entries(
    entries: list[ResourceManifestEntry],
) -> tuple[list[ResourceManifestEntry], dict[str, str]]:
    """Merge repeated materialized resources while preserving all usages."""
    merged: dict[str, ResourceManifestEntry] = {}
    aliases: dict[str, str] = {}
    for entry in entries:
        key = (
            f"{entry.provider}:{entry.provider_asset_id}:{entry.content_hash}"
            if entry.provider and entry.provider_asset_id and entry.content_hash
            else entry.manifest_resource_id
        )
        existing = merged.get(key)
        if existing is None:
            merged[key] = entry.model_copy(deep=True)
            continue
        aliases[entry.manifest_resource_id] = existing.manifest_resource_id
        existing.requirement_ids = sorted(
            set(existing.requirement_ids).union(entry.requirement_ids)
        )
        existing.usages.extend(usage for usage in entry.usages if usage not in existing.usages)
        existing.warnings.extend(entry.warnings)
    return list(merged.values()), aliases


def catalogue_hash() -> str:
    path = (
        Path(__file__).resolve().parents[1]
        / "agents"
        / "visual_design_director"
        / "resources"
        / "catalogue.json"
    )
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "missing"


def _is_external_photo(requirement: ResourceRequirement) -> bool:
    constraints = requirement.constraints
    return requirement.kind in {"image", "photo"} and (
        str(constraints.get("source_policy", "")) == "optional_external_acquisition"
        or str(constraints.get("source_status", "")) == "needs_acquisition"
    )


def resolve_local_requirements(
    requirements: list[ResourceRequirement],
    *,
    pexels_available: bool = False,
) -> ResourceManifest:
    """Create a manifest for deterministic local/fallback decisions.

    Registry and Pexels adapters may replace entries later. This baseline is
    deliberately useful without network credentials and never fabricates a
    concrete remote resource.
    """
    entries: list[ResourceManifestEntry] = []
    warnings: list[str] = []
    for req in requirements:
        resource_id = f"resource-{req.requirement_id}"
        if _is_external_photo(req) and not pexels_available:
            disposition = "fallback_selected"
            reason = "external photography is unavailable without PEXELS_API_KEY"
            warnings.append(f"{req.requirement_id}: {reason}")
        elif req.kind in {"image", "photo", "visual_asset"}:
            disposition = "custom_implementation_required"
            reason = "no verified local asset locator exists"
            warnings.append(
                f"{req.requirement_id}: use the approved visual fallback or custom implementation"
            )
        elif req.kind in {"icon", "icons"}:
            disposition = "materialized"
            reason = "fixed target icon package is available without a network lookup"
            entries.append(
                ResourceManifestEntry(
                    manifest_resource_id="target-lucide-icons",
                    requirement_ids=[req.requirement_id],
                    usages=[
                        {"scope": req.scope, "route_id": req.route_id, "scene_id": req.scene_id}
                    ],
                    disposition=disposition,
                    provider="target",
                    provider_asset_id="lucide-react",
                    source_reference="target-contract:react-vite-v1",
                    dependencies=["lucide-react"],
                    dependencies_allowed=True,
                    reason=reason,
                    provenance={"source": "fixed-target-dependency"},
                    fallback=req.fallback,
                )
            )
            continue
        elif req.kind in {"font", "fonts", "typography"}:
            disposition = "materialized"
            reason = "system font stack requires no runtime network request"
            entries.append(
                ResourceManifestEntry(
                    manifest_resource_id="builtin-system-font-stack",
                    requirement_ids=[req.requirement_id],
                    usages=[
                        {"scope": req.scope, "route_id": req.route_id, "scene_id": req.scene_id}
                    ],
                    disposition=disposition,
                    provider="builtin",
                    provider_asset_id="system-font-stack",
                    source_reference="css-system-font-stack",
                    dependencies_allowed=True,
                    reason=reason,
                    provenance={
                        "font_stack": req.constraints.get(
                            "fallback_stack",
                            "ui-sans-serif, system-ui, sans-serif",
                        )
                    },
                    fallback=req.fallback,
                )
            )
            continue
        elif req.kind in {"component_or_effect", "component", "motion", "background"}:
            disposition = "custom_implementation_required"
            reason = (
                "the current local catalogue is conceptual and no source candidate was materialized"
            )
            warnings.append(
                f"{req.requirement_id}: registry lookup did not produce a verified source"
            )
        else:
            disposition = "custom_implementation_required"
            reason = "no verified local resource is available"
            warnings.append(f"{req.requirement_id}: no verified resource is available")
        entries.append(
            ResourceManifestEntry(
                manifest_resource_id=resource_id,
                requirement_ids=[req.requirement_id],
                usages=[{"scope": req.scope, "route_id": req.route_id, "scene_id": req.scene_id}],
                disposition=disposition,
                reason=reason,
                fallback=req.fallback
                or "preserve the approved intent with a static/custom implementation",
                responsive_concerns=[str(req.constraints.get("mobile_treatment", ""))]
                if req.constraints.get("mobile_treatment")
                else [],
                reduced_motion_concerns=["use a static fallback"]
                if req.kind in {"motion", "component_or_effect"}
                else [],
                provenance={
                    "source": "deterministic-fallback-resolver",
                    "catalogue_hash": catalogue_hash(),
                },
            )
        )
    manifest = ResourceManifest(catalogue_hash=catalogue_hash(), entries=entries, warnings=warnings)
    manifest.manifest_hash = sha256_json(
        manifest.model_dump(mode="json", exclude={"manifest_hash"})
    )
    return manifest


async def resolve_remote_requirements(
    requirements: list[ResourceRequirement],
    *,
    settings: object,
    target_contract: dict[str, object],
    registry_providers: list[ShadcnRegistryProvider] | None = None,
    pexels_client: PexelsClient | None = None,
) -> tuple[list[ResourceManifestEntry], dict[str, bytes], list[str]]:
    """Resolve optional registry/Pexels requirements.

    Provider failures are warnings; the caller retains deterministic fallback
    entries so one unavailable provider never blocks a valid portfolio.
    """
    provider_config = settings.resource_providers  # type: ignore[attr-defined]
    build_config = settings.build_preparation  # type: ignore[attr-defined]
    timeout_seconds = float(getattr(build_config, "network_timeout_seconds", 15.0))
    retry_count = int(getattr(build_config, "network_retry_count", 2))
    raw_allowlist = target_contract.get("allowed_dependencies", [])
    allowed_dependencies = (
        {value for value in raw_allowlist if isinstance(value, str)}
        if isinstance(raw_allowlist, list)
        else set()
    )
    entries: list[ResourceManifestEntry] = []
    files: dict[str, bytes] = {}
    warnings: list[str] = []
    providers = registry_providers or [
        ShadcnRegistryProvider(
            provider="shadcn",
            catalog_url=provider_config.shadcn_catalog_url,
            item_url_template=provider_config.shadcn_item_url_template,
            enabled=provider_config.registries_enabled,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
        ),
        ShadcnRegistryProvider(
            provider="magicui",
            catalog_url=provider_config.magicui_catalog_url,
            item_url_template=provider_config.magicui_item_url_template,
            enabled=provider_config.registries_enabled and provider_config.magicui_enabled,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
        ),
        ShadcnRegistryProvider(
            provider="aceternity",
            catalog_url=provider_config.aceternity_catalog_url,
            item_url_template=provider_config.aceternity_item_url_template,
            enabled=provider_config.registries_enabled and provider_config.aceternity_enabled,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
        ),
    ]
    pexels = pexels_client or PexelsClient(
        os.environ.get("PEXELS_API_KEY", "").strip(),
        timeout_seconds=timeout_seconds,
        retry_count=retry_count,
    )
    for requirement in requirements:
        if requirement.kind in {"component_or_effect", "component", "motion", "background"}:
            for provider in providers:
                try:
                    matches = await provider.search(requirement.intent, limit=4)
                    if not matches:
                        continue
                    resolved = await provider.fetch(str(matches[0].get("name", "")))
                    total = sum(len(value) for value in resolved.files.values())
                    manifest_id = f"registry-{resolved.provider}-{resolved.item_id}"
                    base_path = f"resources/components/{manifest_id}"
                    entry = registry_entry(
                        resolved,
                        requirement,
                        pack_path=f"{base_path}/",
                        content_hash=hashlib.sha256(b"".join(resolved.files.values())).hexdigest(),
                        size_bytes=total,
                        allowed_dependencies=allowed_dependencies,
                    )
                    entry.provenance["target_contract"] = str(target_contract.get("target_id", ""))
                    if entry.disposition == "materialized":
                        for relative, data in resolved.files.items():
                            files[f"{base_path}/{relative}"] = data
                    else:
                        entry.pack_path = ""
                    entries.append(entry)
                    break
                except ProviderUnavailable as exc:
                    warnings.append(f"{provider.provider}: {exc}")
            continue

        if requirement.kind not in {"image", "photo"} or not _is_external_photo(requirement):
            continue
        if not pexels.api_key:
            warnings.append(f"{requirement.requirement_id}: Pexels credential is not configured")
            continue
        try:
            photo = choose_photo(await pexels.search(requirement), requirement)
            if photo is None:
                warnings.append(f"{requirement.requirement_id}: Pexels returned no suitable image")
                continue
            data = await pexels.download(photo)
            _verify_image(data)
            manifest_id = f"pexels-{photo.photo_id}"
            pack_path = f"resources/images/{manifest_id}.jpg"
            files[pack_path] = data
            entries.append(
                ResourceManifestEntry(
                    manifest_resource_id=manifest_id,
                    requirement_ids=[requirement.requirement_id],
                    usages=[
                        {
                            "scope": requirement.scope,
                            "route_id": requirement.route_id,
                            "scene_id": requirement.scene_id,
                        }
                    ],
                    disposition="materialized",
                    provider="pexels",
                    provider_asset_id=photo.photo_id,
                    source_reference=photo.source_reference,
                    content_hash=hashlib.sha256(data).hexdigest(),
                    size_bytes=len(data),
                    pack_path=pack_path,
                    reason="selected from the approved external-photography requirement",
                    provenance={
                        "photographer": photo.photographer,
                        "photographer_url": photo.photographer_url,
                        "width": photo.width,
                        "height": photo.height,
                        "orientation": photo.orientation,
                        "alt": photo.alt,
                        "average_color": photo.average_color,
                    },
                    attribution_required=True,
                    fallback=requirement.fallback,
                )
            )
        except ProviderUnavailable as exc:
            warnings.append(f"{requirement.requirement_id}: {exc}")
    return entries, files, warnings


def _verify_image(data: bytes) -> None:
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except Exception as exc:
        raise ProviderUnavailable("downloaded image failed validation") from exc
