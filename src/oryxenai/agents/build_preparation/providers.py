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
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

from oryxenai.agents.build_preparation.schemas import FetchedResource, ResourceQuery
from oryxenai.agents.shared.component_retrieval import (
    ComponentCandidate,
    ComponentRetrievalError,
    ComponentRetrievalService,
    build_component_retrieval_service,
)
from oryxenai.agents.shared.image_retrieval import (
    ImageCandidate,
    download_image_bytes,
    intent_from_values,
    search_images,
)
from oryxenai.agents.shared.providers.errors import (
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderTimeoutError,
)


class ResourceProviderError(ProviderError):
    """A provider lookup failed but the pipeline may still use a fallback."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        retryable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="RESOURCE_PROVIDER_UNAVAILABLE",
            retryable=retryable,
            details={"provider": provider, **(details or {})},
        )


_PROVIDER_RATE_STATE: dict[str, dict[str, float]] = {}


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
    return f"resource-{prefix}-{digest}"


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _env_value(settings: Any, field: str, fallback: str) -> str:
    name = str(getattr(settings.resource_providers, field, fallback) or fallback)
    return os.environ.get(name, "")


def _retry_after(response: httpx.Response, *, maximum: float = 8.0) -> float:
    try:
        return max(0.0, min(float(response.headers.get("Retry-After", "0")), maximum))
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
    max_retry_after_seconds: float = 8.0,
    provider: str,
) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(max(0, retry_count) + 1):
        delay = 0.0
        try:
            await _respect_provider_budget(provider, max_retry_after_seconds)
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
                _record_rate_headers(provider, response)
                return response
            if response.status_code == 429:
                retry_after = _retry_after(response, maximum=max_retry_after_seconds)
                last_error = ProviderRateLimitError(
                    f"{provider} rate limit reached",
                    retry_after_seconds=retry_after,
                )
                _PROVIDER_RATE_STATE[provider] = {
                    "remaining": 0.0,
                    "reset_at": time.time() + retry_after,
                }
                break
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
            delay = _retry_after(response, maximum=max_retry_after_seconds)
        if attempt < max(0, retry_count):
            await asyncio.sleep(delay)
    if last_error is not None:
        raise ResourceProviderError(
            str(last_error),
            provider=provider,
            details={
                "error_code": getattr(last_error, "code", ""),
                **getattr(last_error, "details", {}),
            },
        ) from last_error
    raise ResourceProviderError(f"{provider} request failed", provider=provider)


def _client_or_new(
    client: httpx.AsyncClient | None, timeout_seconds: float
) -> tuple[httpx.AsyncClient, bool]:
    if client is not None:
        return client, False
    return httpx.AsyncClient(timeout=timeout_seconds), True


async def _respect_provider_budget(provider: str, maximum_wait: float) -> None:
    state = _PROVIDER_RATE_STATE.get(provider, {})
    reset_at = float(state.get("reset_at", 0.0) or 0.0)
    remaining = state.get("remaining")
    if remaining is None or remaining > 0 or reset_at <= time.time():
        return
    wait = reset_at - time.time()
    if wait > maximum_wait:
        raise ResourceProviderError(
            f"{provider} rate budget is exhausted",
            provider=provider,
            details={
                "error_code": "PROVIDER_RATE_LIMIT_ERROR",
                "reset_at": reset_at,
                "remaining": remaining,
            },
        )
    await asyncio.sleep(max(0.0, wait))


def _record_rate_headers(provider: str, response: httpx.Response) -> None:
    remaining_value = response.headers.get("X-Ratelimit-Remaining") or response.headers.get(
        "X-RateLimit-Remaining"
    )
    reset_value = response.headers.get("X-Ratelimit-Reset") or response.headers.get(
        "X-RateLimit-Reset"
    )
    state = _PROVIDER_RATE_STATE.setdefault(provider, {})
    try:
        if remaining_value is not None:
            state["remaining"] = float(remaining_value)
        if reset_value is not None:
            state["reset_at"] = float(reset_value)
    except (TypeError, ValueError):
        return


def _fetched_image(
    candidate: ImageCandidate,
    query: ResourceQuery,
    provider_receipt: dict[str, Any] | None = None,
) -> FetchedResource:
    return FetchedResource(
        resource_id=_stable_id(
            candidate.provider, f"{query.need_id}:{candidate.provider_asset_id}"
        ),
        need_id=query.need_id,
        kind="photo",
        provider=candidate.provider,
        provider_asset_id=candidate.provider_asset_id,
        source_reference=candidate.source_url,
        preview_url=candidate.preview_url,
        hotlink_url=candidate.image_url if candidate.provider == "unsplash" else "",
        download_tracking_url=candidate.download_tracking_url,
        title=candidate.title,
        description=candidate.description,
        photographer=candidate.author,
        photographer_url=candidate.author_url,
        attribution_url=candidate.source_url,
        width=candidate.width,
        height=candidate.height,
        orientation=(
            "landscape"
            if candidate.width > candidate.height
            else "portrait"
            if candidate.height > candidate.width
            else "square"
        ),
        mime_type=candidate.mime_type,
        image_url=candidate.image_url,
        retrieval_metadata={
            "query": query.model_dump(mode="json"),
            "provider_receipt": dict(provider_receipt or {}),
        },
        license=candidate.license,
        license_reference=candidate.license_reference,
    )


async def search_pixabay(
    query: ResourceQuery,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
    limit: int = 6,
) -> list[FetchedResource]:
    """Search Pixabay through the shared provider-neutral image service."""

    intent = intent_from_values(
        purpose=query.purpose or query.query,
        subject=query.subject or query.query,
        style_mood=query.style_mood,
        theme_colors=query.theme_colors,
        orientation=query.orientation,
        aspect_ratio=query.aspect_ratio,
        minimum_width=query.minimum_width,
        minimum_height=query.minimum_height,
        negative_concepts=query.negative_concepts,
        queries=[query.query],
        important=query.important or query.required_for_handoff,
        media_kind="illustration" if "illustr" in query.query.casefold() else "photo",
        category=query.category,
        colors=query.colors,
        editors_choice=query.editors_choice,
    )
    candidates = await search_images(
        intent, settings, providers=["pixabay"], client=client, limit=limit
    )
    return [_fetched_image(candidate, query) for candidate in candidates]


async def search_pexels(
    query: ResourceQuery,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
    api_key: str | None = None,
    limit: int = 20,
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
            "per_page": min(max(limit, 1), 80),
        }
        if query.orientation in {"landscape", "portrait", "square"}:
            params["orientation"] = query.orientation
        minimum = max(query.minimum_width, query.minimum_height)
        if minimum >= 2000:
            params["size"] = "large"
        elif minimum >= 1000:
            params["size"] = "medium"
        if query.colors:
            params["color"] = query.colors[0]
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


async def search_components(
    query: ResourceQuery,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
    limit: int = 5,
    fetch_source: bool = False,
) -> list[FetchedResource]:
    """Discover registry components and optionally fetch their source.

    Build Preparation uses ``fetch_source=False`` for live discovery so the
    model ranks metadata only.  The selected candidate is then fetched through
    :func:`fetch_component`; source retrieval is never implicit during discovery.
    """
    if not getattr(settings.resource_providers, "registries_enabled", True):
        return []
    http, owns = _client_or_new(client, settings.build_preparation.network_timeout_seconds)
    result: list[FetchedResource] = []
    try:
        service = _component_service(settings)
        candidates = await service.discover(
            " ".join([query.query, *query.provider_terms]),
            allowed_providers=query.allowed_providers,
            client=http,
            settings=settings,
            limit=limit,
        )
        for candidate in candidates:
            fetched = None
            if fetch_source:
                try:
                    fetched = await service.fetch(candidate, client=http, settings=settings)
                except ComponentRetrievalError:
                    continue
            result.append(_fetched_resource_from_candidate(query, candidate, fetched))
        return result
    finally:
        if owns:
            await http.aclose()


def _component_service(settings: Any) -> ComponentRetrievalService:
    """Build the shared provider set without retaining provider responses."""

    return build_component_retrieval_service(settings)


def _fetched_resource_from_candidate(
    query: ResourceQuery,
    candidate: ComponentCandidate,
    fetched: Any | None,
) -> FetchedResource:
    return FetchedResource(
        resource_id=_stable_id(candidate.provider, f"{query.need_id}:{candidate.name}"),
        need_id=query.need_id,
        kind="component",
        provider=candidate.provider,
        provider_asset_id=candidate.name,
        source_reference=candidate.item_url,
        title=candidate.title,
        description=candidate.description,
        source_files=dict(fetched.source_files) if fetched is not None else {},
        dependencies=list(fetched.dependencies if fetched is not None else candidate.dependencies),
        registry_dependencies=list(
            fetched.registry_dependencies
            if fetched is not None
            else candidate.registry_dependencies
        ),
        retrieval_metadata=candidate.as_metadata(),
        license=(fetched.license if fetched is not None else candidate.license),
        license_reference=(
            fetched.license_reference if fetched is not None else candidate.license_reference
        ),
        source_version=(
            fetched.source_version if fetched is not None else candidate.source_version
        ),
        fallback=query.fallback,
    )


async def fetch_component(
    candidate: FetchedResource,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
) -> FetchedResource:
    """Fetch the selected component source exactly when the caller asks for it."""

    metadata = candidate.retrieval_metadata
    if not metadata:
        return candidate
    http, owns = _client_or_new(client, settings.build_preparation.network_timeout_seconds)
    try:
        service = _component_service(settings)
        selected = ComponentCandidate.from_metadata(metadata)
        fetched = await service.fetch(selected, client=http, settings=settings)
        return candidate.model_copy(
            update={
                "source_files": dict(fetched.source_files),
                "dependencies": list(fetched.dependencies),
                "registry_dependencies": list(fetched.registry_dependencies),
                "license": fetched.license,
                "license_reference": fetched.license_reference,
                "source_version": fetched.source_version,
            }
        )
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


async def search_fontsource(
    query: ResourceQuery,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
    limit: int = 3,
) -> list[FetchedResource]:
    """Resolve a small, pinned Fontsource font set with local file URLs."""

    if not bool(getattr(settings.resource_providers, "fontsource_enabled", True)):
        return []
    base = str(getattr(settings.resource_providers, "fontsource_api_base_url", "") or "").rstrip(
        "/"
    )
    if not base:
        return []
    # Flatten the set-of-sets while retaining stable order.
    terms: list[str] = []
    for value in [query.query, *query.provider_terms]:
        for token in re.findall(r"[a-z0-9]+", value.lower()):
            if len(token) > 2 and token not in terms:
                terms.append(token)
    http, owns = _client_or_new(client, settings.build_preparation.network_timeout_seconds)
    result: list[FetchedResource] = []
    try:
        response = await _get(
            http,
            f"{base}/fonts",
            params={"subsets": "latin"},
            headers={"Accept": "application/json"},
            timeout_seconds=settings.build_preparation.network_timeout_seconds,
            retry_count=settings.build_preparation.network_retry_count,
            provider="fontsource",
        )
        payload = response.json()
        fonts = payload if isinstance(payload, list) else []
        ranked: list[tuple[int, dict[str, Any]]] = []
        for item in fonts:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            haystack = " ".join(str(item.get(key, "")) for key in ("id", "family", "category"))
            score = sum(1 for token in terms if token in haystack.casefold())
            if score:
                ranked.append((score, item))
        ranked.sort(key=lambda pair: (-pair[0], str(pair[1].get("id", ""))))
        for _, item in ranked[:limit]:
            font_id = str(item.get("id", ""))
            try:
                detail = await _get(
                    http,
                    f"{base}/fonts/{font_id}",
                    headers={"Accept": "application/json"},
                    timeout_seconds=settings.build_preparation.network_timeout_seconds,
                    retry_count=settings.build_preparation.network_retry_count,
                    provider="fontsource",
                )
                detail_payload = detail.json()
            except (ProviderError, ValueError):
                continue
            if not isinstance(detail_payload, dict):
                continue
            variants = detail_payload.get("variants", {})
            urls: dict[str, str] = {}
            if isinstance(variants, dict):
                for weight in ("400", "500", "600", "700"):
                    styles = variants.get(weight)
                    normal = styles.get("normal") if isinstance(styles, dict) else None
                    subset = normal.get("latin") if isinstance(normal, dict) else None
                    url_map = subset.get("url") if isinstance(subset, dict) else None
                    if isinstance(url_map, dict):
                        url = str(
                            url_map.get(
                                str(
                                    getattr(
                                        settings.resource_providers, "fontsource_format", "woff2"
                                    )
                                ),
                                "",
                            )
                        )
                        if url.startswith("https://cdn.jsdelivr.net/"):
                            urls[f"{weight}-normal"] = url
            if not urls:
                continue
            family = str(detail_payload.get("family", item.get("family", font_id)) or font_id)
            weights = sorted({key.split("-", 1)[0] for key in urls})
            result.append(
                FetchedResource(
                    resource_id=_stable_id("fontsource", f"{query.need_id}:{font_id}"),
                    need_id=query.need_id,
                    kind="font",
                    provider="fontsource",
                    provider_asset_id=font_id,
                    source_reference=f"{base}/fonts/{font_id}",
                    title=family,
                    description=f"Fontsource {family} Latin {getattr(settings.resource_providers, 'fontsource_format', 'woff2')} files",
                    font_family=family,
                    font_weights=weights,
                    font_urls=urls,
                    license="OFL-1.1",
                    license_reference="https://scripts.sil.org/OFL",
                    source_version=str(detail_payload.get("version", "") or ""),
                    fallback=query.fallback,
                )
            )
        return result
    except (ProviderError, ValueError, KeyError):
        return []
    finally:
        if owns:
            await http.aclose()


async def download_font(
    candidate: FetchedResource,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
    max_bytes: int | None = None,
) -> dict[str, bytes]:
    if candidate.provider != "fontsource" or not candidate.font_urls:
        raise ResourceProviderError(
            "Fontsource candidate is not approved", provider="fontsource", retryable=False
        )
    http, owns = _client_or_new(client, settings.build_preparation.network_timeout_seconds)
    try:
        result: dict[str, bytes] = {}
        limit = int(
            max_bytes or getattr(settings.resource_providers, "font_max_bytes", 2 * 1024 * 1024)
        )
        for key, url in sorted(candidate.font_urls.items()):
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.hostname != "cdn.jsdelivr.net":
                raise ResourceProviderError(
                    "Fontsource file URL is not approved", provider="fontsource", retryable=False
                )
            response = await _get(
                http,
                url,
                headers={"Accept": "font/woff2,font/woff,application/octet-stream"},
                timeout_seconds=settings.build_preparation.network_timeout_seconds,
                retry_count=settings.build_preparation.network_retry_count,
                provider="fontsource",
            )
            if len(response.content) > limit:
                raise ResourceProviderError(
                    "Fontsource file exceeds the configured limit",
                    provider="fontsource",
                    retryable=False,
                )
            result[key] = response.content
        return result
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


async def download_image(
    candidate: FetchedResource,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
    max_bytes: int = 12 * 1024 * 1024,
) -> bytes:
    """Download a selected Pexels/Pixabay/opt-in Unsplash image safely."""

    try:
        return await download_image_bytes(candidate, settings, client=client, max_bytes=max_bytes)
    except ValueError as exc:
        raise ResourceProviderError(
            str(exc), provider=candidate.provider or "image", retryable=False
        ) from exc


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
    _blocked_until: dict[str, float] = field(default_factory=dict)
    _request_counts: dict[str, int] = field(default_factory=dict)
    _semaphore: asyncio.Semaphore | None = field(default=None, init=False, repr=False)
    calls_made: int = field(default=0, init=False)
    rate_limit_events: int = field(default=0, init=False)
    cache_hits: int = field(default=0, init=False)
    provider_receipts: list[dict[str, Any]] = field(default_factory=list, init=False)
    _image_asset_ids: set[str] = field(default_factory=set, init=False, repr=False)
    _image_terms: set[str] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        limit = max(1, int(getattr(self.settings.build_preparation, "provider_max_concurrency", 2)))
        self._semaphore = asyncio.Semaphore(limit)

    async def _lookup_one(self, query: ResourceQuery) -> list[FetchedResource]:
        now = time.monotonic()
        provider = {
            "photo": "pexels",
            "component": "component",
            "font": "fontsource",
            "icon": "lucide",
        }.get(query.kind, query.kind)
        if now < self._blocked_until.get(provider, 0.0):
            self.rate_limit_events += 1
            return []
        max_requests = max(
            1, int(getattr(self.settings.build_preparation, "provider_max_requests", 32))
        )
        if self._request_counts.get(provider, 0) >= max_requests:
            self._blocked_until[provider] = now + max(
                1.0,
                float(getattr(self.settings.build_preparation, "provider_max_wait_seconds", 8.0)),
            )
            self.rate_limit_events += 1
            return []
        self._request_counts[provider] = self._request_counts.get(provider, 0) + 1
        self.calls_made += 1
        if self._semaphore is None:
            self.__post_init__()
        assert self._semaphore is not None
        async with self._semaphore:
            found: list[FetchedResource] = []
            if query.kind == "photo":
                allowed = query.allowed_providers or list(
                    getattr(
                        getattr(self.settings, "image_retrieval", None),
                        "provider_order",
                        ["pexels", "pixabay"],
                    )
                )
                intent = intent_from_values(
                    purpose=query.purpose or query.query,
                    subject=query.subject or query.query,
                    style_mood=query.style_mood,
                    theme_colors=query.theme_colors,
                    orientation=query.orientation,
                    aspect_ratio=query.aspect_ratio,
                    minimum_width=query.minimum_width,
                    minimum_height=query.minimum_height,
                    negative_concepts=query.negative_concepts,
                    queries=[query.query],
                    important=query.important
                    or any(
                        token in f"{query.purpose} {query.query}".casefold()
                        for token in ("hero", "banner", "showcase")
                    ),
                    media_kind="illustration" if "illustr" in query.query.casefold() else "photo",
                    category=query.category,
                    colors=query.colors,
                    editors_choice=query.editors_choice,
                    used_asset_ids=self._image_asset_ids,
                    used_terms=self._image_terms,
                )
                image_candidates = await search_images(
                    intent,
                    self.settings,
                    providers=allowed,
                    client=self.client,
                    limit=int(
                        getattr(
                            getattr(self.settings, "image_retrieval", None),
                            "max_candidates_per_query",
                            6,
                        )
                    ),
                    diagnostics=self.provider_receipts,
                )
                self.cache_hits += (
                    sum(
                        1
                        for receipt in self.provider_receipts
                        if receipt.get("cache_state") == "hit"
                    )
                    - self.cache_hits
                )
                found = [
                    _fetched_image(
                        candidate,
                        query,
                        next(
                            (
                                receipt
                                for receipt in reversed(self.provider_receipts)
                                if receipt.get("provider") == candidate.provider
                                and receipt.get("query") == query.query
                                and "candidate_count" in receipt
                            ),
                            None,
                        ),
                    )
                    for candidate in image_candidates
                ]
                self._image_asset_ids.update(
                    candidate.provider_asset_id for candidate in image_candidates
                )
                self._image_terms.update(
                    token
                    for candidate in image_candidates
                    for token in re.findall(
                        r"[a-z0-9]+", (candidate.title or candidate.description).casefold()
                    )
                    if len(token) > 2
                )
            elif query.kind == "component":
                found = await search_components(
                    query, self.settings, client=self.client, fetch_source=False
                )
            elif query.kind == "icon":
                found = await resolve_icon(query, self.settings, client=self.client)
            elif query.kind == "font":
                found = await search_fontsource(query, self.settings, client=self.client)
            if query.kind != "photo":
                found = [
                    item.model_copy(
                        update={
                            "retrieval_metadata": {
                                **item.retrieval_metadata,
                                "provider_receipt": {
                                    "provider": item.provider or provider,
                                    "query": query.query,
                                    "attempt": 1,
                                    "http_status": 200 if found else None,
                                    "retry_delay": 0.0,
                                    "cache_state": "not_cached",
                                    "configured_key": True,
                                    "candidate_count": len(found),
                                    "kind": query.kind,
                                },
                            }
                        }
                    )
                    for item in found
                ]
            if query.kind != "photo":
                self.provider_receipts.append(
                    {
                        "provider": provider,
                        "query": query.query,
                        "attempt": 1,
                        "http_status": 200 if found else None,
                        "retry_delay": 0.0,
                        "cache_state": "not_cached",
                        "configured_key": True,
                        "candidate_count": len(found),
                        "kind": query.kind,
                    }
                )
        return found

    async def fetch_component(self, candidate: FetchedResource) -> FetchedResource:
        return await fetch_component(candidate, self.settings, client=self.client)

    async def lookup(self, queries: list[ResourceQuery]) -> list[FetchedResource]:
        if not self.live:
            return []
        result: list[FetchedResource] = []
        for query in queries:
            result.extend(await self._lookup_one(query))
        return result
