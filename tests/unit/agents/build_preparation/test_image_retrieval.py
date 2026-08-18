from __future__ import annotations

import io

import httpx
import pytest
from PIL import Image

from oryxenai.agents.shared.image_retrieval import (
    ImageDownloadError,
    ImageSearchCache,
    ImageSearchIntent,
    prepare_image_bytes,
    search_images,
)
from oryxenai.core.settings import Settings


def _jpeg(width: int, height: int, *, varied: bool) -> bytes:
    image = Image.new("RGB", (width, height), "#202020")
    if varied:
        for x in range(0, width, max(1, width // 8)):
            for y in range(0, height, max(1, height // 8)):
                image.putpixel((x, y), (220, 80, 40))
    output = io.BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_important_image_role_searches_pexels_and_pixabay_with_filters(
    tmp_path, monkeypatch
) -> None:
    settings = Settings()
    settings.image_retrieval.cache_root = str(tmp_path)
    settings.image_retrieval.retry_count = 0
    monkeypatch.setenv("PEXELS_API_KEY", "pexels-test")
    monkeypatch.setenv("PIXABAY_API_KEY", "pixabay-test")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "api.pexels.com":
            assert request.url.params["orientation"] == "landscape"
            assert request.url.params["size"] == "large"
            assert request.url.params["color"] == "blue"
            return httpx.Response(
                200,
                json={
                    "photos": [
                        {
                            "id": 1,
                            "alt": "backend platform systems",
                            "width": 2400,
                            "height": 1350,
                            "photographer": "Pexels Author",
                            "photographer_url": "https://pexels.test/author",
                            "url": "https://pexels.test/photo/1",
                            "src": {
                                "original": "https://images.pexels.com/photo/1.jpg",
                                "large2x": "https://images.pexels.com/photo/1-large2x.jpg",
                                "medium": "https://images.pexels.com/photo/1-medium.jpg",
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
                        "id": 2,
                        "tags": "backend platform systems",
                        "imageURL": "https://cdn.pixabay.com/photo/2.jpg",
                        "previewURL": "https://cdn.pixabay.com/photo/2-preview.jpg",
                        "imageWidth": 2400,
                        "imageHeight": 1350,
                        "user": "Pixabay Author",
                        "pageURL": "https://pixabay.com/photos/2",
                    }
                ]
            },
            request=request,
        )

    intent = ImageSearchIntent(
        purpose="decorative backend platform atmosphere",
        subject="backend platform systems",
        orientation="landscape",
        minimum_width=2000,
        minimum_height=1200,
        colors=["blue"],
        negative_concepts=["portrait", "dashboard"],
        queries=["backend platform systems"],
        important=True,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        candidates = await search_images(
            intent,
            settings,
            providers=["pexels", "pixabay"],
            client=client,
            diagnostics=[],
        )

    assert {candidate.provider for candidate in candidates} == {"pexels", "pixabay"}
    pexels = next(candidate for candidate in candidates if candidate.provider == "pexels")
    assert pexels.image_url.endswith("1-large2x.jpg")
    assert len(requests) == 2


@pytest.mark.asyncio
async def test_empty_image_responses_are_not_cached(tmp_path, monkeypatch) -> None:
    settings = Settings()
    settings.image_retrieval.cache_root = str(tmp_path)
    settings.image_retrieval.retry_count = 0
    monkeypatch.setenv("PEXELS_API_KEY", "pexels-test")
    count = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        return httpx.Response(200, json={"photos": []}, request=request)

    intent = ImageSearchIntent(subject="backend systems", queries=["backend systems"])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await search_images(intent, settings, providers=["pexels"], client=client) == []
        assert await search_images(intent, settings, providers=["pexels"], client=client) == []

    assert count == 2
    assert list(tmp_path.rglob("*.json")) == []


def test_image_processing_rejects_corrupt_and_undersized_bytes() -> None:
    intent = ImageSearchIntent(minimum_width=1200, minimum_height=700)
    with pytest.raises(ImageDownloadError, match="corrupt"):
        prepare_image_bytes(b"not-an-image", intent)
    with pytest.raises(ImageDownloadError, match="dimensions"):
        prepare_image_bytes(_jpeg(400, 300, varied=True), intent)


def test_large_valid_image_is_resized_and_optimized_within_configured_limits() -> None:
    optimized, info = prepare_image_bytes(
        _jpeg(3600, 2200, varied=True),
        ImageSearchIntent(minimum_width=1200, minimum_height=700),
    )
    assert len(optimized) <= 8 * 1024 * 1024
    assert max(info["pixel_width"], info["pixel_height"]) <= 2400
    assert info["pixel_width"] >= 1200
    assert info["pixel_height"] >= 700


def test_image_cache_never_returns_an_empty_entry(tmp_path) -> None:
    cache = ImageSearchCache(tmp_path)
    cache.put("pexels", "empty", {}, [])
    assert cache.get("pexels", "empty", {}) is None
