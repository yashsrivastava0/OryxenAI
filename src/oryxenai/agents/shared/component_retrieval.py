"""Provider-neutral retrieval for source-owned UI components.

The retrieval boundary is deliberately transport-neutral.  Direct registry/API
providers are the normal production path; an MCP caller can be injected for
registries that expose no suitable HTTP discovery endpoint.  Neither path
persists or reuses provider responses.  Source is fetched only after a
candidate has been selected by the caller.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx


class ComponentRetrievalError(RuntimeError):
    """A component provider returned an unsafe or unavailable result."""

    def __init__(self, message: str, *, provider: str, code: str = "PROVIDER_FAILED") -> None:
        self.provider = provider
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ComponentCandidate:
    """Metadata returned by discovery; source files are intentionally absent."""

    provider: str
    name: str
    title: str
    description: str
    tags: tuple[str, ...]
    item_url: str
    source_version: str = ""
    license: str = ""
    license_reference: str = ""
    dependencies: tuple[str, ...] = ()
    registry_dependencies: tuple[str, ...] = ()
    technical_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def candidate_id(self) -> str:
        digest = hashlib.sha256(
            f"{self.provider}:{self.name}:{self.item_url}".encode()
        ).hexdigest()[:20]
        return f"component-{self.provider}-{digest}"

    def as_metadata(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "provider": self.provider,
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "tags": list(self.tags),
            "item_url": self.item_url,
            "source_version": self.source_version,
            "license": self.license,
            "license_reference": self.license_reference,
            "dependencies": list(self.dependencies),
            "registry_dependencies": list(self.registry_dependencies),
            "technical_metadata": self.technical_metadata,
        }

    @classmethod
    def from_metadata(cls, value: dict[str, Any]) -> ComponentCandidate:
        return cls(
            provider=str(value.get("provider", "")),
            name=str(value.get("name", "")),
            title=str(value.get("title", "")),
            description=str(value.get("description", "")),
            tags=tuple(str(item) for item in value.get("tags", []) if str(item)),
            item_url=str(value.get("item_url", "")),
            source_version=str(value.get("source_version", "")),
            license=str(value.get("license", "")),
            license_reference=str(value.get("license_reference", "")),
            dependencies=tuple(str(item) for item in value.get("dependencies", []) if str(item)),
            registry_dependencies=tuple(
                str(item) for item in value.get("registry_dependencies", []) if str(item)
            ),
            technical_metadata=dict(value.get("technical_metadata", {}) or {}),
        )


@dataclass(frozen=True)
class FetchedComponent:
    """Selected component source and its resolved registry dependencies."""

    candidate: ComponentCandidate
    source_files: dict[str, str]
    dependencies: tuple[str, ...]
    registry_dependencies: tuple[str, ...]
    license: str
    license_reference: str
    source_version: str


class McpToolCaller(Protocol):
    async def __call__(self, tool_name: str, arguments: dict[str, Any]) -> Any: ...


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.casefold()) if len(token) > 2}


def _safe_url(url: str, hosts: set[str]) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.hostname not in hosts:
        raise ComponentRetrievalError(
            "Component source URL is outside the configured provider hosts.",
            provider="registry",
            code="SOURCE_HOST_UNAPPROVED",
        )
    return url


def _safe_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip("/")
    parts = normalized.split("/")
    if (
        not normalized
        or any(part in {"", ".", ".."} for part in parts)
        or normalized.startswith(".")
        or normalized.casefold().endswith((".sh", ".ps1", ".bat", ".cmd"))
        or parts[-1].casefold()
        in {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}
    ):
        raise ComponentRetrievalError(
            "Registry returned an unsafe component path.",
            provider="registry",
            code="SOURCE_PATH_UNSAFE",
        )
    return normalized


def _payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        structured = value.get("structuredContent")
        if isinstance(structured, dict):
            return _payload(structured)
        content = value.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict) or not isinstance(block.get("text"), str):
                    continue
                try:
                    return _payload(json.loads(block["text"]))
                except (json.JSONDecodeError, ComponentRetrievalError):
                    continue
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    raise ComponentRetrievalError(
        "Component provider returned malformed JSON.", provider="registry", code="JSON_INVALID"
    )


async def _get_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    provider: str,
    hosts: set[str],
    settings: Any,
    params: dict[str, str | int] | None = None,
) -> dict[str, Any]:
    _safe_url(url, hosts)
    retries = max(0, int(getattr(settings.build_preparation, "network_retry_count", 1)))
    timeout = float(getattr(settings.build_preparation, "network_timeout_seconds", 15.0))
    last_error = "request failed"
    for attempt in range(retries + 1):
        try:
            response = await client.get(
                url,
                params=params,
                headers={"Accept": "application/json"},
                timeout=timeout,
                follow_redirects=False,
            )
        except httpx.TimeoutException:
            last_error = "request timed out"
        except httpx.HTTPError:
            last_error = "connection failed"
        else:
            if response.status_code == 429:
                raise ComponentRetrievalError(
                    f"{provider} rate limit reached; no alternate transport was attempted.",
                    provider=provider,
                    code="RATE_LIMITED",
                )
            if response.status_code >= 500:
                last_error = f"provider returned HTTP {response.status_code}"
            elif response.status_code >= 400:
                raise ComponentRetrievalError(
                    f"{provider} rejected the component request.",
                    provider=provider,
                    code=f"HTTP_{response.status_code}",
                )
            else:
                try:
                    return _payload(response.json())
                except (ValueError, ComponentRetrievalError) as exc:
                    raise ComponentRetrievalError(
                        "Component provider returned malformed JSON.",
                        provider=provider,
                        code="JSON_INVALID",
                    ) from exc
        if attempt < retries:
            await asyncio.sleep(min(2.0**attempt, 4.0))
    raise ComponentRetrievalError(last_error, provider=provider, code="PROVIDER_UNAVAILABLE")


class ComponentProvider(Protocol):
    provider: str

    async def discover(
        self, query: str, *, client: httpx.AsyncClient, settings: Any, limit: int
    ) -> list[ComponentCandidate]: ...

    async def fetch(
        self, candidate: ComponentCandidate, *, client: httpx.AsyncClient, settings: Any
    ) -> FetchedComponent: ...


class RegistryComponentProvider:
    """Provider for shadcn-compatible registry catalogs and item JSON."""

    def __init__(
        self,
        provider: str,
        *,
        catalog_url: str,
        item_url_template: str,
        hosts: set[str],
        license_name: str,
        license_reference: str,
        release_pin: str = "",
        allowed_components: set[str] | None = None,
    ) -> None:
        self.provider = provider
        self.catalog_url = catalog_url
        self.item_url_template = item_url_template
        self.hosts = hosts
        self.license_name = license_name
        self.license_reference = license_reference
        self.release_pin = release_pin
        self.allowed_components = allowed_components or set()

    async def discover(
        self, query: str, *, client: httpx.AsyncClient, settings: Any, limit: int
    ) -> list[ComponentCandidate]:
        payload = await _get_json(
            client,
            self.catalog_url,
            provider=self.provider,
            hosts=self.hosts,
            settings=settings,
        )
        wanted = _tokens(query)
        ranked: list[tuple[int, str, dict[str, Any]]] = []
        catalog_items = payload.get("items", payload.get("components", payload.get("results", [])))
        for item in catalog_items if isinstance(catalog_items, list) else []:
            if not isinstance(item, dict) or not str(item.get("name", "")):
                continue
            name = str(item["name"])
            if self.allowed_components and name not in self.allowed_components:
                continue
            haystack = " ".join(
                str(item.get(key, ""))
                for key in ("name", "title", "description", "type", "category", "tags")
            )
            score = len(wanted.intersection(_tokens(haystack)))
            if score:
                ranked.append((score, name, item))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [self._candidate(item) for _, _, item in ranked[:limit]]

    def _candidate(self, item: dict[str, Any]) -> ComponentCandidate:
        name = str(item.get("name", ""))
        raw_tags = item.get("tags", item.get("categories", []))
        if not isinstance(raw_tags, list):
            raw_tags = [raw_tags] if raw_tags else []
        return ComponentCandidate(
            provider=self.provider,
            name=name,
            title=str(item.get("title", name) or name),
            description=str(item.get("description", "") or ""),
            tags=tuple(str(tag) for tag in raw_tags if str(tag)),
            item_url=self.item_url_template.format(name=name.lstrip("@")),
            source_version=self.release_pin,
            license=str(item.get("license", "") or self.license_name),
            license_reference=str(item.get("licenseUrl", "") or self.license_reference),
            technical_metadata={"type": str(item.get("type", ""))},
        )

    async def fetch(
        self, candidate: ComponentCandidate, *, client: httpx.AsyncClient, settings: Any
    ) -> FetchedComponent:
        return await _fetch_registry_item(
            candidate,
            client=client,
            settings=settings,
            hosts=self.hosts,
            item_url_template=self.item_url_template,
            license_name=self.license_name,
            license_reference=self.license_reference,
            release_pin=self.release_pin,
        )


class SmoothUIComponentProvider(RegistryComponentProvider):
    """SmoothUI REST discovery with registry JSON source retrieval."""

    def __init__(
        self,
        *,
        api_base_url: str,
        registry_item_url_template: str,
        license_reference: str,
        release_pin: str = "",
        allowed_components: set[str] | None = None,
    ) -> None:
        super().__init__(
            "smoothui",
            catalog_url="",
            item_url_template=registry_item_url_template,
            hosts={"smoothui.dev"},
            license_name="MIT",
            license_reference=license_reference,
            release_pin=release_pin,
            allowed_components=allowed_components,
        )
        self.api_base_url = api_base_url.rstrip("/")

    async def discover(
        self, query: str, *, client: httpx.AsyncClient, settings: Any, limit: int
    ) -> list[ComponentCandidate]:
        try:
            payload = await _get_json(
                client,
                f"{self.api_base_url}/suggest",
                provider=self.provider,
                hosts=self.hosts,
                settings=settings,
                params={"need": query},
            )
            items = payload.get("suggestions", [])
        except ComponentRetrievalError as exc:
            if exc.code == "RATE_LIMITED":
                raise
            payload = await _get_json(
                client,
                f"{self.api_base_url}/components/search",
                provider=self.provider,
                hosts=self.hosts,
                settings=settings,
                params={"q": query},
            )
            items = payload.get("components", payload.get("results", []))
        candidates: list[ComponentCandidate] = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", ""))
            if not name or (self.allowed_components and name not in self.allowed_components):
                continue
            registry_url = str(
                item.get("registryUrl", "") or self.item_url_template.format(name=name.lstrip("@"))
            )
            _safe_url(registry_url, self.hosts)
            tags = item.get("tags", item.get("categories", []))
            if not isinstance(tags, list):
                tags = [str(tags)] if tags else []
            candidates.append(
                ComponentCandidate(
                    provider=self.provider,
                    name=name,
                    title=str(item.get("displayName", item.get("title", name)) or name),
                    description=str(item.get("description", "") or ""),
                    tags=tuple(str(value) for value in tags),
                    item_url=registry_url,
                    source_version=self.release_pin,
                    license=str(item.get("license", "") or self.license_name),
                    license_reference=self.license_reference,
                    technical_metadata={
                        "complexity": str(item.get("complexity", "")),
                        "animation_type": str(item.get("animationType", "")),
                        "use_cases": item.get("useCases", []),
                    },
                )
            )
        return candidates[:limit]


async def _fetch_registry_item(
    candidate: ComponentCandidate,
    *,
    client: httpx.AsyncClient,
    settings: Any,
    hosts: set[str],
    item_url_template: str,
    license_name: str,
    license_reference: str,
    release_pin: str,
    seen: set[str] | None = None,
) -> FetchedComponent:
    seen = set() if seen is None else seen
    if candidate.name in seen or len(seen) >= 8:
        raise ComponentRetrievalError(
            "Registry dependency graph is cyclic or too deep.",
            provider=candidate.provider,
            code="DEPENDENCY_GRAPH_UNSAFE",
        )
    seen.add(candidate.name)
    payload = await _get_json(
        client,
        candidate.item_url,
        provider=candidate.provider,
        hosts=hosts,
        settings=settings,
    )
    raw_files = payload.get("files")
    if not isinstance(raw_files, list) and isinstance(payload.get("source"), str):
        source_name = candidate.name.rsplit("/", 1)[-1] or "component"
        raw_files = [{"path": f"{source_name}.tsx", "content": payload["source"]}]
    if not isinstance(raw_files, list):
        raise ComponentRetrievalError(
            "Registry item has no source files.", provider=candidate.provider, code="SOURCE_MISSING"
        )
    files: dict[str, str] = {}
    for item in raw_files:
        if not isinstance(item, dict) or not item.get("path") or item.get("content") is None:
            raise ComponentRetrievalError(
                "Registry item contains malformed source.",
                provider=candidate.provider,
                code="SOURCE_MALFORMED",
            )
        path = _safe_path(str(item["path"]))
        if path in files and files[path] != str(item["content"]):
            raise ComponentRetrievalError(
                "Registry item contains conflicting source paths.",
                provider=candidate.provider,
                code="SOURCE_CONFLICT",
            )
        files[path] = str(item["content"])
    dependencies = tuple(
        str(value) for value in payload.get("dependencies", []) if isinstance(value, str)
    )
    registry_dependencies = tuple(
        str(value) for value in payload.get("registryDependencies", []) if isinstance(value, str)
    )
    all_dependencies = list(dependencies)
    all_registry_dependencies = list(registry_dependencies)
    for dependency in registry_dependencies:
        dependency_url = (
            dependency
            if dependency.startswith("https://")
            else item_url_template.format(name=dependency.lstrip("@"))
        )
        child = await _fetch_registry_item(
            ComponentCandidate(
                provider=candidate.provider,
                name=dependency,
                title=dependency,
                description="",
                tags=(),
                item_url=dependency_url,
                license=license_name,
                license_reference=license_reference,
            ),
            client=client,
            settings=settings,
            hosts=hosts,
            item_url_template=item_url_template,
            license_name=license_name,
            license_reference=license_reference,
            release_pin=release_pin,
            seen=seen,
        )
        for path, content in child.source_files.items():
            if path in files and files[path] != content:
                raise ComponentRetrievalError(
                    "Registry dependencies contain conflicting source paths.",
                    provider=candidate.provider,
                    code="SOURCE_CONFLICT",
                )
            files[path] = content
        all_dependencies.extend(child.dependencies)
        all_registry_dependencies.extend(child.registry_dependencies)
    seen.remove(candidate.name)
    license_value = str(payload.get("license", "") or candidate.license or license_name)
    version = str(payload.get("version", "") or candidate.source_version or release_pin)
    return FetchedComponent(
        candidate=candidate,
        source_files=files,
        dependencies=tuple(dict.fromkeys(all_dependencies)),
        registry_dependencies=tuple(dict.fromkeys(all_registry_dependencies)),
        license=license_value,
        license_reference=candidate.license_reference or license_reference,
        source_version=version,
    )


class McpComponentProvider:
    """Optional MCP adapter driven by an injected trusted tool caller.

    The application does not spawn an MCP process.  A deployment may inject a
    long-lived, authenticated MCP client; absent one, direct providers remain
    authoritative.
    """

    def __init__(self, provider: str, caller: McpToolCaller) -> None:
        self.provider = provider
        self._caller = caller

    async def discover(
        self, query: str, *, client: httpx.AsyncClient, settings: Any, limit: int
    ) -> list[ComponentCandidate]:
        del client, settings
        result = await self._caller(
            "searchRegistryItems",
            {"query": query, "limit": limit, "offset": 0},
        )
        payload = _payload(result)
        items = payload.get("items", payload.get("results", []))
        candidates: list[ComponentCandidate] = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict) or not str(item.get("name", "")):
                continue
            name = str(item["name"])
            candidates.append(
                ComponentCandidate(
                    provider=self.provider,
                    name=name,
                    title=str(item.get("title", name) or name),
                    description=str(item.get("description", "") or ""),
                    tags=tuple(str(value) for value in item.get("tags", []) if str(value)),
                    item_url=str(item.get("url", item.get("registryUrl", name))),
                    license=str(item.get("license", "") or "MIT"),
                    technical_metadata={"mcp": True},
                )
            )
        return candidates[:limit]

    async def fetch(
        self, candidate: ComponentCandidate, *, client: httpx.AsyncClient, settings: Any
    ) -> FetchedComponent:
        del client, settings
        result = await self._caller(
            "getRegistryItem",
            {"name": candidate.name, "includeSource": True},
        )
        payload = _payload(result)
        return await self._fetch_item(candidate, payload, seen=set())

    async def _fetch_item(
        self,
        candidate: ComponentCandidate,
        payload: dict[str, Any],
        *,
        seen: set[str],
    ) -> FetchedComponent:
        if candidate.name in seen or len(seen) >= 8:
            raise ComponentRetrievalError(
                "MCP registry dependency graph is cyclic or too deep.",
                provider=self.provider,
                code="DEPENDENCY_GRAPH_UNSAFE",
            )
        seen.add(candidate.name)
        raw_files = payload.get("files")
        if not isinstance(raw_files, list) and isinstance(payload.get("source"), str):
            source_name = candidate.name.rsplit("/", 1)[-1] or "component"
            raw_files = [{"path": f"{source_name}.tsx", "content": payload["source"]}]
        if not isinstance(raw_files, list):
            raise ComponentRetrievalError(
                "MCP component item has no source files.",
                provider=self.provider,
                code="SOURCE_MISSING",
            )
        files: dict[str, str] = {}
        for item in raw_files:
            if not isinstance(item, dict) or not item.get("path") or item.get("content") is None:
                raise ComponentRetrievalError(
                    "MCP component item contains malformed source.",
                    provider=self.provider,
                    code="SOURCE_MALFORMED",
                )
            path = _safe_path(str(item["path"]))
            files[path] = str(item["content"])
        dependencies = tuple(
            str(value) for value in payload.get("dependencies", []) if isinstance(value, str)
        )
        registry_dependencies = tuple(
            str(value)
            for value in payload.get("registryDependencies", [])
            if isinstance(value, str)
        )
        all_dependencies = list(dependencies)
        all_registry_dependencies = list(registry_dependencies)
        for dependency in registry_dependencies:
            child_payload = _payload(
                await self._caller(
                    "getRegistryItem",
                    {"name": dependency.lstrip("@"), "includeSource": True},
                )
            )
            child = await self._fetch_item(
                ComponentCandidate(
                    provider=self.provider,
                    name=dependency,
                    title=dependency,
                    description="",
                    tags=(),
                    item_url=dependency,
                    license=candidate.license,
                    license_reference=candidate.license_reference,
                    source_version=candidate.source_version,
                ),
                child_payload,
                seen=seen,
            )
            for path, content in child.source_files.items():
                if path in files and files[path] != content:
                    raise ComponentRetrievalError(
                        "MCP registry dependencies contain conflicting source paths.",
                        provider=self.provider,
                        code="SOURCE_CONFLICT",
                    )
                files[path] = content
            all_dependencies.extend(child.dependencies)
            all_registry_dependencies.extend(child.registry_dependencies)
        seen.remove(candidate.name)
        return FetchedComponent(
            candidate=candidate,
            source_files=files,
            dependencies=tuple(dict.fromkeys(all_dependencies)),
            registry_dependencies=tuple(dict.fromkeys(all_registry_dependencies)),
            license=str(payload.get("license", "") or candidate.license or "MIT"),
            license_reference=str(
                payload.get("licenseUrl", "") or candidate.license_reference or ""
            ),
            source_version=str(payload.get("version", "") or candidate.source_version or ""),
        )


class ComponentRetrievalService:
    """Bounded, cache-free orchestration over configured component providers."""

    def __init__(self, providers: dict[str, ComponentProvider], order: list[str]) -> None:
        self.providers = providers
        self.order = order
        self.calls_made = 0
        self.rate_limit_events = 0

    async def discover(
        self,
        query: str,
        *,
        allowed_providers: list[str],
        client: httpx.AsyncClient,
        settings: Any,
        limit: int = 5,
    ) -> list[ComponentCandidate]:
        allowed = set(allowed_providers)
        result: list[ComponentCandidate] = []
        for provider_name in self.order:
            if allowed and provider_name not in allowed:
                continue
            provider = self.providers.get(provider_name)
            if provider is None:
                continue
            self.calls_made += 1
            try:
                result.extend(
                    await provider.discover(query, client=client, settings=settings, limit=limit)
                )
            except ComponentRetrievalError as exc:
                if exc.code == "RATE_LIMITED":
                    self.rate_limit_events += 1
                continue
        return result

    async def fetch(
        self,
        candidate: ComponentCandidate,
        *,
        client: httpx.AsyncClient,
        settings: Any,
    ) -> FetchedComponent:
        provider = self.providers.get(candidate.provider)
        if provider is None:
            raise ComponentRetrievalError(
                "No configured provider exists for the selected component.",
                provider=candidate.provider,
                code="PROVIDER_NOT_CONFIGURED",
            )
        return await provider.fetch(candidate, client=client, settings=settings)


def build_component_retrieval_service(settings: Any) -> ComponentRetrievalService:
    """Build direct providers from the shared application configuration."""

    if not bool(getattr(settings.resource_providers, "registries_enabled", True)):
        return ComponentRetrievalService({}, [])

    licenses = {
        "shadcn": ("MIT", "https://github.com/shadcn-ui/ui/blob/main/LICENSE.md"),
        "magicui": ("MIT", "https://github.com/magicuidesign/magicui/blob/main/LICENSE.md"),
        "smoothui": ("MIT", "https://github.com/educlopez/smoothui/blob/main/LICENSE"),
        "cultui": ("MIT", "https://github.com/nolly-studio/cult-ui/blob/main/LICENSE.md"),
    }
    providers: dict[str, ComponentProvider] = {}
    registry_specs = ("shadcn", "magicui", "cultui")
    for provider in registry_specs:
        if provider != "shadcn" and not bool(
            getattr(settings.resource_providers, f"{provider}_enabled", False)
        ):
            continue
        catalog_url = str(getattr(settings.resource_providers, f"{provider}_catalog_url", "") or "")
        item_template = str(
            getattr(settings.resource_providers, f"{provider}_item_url_template", "") or ""
        )
        if not catalog_url or not item_template:
            continue
        hosts = {urlparse(catalog_url).hostname or ""}
        item_host = urlparse(item_template.format(name="component")).hostname
        if item_host:
            hosts.add(item_host)
        license_name, license_reference = licenses[provider]
        providers[provider] = RegistryComponentProvider(
            provider,
            catalog_url=catalog_url,
            item_url_template=item_template,
            hosts=hosts,
            license_name=license_name,
            license_reference=license_reference,
            release_pin=str(
                getattr(settings.resource_providers, f"{provider}_release_pin", "") or ""
            ),
            allowed_components={
                str(value)
                for value in getattr(
                    settings.resource_providers, f"{provider}_allowed_components", []
                )
            },
        )
    if bool(getattr(settings.resource_providers, "smoothui_enabled", False)):
        smooth_api = str(getattr(settings.resource_providers, "smoothui_api_base_url", "") or "")
        smooth_item = str(
            getattr(settings.resource_providers, "smoothui_item_url_template", "") or ""
        )
        if smooth_api and smooth_item:
            providers["smoothui"] = SmoothUIComponentProvider(
                api_base_url=smooth_api,
                registry_item_url_template=smooth_item,
                license_reference=licenses["smoothui"][1],
                release_pin=str(
                    getattr(settings.resource_providers, "smoothui_release_pin", "") or ""
                ),
                allowed_components={
                    str(value)
                    for value in getattr(
                        settings.resource_providers, "smoothui_allowed_components", []
                    )
                },
            )
    order = [
        str(value)
        for value in getattr(
            settings.resource_providers,
            "registry_order",
            ["shadcn", "magicui", "smoothui", "cultui"],
        )
    ]
    return ComponentRetrievalService(providers, order)
