from __future__ import annotations

import io
from types import SimpleNamespace

import httpx
import pytest
from PIL import Image

from oryxenai.build_preparation.providers import (
    PexelsClient,
    PhotoResource,
    ProviderUnavailable,
    RegistryResource,
    ShadcnRegistryProvider,
    choose_photo,
    registry_entry,
)
from oryxenai.build_preparation.resources import deduplicate_entries, resolve_remote_requirements
from oryxenai.build_preparation.schemas import ResourceManifestEntry, ResourceRequirement


def _requirement(kind: str = "component") -> ResourceRequirement:
    return ResourceRequirement(
        requirement_id="hero-effect",
        kind=kind,
        scope="scene",
        intent="animated hero effect",
        fallback="static hero",
    )


def test_duplicate_materialized_resource_is_deduplicated() -> None:
    first = ResourceManifestEntry(
        manifest_resource_id="registry-magicui-hero",
        requirement_ids=["one"],
        usages=[{"scope": "scene", "scene_id": "a"}],
        disposition="materialized",
        provider="magicui",
        provider_asset_id="hero",
        content_hash="same",
    )
    second = first.model_copy(
        update={
            "manifest_resource_id": "registry-magicui-hero-duplicate",
            "requirement_ids": ["two"],
            "usages": [{"scope": "scene", "scene_id": "b"}],
        }
    )
    entries, aliases = deduplicate_entries([first, second])
    assert len(entries) == 1
    assert entries[0].requirement_ids == ["one", "two"]
    assert aliases["registry-magicui-hero-duplicate"] == "registry-magicui-hero"


@pytest.mark.asyncio
async def test_remote_resolver_accepts_deterministic_fake_providers() -> None:
    class FakeRegistry:
        provider = "magicui"

        async def search(self, query: str, *, limit: int = 4) -> list[dict[str, str]]:
            return [{"name": "hero-effect"}]

        async def fetch(self, item_id: str) -> RegistryResource:
            return RegistryResource(
                provider="magicui",
                item_id=item_id,
                source_reference="https://example.test/hero",
                description="hero",
                files={"hero.tsx": b"export const Hero = () => null"},
                dependencies=("motion",),
                registry_dependencies=(),
            )

    image_buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "#222222").save(image_buffer, format="PNG")
    image_data = image_buffer.getvalue()

    class FakePexels:
        api_key = "fake"

        async def search(self, requirement: ResourceRequirement) -> list[PhotoResource]:
            return [
                PhotoResource(
                    provider="pexels",
                    photo_id="7",
                    photo_page="https://pexels.test/7",
                    photographer="Test Photographer",
                    photographer_url="https://pexels.test/author",
                    alt="Abstract workspace",
                    width=1200,
                    height=800,
                    orientation="landscape",
                    average_color="#222222",
                    image_url="https://images.test/7.png",
                    source_reference="https://pexels.test/7",
                )
            ]

        async def download(self, photo: PhotoResource) -> bytes:
            return image_data

    settings = SimpleNamespace(
        build_preparation=SimpleNamespace(network_timeout_seconds=5.0, network_retry_count=0),
        resource_providers=SimpleNamespace(
            registries_enabled=True,
            shadcn_catalog_url="",
            shadcn_item_url_template="",
            magicui_catalog_url="",
            magicui_item_url_template="",
            magicui_enabled=True,
            aceternity_catalog_url="",
            aceternity_item_url_template="",
            aceternity_enabled=False,
        ),
    )
    requirements = [
        _requirement(),
        ResourceRequirement(
            requirement_id="photo",
            kind="photo",
            scope="scene",
            intent="abstract workspace",
            constraints={
                # VDD permits this status while source_policy remains its
                # default; Build Preparation must still use Pexels.
                "source_status": "needs_acquisition",
                "orientation": "landscape",
            },
        ),
    ]
    entries, files, warnings = await resolve_remote_requirements(
        requirements,
        settings=settings,
        target_contract={"target_id": "react-vite-v1", "allowed_dependencies": ["motion"]},
        registry_providers=[FakeRegistry()],
        pexels_client=FakePexels(),
    )
    assert {entry.provider for entry in entries} == {"magicui", "pexels"}
    assert "resources/images/pexels-7.jpg" in files
    assert warnings == []


@pytest.mark.asyncio
async def test_registry_search_fetch_and_dependency_admission() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("catalog.json"):
            return httpx.Response(
                200,
                json={"items": [{"name": "hero-effect", "description": "animated hero"}]},
            )
        return httpx.Response(
            200,
            json={
                "name": "hero-effect",
                "description": "Animated hero",
                "files": [{"path": "hero.tsx", "content": "export const Hero = () => null"}],
                "dependencies": ["motion"],
                "registryDependencies": [],
                "license": "MIT",
                "version": "1",
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        provider = ShadcnRegistryProvider(
            provider="magicui",
            catalog_url="https://example.test/catalog.json",
            item_url_template="https://example.test/r/{name}.json",
            client=client,
        )
        matches = await provider.search("animated hero")
        resource = await provider.fetch(matches[0]["name"])
        entry = registry_entry(
            resource,
            _requirement(),
            pack_path="resources/components/hero/",
            content_hash="hash",
            size_bytes=32,
        )
        assert entry.disposition == "materialized"
        assert entry.provider_asset_id == "hero-effect"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_registry_malformed_item_is_unavailable() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"name": "broken"}))
    )
    try:
        provider = ShadcnRegistryProvider(
            provider="shadcn",
            catalog_url="https://example.test/catalog.json",
            item_url_template="https://example.test/r/{name}.json",
            client=client,
        )
        with pytest.raises(ProviderUnavailable):
            await provider.fetch("broken")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_registry_dependency_tree_is_materialized_without_package_install() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("root.json"):
            return httpx.Response(
                200,
                json={
                    "name": "root",
                    "files": [{"path": "root.tsx", "content": "root"}],
                    "dependencies": [],
                    "registryDependencies": ["child"],
                },
            )
        return httpx.Response(
            200,
            json={
                "name": "child",
                "files": [{"path": "child.tsx", "content": "child"}],
                "dependencies": ["motion"],
                "registryDependencies": [],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        provider = ShadcnRegistryProvider(
            provider="shadcn",
            catalog_url="",
            item_url_template="https://example.test/r/{name}.json",
            client=client,
        )
        resource = await provider.fetch("root")
        assert set(resource.files) == {"root.tsx", "child.tsx"}
        assert resource.registry_dependencies == ()
        assert resource.dependencies == ("motion",)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_registry_external_dependency_becomes_custom_requirement() -> None:
    resource = RegistryResource(
        provider="aceternity",
        item_id="premium-like",
        source_reference="https://example.test/item",
        description="",
        files={"item.tsx": b"source"},
        dependencies=("unknown-package",),
        registry_dependencies=(),
    )
    entry = registry_entry(
        resource,
        _requirement(),
        pack_path="resources/components/item/",
        content_hash="hash",
        size_bytes=6,
    )
    assert entry.disposition == "custom_implementation_required"
    assert entry.dependencies_allowed is False


@pytest.mark.asyncio
async def test_pexels_empty_and_rate_limited_responses_are_safe() -> None:
    requirement = ResourceRequirement(
        requirement_id="photo",
        kind="photo",
        scope="scene",
        intent="abstract workspace",
        constraints={"orientation": "landscape"},
    )

    empty_client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"photos": []}))
    )
    try:
        assert await PexelsClient("key", client=empty_client).search(requirement) == []
    finally:
        await empty_client.aclose()

    rate_client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(429, json={}))
    )
    try:
        with pytest.raises(ProviderUnavailable, match="rate limit"):
            await PexelsClient("key", client=rate_client).search(requirement)
    finally:
        await rate_client.aclose()


@pytest.mark.asyncio
async def test_pexels_orientation_is_derived_and_download_validates_type() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.pexels.com":
            return httpx.Response(
                200,
                json={
                    "photos": [
                        {
                            "id": 42,
                            "url": "https://pexels.test/photo/42",
                            "photographer": "A Photographer",
                            "photographer_url": "https://pexels.test/a",
                            "alt": "A workspace",
                            "width": 1600,
                            "height": 900,
                            "avg_color": "#111111",
                            "src": {"large": "https://images.pexels.com/42.jpg"},
                        }
                    ]
                },
            )
        return httpx.Response(200, content=b"not-an-image", headers={"content-type": "text/plain"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        pexels = PexelsClient("key", client=client)
        photo = (await pexels.search(_requirement("photo")))[0]
        assert photo.orientation == "landscape"
        with pytest.raises(ProviderUnavailable, match="not an image"):
            await pexels.download(photo)
    finally:
        await client.aclose()


def test_wrong_photo_orientation_is_rejected() -> None:
    portrait = PhotoResource(
        provider="pexels",
        photo_id="portrait",
        photo_page="https://pexels.test/portrait",
        photographer="",
        photographer_url="",
        alt="",
        width=800,
        height=1200,
        orientation="portrait",
        average_color="",
        image_url="https://images.test/portrait.jpg",
        source_reference="https://pexels.test/portrait",
    )
    requirement = ResourceRequirement(
        requirement_id="photo",
        kind="photo",
        scope="scene",
        constraints={"orientation": "landscape"},
    )
    assert choose_photo([portrait], requirement) is None
