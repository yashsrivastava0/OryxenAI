"""Small, replaceable provider clients used during preparation only."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from oryxenai.build_preparation.schemas import ResourceManifestEntry, ResourceRequirement


class ProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class RegistryResource:
    provider: str
    item_id: str
    source_reference: str
    description: str
    files: dict[str, bytes]
    dependencies: tuple[str, ...]
    registry_dependencies: tuple[str, ...]
    license: str = ""
    version: str = ""


class ShadcnRegistryProvider:
    """HTTP implementation of the documented shadcn registry JSON contract."""

    def __init__(
        self,
        *,
        provider: str,
        catalog_url: str,
        item_url_template: str,
        enabled: bool = True,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 15.0,
        retry_count: int = 2,
    ) -> None:
        self.provider = provider
        self.catalog_url = catalog_url
        self.item_url_template = item_url_template
        self.enabled = enabled
        self._client = client
        self._timeout_seconds = max(timeout_seconds, 1.0)
        self._retry_count = max(retry_count, 0)
        self._catalog_items: list[dict[str, Any]] | None = None
        self._item_cache: dict[str, RegistryResource] = {}

    async def search(self, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
        if not self.enabled or not self.catalog_url:
            return []
        if self._catalog_items is None:
            payload = await self._get_json(self.catalog_url)
            items = payload.get("items", []) if isinstance(payload, dict) else []
            if not isinstance(items, list):
                raise ProviderUnavailable(f"{self.provider} registry catalogue is malformed")
            self._catalog_items = [item for item in items if isinstance(item, dict)]
        items = self._catalog_items
        tokens = {token for token in re.findall(r"[a-z0-9]+", query.lower()) if len(token) > 2}
        ranked: list[tuple[int, dict[str, Any]]] = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                continue
            if _is_premium_registry_item(item):
                continue
            haystack = " ".join(
                str(item.get(key, "")) for key in ("name", "title", "description", "type")
            ).lower()
            score = sum(1 for token in tokens if token in haystack)
            if score:
                ranked.append((score, item))
        ranked.sort(key=lambda pair: (-pair[0], str(pair[1].get("name", ""))))
        return [item for _, item in ranked[:limit]]

    async def fetch(self, item_id: str, *, max_depth: int = 8) -> RegistryResource:
        if not self.enabled:
            raise ProviderUnavailable(f"{self.provider} registry is disabled")
        cached = self._item_cache.get(item_id)
        if cached is not None:
            return cached
        resource = await self._fetch_recursive(item_id, depth=0, seen=set(), max_depth=max_depth)
        self._item_cache[item_id] = resource
        return resource

    async def _fetch_recursive(
        self, item_id: str, *, depth: int, seen: set[str], max_depth: int
    ) -> RegistryResource:
        if depth > max_depth or item_id in seen:
            raise ProviderUnavailable("registry dependency graph is cyclic or too deep")
        if (
            not item_id
            or ".." in item_id
            or "://" in item_id
            or any(char.isspace() for char in item_id)
        ):
            raise ProviderUnavailable(f"{self.provider} registry item ID is unsafe")
        seen.add(item_id)
        url = self.item_url_template.format(name=item_id.lstrip("@"))
        payload = await self._get_json(url)
        if not isinstance(payload, dict) or not isinstance(payload.get("name"), str):
            raise ProviderUnavailable(f"{self.provider} registry item is malformed")
        files_payload = payload.get("files")
        if not isinstance(files_payload, list) or not files_payload:
            raise ProviderUnavailable(f"{self.provider} registry item files are malformed")
        files: dict[str, bytes] = {}
        for file_item in files_payload:
            if not isinstance(file_item, dict) or not isinstance(file_item.get("path"), str):
                raise ProviderUnavailable(
                    f"{self.provider} registry item contains a malformed file"
                )
            path = str(file_item["path"]).replace("\\", "/")
            if path.startswith("/") or ".." in path.split("/") or not file_item.get("content"):
                raise ProviderUnavailable(f"{self.provider} registry item contains an unsafe file")
            if Path(path).name.lower() in {
                "package.json",
                "package-lock.json",
                "pnpm-lock.yaml",
                "yarn.lock",
            } or Path(path).suffix.lower() in {".sh", ".ps1", ".bat", ".cmd"}:
                raise ProviderUnavailable(
                    f"{self.provider} registry item contains a forbidden file"
                )
            files[path] = str(file_item["content"]).encode("utf-8")
        dependencies = payload.get("dependencies", [])
        registry_dependencies = payload.get("registryDependencies", [])
        if not isinstance(dependencies, list) or not isinstance(registry_dependencies, list):
            raise ProviderUnavailable(f"{self.provider} registry dependency metadata is malformed")
        if any(not isinstance(value, str) for value in dependencies + registry_dependencies):
            raise ProviderUnavailable(f"{self.provider} registry dependency metadata is malformed")
        merged_dependencies = list(dependencies)
        for dependency in registry_dependencies:
            dependency_id = dependency.rsplit("/", 1)[-1].lstrip("@")
            child = await self._fetch_recursive(
                dependency_id,
                depth=depth + 1,
                seen=seen,
                max_depth=max_depth,
            )
            files.update(child.files)
            merged_dependencies.extend(child.dependencies)
        seen.remove(item_id)
        return RegistryResource(
            provider=self.provider,
            item_id=str(payload["name"]),
            source_reference=url,
            description=str(payload.get("description", payload.get("title", "")) or ""),
            files=files,
            dependencies=tuple(dict.fromkeys(merged_dependencies)),
            registry_dependencies=(),
            license=str(payload.get("license", "") or ""),
            version=str(payload.get("version", payload.get("$schema", "")) or ""),
        )

    async def _get_json(self, url: str) -> dict[str, Any]:
        client = self._client
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    self._timeout_seconds, connect=min(self._timeout_seconds, 10.0)
                ),
                follow_redirects=False,
            )
        try:
            response: httpx.Response | None = None
            for attempt in range(self._retry_count + 1):
                try:
                    response = await client.get(url, headers={"Accept": "application/json"})
                except httpx.HTTPError as exc:
                    if attempt >= self._retry_count:
                        raise ProviderUnavailable(
                            f"{self.provider} registry is unavailable"
                        ) from exc
                    continue
                if (
                    response.status_code == 429 or response.status_code >= 500
                ) and attempt < self._retry_count:
                    continue
                break
            if response is None or response.status_code >= 400:
                raise ProviderUnavailable(f"{self.provider} registry request failed")
            value = response.json()
            if not isinstance(value, dict):
                raise ProviderUnavailable(f"{self.provider} registry response is malformed")
            return value
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable(f"{self.provider} registry is unavailable") from exc
        finally:
            if owns_client:
                await client.aclose()


@dataclass(frozen=True)
class PhotoResource:
    provider: str
    photo_id: str
    photo_page: str
    photographer: str
    photographer_url: str
    alt: str
    width: int
    height: int
    orientation: str
    average_color: str
    image_url: str
    source_reference: str


class PexelsClient:
    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 15.0,
        retry_count: int = 2,
    ) -> None:
        self.api_key = api_key
        self._client = client
        self._timeout_seconds = max(timeout_seconds, 1.0)
        self._retry_count = max(retry_count, 0)

    async def search(
        self, requirement: ResourceRequirement, *, per_page: int = 12
    ) -> list[PhotoResource]:
        if not self.api_key:
            return []
        constraints = requirement.constraints
        query = " ".join(
            str(value)
            for value in (
                constraints.get("subject", ""),
                constraints.get("mood", ""),
                requirement.intent,
            )
            if value
        ).strip()
        if not query:
            return []
        params: dict[str, str | int] = {"query": query[:180], "per_page": min(max(per_page, 1), 80)}
        orientation = str(constraints.get("orientation", "") or "").lower()
        if orientation in {"landscape", "portrait", "square"}:
            params["orientation"] = orientation
        if constraints.get("aspect_ratio_need"):
            params["size"] = "large"
        color = str(constraints.get("color", constraints.get("color_hex", "")) or "")
        if re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            params["color"] = color
        min_width = constraints.get("min_width")
        if isinstance(min_width, int) and 0 < min_width <= 10000:
            params["min_width"] = min_width
        locale = str(constraints.get("locale", "") or "")
        if locale and re.fullmatch(r"[a-zA-Z-]{2,10}", locale):
            params["locale"] = locale
        client = self._client
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    self._timeout_seconds, connect=min(self._timeout_seconds, 10.0)
                ),
                follow_redirects=False,
            )
        try:
            response: httpx.Response | None = None
            for attempt in range(self._retry_count + 1):
                try:
                    response = await client.get(
                        "https://api.pexels.com/v1/search",
                        params=params,
                        headers={"Authorization": self.api_key},
                    )
                except httpx.HTTPError as exc:
                    if attempt >= self._retry_count:
                        raise ProviderUnavailable("Pexels is unavailable") from exc
                    continue
                if (
                    response.status_code == 429 or response.status_code >= 500
                ) and attempt < self._retry_count:
                    continue
                break
            if response is None:
                raise ProviderUnavailable("Pexels is unavailable")
            if response.status_code == 429:
                raise ProviderUnavailable("Pexels rate limit reached")
            if response.status_code >= 400:
                raise ProviderUnavailable("Pexels request failed")
            payload = response.json()
            photos = payload.get("photos", []) if isinstance(payload, dict) else []
            result: list[PhotoResource] = []
            for photo in photos:
                if not isinstance(photo, dict):
                    continue
                src = photo.get("src")
                if not isinstance(src, dict):
                    continue
                photo_id = photo.get("id")
                photo_page = photo.get("url")
                image_url = src.get("large2x") or src.get("large") or src.get("original")
                if (
                    not photo_id
                    or not isinstance(photo_page, str)
                    or not photo_page
                    or not isinstance(image_url, str)
                    or not image_url
                ):
                    continue
                width = int(photo.get("width", 0) or 0)
                height = int(photo.get("height", 0) or 0)
                result.append(
                    PhotoResource(
                        provider="pexels",
                        photo_id=str(photo_id),
                        photo_page=photo_page,
                        photographer=str(photo.get("photographer", "")),
                        photographer_url=str(photo.get("photographer_url", "")),
                        alt=str(photo.get("alt", "")),
                        width=width,
                        height=height,
                        orientation=str(photo.get("orientation", "") or "")
                        or _derive_orientation(width, height),
                        average_color=str(photo.get("avg_color", "")),
                        image_url=image_url,
                        source_reference=photo_page,
                    )
                )
            return result
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable("Pexels is unavailable") from exc
        finally:
            if owns_client:
                await client.aclose()

    async def download(self, photo: PhotoResource, *, max_bytes: int = 12 * 1024 * 1024) -> bytes:
        parsed = urlparse(photo.image_url)
        if parsed.scheme != "https" or parsed.hostname not in {
            "images.pexels.com",
            "www.pexels.com",
        }:
            raise ProviderUnavailable("Pexels image URL is not an approved host")
        client = self._client
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    self._timeout_seconds, connect=min(self._timeout_seconds, 10.0)
                ),
                follow_redirects=False,
            )
        try:
            response: httpx.Response | None = None
            for attempt in range(self._retry_count + 1):
                try:
                    response = await client.get(photo.image_url, headers={"Accept": "image/*"})
                except httpx.HTTPError as exc:
                    if attempt >= self._retry_count:
                        raise ProviderUnavailable("Pexels image download failed") from exc
                    continue
                if (
                    response.status_code == 429 or response.status_code >= 500
                ) and attempt < self._retry_count:
                    continue
                break
            if response is None:
                raise ProviderUnavailable("Pexels image download failed")
            if response.status_code >= 400 or len(response.content) > max_bytes:
                raise ProviderUnavailable("Pexels image could not be downloaded safely")
            content_type = response.headers.get("content-type", "").lower()
            if not content_type.startswith("image/"):
                raise ProviderUnavailable("Pexels response is not an image")
            return response.content
        except httpx.HTTPError as exc:
            raise ProviderUnavailable("Pexels image download failed") from exc
        finally:
            if owns_client:
                await client.aclose()


def choose_photo(
    candidates: list[PhotoResource], requirement: ResourceRequirement
) -> PhotoResource | None:
    constraints = requirement.constraints
    desired = str(constraints.get("orientation", "") or "").lower()
    filtered = [
        photo
        for photo in candidates
        if not desired
        or (photo.orientation or _derive_orientation(photo.width, photo.height)).lower() == desired
    ]
    filtered.sort(key=lambda photo: (-(photo.width * photo.height), photo.photo_id))
    return filtered[0] if filtered else None


def _derive_orientation(width: int, height: int) -> str:
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    if width > 0:
        return "square"
    return ""


def registry_entry(
    resource: RegistryResource,
    requirement: ResourceRequirement,
    *,
    pack_path: str,
    content_hash: str,
    size_bytes: int,
    allowed_dependencies: set[str] | None = None,
) -> ResourceManifestEntry:
    dependency_allowlist = allowed_dependencies or _allowed_dependencies()
    allowed = not resource.registry_dependencies and all(
        _dependency_name(dep) in dependency_allowlist for dep in resource.dependencies
    )
    return ResourceManifestEntry(
        manifest_resource_id=f"registry-{resource.provider}-{resource.item_id}",
        requirement_ids=[requirement.requirement_id],
        usages=[
            {
                "scope": requirement.scope,
                "route_id": requirement.route_id,
                "scene_id": requirement.scene_id,
            }
        ],
        disposition="materialized" if allowed else "custom_implementation_required",
        provider=resource.provider,
        provider_asset_id=resource.item_id,
        source_reference=resource.source_reference,
        source_version=resource.version,
        content_hash=content_hash,
        size_bytes=size_bytes,
        pack_path=pack_path if allowed else "",
        reason="verified registry source"
        if allowed
        else "registry dependency is outside the approved target contract",
        dependencies=list(resource.dependencies),
        dependencies_allowed=allowed,
        license=resource.license,
        provenance={
            "description": resource.description,
            "registry_dependencies": list(resource.registry_dependencies),
        },
        fallback=requirement.fallback or "custom implementation preserving the approved intent",
    )


def _dependency_name(value: str) -> str:
    return (
        value.split("@", 1)[0]
        if not value.startswith("@")
        else value.rsplit("@", 1)[0]
        if value.count("@") > 1
        else value
    )


def _is_premium_registry_item(item: dict[str, Any]) -> bool:
    for key in ("premium", "pro", "paid"):
        value = item.get(key)
        if value is True or (isinstance(value, str) and value.lower() in {"true", "pro", "paid"}):
            return True
    text = " ".join(str(item.get(key, "")) for key in ("title", "description", "license")).lower()
    return any(marker in text for marker in ("premium", "pro only", "paid"))


def _allowed_dependencies() -> set[str]:
    # Kept in sync with the checked-in target contract. The resolver also
    # receives the target contract in service-level tests; this conservative
    # list prevents an accidental package-install path.
    return {
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
