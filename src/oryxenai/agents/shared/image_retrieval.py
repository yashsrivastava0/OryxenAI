"""Shared, local-first image retrieval for Build Preparation and Code Generator.

The module deliberately stops at trusted metadata and bytes.  Models may
describe an image need, but provider credentials, URLs, downloads, image
validation, and local optimization stay in this module and its callers.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import io
import json
import os
import re
import tempfile
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ImageSearchIntent(BaseModel):
    """Small structured search brief shared by both generation stages."""

    model_config = ConfigDict(extra="forbid")

    purpose: str = ""
    subject: str = ""
    style_mood: str = ""
    theme_colors: list[str] = Field(default_factory=list)
    media_kind: str = "photo"
    category: str = ""
    colors: list[str] = Field(default_factory=list)
    editors_choice: bool = False
    orientation: str = ""
    aspect_ratio: str = ""
    minimum_width: int = 0
    minimum_height: int = 0
    negative_concepts: list[str] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    important: bool = False
    used_asset_ids: list[str] = Field(default_factory=list)
    used_terms: list[str] = Field(default_factory=list)

    @field_validator("queries")
    @classmethod
    def _limit_queries(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()][:3]


class ImageCandidate(BaseModel):
    """Provider-neutral metadata returned before the selected asset is fetched."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    provider_asset_id: str
    title: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    source_url: str = ""
    image_url: str
    preview_url: str = ""
    author: str = ""
    author_url: str = ""
    width: int = 0
    height: int = 0
    mime_type: str = "image/*"
    license: str = ""
    license_reference: str = ""
    popularity: float = 0.0
    editorial: bool = False
    ai_generated: bool = False
    provider_rank: int = 0
    query: str = ""
    download_tracking_url: str = ""


class ImageDownloadError(ValueError):
    """Raised when a provider response cannot be safely materialized."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        self.details = dict(details or {})
        super().__init__(message)


def compile_search_queries(
    intent: ImageSearchIntent,
    *,
    provider: str = "",
    max_variants: int | None = None,
    max_terms: int = 6,
) -> list[str]:
    """Compile bounded provider queries from semantic intent only.

    Negative concepts, colors, breakpoints, and route copy stay structured
    filters.  The exact returned string is the string sent to the provider and
    recorded on each candidate/diagnostic receipt.
    """

    limit = 100 if provider == "pixabay" else 180
    count = max(1, int(max_variants or 3))

    def terms(value: str) -> list[str]:
        result: list[str] = []
        for token in re.findall(r"[a-z0-9][a-z0-9-]*", value.casefold()):
            if len(token) < 3 or token in {"the", "and", "with", "for", "from", "portfolio"}:
                continue
            if token not in result:
                result.append(token)
            if len(result) >= max_terms:
                break
        return result

    subject = terms(intent.subject)
    purpose = terms(intent.purpose)
    style = terms(intent.style_mood)
    variants: list[list[str]] = [subject, subject[:4] + purpose[:2], subject[:3] + style[:3]]
    if not any(variants):
        variants = [terms("editorial portfolio")]
    compiled: list[str] = []
    for candidate in variants[:count]:
        words = list(dict.fromkeys(candidate))[:max_terms]
        query = " ".join(words).strip()
        if not query:
            continue
        if len(query) > limit:
            query = query[:limit].rsplit(" ", 1)[0] or query[:limit]
        if query not in compiled:
            compiled.append(query)
    return compiled[:count]


def compile_provider_query(intent: ImageSearchIntent, query: str, provider: str) -> str:
    """Bound one already-compiled query to a provider's transport limit."""

    limit = 100 if provider == "pixabay" else 180
    del intent
    words = re.findall(r"[a-z0-9][a-z0-9-]*", str(query).casefold())
    normalized = " ".join(list(dict.fromkeys(words))[:6])
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rsplit(" ", 1)[0] or normalized[:limit]


def bounded_provider_query(query: str, provider: str, *, max_terms: int = 6) -> str:
    """Bound a legacy string query before a provider request and receipt."""

    words = re.findall(r"[a-z0-9][a-z0-9-]*", str(query).casefold())
    normalized = " ".join(list(dict.fromkeys(words))[: max(2, max_terms)])
    limit = 100 if provider == "pixabay" else 180
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rsplit(" ", 1)[0] or normalized[:limit]


_RATE_STATE: dict[str, dict[str, float]] = {}
_SCHEMA_VERSION = "image-search-v1"
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_ALLOWED_HOSTS = {
    "pexels": {"images.pexels.com"},
    "pixabay": {"pixabay.com", "cdn.pixabay.com"},
    "unsplash": {"images.unsplash.com", "plus.unsplash.com"},
}


def _config(settings: Any) -> Any:
    return getattr(settings, "image_retrieval", None)


def _value(settings: Any, name: str, default: Any) -> Any:
    config = _config(settings)
    return getattr(config, name, default) if config is not None else default


def _provider_key(settings: Any, name: str, fallback: str) -> str:
    providers = getattr(settings, "resource_providers", None)
    env_name = str(getattr(providers, name, fallback) or fallback)
    return os.environ.get(env_name, "")


def _provider_key_configured(settings: Any, provider: str) -> bool:
    if provider == "pexels":
        return bool(_provider_key(settings, "pexels_api_key_env", "PEXELS_API_KEY"))
    if provider == "pixabay":
        return bool(_provider_key(settings, "pixabay_api_key_env", "PIXABAY_API_KEY"))
    if provider == "unsplash":
        return bool(_provider_key(settings, "unsplash_access_key_env", "UNSPLASH_ACCESS_KEY"))
    return True


def _tokens(value: str | Iterable[str]) -> set[str]:
    text = value if isinstance(value, str) else " ".join(value)
    return {token for token in _TOKEN_RE.findall(text.casefold()) if len(token) > 2}


def _orientation(width: int, height: int) -> str:
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"


def _ratio(value: str) -> float | None:
    try:
        left, right = value.split(":", 1)
        return float(left) / float(right)
    except (AttributeError, TypeError, ValueError, ZeroDivisionError):
        return None


def intent_from_values(
    *,
    purpose: str = "",
    subject: str = "",
    style_mood: str = "",
    orientation: str = "",
    aspect_ratio: str = "",
    minimum_width: int = 0,
    minimum_height: int = 0,
    negative_concepts: Iterable[str] = (),
    queries: Iterable[str] = (),
    important: bool = False,
    used_asset_ids: Iterable[str] = (),
    used_terms: Iterable[str] = (),
    theme_colors: Iterable[str] = (),
    media_kind: str = "photo",
    category: str = "",
    colors: Iterable[str] = (),
    editors_choice: bool = False,
) -> ImageSearchIntent:
    """Build a concise intent from an approved request, never from raw prompts."""

    query_values = [str(item).strip() for item in queries if str(item).strip()]
    if not query_values:
        parts = [subject or purpose, style_mood]
        query_values = [" ".join(item.split()) for item in parts if item.strip()]
    return ImageSearchIntent(
        purpose=purpose.strip(),
        subject=subject.strip(),
        style_mood=style_mood.strip(),
        theme_colors=[str(item).strip() for item in theme_colors if str(item).strip()][:5],
        media_kind=media_kind.strip() or "photo",
        category=category.strip(),
        colors=[str(item).strip() for item in colors if str(item).strip()][:3],
        editors_choice=editors_choice,
        orientation=orientation.strip().casefold(),
        aspect_ratio=aspect_ratio.strip(),
        minimum_width=max(0, int(minimum_width or 0)),
        minimum_height=max(0, int(minimum_height or 0)),
        negative_concepts=[str(item).strip() for item in negative_concepts if str(item).strip()][
            :12
        ],
        queries=query_values,
        important=important,
        used_asset_ids=[str(item) for item in used_asset_ids if str(item)],
        used_terms=[str(item) for item in used_terms if str(item)],
    )


def intent_from_request(request: Any) -> ImageSearchIntent:
    """Adapt either agent's request schema to the shared image intent."""

    placement = getattr(request, "placement", None)
    query = getattr(request, "query", None)
    constraints = getattr(request, "technical_constraints", None)
    purpose = str(getattr(placement, "purpose", "") or "")
    positive = list(getattr(query, "positive_terms", []) or [])
    negative = list(getattr(query, "negative_terms", []) or [])
    forbidden = list(getattr(query, "forbidden_subjects", []) or [])
    minimum = str(getattr(constraints, "minimum_dimensions", "") or "")
    minimum_width = minimum_height = 0
    match = re.match(r"\s*(\d+)\s*x\s*(\d+)", minimum.casefold())
    if match:
        minimum_width, minimum_height = int(match.group(1)), int(match.group(2))
    category = str(getattr(request, "category", "image") or "image")
    return intent_from_values(
        purpose=purpose,
        subject=" ".join(positive),
        style_mood=str(getattr(query, "style_mood", "") or ""),
        orientation=str(getattr(query, "orientation", "") or ""),
        aspect_ratio=str(
            getattr(query, "aspect_ratio", "") or getattr(constraints, "aspect_ratio", "") or ""
        ),
        minimum_width=minimum_width,
        minimum_height=minimum_height,
        negative_concepts=[*negative, *forbidden],
        queries=[" ".join(positive), purpose],
        important=any(token in purpose.casefold() for token in ("hero", "banner", "showcase")),
        media_kind="illustration" if category == "illustration" else "photo",
        theme_colors=list(getattr(query, "theme_colors", []) or []),
        category=str(getattr(query, "category", "") or ""),
        colors=list(getattr(query, "colors", []) or []),
        editors_choice=bool(getattr(query, "editors_choice", False)),
    )


class ImageSearchCache:
    """Atomic filesystem cache shared by worker processes through a volume."""

    def __init__(self, root: str | Path, ttl_seconds: int = 86400) -> None:
        self.root = Path(root)
        self.ttl_seconds = max(1, int(ttl_seconds))

    def _path(self, provider: str, query: str, filters: dict[str, Any]) -> Path:
        payload = json.dumps(
            {"schema": _SCHEMA_VERSION, "provider": provider, "query": query, "filters": filters},
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return self.root / provider / f"{digest}.json"

    def get(
        self, provider: str, query: str, filters: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        path = self._path(provider, query, filters)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("schema") != _SCHEMA_VERSION:
                return None
            if float(payload.get("expires_at", 0)) <= time.time():
                return None
            value = payload.get("candidates", [])
            # Empty responses are not durable retrieval evidence. Treat old
            # empty cache files as misses too.
            return value if isinstance(value, list) and value else None
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def put(
        self, provider: str, query: str, filters: dict[str, Any], candidates: list[dict[str, Any]]
    ) -> None:
        if not candidates:
            return
        path = self._path(provider, query, filters)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {
                "schema": _SCHEMA_VERSION,
                "expires_at": time.time() + self.ttl_seconds,
                "candidates": candidates,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=path.parent, prefix=".pending-", delete=False
            ) as fh:
                fh.write(payload)
                temporary = Path(fh.name)
            assert temporary is not None
            temporary.replace(path)
        except OSError:
            if temporary is not None:
                with contextlib.suppress(OSError):
                    temporary.unlink()


async def _respect_budget(provider: str, maximum_wait: float) -> None:
    state = _RATE_STATE.get(provider, {})
    remaining = state.get("remaining")
    reset_at = state.get("reset_at", 0.0)
    if remaining is None or remaining > 0 or reset_at <= time.time():
        return
    wait = reset_at - time.time()
    if wait > maximum_wait:
        raise ImageDownloadError(
            f"{provider} rate budget exhausted",
            details={
                "rejection_reason": "provider_rate_budget_exhausted",
                "rate_limit_event": True,
                "retry_delay": wait,
            },
        )
    await asyncio.sleep(max(0.0, wait))


def _record_headers(provider: str, response: httpx.Response) -> None:
    state = _RATE_STATE.setdefault(provider, {})
    for key, state_key in (
        ("X-RateLimit-Limit", "limit"),
        ("X-RateLimit-Remaining", "remaining"),
        ("X-RateLimit-Reset", "reset_at"),
    ):
        value = response.headers.get(key) or response.headers.get(key.replace("Rate", "rate"))
        if value is not None:
            with contextlib.suppress(ValueError):
                state[state_key] = float(value)


async def _get(
    client: httpx.AsyncClient,
    url: str,
    *,
    provider: str,
    settings: Any,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    diagnostics: list[dict[str, Any]] | None = None,
) -> httpx.Response:
    retries = max(0, int(_value(settings, "retry_count", 2)))
    timeout = float(_value(settings, "timeout_seconds", 15.0))
    max_wait = float(_value(settings, "max_retry_wait_seconds", 8.0))
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            await _respect_budget(provider, max_wait)
            response = await client.get(
                url, headers=headers, params=params, timeout=timeout, follow_redirects=True
            )
            if response.status_code < 400:
                if diagnostics is not None:
                    diagnostics.append(
                        {
                            "provider": provider,
                            "attempt": attempt + 1,
                            "http_status": response.status_code,
                            "retry_delay": 0.0,
                            "rate_limit_event": False,
                        }
                    )
                _record_headers(provider, response)
                return response
            if response.status_code not in {429, 500, 502, 503, 504}:
                raise ImageDownloadError(
                    f"{provider} rejected the request ({response.status_code})",
                    details={"http_status": response.status_code},
                )
            retry_after = response.headers.get("Retry-After", "0")
            try:
                delay = min(max_wait, max(0.0, float(retry_after)))
            except ValueError:
                delay = 0.0
            if response.status_code == 429:
                _RATE_STATE[provider] = {"remaining": 0.0, "reset_at": time.time() + delay}
            last = ImageDownloadError(
                f"{provider} returned HTTP {response.status_code}",
                details={
                    "http_status": response.status_code,
                    "retry_delay": delay,
                    "rate_limit_event": response.status_code == 429,
                },
            )
            if diagnostics is not None:
                diagnostics.append(
                    {
                        "provider": provider,
                        "attempt": attempt + 1,
                        "http_status": response.status_code,
                        "retry_delay": delay,
                        "rate_limit_event": response.status_code == 429,
                    }
                )
            if attempt < retries:
                await asyncio.sleep(delay)
        except (httpx.HTTPError, TimeoutError) as exc:
            last = exc
            if diagnostics is not None:
                diagnostics.append(
                    {
                        "provider": provider,
                        "attempt": attempt + 1,
                        "http_status": None,
                        "retry_delay": 0.0,
                        "error": type(exc).__name__,
                        "rate_limit_event": False,
                    }
                )
            if attempt < retries:
                await asyncio.sleep(0)
    if isinstance(last, ImageDownloadError):
        raise last
    raise ImageDownloadError(str(last or f"{provider} request failed"))


def _filters(intent: ImageSearchIntent) -> dict[str, Any]:
    filters: dict[str, Any] = {
        "orientation": intent.orientation,
        "aspect_ratio": intent.aspect_ratio,
        "minimum_width": intent.minimum_width,
        "minimum_height": intent.minimum_height,
        "media_kind": intent.media_kind,
        "category": intent.category,
        "colors": intent.colors,
        "editors_choice": intent.editors_choice,
        "provider_minimum_size": (
            "large"
            if max(intent.minimum_width, intent.minimum_height) >= 2000
            else "medium"
            if max(intent.minimum_width, intent.minimum_height) >= 1000
            else ""
        ),
    }
    return {key: value for key, value in filters.items() if value not in ("", 0, None)}


def _pixabay_params(intent: ImageSearchIntent, query: str, limit: int) -> dict[str, Any]:
    params: dict[str, Any] = {
        "q": query,
        "per_page": min(max(limit, 1), 20),
        "safesearch": "true",
        "order": "popular",
        "image_type": "illustration"
        if intent.media_kind in {"illustration", "vector"}
        else "photo",
    }
    if intent.category:
        params["category"] = intent.category
    if intent.colors:
        params["colors"] = ",".join(intent.colors)
    if intent.editors_choice:
        params["editors_choice"] = "true"
    if intent.orientation in {"horizontal", "landscape"}:
        params["orientation"] = "horizontal"
    elif intent.orientation == "portrait":
        params["orientation"] = "vertical"
    if intent.minimum_width:
        params["min_width"] = min(intent.minimum_width, 5000)
    if intent.minimum_height:
        params["min_height"] = min(intent.minimum_height, 5000)
    return params


def _pexels_candidate(photo: dict[str, Any], query: str, rank: int) -> ImageCandidate | None:
    source = photo.get("src") if isinstance(photo.get("src"), dict) else {}
    # Prefer a provider-sized rendition. ``original`` can be needlessly huge
    # and defeat the raw/optimized artifact limits.
    image_url = str(source.get("large2x") or source.get("large") or source.get("original") or "")
    asset_id = str(photo.get("id", "") or "")
    if not asset_id or not image_url.startswith("https://"):
        return None
    return ImageCandidate(
        provider="pexels",
        provider_asset_id=asset_id,
        title=str(photo.get("alt", "") or ""),
        description=str(photo.get("alt", "") or ""),
        tags=sorted(_tokens(str(photo.get("alt", "") or ""))),
        source_url=str(photo.get("url", "") or ""),
        image_url=image_url,
        preview_url=str(source.get("medium", image_url) or image_url),
        author=str(photo.get("photographer", "") or ""),
        author_url=str(photo.get("photographer_url", "") or ""),
        width=int(photo.get("width", 0) or 0),
        height=int(photo.get("height", 0) or 0),
        license="Pexels license",
        license_reference="https://www.pexels.com/legal-pages/license/",
        provider_rank=rank,
        query=query,
    )


def _pixabay_candidate(hit: dict[str, Any], query: str, rank: int) -> ImageCandidate | None:
    if bool(hit.get("isAiGenerated", False)):
        return None
    asset_id = str(hit.get("id", "") or "")
    image_url = str(
        hit.get("imageURL")
        or hit.get("fullHDURL")
        or hit.get("largeImageURL")
        or hit.get("webformatURL")
        or ""
    )
    if not asset_id or not image_url.startswith("https://"):
        return None
    user = str(hit.get("user", "") or "Pixabay contributor")
    page = str(hit.get("pageURL", "") or "")
    tags = sorted(_tokens(str(hit.get("tags", "") or "")))
    return ImageCandidate(
        provider="pixabay",
        provider_asset_id=asset_id,
        title=str(hit.get("tags", "") or ""),
        description=str(hit.get("tags", "") or ""),
        tags=tags,
        source_url=page,
        image_url=image_url,
        preview_url=str(hit.get("previewURL") or hit.get("webformatURL") or image_url),
        author=user,
        width=int(hit.get("imageWidth", 0) or hit.get("webformatWidth", 0) or 0),
        height=int(hit.get("imageHeight", 0) or hit.get("webformatHeight", 0) or 0),
        license="Pixabay Content License",
        license_reference="https://pixabay.com/service/license-summary/",
        popularity=float(hit.get("likes", 0) or 0) + float(hit.get("downloads", 0) or 0) / 10,
        editorial=True,
        ai_generated=False,
        provider_rank=rank,
        query=query,
    )


async def _search_provider(
    provider: str,
    intent: ImageSearchIntent,
    query: str,
    settings: Any,
    client: httpx.AsyncClient,
    limit: int,
    diagnostics: list[dict[str, Any]] | None = None,
) -> list[ImageCandidate]:
    filters = _filters(intent)
    cache = ImageSearchCache(
        _value(settings, "cache_root", ".workspace/image-search-cache"),
        int(_value(settings, "cache_ttl_seconds", 86400)),
    )
    normalized_query = " ".join(query.casefold().split())
    cached = cache.get(provider, normalized_query, filters)
    if cached is not None:
        if diagnostics is not None:
            diagnostics.append(
                {
                    "provider": provider,
                    "query": query,
                    "attempt": 0,
                    "http_status": None,
                    "retry_delay": 0.0,
                    "cache_state": "hit",
                    "configured_key": _provider_key_configured(settings, provider),
                    "candidate_count": len(cached),
                }
            )
        return [ImageCandidate.model_validate(item) for item in cached]
    if provider == "pexels":
        key = _provider_key(settings, "pexels_api_key_env", "PEXELS_API_KEY")
        if not key:
            if diagnostics is not None:
                diagnostics.append(
                    {
                        "provider": provider,
                        "query": query,
                        "attempt": 0,
                        "http_status": None,
                        "retry_delay": 0.0,
                        "cache_state": "miss",
                        "configured_key": False,
                        "candidate_count": 0,
                    }
                )
            return []
        params: dict[str, Any] = {"query": query, "per_page": min(max(limit, 1), 20)}
        if intent.orientation in {"landscape", "portrait", "square"}:
            params["orientation"] = intent.orientation
        if max(intent.minimum_width, intent.minimum_height) >= 2000:
            params["size"] = "large"
        elif max(intent.minimum_width, intent.minimum_height) >= 1000:
            params["size"] = "medium"
        if intent.colors:
            params["color"] = intent.colors[0]
        response = await _get(
            client,
            "https://api.pexels.com/v1/search",
            provider=provider,
            settings=settings,
            headers={"Authorization": key, "Accept": "application/json"},
            params=params,
            diagnostics=diagnostics,
        )
        payload = response.json()
        raw = payload.get("photos", []) if isinstance(payload, dict) else []
        candidates = [
            item
            for index, photo in enumerate(raw)
            if isinstance(photo, dict)
            and (item := _pexels_candidate(photo, query, index)) is not None
        ]
    elif provider == "pixabay":
        key = _provider_key(settings, "pixabay_api_key_env", "PIXABAY_API_KEY")
        if not key:
            if diagnostics is not None:
                diagnostics.append(
                    {
                        "provider": provider,
                        "query": query,
                        "attempt": 0,
                        "http_status": None,
                        "retry_delay": 0.0,
                        "cache_state": "miss",
                        "configured_key": False,
                        "candidate_count": 0,
                    }
                )
            return []
        params = _pixabay_params(intent, query, limit)
        params["key"] = key
        response = await _get(
            client,
            "https://pixabay.com/api/",
            provider=provider,
            settings=settings,
            headers={"Accept": "application/json"},
            params=params,
            diagnostics=diagnostics,
        )
        payload = response.json()
        raw = payload.get("hits", []) if isinstance(payload, dict) else []
        candidates = [
            item
            for index, hit in enumerate(raw)
            if isinstance(hit, dict) and (item := _pixabay_candidate(hit, query, index)) is not None
        ]
    elif provider == "unsplash":
        if not (
            _value(settings, "unsplash_enabled", False)
            and _value(settings, "unsplash_local_vendoring_authorized", False)
        ):
            return []
        key = _provider_key(settings, "unsplash_access_key_env", "UNSPLASH_ACCESS_KEY")
        if not key:
            return []
        response = await _get(
            client,
            "https://api.unsplash.com/search/photos",
            provider=provider,
            settings=settings,
            headers={"Authorization": f"Client-ID {key}", "Accept": "application/json"},
            params={"query": query, "per_page": min(max(limit, 1), 5)},
            diagnostics=diagnostics,
        )
        payload = response.json()
        candidates = []
        for index, photo in enumerate(
            payload.get("results", []) if isinstance(payload, dict) else []
        ):
            if not isinstance(photo, dict):
                continue
            urls = photo.get("urls") if isinstance(photo.get("urls"), dict) else {}
            user = photo.get("user") if isinstance(photo.get("user"), dict) else {}
            links = photo.get("links") if isinstance(photo.get("links"), dict) else {}
            image_url = str(urls.get("full") or urls.get("regular") or "")
            if not image_url.startswith("https://"):
                continue
            candidates.append(
                ImageCandidate(
                    provider="unsplash",
                    provider_asset_id=str(photo.get("id", "")),
                    title=str(photo.get("alt_description") or ""),
                    description=str(photo.get("description") or ""),
                    tags=sorted(_tokens(str(photo.get("alt_description") or ""))),
                    source_url=str(links.get("html", "")),
                    image_url=image_url,
                    preview_url=str(urls.get("small") or image_url),
                    author=str(user.get("name", "")),
                    author_url=str(
                        (user.get("links") or {}).get("html", "")
                        if isinstance(user.get("links"), dict)
                        else ""
                    ),
                    width=int(photo.get("width", 0) or 0),
                    height=int(photo.get("height", 0) or 0),
                    license="Unsplash license",
                    license_reference="https://unsplash.com/license",
                    provider_rank=index,
                    query=query,
                    download_tracking_url=str(links.get("download_location", "")),
                )
            )
    else:
        return []
    cache.put(
        provider,
        normalized_query,
        filters,
        [item.model_dump(mode="json") for item in candidates],
    )
    if diagnostics is not None:
        diagnostics.append(
            {
                "provider": provider,
                "query": query,
                "attempt": 1,
                "http_status": 200,
                "retry_delay": 0.0,
                "cache_state": "miss",
                "configured_key": True,
                "candidate_count": len(candidates),
            }
        )
    return candidates


def _weak(candidates: list[ImageCandidate], intent: ImageSearchIntent) -> bool:
    if not candidates:
        return True
    terms = _tokens([intent.subject, intent.purpose, intent.style_mood])
    top = candidates[0]
    overlap = len(terms.intersection(_tokens([top.title, top.description, *top.tags])))
    if intent.minimum_width and top.width < intent.minimum_width:
        return True
    if intent.minimum_height and top.height < intent.minimum_height:
        return True
    return bool(terms) and overlap == 0


def rank_image_candidates(
    candidates: Iterable[ImageCandidate], intent: ImageSearchIntent
) -> list[ImageCandidate]:
    terms = _tokens([intent.subject, intent.purpose, intent.style_mood, *intent.theme_colors])
    forbidden = _tokens(intent.negative_concepts)
    used_ids = set(intent.used_asset_ids)
    used_terms = _tokens(intent.used_terms)
    target_ratio = _ratio(intent.aspect_ratio)

    def score(candidate: ImageCandidate) -> tuple[float, str, str]:
        metadata = _tokens([candidate.title, candidate.description, *candidate.tags])
        semantic = 100.0 * len(terms.intersection(metadata)) / max(1, len(terms))
        if forbidden.intersection(metadata):
            semantic -= 35.0
        quality = 100.0
        if intent.minimum_width:
            quality = min(quality, 100.0 * candidate.width / intent.minimum_width)
        if intent.minimum_height:
            quality = min(quality, 100.0 * candidate.height / intent.minimum_height)
        if target_ratio and candidate.width and candidate.height:
            quality = max(
                0.0,
                quality - min(35.0, abs(candidate.width / candidate.height - target_ratio) * 35),
            )
        popularity = min(100.0, candidate.popularity / 10.0) + (
            10.0 if candidate.editorial else 0.0
        )
        diversity = -45.0 if candidate.provider_asset_id in used_ids else 0.0
        if used_terms and metadata.intersection(used_terms):
            diversity -= 12.0
        total = semantic * 0.45 + quality * 0.25 + popularity * 0.15 + (100.0 + diversity) * 0.15
        return total, candidate.provider, candidate.provider_asset_id

    return sorted(candidates, key=lambda item: score(item), reverse=True)


async def search_images(
    intent: ImageSearchIntent,
    settings: Any,
    *,
    providers: Iterable[str] | None = None,
    client: httpx.AsyncClient | None = None,
    limit: int | None = None,
    diagnostics: list[dict[str, Any]] | None = None,
) -> list[ImageCandidate]:
    """Search a bounded provider set and return deterministic ranked metadata."""

    configured = list(providers or _value(settings, "provider_order", ["pexels", "pixabay"]))
    configured = [item for item in configured if item in {"pexels", "pixabay", "unsplash"}]
    if not configured:
        return []
    query_limit = max(1, int(_value(settings, "max_queries", 3)))
    logical_queries = compile_search_queries(intent, max_variants=query_limit)
    if intent.queries:
        # Preserve explicit, already-approved variants but normalize their
        # term/length budget before transport.
        explicit = [
            compile_provider_query(intent, value, "")
            for value in intent.queries[:query_limit]
            if str(value).strip()
        ]
        queries = list(dict.fromkeys(explicit or logical_queries))[:query_limit]
    else:
        queries = logical_queries
    candidate_limit = limit or int(_value(settings, "max_candidates_per_query", 6))
    own_client = client is None
    http = client or httpx.AsyncClient()
    try:
        found: list[ImageCandidate] = []
        for query in queries:
            if not query.strip():
                continue
            if intent.important:
                for provider in configured:
                    sent_query = compile_provider_query(intent, query, provider)
                    try:
                        found.extend(
                            await _search_provider(
                                provider,
                                intent,
                                sent_query,
                                settings,
                                http,
                                candidate_limit,
                                diagnostics,
                            )
                        )
                    except (ImageDownloadError, ValueError, httpx.HTTPError):
                        continue
            else:
                for provider in configured:
                    sent_query = compile_provider_query(intent, query, provider)
                    try:
                        batch = await _search_provider(
                            provider,
                            intent,
                            sent_query,
                            settings,
                            http,
                            candidate_limit,
                            diagnostics,
                        )
                    except (ImageDownloadError, ValueError, httpx.HTTPError):
                        batch = []
                    found.extend(batch)
                    has_unused_asset = any(
                        candidate.provider_asset_id not in set(intent.used_asset_ids)
                        for candidate in batch
                    )
                    if batch and has_unused_asset and not _weak(batch, intent):
                        break
        unique: dict[tuple[str, str], ImageCandidate] = {}
        for candidate in found:
            unique.setdefault((candidate.provider, candidate.provider_asset_id), candidate)
        unique_candidates = list(unique.values())
        used_ids = set(intent.used_asset_ids)
        unused_candidates = [
            candidate
            for candidate in unique_candidates
            if candidate.provider_asset_id not in used_ids
        ]
        # Provider search results are often stable across semantically
        # different queries. Prefer a genuinely new provider asset whenever
        # one exists; only reuse a prior asset when the closed provider result
        # set has no unused candidate at all.
        ranked_pool = unused_candidates or unique_candidates
        return rank_image_candidates(ranked_pool, intent)[
            : max(1, int(_value(settings, "max_candidates_total", 12)))
        ]
    finally:
        if own_client:
            await http.aclose()


async def download_image_bytes(
    candidate_or_url: ImageCandidate | Any,
    settings: Any,
    *,
    client: httpx.AsyncClient | None = None,
    max_bytes: int = 12 * 1024 * 1024,
) -> bytes:
    provider = str(
        getattr(candidate_or_url, "provider", "")
        or getattr(candidate_or_url, "provider_key", "")
        or ""
    )
    if isinstance(candidate_or_url, str):
        url = candidate_or_url
    else:
        url = str(
            getattr(candidate_or_url, "image_url", "")
            or getattr(candidate_or_url, "canonical_source", "")
            or ""
        )
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_HOSTS.get(provider, set()):
        raise ImageDownloadError(
            f"{provider} image URL is not approved",
            details={
                "rejection_reason": "unapproved_https_host",
                "url_host": parsed.hostname or "",
            },
        )
    own_client = client is None
    http = client or httpx.AsyncClient()
    try:
        headers = {"Accept": "image/*"}
        if provider == "pexels":
            key = _provider_key(settings, "pexels_api_key_env", "PEXELS_API_KEY")
            if key:
                headers["Authorization"] = key
        response = await _get(http, url, provider=provider, settings=settings, headers=headers)
        if response.url.scheme != "https" or response.url.host not in _ALLOWED_HOSTS.get(
            provider, set()
        ):
            raise ImageDownloadError(
                f"{provider} redirected to an unapproved image host",
                details={
                    "rejection_reason": "redirected_to_unapproved_host",
                    "url_host": response.url.host or "",
                },
            )
        content_type = response.headers.get("content-type", "").casefold()
        raw_size = len(response.content)
        if not content_type.startswith("image/"):
            raise ImageDownloadError(
                f"{provider} returned a non-image response",
                details={
                    "rejection_reason": "response_content_type_not_image",
                    "response_content_type": content_type,
                    "raw_byte_size": raw_size,
                    "configured_raw_limit": max_bytes,
                },
            )
        if raw_size > max_bytes:
            raise ImageDownloadError(
                f"{provider} returned an oversized image",
                details={
                    "rejection_reason": "raw_download_size_limit",
                    "response_content_type": content_type,
                    "raw_byte_size": raw_size,
                    "configured_raw_limit": max_bytes,
                },
            )
        return response.content
    finally:
        if own_client:
            await http.aclose()


def prepare_image_bytes(
    data: bytes,
    intent: ImageSearchIntent | None = None,
    *,
    max_bytes: int = 8 * 1024 * 1024,
    max_dimension: int = 2400,
) -> tuple[bytes, dict[str, Any]]:
    """Decode, orient, crop to the requested ratio, and optimize when useful."""

    try:
        with Image.open(io.BytesIO(data)) as source:
            source.verify()
        with Image.open(io.BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
    except Exception as exc:
        raise ImageDownloadError(
            "image bytes are corrupt or not a supported raster",
            details={
                "rejection_reason": "corrupt_or_unsupported_raster",
                "raw_byte_size": len(data),
            },
        ) from exc
    original_width, original_height = image.size
    if (
        intent
        and (intent.minimum_width or intent.minimum_height)
        and (
            (intent.minimum_width and original_width < intent.minimum_width)
            or (intent.minimum_height and original_height < intent.minimum_height)
        )
    ):
        raise ImageDownloadError(
            "image dimensions are below the requested minimum",
            details={
                "rejection_reason": "minimum_dimensions",
                "raw_byte_size": len(data),
                "original_width": original_width,
                "original_height": original_height,
                "minimum_width": intent.minimum_width,
                "minimum_height": intent.minimum_height,
            },
        )
    if max_dimension > 0 and max(image.size) > max_dimension:
        scale = max_dimension / max(image.size)
        image = image.resize(
            (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
            Image.Resampling.LANCZOS,
        )
    target_ratio = _ratio(intent.aspect_ratio) if intent else None
    if target_ratio and image.width and image.height:
        current = image.width / image.height
        if abs(current - target_ratio) / target_ratio > 0.08:
            if current > target_ratio:
                width = max(1, int(image.height * target_ratio))
                left = max(0, (image.width - width) // 2)
                image = image.crop((left, 0, left + width, image.height))
            else:
                height = max(1, int(image.width / target_ratio))
                top = max(0, (image.height - height) // 2)
                image = image.crop((0, top, image.width, top + height))
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=88, optimize=True, progressive=True)
    optimized = output.getvalue()
    if len(optimized) > max_bytes:
        for quality in (82, 76, 68):
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
            optimized = output.getvalue()
            if len(optimized) <= max_bytes:
                break
    if len(optimized) > max_bytes:
        raise ImageDownloadError(
            "optimized image exceeds the configured local size limit",
            details={
                "rejection_reason": "optimized_size_limit",
                "raw_byte_size": len(data),
                "optimized_byte_size": len(optimized),
                "configured_optimized_limit": max_bytes,
                "pixel_width": image.width,
                "pixel_height": image.height,
            },
        )
    if len(optimized) > len(data) and not target_ratio and len(data) <= max_bytes:
        optimized = data
    return optimized, {
        "original_width": original_width,
        "original_height": original_height,
        "pixel_width": image.width,
        "pixel_height": image.height,
        "sha256": hashlib.sha256(optimized).hexdigest(),
        "output_mime_type": "image/jpeg" if optimized != data else "original",
    }
