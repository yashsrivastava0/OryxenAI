from __future__ import annotations

from oryxenai.agents.code_generator.core.final_source_validation import _slot_is_bound


def test_required_media_binding_needs_a_real_url_not_a_comment() -> None:
    slot = {
        "category": "editorial_photo",
        "resolution_type": "local_materialized",
        "local_paths": ["resources/images/hero.png"],
    }
    assert _slot_is_bound(
        slot=slot,
        source_by_path={
            "src/routes/home/index.tsx": '<img src="/resources/pack/images/hero.png" alt="" />'
        },
    )
    assert not _slot_is_bound(
        slot=slot,
        source_by_path={"src/routes/home/index.tsx": "// /resources/pack/images/hero.png"},
    )


def test_required_media_binding_accepts_trusted_local_image_slot_reference() -> None:
    slot = {
        "category": "editorial_photo",
        "resource_slot_id": "slot-hero-photo",
        "resolution_type": "local_materialized",
        "local_paths": ["resources/images/hero.png"],
    }

    assert _slot_is_bound(
        slot=slot,
        source_by_path={
            "src/routes/home/sections/hero.tsx": (
                'import { LocalImage } from "../../../components/generated/SharedSystems";\n'
                'export const Hero = () => <LocalImage resourceId="slot-hero-photo" alt="" />;'
            )
        },
    )
    assert not _slot_is_bound(
        slot=slot,
        source_by_path={
            "src/routes/home/sections/hero.tsx": (
                '// <LocalImage resourceId="slot-hero-photo" />\nexport const Hero = () => <div />;'
            )
        },
    )


def test_required_component_binding_needs_import_and_render() -> None:
    slot = {
        "category": "visual_component",
        "resolution_type": "local_materialized",
        "local_paths": [
            "resources/components/generated-local/story/source/PreparedVisualStory.tsx"
        ],
    }
    assert _slot_is_bound(
        slot=slot,
        source_by_path={
            "src/routes/home/index.tsx": (
                'import VisualStory from "../../generated/resources/pack/components/'
                'generated-local/story/source/PreparedVisualStory";\n'
                "export const Page = () => <VisualStory />;"
            )
        },
    )
    assert not _slot_is_bound(
        slot=slot,
        source_by_path={
            "src/routes/home/index.tsx": (
                "// PreparedVisualStory\nexport const Page = () => <div />;"
            )
        },
    )


def test_package_binding_requires_an_admitted_import() -> None:
    slot = {
        "category": "icon",
        "resolution_type": "target_package_binding",
        "package_name": "lucide-react",
        "expected_exports": ["ArrowUpRight"],
    }
    assert _slot_is_bound(
        slot=slot,
        source_by_path={
            "src/routes/home/index.tsx": (
                'import { ArrowUpRight } from "lucide-react";\n'
                "export const Page = () => <ArrowUpRight />;"
            )
        },
    )
    assert not _slot_is_bound(
        slot=slot,
        source_by_path={"src/generated/resource-manifest.ts": "lucide-react ArrowUpRight"},
    )
