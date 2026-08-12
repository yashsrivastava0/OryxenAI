"""Small provider clients used by Build Preparation.

The module intentionally contains plain async functions and a thin facade for
dependency injection. Provider responses are reduced to safe metadata before
they reach the agent; remote source is never executed.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

from oryxenai.agents.build_preparation.schemas import FetchedResource, ResourceQuery
from oryxenai.agents.shared.providers.errors import (
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderTimeoutError,
)


class ResourceProviderError(ProviderError):
    """A provider lookup failed but the pipeline may still use a fallback."""

    def __init__(self, message: str, *, provider: str, retryable: bool = True) -> None:
        super().__init__(
            message,
            code="RESOURCE_PROVIDER_UNAVAILABLE",
            retryable=retryable,
            details={"provider": provider},
        )


_REGISTRY_LICENSES: dict[str, tuple[str, str]] = {
    "shadcn": (
        "MIT",
        "https://github.com/shadcn-ui/ui/blob/main/LICENSE.md",
    ),
    "magicui": (
        "MIT",
        "https://github.com/magicuidesign/magicui/blob/main/LICENSE.md",
    ),
}


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
    return f"resource-{prefix}-{digest}"


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _env_value(settings: Any, field: str, fallback: str) -> str:
    name = str(getattr(settings.resource_providers, field, fallback) or fallback)
    return os.environ.get(name, "")


def _retry_after(response: httpx.Response) -> float:
    try:
        return max(0.0, min(float(response.headers.get("Retry-After", "0")), 5.0))
    except (TypeError, ValueError):
        return 0.0


async def _get(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, str | int] | None = None,
    timeout_seconds: float = 15.0,
    retry_count: int = 2,
    provider: str,
) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(max(0, retry_count) + 1):
        delay = 0.0
        try:
            response = await client.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout_seconds,
                follow_redirects=False,
            )
        except httpx.TimeoutException:
            last_error = ProviderTimeoutError(f"{provider} request timed out")
        except httpx.HTTPError:
            last_error = ProviderConnectionError(f"{provider} connection failed")
        else:
            if response.status_code < 400:
                return response
            if response.status_code == 429:
                last_error = ProviderRateLimitError(
                    f"{provider} rate limit reached", retry_after_seconds=_retry_after(response)
                )
            elif response.status_code >= 500:
                last_error = ProviderServerError(
                    f"{provider} returned a server error", status_code=response.status_code
                )
            else:
                raise ResourceProviderError(
                    f"{provider} rejected the resource request",
                    provider=provider,
                    retryable=False,
                )
            delay = _retry_after(response)
        if attempt < max(0, retry_count):
            await asyncio.sleep(delay)
    if last_error is not None:
        raise ResourceProviderError(str(last_error), provider=provider) from last_error
    raise ResourceProviderError(f"{provider} request failed", provider=provider)


def _client_or_new(
    client: httpx.AsyncClient | None, timeout_seconds: float
) -> tuple[httpx.AsyncClient, bool]:
    if client is not None:
        return client, False
    return httpx.AsyncClient(timeout=timeout_seconds), True


async def search_pexels(
    query: ResourceQuery,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
    api_key: str | None = None,
    limit: int = 5,
) -> list[FetchedResource]:
    key = (
        api_key
        if api_key is not None
        else _env_value(settings, "pexels_api_key_env", "PEXELS_API_KEY")
    )
    if not key or not query.query.strip():
        return []
    http, owns = _client_or_new(client, settings.build_preparation.network_timeout_seconds)
    try:
        params: dict[str, str | int] = {
            "query": query.query[:180],
            "per_page": min(max(limit, 1), 12),
        }
        if query.orientation in {"landscape", "portrait", "square"}:
            params["orientation"] = query.orientation
        response = await _get(
            http,
            "https://api.pexels.com/v1/search",
            headers={"Authorization": key, "Accept": "application/json"},
            params=params,
            timeout_seconds=settings.build_preparation.network_timeout_seconds,
            retry_count=settings.build_preparation.network_retry_count,
            provider="pexels",
        )
        payload = response.json()
        photos = payload.get("photos", []) if isinstance(payload, dict) else []
        result: list[FetchedResource] = []
        for photo in photos:
            if not isinstance(photo, dict) or not isinstance(photo.get("src"), dict):
                continue
            source = photo["src"]
            # Preserve the original provider asset for local inspection and
            # controlled packaging; delivery sizing remains Code Generator's
            # responsibility after the image has passed the handoff gate.
            image_url = str(
                source.get("original") or source.get("large2x") or source.get("large") or ""
            )
            photo_id = str(photo.get("id", "") or "")
            if not photo_id or not image_url.startswith("https://"):
                continue
            width = int(photo.get("width", 0) or 0)
            height = int(photo.get("height", 0) or 0)
            orientation = (
                "landscape" if width > height else "portrait" if height > width else "square"
            )
            result.append(
                FetchedResource(
                    resource_id=_stable_id("pexels", f"{query.need_id}:{photo_id}"),
                    need_id=query.need_id,
                    kind="photo",
                    provider="pexels",
                    provider_asset_id=photo_id,
                    source_reference=str(photo.get("url", "") or ""),
                    preview_url=str(source.get("medium", image_url) or image_url),
                    title=str(photo.get("alt", "") or ""),
                    description=str(photo.get("alt", "") or ""),
                    photographer=str(photo.get("photographer", "") or ""),
                    photographer_url=str(photo.get("photographer_url", "") or ""),
                    attribution_url=str(photo.get("url", "") or ""),
                    width=width,
                    height=height,
                    orientation=orientation,
                    mime_type="image/*",
                    image_url=image_url,
                    license="Pexels license",
                    license_reference="https://www.pexels.com/legal-pages/license/",
                )
            )
        return result
    except (ValueError, KeyError) as exc:
        raise ResourceProviderError("Pexels returned malformed JSON", provider="pexels") from exc
    finally:
        if owns:
            await http.aclose()


async def search_unsplash(
    query: ResourceQuery,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
    access_key: str | None = None,
    limit: int = 5,
) -> list[FetchedResource]:
    key = (
        access_key
        if access_key is not None
        else _env_value(settings, "unsplash_access_key_env", "UNSPLASH_ACCESS_KEY")
    )
    if not key or not query.query.strip():
        return []
    http, owns = _client_or_new(client, settings.build_preparation.network_timeout_seconds)
    try:
        response = await _get(
            http,
            "https://api.unsplash.com/search/photos",
            headers={"Authorization": f"Client-ID {key}", "Accept": "application/json"},
            params={"query": query.query[:180], "per_page": min(max(limit, 1), 5)},
            timeout_seconds=settings.build_preparation.network_timeout_seconds,
            retry_count=settings.build_preparation.network_retry_count,
            provider="unsplash",
        )
        payload = response.json()
        photos = payload.get("results", []) if isinstance(payload, dict) else []
        result: list[FetchedResource] = []
        for photo in photos:
            if not isinstance(photo, dict):
                continue
            photo_id = str(photo.get("id", "") or "")
            urls: dict[str, Any] = {}
            links: dict[str, Any] = {}
            user: dict[str, Any] = {}
            if isinstance(photo.get("urls"), dict):
                urls = photo["urls"]
            if isinstance(photo.get("links"), dict):
                links = photo["links"]
            if isinstance(photo.get("user"), dict):
                user = photo["user"]
            user_links: dict[str, Any] = {}
            if isinstance(user.get("links"), dict):
                user_links = user["links"]
            hotlink = str(urls.get("regular") or urls.get("full") or "")
            if not photo_id or not hotlink.startswith("https://"):
                continue
            width = int(photo.get("width", 0) or 0)
            height = int(photo.get("height", 0) or 0)
            result.append(
                FetchedResource(
                    resource_id=_stable_id("unsplash", f"{query.need_id}:{photo_id}"),
                    need_id=query.need_id,
                    kind="photo",
                    provider="unsplash",
                    provider_asset_id=photo_id,
                    source_reference=str(links.get("html", "") or ""),
                    preview_url=str(urls.get("small", hotlink) or hotlink),
                    hotlink_url=hotlink,
                    download_tracking_url=str(links.get("download_location", "") or ""),
                    title=str(photo.get("alt_description") or photo.get("description") or ""),
                    description=str(photo.get("description") or ""),
                    photographer=str(user.get("name", "") or ""),
                    photographer_url=str(user_links.get("html", "") or ""),
                    attribution_url=str(links.get("html", "") or ""),
                    width=width,
                    height=height,
                    orientation=(
                        "landscape"
                        if width > height
                        else "portrait"
                        if height > width
                        else "square"
                    ),
                    mime_type="image/*",
                    license="Unsplash license",
                    license_reference="https://unsplash.com/license",
                )
            )
        return result
    except (ValueError, KeyError) as exc:
        raise ResourceProviderError(
            "Unsplash returned malformed JSON", provider="unsplash"
        ) from exc
    finally:
        if owns:
            await http.aclose()


def _safe_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip("/")
    if not normalized or ".." in normalized.split("/") or normalized.startswith("."):
        raise ResourceProviderError(
            "Registry returned an unsafe file path", provider="registry", retryable=False
        )
    if normalized.rsplit("/", 1)[-1].lower() in {
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
    } or normalized.lower().endswith((".sh", ".ps1", ".bat", ".cmd")):
        raise ResourceProviderError(
            "Registry returned a forbidden file", provider="registry", retryable=False
        )
    return normalized


async def _registry_item(
    provider: str,
    name: str,
    template: str,
    settings: Any,
    client: httpx.AsyncClient,
    *,
    seen: set[str] | None = None,
) -> tuple[dict[str, str], list[str], list[str], str, str]:
    seen = set() if seen is None else seen
    if not name or name in seen or len(seen) > 8 or any(char.isspace() for char in name):
        raise ResourceProviderError(
            "Registry dependency graph is unsafe", provider=provider, retryable=False
        )
    seen.add(name)
    response = await _get(
        client,
        template.format(name=name.lstrip("@")),
        headers={"Accept": "application/json"},
        timeout_seconds=settings.build_preparation.network_timeout_seconds,
        retry_count=settings.build_preparation.network_retry_count,
        provider=provider,
    )
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        raise ResourceProviderError(
            "Registry item is malformed", provider=provider, retryable=False
        )
    files: dict[str, str] = {}
    for file_item in payload["files"]:
        if (
            not isinstance(file_item, dict)
            or not file_item.get("path")
            or not file_item.get("content")
        ):
            raise ResourceProviderError(
                "Registry item contains malformed source", provider=provider, retryable=False
            )
        files[_safe_path(str(file_item["path"]))] = str(file_item["content"])
    dependencies = [
        str(value) for value in payload.get("dependencies", []) if isinstance(value, str)
    ]
    registry_dependencies = [
        str(value) for value in payload.get("registryDependencies", []) if isinstance(value, str)
    ]
    for dependency in registry_dependencies:
        child_name = dependency.rsplit("/", 1)[-1].lstrip("@")
        child_files, child_deps, _, _, _ = await _registry_item(
            provider, child_name, template, settings, client, seen=seen
        )
        conflicting_paths = {
            path for path in set(files) & set(child_files) if files[path] != child_files[path]
        }
        if conflicting_paths:
            raise ResourceProviderError(
                "Registry dependencies contain conflicting source paths",
                provider=provider,
                retryable=False,
            )
        files.update(child_files)
        dependencies.extend(child_deps)
    seen.remove(name)
    return (
        files,
        list(dict.fromkeys(dependencies)),
        registry_dependencies,
        str(payload.get("license", "") or ""),
        str(payload.get("version", payload.get("$schema", "")) or ""),
    )


async def search_components(
    query: ResourceQuery,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
    limit: int = 5,
) -> list[FetchedResource]:
    if not getattr(settings.resource_providers, "registries_enabled", True):
        return []
    http, owns = _client_or_new(client, settings.build_preparation.network_timeout_seconds)
    result: list[FetchedResource] = []
    try:
        order = list(getattr(settings.resource_providers, "registry_order", ["shadcn", "magicui"]))
        for provider in order:
            enabled = provider == "shadcn" or bool(
                getattr(settings.resource_providers, f"{provider}_enabled", False)
            )
            if not enabled:
                continue
            catalog_url = str(
                getattr(settings.resource_providers, f"{provider}_catalog_url", "") or ""
            )
            template = str(
                getattr(settings.resource_providers, f"{provider}_item_url_template", "") or ""
            )
            if not catalog_url or not template:
                continue
            try:
                response = await _get(
                    http,
                    catalog_url,
                    headers={"Accept": "application/json"},
                    timeout_seconds=settings.build_preparation.network_timeout_seconds,
                    retry_count=settings.build_preparation.network_retry_count,
                    provider=provider,
                )
                payload = response.json()
                items = payload.get("items", []) if isinstance(payload, dict) else []
                ranked: list[tuple[int, dict[str, Any]]] = []
                wanted = _tokens(" ".join([query.query, *query.provider_terms]))
                for item in items if isinstance(items, list) else []:
                    if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                        continue
                    haystack = " ".join(
                        str(item.get(key, "")) for key in ("name", "title", "description", "type")
                    )
                    score = sum(1 for token in wanted if token in haystack.lower())
                    if score:
                        ranked.append((score, item))
                ranked.sort(key=lambda pair: (-pair[0], str(pair[1].get("name", ""))))
                for _, item in ranked[:limit]:
                    name = str(item["name"])
                    try:
                        (
                            files,
                            dependencies,
                            registry_dependencies,
                            license_name,
                            version,
                        ) = await _registry_item(provider, name, template, settings, http)
                    except ResourceProviderError:
                        continue
                    result.append(
                        FetchedResource(
                            resource_id=_stable_id(provider, f"{query.need_id}:{name}"),
                            need_id=query.need_id,
                            kind="component",
                            provider=provider,
                            provider_asset_id=name,
                            source_reference=template.format(name=name.lstrip("@")),
                            title=str(item.get("title", item.get("description", name)) or name),
                            description=str(item.get("description", "") or ""),
                            source_files=files,
                            dependencies=dependencies,
                            registry_dependencies=registry_dependencies,
                            license=license_name or _REGISTRY_LICENSES.get(provider, ("", ""))[0],
                            license_reference=_REGISTRY_LICENSES.get(provider, ("", ""))[1],
                            source_version=version,
                            fallback=query.fallback,
                        )
                    )
            except ResourceProviderError:
                continue
        return result
    finally:
        if owns:
            await http.aclose()


async def resolve_icon(
    query: ResourceQuery,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
) -> list[FetchedResource]:
    name = query.icon_name.strip()
    template = str(
        getattr(
            settings.resource_providers,
            "lucide_icon_url_template",
            "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{name}.svg",
        )
        or ""
    )
    if not name or not template or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        return []
    http, owns = _client_or_new(client, settings.build_preparation.network_timeout_seconds)
    try:
        try:
            response = await _get(
                http,
                template.format(name=name.lower()),
                headers={"Accept": "image/svg+xml,text/plain"},
                timeout_seconds=settings.build_preparation.network_timeout_seconds,
                retry_count=settings.build_preparation.network_retry_count,
                provider="lucide",
            )
        except ResourceProviderError:
            return []
        return [
            FetchedResource(
                resource_id=_stable_id("lucide", f"{query.need_id}:{name.lower()}"),
                need_id=query.need_id,
                kind="icon",
                provider="lucide",
                provider_asset_id=name,
                source_reference=str(response.url),
                icon_name=name,
                license="ISC",
                license_reference="https://github.com/lucide-icons/lucide/blob/main/LICENSE",
            )
        ]
    finally:
        if owns:
            await http.aclose()


async def download_pexels(
    candidate: FetchedResource,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
    max_bytes: int = 12 * 1024 * 1024,
) -> bytes:
    parsed = urlparse(candidate.image_url)
    if (
        candidate.provider != "pexels"
        or parsed.scheme != "https"
        or parsed.hostname != "images.pexels.com"
    ):
        raise ResourceProviderError(
            "Pexels image URL is not approved", provider="pexels", retryable=False
        )
    key = _env_value(settings, "pexels_api_key_env", "PEXELS_API_KEY")
    http, owns = _client_or_new(client, settings.build_preparation.network_timeout_seconds)
    try:
        response = await _get(
            http,
            candidate.image_url,
            headers={"Authorization": key, "Accept": "image/*"},
            timeout_seconds=settings.build_preparation.network_timeout_seconds,
            retry_count=settings.build_preparation.network_retry_count,
            provider="pexels",
        )
        content_type = response.headers.get("content-type", "").lower()
        if not content_type.startswith("image/") or len(response.content) > max_bytes:
            raise ResourceProviderError(
                "Pexels response is not a safe image", provider="pexels", retryable=False
            )
        return response.content
    finally:
        if owns:
            await http.aclose()


async def trigger_unsplash_download(
    candidate: FetchedResource,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
) -> None:
    if candidate.provider != "unsplash" or not candidate.download_tracking_url:
        return
    key = _env_value(settings, "unsplash_access_key_env", "UNSPLASH_ACCESS_KEY")
    if not key:
        return
    separator = "&" if "?" in candidate.download_tracking_url else "?"
    url = f"{candidate.download_tracking_url}{separator}{urlencode({'client_id': key})}"
    http, owns = _client_or_new(client, settings.build_preparation.network_timeout_seconds)
    try:
        await _get(
            http,
            url,
            headers={"Accept": "application/json"},
            timeout_seconds=settings.build_preparation.network_timeout_seconds,
            retry_count=settings.build_preparation.network_retry_count,
            provider="unsplash",
        )
    finally:
        if owns:
            await http.aclose()


@dataclass
class ProviderLookup:
    settings: Any
    client: httpx.AsyncClient | None = None
    live: bool = True

    async def lookup(self, queries: list[ResourceQuery]) -> list[FetchedResource]:
        if not self.live:
            return []
        result: list[FetchedResource] = []
        for query in queries:
            if query.kind == "photo":
                try:
                    found = await search_pexels(query, self.settings, client=self.client)
                except ResourceProviderError:
                    found = []
                # Unsplash requires hotlinking and cannot satisfy a required
                # local resource while the static target forbids remote assets.
                if not found and not query.required_for_handoff:
                    try:
                        found = await search_unsplash(query, self.settings, client=self.client)
                    except ResourceProviderError:
                        found = []
                result.extend(found)
            elif query.kind == "component":
                result.extend(await search_components(query, self.settings, client=self.client))
            elif query.kind == "icon":
                result.extend(await resolve_icon(query, self.settings, client=self.client))
        return result
