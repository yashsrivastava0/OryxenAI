from __future__ import annotations

import httpx
import pytest

from oryxenai.agents.build_preparation.providers import (
    ProviderLookup,
    search_components,
)
from oryxenai.agents.build_preparation.schemas import ResourceQuery
from oryxenai.core.settings import Settings


def _query(kind: str = "photo") -> ResourceQuery:
    return ResourceQuery(
        need_id="need-1",
        kind=kind,  # type: ignore[arg-type]
        query="quiet editorial workspace",
        provider_terms=["editorial", "workspace"],
    )


@pytest.mark.asyncio
async def test_pexels_metadata_search_and_unsplash_fallback() -> None:
    settings = Settings()
    settings.build_preparation.network_retry_count = 0
    requests: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.url.host == "api.pexels.com":
            return httpx.Response(429, headers={"Retry-After": "0"}, request=request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "unsplash-1",
                        "width": 1200,
                        "height": 800,
                        "urls": {"regular": "https://images.unsplash.com/photo-1"},
                        "links": {
                            "html": "https://unsplash.com/photos/unsplash-1",
                            "download_location": "https://api.unsplash.com/photos/unsplash-1/download",
                        },
                        "user": {
                            "name": "Photographer",
                            "links": {"html": "https://unsplash.com/@photo"},
                        },
                    }
                ]
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        candidates = await ProviderLookup(settings, client=client, live=True).lookup([_query()])

    assert [candidate.provider for candidate in candidates] == ["unsplash"]
    assert candidates[0].hotlink_url.startswith("https://")
    assert candidates[0].image_url == ""
    assert any("api.pexels.com" in url for url in requests)
    assert any("api.unsplash.com/search/photos" in url for url in requests)


@pytest.mark.asyncio
async def test_registry_component_lookup_collects_safe_dependency_source() -> None:
    settings = Settings()
    settings.resource_providers.registry_order = ["shadcn"]
    settings.resource_providers.shadcn_catalog_url = "https://registry.test/catalog.json"
    settings.resource_providers.shadcn_item_url_template = "https://registry.test/{name}.json"

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/catalog.json":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "name": "card",
                            "title": "Workspace Card",
                            "description": "editorial workspace content card",
                        }
                    ]
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "files": [
                    {"path": "card.tsx", "content": "export function Card() { return null; }"}
                ],
                "dependencies": ["react"],
                "registryDependencies": [],
                "version": "1.0.0",
            },
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        candidates = await search_components(
            _query("component"), settings, client=client, fetch_source=True
        )

    assert len(candidates) == 1
    assert candidates[0].source_files["card.tsx"].startswith("export function")
    assert candidates[0].dependencies == ["react"]
    assert candidates[0].license == "MIT"
    assert candidates[0].license_reference.endswith("LICENSE.md")


@pytest.mark.asyncio
async def test_provider_lookup_fetches_identical_live_queries_again() -> None:
    settings = Settings()
    settings.resource_providers.registry_order = ["shadcn"]
    settings.resource_providers.shadcn_catalog_url = "https://registry.test/live-catalog.json"
    settings.resource_providers.shadcn_item_url_template = "https://registry.test/live-{name}.json"
    requests: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.url.path.endswith("live-catalog.json"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "name": "card",
                            "title": "Editorial workspace card",
                            "description": "editorial workspace content card",
                        }
                    ]
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "files": [
                    {
                        "path": "card.tsx",
                        "content": "export function Card() { return <article>Card</article>; }",
                    }
                ],
                "dependencies": ["react"],
                "registryDependencies": [],
                "version": "1.0.0",
            },
            request=request,
        )

    query = _query("component")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        lookup = ProviderLookup(settings, client=client, live=True)
        first = await lookup.lookup([query])
        second = await lookup.lookup([query])

    assert len(first) == len(second) == 1
    assert lookup.calls_made == 2
    assert sum("live-catalog.json" in item for item in requests) == 2
