from __future__ import annotations

import io
import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from oryxenai.agents.build_preparation.materializer import (
    _safe_component_source_path,
    materialize_build_context,
)
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


@pytest.mark.parametrize("path", ["../escape.tsx", "/absolute.tsx", "C:\\escape.tsx"])
def test_component_source_paths_must_be_safe_relative_paths(path: str) -> None:
    with pytest.raises(ValueError):
        _safe_component_source_path(path)


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
        assert (root / "resources/plan.json").is_file()
        assert not (root / "target/package-lock.json").exists()
        target = json.loads((root / "target/target-contract.json").read_text())
        assert target["dependency_resolution"]["lockfile_included"] is False
        assert target["dependency_resolution"]["code_generator_must_generate_lockfile"] is True
        route_resources = json.loads((root / "routes/home/resources.json").read_text())
        assert route_resources["need_ids"] == [need.need_id]
        plan = json.loads((root / "resources/plan.json").read_text())
        assert plan["needs"][0]["disposition"] == "local_file"
        assert plan["needs"][0]["later_fetch"]["allowed"] is False
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


@pytest.mark.asyncio
async def test_materializer_preserves_component_source_paths_and_license_provenance() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        need = ResourceNeed(
            need_id="component-need",
            kind="resource",
            source_id="magic-card",
            category="component",
            purpose="Interactive project surface",
            route_ids=["home"],
            scene_ids=["home-projects"],
            fallback="Use a plain bordered project surface.",
        )
        candidate = FetchedResource(
            resource_id="resource-magicui-card",
            need_id=need.need_id,
            kind="component",
            provider="magicui",
            provider_asset_id="magic-card",
            source_reference="https://magicui.design/r/magic-card.json",
            source_files={
                "registry/magicui/magic-card.tsx": "export function MagicCard() { return null; }"
            },
            dependencies=["motion"],
            license="MIT",
            license_reference="https://github.com/magicuidesign/magicui/blob/main/LICENSE.md",
        )
        result = await materialize_build_context(
            output_dir=output_dir,
            run_id="run-component",
            routes=[RouteScope(route_id="home", path="/")],
            needs=[need],
            selections=[
                ResourceSelection(
                    need_id=need.need_id,
                    selected_resource_id=candidate.resource_id,
                    fallback=need.fallback,
                )
            ],
            candidates=[candidate],
            context=BuildContextDraft(
                overview_markdown="# Build context",
                routes=[RouteBuildContext(route_id="home", brief_markdown="# Home")],
            ),
            content_architect={},
            settings=settings,
        )

        root = Path(result.root_path)
        expected = (
            root
            / "resources/components/magicui/resource-magicui-card/source/registry/magicui/magic-card.tsx"
        )
        assert expected.is_file()
        manifest = json.loads((root / "resources/manifest.json").read_text())
        resource = manifest["resources"][0]
        assert resource["disposition"] == "adaptable_source"
        assert resource["source_files"][0]["original_path"] == ("registry/magicui/magic-card.tsx")
        assert resource["license_reference"].endswith("LICENSE.md")
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_resource_plan_makes_later_fetch_an_exclusive_codegen_only_fallback() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        need = ResourceNeed(
            need_id="diagram-need",
            kind="resource",
            source_id="diagram-process-flow",
            category="diagram_primitive",
            purpose="Representative process flow",
            route_ids=["home"],
            scene_ids=["home-projects"],
            fallback="Use a lightweight custom diagram.",
        )
        result = await materialize_build_context(
            output_dir=output_dir,
            run_id="run-resource-plan",
            routes=[RouteScope(route_id="home", path="/")],
            needs=[need],
            selections=[ResourceSelection(need_id=need.need_id, fallback=need.fallback)],
            candidates=[],
            context=BuildContextDraft(
                overview_markdown="# Build context",
                routes=[RouteBuildContext(route_id="home", brief_markdown="# Home")],
            ),
            content_architect={},
            settings=settings,
        )

        plan = json.loads(
            (Path(result.root_path) / "resources/plan.json").read_text(encoding="utf-8")
        )
        entry = plan["needs"][0]
        assert entry["disposition"] == "custom_fallback"
        assert entry["later_fetch"]["allowed"] is True
        assert entry["later_fetch"]["phase"] == "code_generation_only"
        assert entry["later_fetch"]["must_replace_not_duplicate"] is True
        assert entry["later_fetch"]["providers"] == ["shadcn", "magicui"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
