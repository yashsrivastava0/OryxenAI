from __future__ import annotations

from io import BytesIO

import httpx
import pytest
from PIL import Image

from oryxenai.agents.build_preparation.providers import (
    ProviderLookup,
    download_image,
    search_components,
)
from oryxenai.agents.build_preparation.schemas import FetchedResource, ResourceQuery
from oryxenai.agents.shared.image_retrieval import ImageSearchIntent, search_images
from oryxenai.core.settings import Settings


def _query(kind: str = "photo") -> ResourceQuery:
    return ResourceQuery(
        need_id="need-1",
        kind=kind,  # type: ignore[arg-type]
        query="quiet editorial workspace",
        provider_terms=["editorial", "workspace"],
    )


@pytest.mark.asyncio
async def test_pexels_metadata_search_and_pixabay_fallback(monkeypatch, tmp_path) -> None:
    settings = Settings()
    settings.build_preparation.network_retry_count = 0
    settings.image_retrieval.cache_root = str(tmp_path / "cache")
    monkeypatch.setenv("PEXELS_API_KEY", "pexels-test-key")
    monkeypatch.setenv("PIXABAY_API_KEY", "pixabay-test-key")
    requests: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.url.host == "api.pexels.com":
            return httpx.Response(429, headers={"Retry-After": "0"}, request=request)
        return httpx.Response(
            200,
            json={
                "hits": [
                    {
                        "id": 1,
                        "tags": "quiet, editorial, workspace",
                        "imageWidth": 1800,
                        "imageHeight": 1200,
                        "largeImageURL": "https://cdn.pixabay.com/photo-1.jpg",
                        "webformatURL": "https://cdn.pixabay.com/photo-1-small.jpg",
                        "pageURL": "https://pixabay.com/photos/1",
                        "user": "Photographer",
                        "likes": 20,
                    }
                ]
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        candidates = await ProviderLookup(settings, client=client, live=True).lookup([_query()])

    assert [candidate.provider for candidate in candidates] == ["pixabay"]
    assert candidates[0].image_url.startswith("https://cdn.pixabay.com")
    assert candidates[0].license_reference.endswith("license-summary/")
    assert any("api.pexels.com" in url for url in requests)
    assert any("pixabay.com/api/" in url for url in requests)


@pytest.mark.asyncio
async def test_selected_pixabay_image_downloads_real_bytes(monkeypatch) -> None:
    settings = Settings()
    monkeypatch.setenv("PIXABAY_API_KEY", "pixabay-test-key")
    output = BytesIO()
    Image.effect_noise((24, 24), 40).convert("RGB").save(output, format="PNG")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=output.getvalue(),
            headers={"content-type": "image/png"},
            request=request,
        )

    candidate = FetchedResource(
        resource_id="pixabay-1",
        need_id="need-1",
        kind="photo",
        provider="pixabay",
        provider_asset_id="1",
        image_url="https://cdn.pixabay.com/photo-1.png",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        data = await download_image(candidate, settings, client=client)

    assert data.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_important_image_search_queries_both_active_providers(monkeypatch, tmp_path) -> None:
    settings = Settings()
    settings.image_retrieval.cache_root = str(tmp_path / "cache")
    monkeypatch.setenv("PEXELS_API_KEY", "pexels-test-key")
    monkeypatch.setenv("PIXABAY_API_KEY", "pixabay-test-key")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "api.pexels.com":
            return httpx.Response(
                200,
                json={
                    "photos": [
                        {
                            "id": 2,
                            "width": 2000,
                            "height": 1200,
                            "alt": "quiet editorial workspace",
                            "url": "https://www.pexels.com/photo/2",
                            "photographer": "Pexels author",
                            "src": {
                                "original": "https://images.pexels.com/photo-2.jpg",
                                "medium": "https://images.pexels.com/photo-2-medium.jpg",
                            },
                        }
                    ]
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "hits": [
                    {
                        "id": 3,
                        "tags": "quiet editorial workspace",
                        "imageWidth": 2000,
                        "imageHeight": 1200,
                        "largeImageURL": "https://cdn.pixabay.com/photo-3.jpg",
                        "pageURL": "https://pixabay.com/photos/3",
                        "user": "Pixabay author",
                        "likes": 30,
                    }
                ]
            },
            request=request,
        )

    intent = ImageSearchIntent(
        purpose="project showcase",
        subject="quiet editorial workspace",
        queries=["quiet editorial workspace"],
        important=True,
        orientation="landscape",
        minimum_width=1200,
        minimum_height=700,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        candidates = await search_images(intent, settings, client=client, limit=2)

    assert {item.provider for item in candidates} == {"pexels", "pixabay"}
    pixabay_request = next(item for item in requests if item.url.host == "pixabay.com")
    assert pixabay_request.url.params["safesearch"] == "true"
    assert pixabay_request.url.params["orientation"] == "horizontal"


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
