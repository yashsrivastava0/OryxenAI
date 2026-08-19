from __future__ import annotations

import io
import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from oryxenai.agents.build_preparation.materializer import (
    _overview_text,
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
    Image.effect_noise((1200, 700), 40).convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _output_dir() -> Path:
    path = Path("output") / "test-build-preparation" / str(uuid4())
    path.mkdir(parents=True)
    return path


def test_overview_explains_handoff_without_imposing_portfolio_quotas() -> None:
    overview = _overview_text(
        BuildContextDraft(
            overview_markdown="# Portfolio context",
            routes=[
                RouteBuildContext(
                    route_id="home",
                    path="/",
                    resource_ids=["resource-image"],
                    acceptance_criteria=["Keyboard access"],
                )
            ],
        )
    )

    assert "## How Code Generator consumes this pack" in overview
    assert "`execution/contract.json`" in overview
    assert "`resources/components/`" in overview
    assert "`home` at `/`" in overview
    assert "does not set a fixed screen count" in overview
    assert "not a visual template" in overview


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
async def test_materializer_tries_closed_set_image_alternate_after_validation_failure() -> None:
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
        )
        primary = FetchedResource(
            resource_id="resource-primary",
            need_id=need.need_id,
            kind="photo",
            provider="pexels",
            provider_asset_id="primary",
            image_url="https://images.pexels.com/primary.jpg",
        )
        alternate = primary.model_copy(
            update={
                "resource_id": "resource-alternate",
                "provider_asset_id": "alternate",
                "image_url": "https://images.pexels.com/alternate.jpg",
            }
        )

        async def download(candidate: FetchedResource) -> bytes:
            return b"corrupt" if candidate.resource_id == primary.resource_id else _png()

        result = await materialize_build_context(
            output_dir=output_dir,
            run_id="run-image-alternate",
            routes=[route],
            needs=[need],
            selections=[
                ResourceSelection(
                    need_id=need.need_id,
                    selected_resource_id=primary.resource_id,
                    alternate_resource_ids=[alternate.resource_id],
                )
            ],
            candidates=[primary, alternate],
            context=BuildContextDraft(
                overview_markdown="# Build context",
                routes=[RouteBuildContext(route_id="home", brief_markdown="# Home")],
            ),
            content_architect={},
            settings=settings,
            download_image=download,
        )

        assert result.effective_selections[0].selected_resource_id == alternate.resource_id
        assert [item["status"] for item in result.resource_attempts] == [
            "rejected",
            "materialized",
        ]
        assert result.resources[0]["id"] == alternate.resource_id
        assert result.resources[0]["source_hashes"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_materializer_tries_image_alternate_after_duplicate_local_content() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        route = RouteScope(route_id="home", path="/", title="Home")
        first_need = ResourceNeed(
            need_id="first-photo-need",
            kind="asset",
            source_id="asset-1",
            category="photo",
            purpose="Opening image",
            route_ids=["home"],
        )
        second_need = first_need.model_copy(
            update={"need_id": "second-photo-need", "source_id": "asset-2"}
        )
        first = FetchedResource(
            resource_id="resource-first",
            need_id=first_need.need_id,
            kind="photo",
            provider="pexels",
            provider_asset_id="first",
            image_url="https://images.pexels.com/first.jpg",
        )
        duplicate = FetchedResource(
            resource_id="resource-duplicate",
            need_id=second_need.need_id,
            kind="photo",
            provider="pexels",
            provider_asset_id="duplicate",
            image_url="https://images.pexels.com/duplicate.jpg",
        )
        alternate = duplicate.model_copy(
            update={
                "resource_id": "resource-distinct",
                "provider_asset_id": "distinct",
                "image_url": "https://images.pexels.com/distinct.jpg",
            }
        )

        # The first two candidates intentionally share bytes; the alternate
        # uses a different deterministic image so the duplicate guard can
        # exercise the closed-set retry path.
        first_bytes = _png()
        alternate_bytes = Image.effect_noise((1200, 700), 90).convert("RGB")
        alternate_buffer = io.BytesIO()
        alternate_bytes.save(alternate_buffer, format="PNG")
        payloads = {
            first.resource_id: first_bytes,
            duplicate.resource_id: first_bytes,
            alternate.resource_id: alternate_buffer.getvalue(),
        }

        async def download_distinct(candidate: FetchedResource) -> bytes:
            return payloads[candidate.resource_id]

        result = await materialize_build_context(
            output_dir=output_dir,
            run_id="run-image-duplicate",
            routes=[route],
            needs=[first_need, second_need],
            selections=[
                ResourceSelection(
                    need_id=first_need.need_id,
                    selected_resource_id=first.resource_id,
                ),
                ResourceSelection(
                    need_id=second_need.need_id,
                    selected_resource_id=duplicate.resource_id,
                    alternate_resource_ids=[alternate.resource_id],
                ),
            ],
            candidates=[first, duplicate, alternate],
            context=BuildContextDraft(
                overview_markdown="# Build context",
                routes=[RouteBuildContext(route_id="home", brief_markdown="# Home")],
            ),
            content_architect={},
            settings=settings,
            download_image=download_distinct,
        )

        assert result.effective_selections[1].selected_resource_id == alternate.resource_id
        assert [item["status"] for item in result.resource_attempts] == [
            "materialized",
            "rejected",
            "materialized",
        ]
        assert {item["id"] for item in result.resources} == {
            first.resource_id,
            alternate.resource_id,
        }
        assert len({item["content_hash"] for item in result.resources}) == 2
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_materializer_rejects_generated_local_visuals() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        photo_need = ResourceNeed(
            need_id="visual-photo-need",
            kind="asset",
            source_id="editorial-hero-image",
            category="editorial_photo",
            purpose="Abstract hero visual",
            route_ids=["home"],
            required_for_handoff=True,
        )
        component_need = ResourceNeed(
            need_id="visual-component-need",
            kind="resource",
            source_id="visual-component-home",
            category="visual_component",
            purpose="Featured project visual treatment",
            route_ids=["home"],
            required_for_handoff=True,
        )
        candidates = [
            FetchedResource(
                resource_id="generated-photo",
                need_id=photo_need.need_id,
                kind="photo",
                provider="generated-local",
                source_reference="local://oryxenai/generated-visual",
                license="local-generated",
            ),
            FetchedResource(
                resource_id="generated-component",
                need_id=component_need.need_id,
                kind="component",
                provider="generated-local",
                source_reference="local://oryxenai/generated-component",
                source_files={
                    "PreparedVisualStory.tsx": "export default function PreparedVisualStory() { return null; }"
                },
                license="local-generated",
            ),
        ]
        result = await materialize_build_context(
            output_dir=output_dir,
            run_id="run-generated-local",
            routes=[RouteScope(route_id="home", path="/")],
            needs=[photo_need, component_need],
            selections=[
                ResourceSelection(
                    need_id=photo_need.need_id, selected_resource_id="generated-photo"
                ),
                ResourceSelection(
                    need_id=component_need.need_id, selected_resource_id="generated-component"
                ),
            ],
            candidates=candidates,
            context=BuildContextDraft(
                overview_markdown="# Build context",
                routes=[RouteBuildContext(route_id="home", brief_markdown="# Home")],
            ),
            content_architect={},
            settings=settings,
        )
        root = Path(result.root_path)
        assert not (root / "resources/images/generated-photo.png").exists()
        assert not (
            root
            / "resources/components/generated-local/generated-component/source/PreparedVisualStory.tsx"
        ).exists()
        assert {item["disposition"] for item in result.resources} == {
            "custom_implementation_required",
        }
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_materializer_rejects_remote_only_unsplash_resources() -> None:
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

        assert triggered == []
        assert not any(item.kind == "image" for item in result.files)
        assert result.resources[0]["disposition"] == "custom_implementation_required"
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
                "registry/magicui/magic-card.tsx": (
                    "import type { ReactNode } from 'react';\n"
                    "export function MagicCard({ children }: { children: ReactNode }) {\n"
                    '  return <section className="magic-card">{children}</section>;\n'
                    "}\n"
                )
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
        assert resource["expected_exports"] == ["MagicCard"]
        assert resource["usage_contract"]["local_paths"]
        assert resource["usage_contract"]["expected_exports"] == ["MagicCard"]
        assert resource["usage_contract"]["source_hashes"]
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
        assert entry["later_fetch"]["providers"] == [
            "shadcn",
            "magicui",
            "smoothui",
            "cultui",
        ]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
