"""Discovery-only provider clients used by Build Preparation.

Every function here searches for real candidate resources and returns safe
metadata -- a provider ID, a license, a direct or preview URL. None of them
download or persist resource bytes. Code Generator's own acquisition adapters
fetch the actual bytes at generation time from the exact candidate Build
Preparation found.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from oryxenai.agents.build_preparation.schemas import FetchedResource, ResourceQuery
from oryxenai.agents.shared.component_retrieval import (
    ComponentCandidate,
    ComponentRetrievalService,
    build_component_retrieval_service,
)
from oryxenai.agents.shared.image_retrieval import (
    ImageCandidate,
    bounded_provider_query,
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
    """A provider lookup failed. Discovery degrades to no candidates, never a fabricated one."""

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
        sent_query = bounded_provider_query(query.query, "pexels")
        params: dict[str, str | int] = {
            "query": sent_query,
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
            image_url = str(
                source.get("large2x") or source.get("large") or source.get("original") or ""
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
                    retrieval_metadata={"sent_query": sent_query},
                )
            )
        return result
    except (ValueError, KeyError) as exc:
        raise ResourceProviderError("Pexels returned malformed JSON", provider="pexels") from exc
    finally:
        if owns:
            await http.aclose()


async def search_components(
    query: ResourceQuery,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
    limit: int = 5,
    diagnostics: list[dict[str, Any]] | None = None,
) -> list[FetchedResource]:
    """Discover real, currently-available registry components -- metadata only.

    Build Preparation only ever suggests a component by name/provider/URL; it
    never fetches source. Code Generator's own registry-fetch adapters
    materialize the actual source at generation time.
    """
    if not getattr(settings.resource_providers, "registries_enabled", True):
        return []
    http, owns = _client_or_new(client, settings.build_preparation.network_timeout_seconds)
    try:
        service = _component_service(settings)
        candidates = await service.discover(
            query.query,
            allowed_providers=query.allowed_providers,
            client=http,
            settings=settings,
            limit=limit,
            diagnostics=diagnostics,
        )
        return [_fetched_resource_from_candidate(query, candidate) for candidate in candidates]
    finally:
        if owns:
            await http.aclose()


def _component_service(settings: Any) -> ComponentRetrievalService:
    return build_component_retrieval_service(settings)


def _fetched_resource_from_candidate(
    query: ResourceQuery,
    candidate: ComponentCandidate,
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
        retrieval_metadata={
            **candidate.as_metadata(),
            "query": query.query,
            "provider_terms": list(query.provider_terms),
            "interaction_class": query.interaction_class,
            "interaction_outcome": query.interaction_outcome,
            "placement": query.placement,
            "expected_exports": list(query.expected_exports),
        },
        license=candidate.license,
        license_reference=candidate.license_reference,
        source_version=candidate.source_version,
        fallback=query.fallback,
    )


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
    """Find real, direct-fetchable Fontsource font files -- metadata only."""

    if not bool(getattr(settings.resource_providers, "fontsource_enabled", True)):
        return []
    base = str(getattr(settings.resource_providers, "fontsource_api_base_url", "") or "").rstrip(
        "/"
    )
    if not base:
        return []
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


@dataclass
class ProviderLookup:
    """Discovery-only facade: search for real candidates, never fetch bytes."""

    settings: Any
    client: httpx.AsyncClient | None = None
    live: bool = True
    _semaphore: asyncio.Semaphore | None = field(default=None, init=False, repr=False)
    calls_made: int = field(default=0, init=False)
    rate_limit_events: int = field(default=0, init=False)
    cooldown_skips: int = field(default=0, init=False)
    provider_receipts: list[dict[str, Any]] = field(default_factory=list, init=False)
    _image_asset_ids: set[str] = field(default_factory=set, init=False, repr=False)
    _image_terms: set[str] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        limit = max(1, int(getattr(self.settings.build_preparation, "provider_max_concurrency", 2)))
        self._semaphore = asyncio.Semaphore(limit)

    async def _lookup_one(self, query: ResourceQuery) -> list[FetchedResource]:
        self.calls_made += 1
        if self._semaphore is None:
            self.__post_init__()
        assert self._semaphore is not None
        async with self._semaphore:
            found: list[FetchedResource] = []
            if query.kind == "photo":
                receipt_start = len(self.provider_receipts)
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
                self.rate_limit_events += sum(
                    bool(item.get("rate_limit_event"))
                    for item in self.provider_receipts[receipt_start:]
                )
                self.cooldown_skips += sum(
                    bool(item.get("cooldown_skip"))
                    for item in self.provider_receipts[receipt_start:]
                )
                found = [_fetched_image(candidate, query) for candidate in image_candidates]
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
                receipt_start = len(self.provider_receipts)
                found = await search_components(
                    query, self.settings, client=self.client, diagnostics=self.provider_receipts
                )
                self.rate_limit_events += sum(
                    bool(item.get("rate_limit_event"))
                    for item in self.provider_receipts[receipt_start:]
                )
                self.cooldown_skips += sum(
                    bool(item.get("cooldown_skip"))
                    for item in self.provider_receipts[receipt_start:]
                )
            elif query.kind == "icon":
                found = await resolve_icon(query, self.settings, client=self.client)
            elif query.kind == "font":
                found = await search_fontsource(query, self.settings, client=self.client)
            if query.kind not in {"photo", "component"}:
                self.provider_receipts.append(
                    {
                        "provider": found[0].provider if found else query.kind,
                        "query": query.query,
                        "attempt": 1,
                        "candidate_count": len(found),
                        "kind": query.kind,
                    }
                )
        return found

    async def lookup(self, queries: list[ResourceQuery]) -> list[FetchedResource]:
        if not self.live:
            return []
        result: list[FetchedResource] = []
        for query in queries:
            result.extend(await self._lookup_one(query))
        return result
