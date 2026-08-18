"""Trusted, provider-neutral resource acquisition adapters.

The adapters expose textual candidate metadata to orchestration and materialize
bytes only in trusted Python. The offline registry is the normal automated-test
path; configured HTTP providers are deliberately small and never expose a raw
client or credentials to a model.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from collections.abc import Iterable
from contextlib import suppress
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Protocol

import httpx

from oryxenai.agents.code_generator.core.acquisition_validators import (
    AcquisitionValidationError,
    inspect_bytes,
)
from oryxenai.agents.code_generator.core.development_schemas import (
    LocalMaterialFile,
    ResourceCandidate,
    ResourceRequest,
)
from oryxenai.agents.shared.component_retrieval import (
    ComponentCandidate,
    ComponentRetrievalError,
    build_component_retrieval_service,
)


class ResourceProviderError(RuntimeError):
    """A provider failed after trusted retry policy was applied."""

    def __init__(self, message: str, *, provider: str, retryable: bool = True) -> None:
        self.code = "RESOURCE_PROVIDER_UNAVAILABLE"
        self.provider = provider
        self.retryable = retryable
        super().__init__(message)


class ResourceAdapter(Protocol):
    category: str

    async def search(
        self, request: ResourceRequest, *, settings: Any
    ) -> list[ResourceCandidate]: ...

    async def materialize(
        self,
        candidate: ResourceCandidate,
        request: ResourceRequest,
        *,
        storage_root: Path,
        settings: Any,
    ) -> LocalMaterialFile | list[LocalMaterialFile]: ...


class OfflineResourceProviderRegistry:
    """Deterministic provider registry used by tests and the local harness."""

    def __init__(self) -> None:
        self._entries: dict[str, list[tuple[ResourceCandidate, bytes]]] = {}

    def register(self, candidate: ResourceCandidate, data: bytes) -> None:
        self._entries.setdefault(candidate.provider_key, []).append((candidate, bytes(data)))

    def candidates(self, provider_keys: Iterable[str], category: str) -> list[ResourceCandidate]:
        result: list[ResourceCandidate] = []
        for provider_key in provider_keys:
            result.extend(
                candidate
                for candidate, _ in self._entries.get(provider_key, [])
                if candidate.category == category
            )
        return result

    def bytes_for(self, candidate_id: str) -> bytes:
        for entries in self._entries.values():
            for candidate, data in entries:
                if candidate.candidate_id == candidate_id:
                    return data
        raise ResourceProviderError(
            "The offline resource candidate has no materialized bytes.",
            provider="offline",
            retryable=False,
        )

    @classmethod
    def from_directory(cls, root: Path) -> OfflineResourceProviderRegistry:
        registry = cls()
        if not root.is_dir():
            return registry
        for metadata_path in sorted(root.rglob("*.meta.json")):
            data_path = metadata_path.with_name(metadata_path.name.removesuffix(".meta.json"))
            if not data_path.is_file():
                continue
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                candidate = ResourceCandidate.model_validate(metadata)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
                continue
            registry.register(candidate, data_path.read_bytes())
        return registry


def _stable_id(prefix: str, value: str) -> str:
    return f"resource-{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:20]}"


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _env_value(settings: Any, field: str) -> str:
    name = str(getattr(settings.resource_providers, field, "") or "")
    return os.environ.get(name, "") if name else ""


async def _get(
    client: httpx.AsyncClient,
    url: str,
    *,
    provider: str,
    headers: dict[str, str] | None = None,
    params: dict[str, str | int] | None = None,
    retries: int = 2,
) -> httpx.Response:
    last: str = "request failed"
    for attempt in range(max(0, retries) + 1):
        try:
            response = await client.get(
                url,
                headers=headers,
                params=params,
                timeout=15.0,
                follow_redirects=False,
            )
        except httpx.TimeoutException as exc:
            last = "request timed out"
            if attempt >= retries:
                raise ResourceProviderError(last, provider=provider) from exc
        except httpx.HTTPError as exc:
            last = "connection failed"
            if attempt >= retries:
                raise ResourceProviderError(last, provider=provider) from exc
        else:
            if response.status_code < 400:
                return response
            if response.status_code == 429 or response.status_code >= 500:
                last = f"provider returned HTTP {response.status_code}"
                if attempt < retries:
                    retry_after = response.headers.get("Retry-After", "0")
                    with suppress(ValueError):
                        await asyncio.sleep(min(5.0, max(0.0, float(retry_after))))
                    continue
            raise ResourceProviderError(
                f"{provider} rejected the resource request", provider=provider, retryable=False
            )
        if attempt < retries:
            await asyncio.sleep(0)
    raise ResourceProviderError(last, provider=provider)


async def _download_url(client: httpx.AsyncClient, url: str) -> bytes:
    response = await _get(client, url, provider="fontsource")
    return response.content


def _safe_relative(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or bool(PureWindowsPath(value).drive)
        or ".." in path.parts
        or any(not part or any(ord(char) < 32 for char in part) for part in path.parts)
    ):
        raise AcquisitionValidationError(
            "SOURCE_PATH_UNSAFE", "The resource source path is unsafe."
        )
    return path.as_posix()


def _extension(category: str, inspection: dict[str, str | int | float | bool]) -> str:
    media_type = str(inspection.get("media_type", ""))
    return {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif",
        "image/svg+xml": "svg",
        "font/woff": "woff",
        "font/woff2": "woff2",
        "text/plain": "txt",
    }.get(media_type, "svg" if category == "icon" else "bin")


class _BaseAdapter:
    category = ""

    def __init__(self, registry: OfflineResourceProviderRegistry | None = None) -> None:
        self.registry = registry

    def _offline_candidates(
        self, request: ResourceRequest, providers: list[str]
    ) -> list[ResourceCandidate]:
        if self.registry is None:
            return []
        return self.registry.candidates(providers, self.category)

    async def _download(self, candidate: ResourceCandidate) -> bytes:
        if self.registry is not None:
            try:
                return self.registry.bytes_for(candidate.candidate_id)
            except ResourceProviderError:
                pass
        url = candidate.canonical_source
        if not url.startswith("https://"):
            raise ResourceProviderError(
                "The candidate source is not an approved HTTPS URL.",
                provider=candidate.provider_key,
                retryable=False,
            )
        async with httpx.AsyncClient() as client:
            response = await _get(client, url, provider=candidate.provider_key)
        return response.content

    async def materialize(
        self,
        candidate: ResourceCandidate,
        request: ResourceRequest,
        *,
        storage_root: Path,
        settings: Any,
    ) -> LocalMaterialFile | list[LocalMaterialFile]:
        data = await self._download(candidate)
        max_bytes = request.technical_constraints.max_bytes or _category_limit(
            self.category, settings
        )
        inspection = inspect_bytes(data, category=self.category, max_bytes=max_bytes or None)
        if request.technical_constraints.minimum_dimensions:
            _validate_dimensions(inspection, request.technical_constraints.minimum_dimensions)
        digest = str(inspection["sha256"])
        category_root = (storage_root / self.category).resolve()
        root = Path(storage_root).resolve()
        if not category_root.is_relative_to(root):
            raise AcquisitionValidationError(
                "MATERIAL_ROOT_UNSAFE", "The materialization root is unsafe."
            )
        category_root.mkdir(parents=True, exist_ok=True)
        filename = f"{digest}.{_extension(self.category, inspection)}"
        target = category_root / filename
        target.write_bytes(data)
        relative = target.relative_to(root).as_posix()
        license_dir = root / "licences"
        license_dir.mkdir(parents=True, exist_ok=True)
        license_path = license_dir / f"{digest}.json"
        license_path.write_text(
            json.dumps(
                {
                    "provider": candidate.provider_key,
                    "canonical_source": candidate.canonical_source,
                    "licence": candidate.licence,
                    "attribution": candidate.attribution,
                    "sha256": digest,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        inspection = dict(inspection)
        inspection["licence_path"] = license_path.relative_to(root).as_posix()
        return LocalMaterialFile(
            local_path=relative,
            media_type=str(inspection.get("media_type", "application/octet-stream")),
            size=len(data),
            sha256=digest,
            inspection=inspection,
        )


class ImageAdapter(_BaseAdapter):
    category = "image"

    def __init__(
        self, registry: OfflineResourceProviderRegistry | None = None, *, category: str = "image"
    ) -> None:
        super().__init__(registry)
        self.category = category

    async def search(self, request: ResourceRequest, *, settings: Any) -> list[ResourceCandidate]:
        providers = list(
            getattr(settings.code_generator_acquisition, "allowlist_image_providers", [])
        )
        offline = self._offline_candidates(request, [*providers, "fixture"])
        if offline or self.registry is not None:
            return offline
        query = " ".join(request.query.positive_terms)
        candidates: list[ResourceCandidate] = []
        pexels_key = _env_value(settings, "pexels_api_key_env")
        if "pexels" in providers and pexels_key:
            async with httpx.AsyncClient() as client:
                response = await _get(
                    client,
                    "https://api.pexels.com/v1/search",
                    provider="pexels",
                    headers={"Authorization": pexels_key},
                    params={"query": query, "per_page": 5},
                )
            payload = response.json()
            for photo in payload.get("photos", []):
                source = str(photo.get("src", {}).get("large", ""))
                if source:
                    candidates.append(
                        ResourceCandidate(
                            candidate_id=_stable_id("pexels", str(photo.get("id", source))),
                            provider_key="pexels",
                            provider_resource_id=str(photo.get("id", "")),
                            category=self.category,
                            title=str(photo.get("alt", "")) or "Editorial image",
                            description=str(photo.get("alt", "")),
                            tags=sorted(_tokens(str(photo.get("alt", "")))),
                            technical_metadata={
                                "width": int(photo.get("width", 0) or 0),
                                "height": int(photo.get("height", 0) or 0),
                            },
                            canonical_source=source,
                            licence="Pexels License",
                            attribution=f"Photo by {photo.get('photographer', 'Pexels contributor')}",
                            vendoring_policy="download and vendor",
                        )
                    )
        unsplash_key = _env_value(settings, "unsplash_access_key_env")
        if "unsplash" in providers and unsplash_key:
            async with httpx.AsyncClient() as client:
                response = await _get(
                    client,
                    "https://api.unsplash.com/search/photos",
                    provider="unsplash",
                    headers={"Authorization": f"Client-ID {unsplash_key}"},
                    params={"query": query, "per_page": 5},
                )
            payload = response.json()
            for photo in payload.get("results", []):
                source = str(photo.get("urls", {}).get("regular", ""))
                if source:
                    candidates.append(
                        ResourceCandidate(
                            candidate_id=_stable_id("unsplash", str(photo.get("id", source))),
                            provider_key="unsplash",
                            provider_resource_id=str(photo.get("id", "")),
                            category=self.category,
                            title=str(photo.get("alt_description", "")) or "Editorial image",
                            description=str(
                                photo.get("description", "") or photo.get("alt_description", "")
                            ),
                            tags=sorted(
                                _tokens(
                                    str(
                                        photo.get("description", "")
                                        or photo.get("alt_description", "")
                                    )
                                )
                            ),
                            technical_metadata={
                                "width": int(photo.get("width", 0) or 0),
                                "height": int(photo.get("height", 0) or 0),
                            },
                            canonical_source=source,
                            licence="Unsplash License",
                            attribution=f"Photo by {photo.get('user', {}).get('name', 'Unsplash contributor')}",
                            vendoring_policy="download and vendor",
                        )
                    )
        return candidates


class FontAdapter(_BaseAdapter):
    category = "font"

    async def search(self, request: ResourceRequest, *, settings: Any) -> list[ResourceCandidate]:
        providers = ["fixture", "local", "fontsource"]
        offline = self._offline_candidates(request, providers)
        if offline or self.registry is not None:
            return offline
        if not bool(getattr(settings.resource_providers, "fontsource_enabled", True)):
            return []
        base = str(
            getattr(settings.resource_providers, "fontsource_api_base_url", "") or ""
        ).rstrip("/")
        if not base:
            return []
        terms = _tokens(" ".join(request.query.positive_terms))
        async with httpx.AsyncClient() as client:
            response = await _get(
                client,
                f"{base}/fonts",
                provider="fontsource",
                params={"subsets": "latin"},
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
            candidates: list[ResourceCandidate] = []
            for _, item in ranked[:3]:
                font_id = str(item["id"])
                detail_response = await _get(
                    client, f"{base}/fonts/{font_id}", provider="fontsource"
                )
                detail = detail_response.json()
                urls: dict[str, str] = {}
                variants = detail.get("variants", {}) if isinstance(detail, dict) else {}
                if isinstance(variants, dict):
                    for weight in ("400", "500", "600", "700"):
                        normal = (
                            variants.get(weight, {}).get("normal", {})
                            if isinstance(variants.get(weight), dict)
                            else {}
                        )
                        latin = normal.get("latin", {}) if isinstance(normal, dict) else {}
                        url_map = latin.get("url", {}) if isinstance(latin, dict) else {}
                        format_name = str(
                            getattr(settings.resource_providers, "fontsource_format", "woff2")
                        )
                        url = str(url_map.get(format_name, "")) if isinstance(url_map, dict) else ""
                        if url.startswith("https://cdn.jsdelivr.net/"):
                            urls[f"{weight}-normal"] = url
                if not urls:
                    continue
                candidates.append(
                    ResourceCandidate(
                        candidate_id=_stable_id("fontsource", font_id),
                        provider_key="fontsource",
                        provider_resource_id=font_id,
                        category="font",
                        title=str(detail.get("family", font_id)),
                        description="Fontsource Latin font files",
                        tags=sorted(_tokens(str(detail.get("family", font_id)))),
                        technical_metadata={
                            "font_family": str(detail.get("family", font_id)),
                            "font_weights": sorted({key.split("-", 1)[0] for key in urls}),
                            "font_urls": urls,
                            "font_format": str(
                                getattr(settings.resource_providers, "fontsource_format", "woff2")
                            ),
                        },
                        canonical_source=next(iter(urls.values())),
                        licence="OFL-1.1",
                        attribution="Fontsource / SIL Open Font License",
                        vendoring_policy="download and vendor",
                    )
                )
            return candidates

    async def materialize(
        self,
        candidate: ResourceCandidate,
        request: ResourceRequest,
        *,
        storage_root: Path,
        settings: Any,
    ) -> LocalMaterialFile | list[LocalMaterialFile]:
        urls = candidate.technical_metadata.get("font_urls")
        if not isinstance(urls, dict):
            return await super().materialize(
                candidate, request, storage_root=storage_root, settings=settings
            )
        root = Path(storage_root).resolve()
        category_root = (root / self.category).resolve()
        if not category_root.is_relative_to(root):
            raise AcquisitionValidationError(
                "MATERIAL_ROOT_UNSAFE", "The materialization root is unsafe."
            )
        category_root.mkdir(parents=True, exist_ok=True)
        results: list[LocalMaterialFile] = []
        async with httpx.AsyncClient() as client:
            for variant, value in sorted(urls.items()):
                url = str(value)
                if not url.startswith("https://cdn.jsdelivr.net/"):
                    raise AcquisitionValidationError(
                        "FONT_SOURCE_UNSAFE", "The font source is not approved."
                    )
                data = await (
                    self._download(candidate)
                    if url == candidate.canonical_source
                    else _download_url(client, url)
                )
                inspection = inspect_bytes(
                    data,
                    category="font",
                    max_bytes=request.technical_constraints.max_bytes
                    or _category_limit("font", settings)
                    or None,
                )
                digest = str(inspection["sha256"])
                suffix = str(candidate.technical_metadata.get("font_format", "woff2"))
                target = category_root / f"{digest}-{_safe_relative(variant)}.{suffix}"
                target.write_bytes(data)
                results.append(
                    LocalMaterialFile(
                        local_path=target.relative_to(root).as_posix(),
                        media_type=str(inspection.get("media_type", "font/woff2")),
                        size=len(data),
                        sha256=digest,
                        inspection=inspection,
                    )
                )
        return results


class IconAdapter(_BaseAdapter):
    category = "icon"

    async def search(self, request: ResourceRequest, *, settings: Any) -> list[ResourceCandidate]:
        package = str(
            getattr(settings.code_generator_acquisition, "allowlist_icon_package", "lucide")
        )
        candidates = self._offline_candidates(request, [package, "fixture"])
        if candidates or self.registry is not None:
            return candidates
        terms = request.query.positive_terms or ["circle"]
        name = re.sub(r"[^a-z0-9-]", "-", terms[0].casefold()).strip("-") or "circle"
        template = str(getattr(settings.resource_providers, "lucide_icon_url_template", ""))
        if not template:
            return []
        return [
            ResourceCandidate(
                candidate_id=_stable_id("lucide", name),
                provider_key="lucide",
                provider_resource_id=name,
                category=self.category,
                title=name,
                tags=[name, "icon"],
                canonical_source=template.format(name=name),
                licence="ISC",
                attribution="Lucide",
                vendoring_policy="download and vendor",
            )
        ]


class ComponentSourceAdapter(_BaseAdapter):
    category = "component_source"

    async def search(self, request: ResourceRequest, *, settings: Any) -> list[ResourceCandidate]:
        providers = list(
            getattr(settings.code_generator_acquisition, "allowlist_component_registries", [])
        )
        offline = self._offline_candidates(request, [*providers, "fixture"])
        if offline or self.registry is not None:
            return offline
        query = " ".join(
            [
                request.placement.purpose,
                *request.query.positive_terms,
                *request.query.negative_terms,
            ]
        ).strip()
        service = build_component_retrieval_service(settings)
        async with httpx.AsyncClient() as client:
            discovered = await service.discover(
                query,
                allowed_providers=providers,
                client=client,
                settings=settings,
                limit=5,
            )
        return [
            ResourceCandidate(
                candidate_id=item.candidate_id,
                provider_key=item.provider,
                provider_resource_id=item.name,
                category=self.category,
                title=item.title,
                description=item.description,
                tags=list(item.tags),
                technical_metadata={
                    "retrieval_candidate": item.as_metadata(),
                    "file_paths": [],
                },
                canonical_source=item.item_url,
                licence=item.license,
                vendoring_policy="download and vendor source",
                dependency_metadata={dependency: [] for dependency in item.dependencies},
            )
            for item in discovered
        ]

    async def materialize(
        self,
        candidate: ResourceCandidate,
        request: ResourceRequest,
        *,
        storage_root: Path,
        settings: Any,
    ) -> LocalMaterialFile | list[LocalMaterialFile]:
        paths = candidate.technical_metadata.get("file_paths", [])
        if isinstance(paths, list):
            for path in paths:
                _safe_relative(str(path))
        for package_name in candidate.dependency_metadata:
            if any(
                token in package_name.casefold() for token in ("://", "git+", "file:", "workspace:")
            ):
                raise AcquisitionValidationError(
                    "DEPENDENCY_SOURCE_UNSAFE",
                    "The component declares an unsafe dependency source.",
                )
        if candidate.technical_metadata.get("install_scripts", False):
            raise AcquisitionValidationError(
                "COMPONENT_INSTALL_SCRIPT",
                "Component source requiring install scripts is not admissible.",
            )
        retrieval_value = candidate.technical_metadata.get("retrieval_candidate")
        if isinstance(retrieval_value, dict) and self.registry is None:
            selected = ComponentCandidate.from_metadata(retrieval_value)
            service = build_component_retrieval_service(settings)
            async with httpx.AsyncClient() as client:
                try:
                    fetched = await service.fetch(selected, client=client, settings=settings)
                except ComponentRetrievalError as exc:
                    raise AcquisitionValidationError(
                        exc.code,
                        f"The live component source could not be fetched: {exc}",
                    ) from exc
            if not fetched.source_files:
                raise AcquisitionValidationError(
                    "COMPONENT_SOURCE_MISSING", "The live component returned no source files."
                )
            root = Path(storage_root).resolve()
            component_root = (
                root / "component_source" / selected.provider / selected.name
            ).resolve()
            if not component_root.is_relative_to(root):
                raise AcquisitionValidationError(
                    "MATERIAL_ROOT_UNSAFE", "The component materialization root is unsafe."
                )
            component_root.mkdir(parents=True, exist_ok=True)
            licence_dir = root / "licences"
            licence_dir.mkdir(parents=True, exist_ok=True)
            files: list[LocalMaterialFile] = []
            for source_path, content in fetched.source_files.items():
                safe_path = _safe_relative(source_path)
                data = content.encode("utf-8")
                inspection = inspect_bytes(
                    data,
                    category=self.category,
                    max_bytes=_category_limit(self.category, settings),
                )
                target = (component_root / safe_path).resolve()
                if not target.is_relative_to(component_root):
                    raise AcquisitionValidationError(
                        "SOURCE_PATH_UNSAFE", "The component source path escapes its provider root."
                    )
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                digest = str(inspection["sha256"])
                license_path = licence_dir / f"{digest}.json"
                license_path.write_text(
                    json.dumps(
                        {
                            "provider": selected.provider,
                            "canonical_source": selected.item_url,
                            "licence": fetched.license,
                            "licence_reference": fetched.license_reference,
                            "sha256": digest,
                        },
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )
                inspection = dict(inspection)
                inspection["licence_path"] = license_path.relative_to(root).as_posix()
                files.append(
                    LocalMaterialFile(
                        local_path=target.relative_to(root).as_posix(),
                        media_type=str(inspection.get("media_type", "text/plain")),
                        size=len(data),
                        sha256=digest,
                        inspection=inspection,
                    )
                )
            return files
        return await super().materialize(
            candidate, request, storage_root=storage_root, settings=settings
        )


class StylePrimitiveAdapter(_BaseAdapter):
    category = "style_primitive"

    async def search(self, request: ResourceRequest, *, settings: Any) -> list[ResourceCandidate]:
        providers = list(getattr(settings.code_generator_acquisition, "allowlist_style_kinds", []))
        return self._offline_candidates(request, [*providers, "fixture"])


def _category_limit(category: str, settings: Any) -> int:
    config = getattr(settings, "code_generator_acquisition", None)
    if config is None:
        return 0
    if category == "icon":
        return int(getattr(config, "icon_svg_max_bytes", 0))
    if category == "component_source":
        return int(getattr(config, "component_max_bytes", 0))
    if category == "style_primitive":
        return int(getattr(config, "style_max_bytes", 0))
    return int(getattr(config, f"{category}_max_bytes", 0))


def _validate_dimensions(inspection: dict[str, str | int | float | bool], value: str) -> None:
    try:
        minimum_width, minimum_height = (int(part) for part in value.lower().split("x", 1))
        width = int(inspection.get("width", 0))
        height = int(inspection.get("height", 0))
    except (TypeError, ValueError) as exc:
        raise AcquisitionValidationError(
            "DIMENSION_CONSTRAINT_INVALID", "The minimum dimension constraint is invalid."
        ) from exc
    if width < minimum_width or height < minimum_height:
        raise AcquisitionValidationError(
            "DIMENSIONS_INSUFFICIENT", "The selected resource is smaller than requested."
        )


def default_adapters(
    *, registry: OfflineResourceProviderRegistry | None = None
) -> dict[str, ResourceAdapter]:
    return {
        "image": ImageAdapter(registry),
        "texture": ImageAdapter(registry, category="texture"),
        "illustration": ImageAdapter(registry, category="illustration"),
        "font": FontAdapter(registry),
        "icon": IconAdapter(registry),
        "component_source": ComponentSourceAdapter(registry),
        "style_primitive": StylePrimitiveAdapter(registry),
    }
