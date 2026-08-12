from __future__ import annotations

import io
import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from oryxenai.agents.build_preparation.materializer import materialize_build_context
from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    FetchedResource,
    ResourceNeed,
    ResourceSelection,
    RouteBuildContext,
    RouteScope,
)
from oryxenai.core.settings import Settings


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 3), "#334155").save(buffer, format="PNG")
    return buffer.getvalue()


def _output_dir() -> Path:
    path = Path("output") / "test-build-preparation" / str(uuid4())
    path.mkdir(parents=True)
    return path


@pytest.mark.asyncio
async def test_materializer_inspects_pexels_bytes_and_writes_local_tree() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        route = RouteScope(route_id="home", path="/", title="Home")
        need = ResourceNeed(
            need_id="photo-need",
            kind="asset",
            source_id="asset-1",
            category="photo",
            purpose="Hero image",
            route_ids=["home"],
            fallback="Use a typographic hero.",
        )
        candidate = FetchedResource(
            resource_id="resource-pexels-1",
            need_id=need.need_id,
            kind="photo",
            provider="pexels",
            provider_asset_id="1",
            source_reference="https://www.pexels.com/photo/1",
            image_url="https://images.pexels.com/photo/1",
            title="A calm workspace",
        )
        context = BuildContextDraft(
            overview_markdown="# Build context",
            routes=[
                RouteBuildContext(
                    route_id="home",
                    path="/",
                    brief_markdown="# Home",
                    resource_ids=[candidate.resource_id],
                )
            ],
        )

        async def download(_candidate: FetchedResource) -> bytes:
            return _png()

        result = await materialize_build_context(
            output_dir=output_dir,
            run_id="run-1",
            routes=[route],
            needs=[need],
            selections=[
                ResourceSelection(need_id=need.need_id, selected_resource_id=candidate.resource_id)
            ],
            candidates=[candidate],
            context=context,
            content_architect={},
            settings=settings,
            download_image=download,
        )

        root = output_dir / "build-preparation" / "run-1" / "build-context"
        assert result.root_path == str(root)
        assert (root / "overview.md").is_file()
        assert any(item.kind == "image" for item in result.files)
        metadata = json.loads((root / f"resources/images/{candidate.resource_id}.json").read_text())
        assert metadata["inspection_level"] == "pixel_inspected"
        assert (root / "resources/manifest.json").is_file()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_materializer_keeps_unsplash_metadata_only() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        need = ResourceNeed(
            need_id="photo-need",
            kind="asset",
            source_id="asset-1",
            category="photo",
            route_ids=["home"],
        )
        candidate = FetchedResource(
            resource_id="resource-unsplash-1",
            need_id=need.need_id,
            kind="photo",
            provider="unsplash",
            provider_asset_id="1",
            source_reference="https://unsplash.com/photos/1",
            hotlink_url="https://images.unsplash.com/photo-1",
            download_tracking_url="https://api.unsplash.com/photos/1/download",
        )
        context = BuildContextDraft(
            overview_markdown="# Build context",
            routes=[RouteBuildContext(route_id="home", brief_markdown="# Home")],
        )
        triggered: list[str] = []

        async def trigger(resource: FetchedResource) -> None:
            triggered.append(resource.resource_id)

        result = await materialize_build_context(
            output_dir=output_dir,
            run_id="run-2",
            routes=[RouteScope(route_id="home", path="/")],
            needs=[need],
            selections=[
                ResourceSelection(need_id=need.need_id, selected_resource_id=candidate.resource_id)
            ],
            candidates=[candidate],
            context=context,
            content_architect={},
            settings=settings,
            trigger_download=trigger,
        )

        assert triggered == [candidate.resource_id]
        assert not any(item.kind == "image" for item in result.files)
        metadata = json.loads(
            (
                output_dir
                / "build-preparation/run-2/build-context/resources/images/resource-unsplash-1.json"
            ).read_text()
        )
        assert metadata["inspection_level"] == "metadata_only"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_materializer_excludes_private_and_pending_route_content() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        result = await materialize_build_context(
            output_dir=output_dir,
            run_id="run-public-filter",
            routes=[RouteScope(route_id="home", path="/")],
            needs=[],
            selections=[],
            candidates=[],
            context=BuildContextDraft(
                overview_markdown="# Build context",
                routes=[RouteBuildContext(route_id="home", brief_markdown="# Home")],
            ),
            content_architect={
                "page_content_packs": [
                    {
                        "route_id": "home",
                        "sections": [
                            {"id": "public", "status": "approved", "body": "Keep"},
                            {"id": "pending", "status": "pending", "body": "Drop"},
                        ],
                    }
                ],
                "public_content_manifest": {"nav": [{"label": "Home", "status": "approved"}]},
            },
            settings=settings,
        )
        route_data = json.loads(
            (Path(result.root_path) / "routes/home/data.json").read_text(encoding="utf-8")
        )
        assert route_data["sections"] == [{"body": "Keep", "id": "public", "status": "approved"}]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
