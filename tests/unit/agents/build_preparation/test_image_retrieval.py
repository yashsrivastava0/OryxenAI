from __future__ import annotations

import io

import httpx
import pytest
from PIL import Image

from oryxenai.agents.shared.image_retrieval import (
    ImageDownloadError,
    ImageSearchCache,
    ImageSearchIntent,
    _clean_pixabay_tags,
    _pixabay_candidate,
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
                        # largeImageURL, not imageURL: imageURL/fullHDURL are
                        # only served to specially-approved Pixabay accounts
                        # and a normal API key's download 400s even when the
                        # field is present in the response (confirmed live).
                        "largeImageURL": "https://cdn.pixabay.com/photo/2.jpg",
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


@pytest.mark.asyncio
async def test_image_search_prefers_unused_provider_assets(tmp_path, monkeypatch) -> None:
    settings = Settings()
    settings.image_retrieval.cache_root = str(tmp_path)
    settings.image_retrieval.retry_count = 0
    monkeypatch.setenv("PEXELS_API_KEY", "pexels-test")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "photos": [
                    {
                        "id": 1,
                        "alt": "reused result",
                        "width": 2400,
                        "height": 1350,
                        "url": "https://pexels.test/photo/1",
                        "src": {"large2x": "https://images.pexels.com/photo/1.jpg"},
                    },
                    {
                        "id": 2,
                        "alt": "distinct result",
                        "width": 2400,
                        "height": 1350,
                        "url": "https://pexels.test/photo/2",
                        "src": {"large2x": "https://images.pexels.com/photo/2.jpg"},
                    },
                ]
            },
            request=request,
        )

    intent = ImageSearchIntent(
        subject="editorial architecture",
        queries=["editorial architecture"],
        used_asset_ids=["1"],
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        candidates = await search_images(
            intent, settings, providers=["pexels"], client=client, limit=2
        )

    assert candidates
    assert all(candidate.provider_asset_id != "1" for candidate in candidates)


@pytest.mark.asyncio
async def test_image_search_tries_next_provider_when_first_returns_only_used_assets(
    tmp_path, monkeypatch
) -> None:
    settings = Settings()
    settings.image_retrieval.cache_root = str(tmp_path)
    settings.image_retrieval.retry_count = 0
    monkeypatch.setenv("PEXELS_API_KEY", "pexels-test")
    monkeypatch.setenv("PIXABAY_API_KEY", "pixabay-test")

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.pexels.com":
            return httpx.Response(
                200,
                json={
                    "photos": [
                        {
                            "id": 1,
                            "alt": "reused architecture",
                            "width": 2400,
                            "height": 1350,
                            "url": "https://pexels.test/photo/1",
                            "src": {"large2x": "https://images.pexels.com/photo/1.jpg"},
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
                        "tags": "fresh editorial architecture",
                        "imageWidth": 2400,
                        "imageHeight": 1350,
                        "largeImageURL": "https://cdn.pixabay.com/photo-3.jpg",
                        "pageURL": "https://pixabay.com/photos/3",
                    }
                ]
            },
            request=request,
        )

    intent = ImageSearchIntent(
        purpose="editorial architecture atmosphere",
        subject="editorial architecture",
        queries=["editorial architecture"],
        used_asset_ids=["1"],
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        candidates = await search_images(
            intent,
            settings,
            providers=["pexels", "pixabay"],
            client=client,
            limit=2,
        )

    assert candidates
    assert any(candidate.provider == "pixabay" for candidate in candidates)
    assert all(candidate.provider_asset_id != "1" for candidate in candidates)


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


def test_pixabay_tags_are_deduplicated_preserving_order() -> None:
    raw = "graphic designer, graphic designer, Graphic Designer, designer, UI designer, designer"
    cleaned = _clean_pixabay_tags(raw)
    assert cleaned == "graphic designer, designer, UI designer"


def test_pixabay_candidate_prefers_large_image_url_over_gated_image_url() -> None:
    # Pixabay only serves imageURL/fullHDURL to specially-approved accounts;
    # for a normal API key the field can still be present in the response
    # but every download 400s (confirmed live). largeImageURL is served to
    # every API key and must be preferred.
    hit = {
        "id": 12345,
        "imageURL": "https://pixabay.com/get/gated-original_1920.jpg",
        "fullHDURL": "https://pixabay.com/get/gated-fullhd_1920.jpg",
        "largeImageURL": "https://pixabay.com/get/large-1280.jpg",
        "webformatURL": "https://pixabay.com/get/webformat-640.jpg",
        "previewURL": "https://pixabay.com/get/preview-150.jpg",
        "tags": "office, workspace",
        "user": "contributor",
        "pageURL": "https://pixabay.com/photos/office-12345/",
        "imageWidth": 1920,
        "imageHeight": 1280,
        "likes": 10,
        "downloads": 100,
    }
    candidate = _pixabay_candidate(hit, "office workspace", 0)
    assert candidate is not None
    assert candidate.image_url == "https://pixabay.com/get/large-1280.jpg"


def test_pixabay_candidate_falls_back_to_webformat_when_large_is_absent() -> None:
    hit = {
        "id": 12345,
        "webformatURL": "https://pixabay.com/get/webformat-640.jpg",
        "tags": "office, workspace",
        "user": "contributor",
        "pageURL": "https://pixabay.com/photos/office-12345/",
    }
    candidate = _pixabay_candidate(hit, "office workspace", 0)
    assert candidate is not None
    assert candidate.image_url == "https://pixabay.com/get/webformat-640.jpg"
