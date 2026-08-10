from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from oryxenai.agents.content_architect.schemas import (
    ContentArchitectApproval,
    ContentArchitectState,
    ContentSection,
    PageContentPack,
    PublicationStatus,
    RoutePlanEntry,
)
from oryxenai.agents.visual_design_director.schemas import (
    PagePublicationStatus,
    PageVisualDirection,
    SceneDirection,
    VisualDesignDirectorApproval,
    VisualDesignDirectorState,
)
from oryxenai.build_preparation.bundle import (
    BundleIntegrityError,
    create_bundle,
    extract_verified,
    verify_zip_file,
)
from oryxenai.build_preparation.compiler import compile_blueprint, compile_context
from oryxenai.build_preparation.resources import resolve_local_requirements
from oryxenai.build_preparation.schemas import ResourceManifest
from oryxenai.build_preparation.storage import MemoryArtifactStore


def _states() -> tuple[ContentArchitectState, VisualDesignDirectorState]:
    content = ContentArchitectState(
        status="approved",
        site_story_strategy={
            "presentation_mode": "single_page",
            "primary_audience": "Hiring managers",
            "primary_action": "Contact",
            "narrative_thesis": "Reliable systems, clearly explained.",
        },
        route_plan=[
            RoutePlanEntry(
                route_id="home",
                path="/",
                purpose="Portfolio home",
                section_sequence=["hero", "project"],
                publication_status=PublicationStatus.APPROVED,
            )
        ],
        page_content_packs=[
            PageContentPack(
                route_id="home",
                sections=[
                    ContentSection(section_id="hero", content={"headline": "Hello"}),
                    ContentSection(section_id="project", content={"title": "QueueGuard"}),
                ],
            )
        ],
        approved=ContentArchitectApproval(content_hash="content-hash"),
    )
    visual = VisualDesignDirectorState(
        status="approved",
        visual_language={"typography": "calm"},
        pages=[
            PageVisualDirection(
                route_id="home",
                publication_status=PagePublicationStatus.APPROVED,
                compilable=True,
                path="/",
                scenes=[
                    SceneDirection(
                        scene_id="hero-scene",
                        route_id="home",
                        content_refs=["hero"],
                        reduced_motion_behavior="static",
                        failure_safe_static_state="static hero",
                    )
                ],
            )
        ],
        approved=VisualDesignDirectorApproval(visual_direction_hash="visual-hash"),
    )
    return content, visual


def test_compiles_separate_route_and_scene_context() -> None:
    content, visual = _states()
    from oryxenai.build_preparation.schemas import SourceRef

    blueprint, packets, _ = compile_blueprint(
        content,
        visual,
        source=SourceRef(content_hash="content-hash", visual_direction_hash="visual-hash"),
        preparation_hash="input-hash",
    )
    manifest = resolve_local_requirements(blueprint.resource_requirements)
    context = compile_context(blueprint, packets, manifest)
    assert blueprint.route_map[0].packet_id == "page-home"
    assert packets[0].scene_sequence == ["hero-scene"]
    assert context.global_context.route_graph[0]["route_id"] == "home"


def test_pending_route_is_gated_without_a_page_packet() -> None:
    content, visual = _states()
    content.route_plan[0].publication_status = PublicationStatus.PENDING
    visual.pages[0].publication_status = PagePublicationStatus.PENDING
    visual.pages[0].compilable = False
    from oryxenai.build_preparation.schemas import SourceRef

    blueprint, packets, _ = compile_blueprint(
        content,
        visual,
        source=SourceRef(),
        preparation_hash="input-hash",
    )
    assert packets == []
    assert blueprint.gated_routes[0].route_id == "home"


def test_pending_visual_route_is_gated_without_public_packet() -> None:
    content, visual = _states()
    visual.pages[0].publication_status = PagePublicationStatus.PENDING
    visual.pages[0].compilable = False
    from oryxenai.build_preparation.schemas import SourceRef

    blueprint, packets, _ = compile_blueprint(
        content,
        visual,
        source=SourceRef(),
        preparation_hash="input-hash",
    )
    assert packets == []
    assert blueprint.gated_routes[0].publication_status == "pending"


def test_fixed_icon_and_font_requirements_resolve_without_network() -> None:
    from oryxenai.build_preparation.schemas import ResourceRequirement

    manifest = resolve_local_requirements(
        [
            ResourceRequirement(requirement_id="icons", kind="icon", scope="global"),
            ResourceRequirement(requirement_id="fonts", kind="font", scope="global"),
        ]
    )
    by_id = {entry.manifest_resource_id: entry for entry in manifest.entries}
    assert by_id["target-lucide-icons"].disposition == "materialized"
    assert by_id["builtin-system-font-stack"].disposition == "materialized"


def test_bundle_is_verified_and_extracts_safely() -> None:
    content, visual = _states()
    from oryxenai.build_preparation.schemas import SourceRef

    blueprint, packets, _ = compile_blueprint(
        content,
        visual,
        source=SourceRef(),
        preparation_hash="input-hash",
    )
    manifest = ResourceManifest()
    context = compile_context(blueprint, packets, manifest)
    working = Path("scratch") / f"build-preparation-{uuid4().hex}"
    working.mkdir(parents=True, exist_ok=True)
    try:
        bundle, digest, size = create_bundle(
            blueprint,
            manifest,
            context,
            packets,
            resource_files={"resources/icons/check.svg": b"<svg/>"},
            workspace_dir=working,
        )
        assert size == bundle.stat().st_size
        assert digest
        second_bundle, second_digest, _ = create_bundle(
            blueprint,
            manifest,
            context,
            packets,
            resource_files={"resources/icons/check.svg": b"<svg/>"},
            workspace_dir=working,
        )
        assert second_digest == digest
        assert second_bundle.read_bytes() == bundle.read_bytes()
        checksums = verify_zip_file(bundle)
        assert "experience-blueprint.json" in checksums
        destination = Path(working) / "unpacked"
        extract_verified(bundle, destination)
        assert (destination / "resources/icons/check.svg").read_bytes() == b"<svg/>"
    finally:
        shutil.rmtree(working, ignore_errors=True)


def test_bundle_rejects_traversal() -> None:
    content, visual = _states()
    from oryxenai.build_preparation.schemas import SourceRef

    blueprint, packets, _ = compile_blueprint(
        content, visual, source=SourceRef(), preparation_hash="hash"
    )
    manifest = ResourceManifest()
    context = compile_context(blueprint, packets, manifest)
    working = Path("scratch") / f"build-preparation-{uuid4().hex}"
    working.mkdir(parents=True, exist_ok=True)
    try:
        with pytest.raises(BundleIntegrityError):
            create_bundle(
                blueprint,
                manifest,
                context,
                packets,
                resource_files={"../secret": b"no"},
                workspace_dir=working,
            )
    finally:
        shutil.rmtree(working, ignore_errors=True)


@pytest.mark.asyncio
async def test_memory_store_expires_and_downloads() -> None:
    from datetime import UTC, datetime, timedelta

    store = MemoryArtifactStore()
    working = Path("scratch") / f"build-preparation-{uuid4().hex}"
    working.mkdir(parents=True, exist_ok=True)
    try:
        source = Path(working) / "bundle.zip"
        source.write_bytes(b"bundle")
        ref = await store.put(
            "temporary/test.zip",
            source,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            metadata={},
        )
        assert (await store.head(ref.object_key)) is not None
        target = Path(working) / "download.zip"
        await store.download(ref.object_key, target)
        assert target.read_bytes() == b"bundle"
    finally:
        shutil.rmtree(working, ignore_errors=True)
