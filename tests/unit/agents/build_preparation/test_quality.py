from __future__ import annotations

from oryxenai.agents.build_preparation.quality import (
    build_handoff_report,
    qualify_candidates,
    select_required_candidates,
)
from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    BuildPreparationSourceRef,
    FetchedResource,
    MaterializationResult,
    ResourceNeed,
    ResourceSelection,
    RouteBuildContext,
    RouteScope,
)


def _source_ref() -> BuildPreparationSourceRef:
    return BuildPreparationSourceRef(
        content_architect_content_hash="content-hash",
        visual_design_director_direction_hash="visual-hash",
        input_projection_hash="projection-hash",
    )


def _required_image() -> ResourceNeed:
    return ResourceNeed(
        need_id="need-image",
        kind="asset",
        source_id="editorial-hero-image",
        category="editorial_photo",
        route_ids=["home"],
        required_for_handoff=True,
        query_terms=["abstract technology", "editorial"],
    )


def _route_handoff_args() -> dict[str, object]:
    return {
        "routes": [RouteScope(route_id="home", path="/", title="Home")],
        "build_context": BuildContextDraft(
            routes=[
                RouteBuildContext(
                    route_id="home",
                    path="/",
                    brief_markdown="Build the approved home page.",
                )
            ]
        ),
        "content_architect": {
            "page_content_packs": [
                {
                    "route_id": "home",
                    "sections": [{"section_id": "hero", "content": "Grounded copy"}],
                }
            ]
        },
    }


def test_quality_rejects_unrelated_component_candidate() -> None:
    need = ResourceNeed(
        need_id="need-component",
        kind="resource",
        source_id="hero-pattern",
        category="hero_pattern",
        query_terms=["asymmetric hero pattern"],
    )
    candidate = FetchedResource(
        resource_id="component-1",
        need_id=need.need_id,
        kind="component",
        provider="shadcn",
        provider_asset_id="checkbox-with-text",
        title="Checkbox with text",
        source_files={"checkbox.tsx": "export const Checkbox = () => null"},
        dependencies=["react"],
        license="MIT",
    )
    qualification = qualify_candidates([need], [candidate])[0]
    assert qualification.eligible is False
    assert "COMPONENT_NOT_RELEVANT" in qualification.issue_codes


def test_quality_rejects_synthetic_visual_candidates() -> None:
    image_need = _required_image()
    image = FetchedResource(
        resource_id="mock-image",
        need_id=image_need.need_id,
        kind="photo",
        provider="pexels",
        provider_asset_id="mock-1",
        image_url="https://images.pexels.com/mock/1.jpg",
        width=1600,
        height=1000,
        photographer="Fixture",
        attribution_url="https://www.pexels.com/",
        license="Pexels license",
        license_reference="https://www.pexels.com/legal-pages/license/",
    )
    component_need = ResourceNeed(
        need_id="need-component",
        kind="resource",
        source_id="visual-component",
        category="visual_component",
        required_for_handoff=True,
        query_terms=["workspace", "card"],
    )
    component = FetchedResource(
        resource_id="generated-component",
        need_id=component_need.need_id,
        kind="component",
        provider="generated-local",
        source_files={"component.tsx": "export function Card() { return <div>Card</div>; }"},
        license="MIT",
        license_reference="https://example.test/license",
    )
    qualifications = qualify_candidates([image_need, component_need], [image, component])
    assert qualifications[0].eligible is False
    assert "SYNTHETIC_IMAGE_CANDIDATE" in qualifications[0].issue_codes
    assert qualifications[1].eligible is False
    assert "SYNTHETIC_COMPONENT_CANDIDATE" in qualifications[1].issue_codes


def test_quality_accepts_allowed_versioned_component_dependencies() -> None:
    need = ResourceNeed(
        need_id="need-component",
        kind="resource",
        source_id="workspace-card",
        category="component",
        query_terms=["workspace", "card"],
    )
    candidate = FetchedResource(
        resource_id="component-1",
        need_id=need.need_id,
        kind="component",
        provider="shadcn",
        provider_asset_id="workspace-card",
        title="Workspace card",
        source_files={
            "card.tsx": (
                "import type { ReactNode } from 'react';\n"
                "export function Card({ children }: { children: ReactNode }) {\n"
                '  return <article data-testid="card">{children}</article>;\n'
                "}\n"
            )
        },
        dependencies=["react@^19.0.0"],
        license="MIT",
        license_reference="https://example.test/license",
    )
    qualification = qualify_candidates([need], [candidate])[0]
    assert qualification.eligible is True


def test_component_quality_uses_provider_terms_from_typed_intent() -> None:
    from oryxenai.agents.build_preparation.schemas import ComponentIntent

    need = ResourceNeed(
        need_id="need-disclosure",
        kind="resource",
        source_id="capability-disclosure",
        category="visual_component",
        query_terms=["capability grouping"],
        component_intent=ComponentIntent(
            role_id="capability-grouping",
            route_id="home",
            section_id="capabilities",
            interaction_class="disclosure",
            interaction_outcome="Reveal grouped approved capabilities.",
            provider_terms=["accordion", "collapsible", "disclosure"],
        ),
    )
    candidate = FetchedResource(
        resource_id="accordion-1",
        need_id=need.need_id,
        kind="component",
        provider="shadcn",
        provider_asset_id="accordion",
        title="Accordion",
        description="Accessible collapsible disclosure groups.",
        source_files={
            "accordion.tsx": (
                "import * as React from 'react';\n"
                "export function Accordion() { return <div aria-expanded={false} className='accordion' data-state='closed'><button type='button'>Open approved capability groups</button><span>Accessible disclosure content</span></div>; }\n"
            )
        },
        dependencies=["react"],
        license="MIT",
        license_reference="https://example.test/license",
        retrieval_metadata={"provider_terms": ["accordion", "disclosure"]},
    )

    qualification = qualify_candidates([need], [candidate])[0]

    assert qualification.eligible is True
    assert qualification.relevance_score >= 70


def test_quality_rejects_npm_alias_for_allowed_dependency_name() -> None:
    need = ResourceNeed(
        need_id="need-component",
        kind="resource",
        source_id="workspace-card",
        category="component",
        query_terms=["workspace", "card"],
    )
    candidate = FetchedResource(
        resource_id="component-1",
        need_id=need.need_id,
        kind="component",
        provider="shadcn",
        provider_asset_id="workspace-card",
        title="Workspace card",
        source_files={"card.tsx": "export const Card = () => null"},
        dependencies=["react@npm:unreviewed-package@1.0.0"],
        license="MIT",
    )
    qualification = qualify_candidates([need], [candidate])[0]
    assert qualification.eligible is False
    assert "COMPONENT_DEPENDENCY_NOT_ALLOWED" in qualification.issue_codes


def test_required_local_image_is_forced_then_admitted_only_when_materialized() -> None:
    need = _required_image()
    candidate = FetchedResource(
        resource_id="image-1",
        need_id=need.need_id,
        kind="photo",
        provider="pexels",
        provider_asset_id="1",
        source_reference="https://www.pexels.com/photo/1",
        image_url="https://images.pexels.com/photo/1.jpg",
        title="Abstract technology light",
        description="Abstract technology editorial image",
        photographer="A Photographer",
        attribution_url="https://www.pexels.com/photo/1",
        width=1600,
        height=1000,
        license="Pexels license",
        license_reference="https://www.pexels.com/legal-pages/license/",
    )
    qualifications = qualify_candidates([need], [candidate])
    selections, warnings = select_required_candidates(
        [ResourceSelection(need_id=need.need_id, fallback="blocked")], [need], qualifications
    )
    assert selections[0].selected_resource_id == candidate.resource_id
    assert warnings
    pending = build_handoff_report(
        source_ref=_source_ref(),
        **_route_handoff_args(),
        needs=[need],
        selections=selections,
        qualifications=qualifications,
        materialization=MaterializationResult(root_path="x", relative_root="x"),
    )
    assert pending.handoff_eligible is False
    assert pending.issues[0].code == "REQUIRED_RESOURCE_NOT_MATERIALIZED"
    complete = build_handoff_report(
        source_ref=_source_ref(),
        **_route_handoff_args(),
        needs=[need],
        selections=selections,
        qualifications=qualifications,
        materialization=MaterializationResult(
            root_path="x",
            relative_root="x",
            resources=[{"id": candidate.resource_id, "local_path": "resources/images/image-1.jpg"}],
        ),
    )
    assert complete.handoff_eligible is True
    assert complete.upstream_approval_verified is True


def test_handoff_is_review_only_without_both_approval_hashes() -> None:
    report = build_handoff_report(
        source_ref=BuildPreparationSourceRef(input_projection_hash="projection-hash"),
        **_route_handoff_args(),
        needs=[],
        selections=[],
        qualifications=[],
        materialization=MaterializationResult(root_path="x", relative_root="x"),
    )
    assert report.handoff_eligible is False
    assert report.upstream_approval_verified is False
    assert [issue.code for issue in report.issues] == ["UPSTREAM_APPROVAL_UNVERIFIED"]


def test_handoff_rejects_empty_public_route_content() -> None:
    report = build_handoff_report(
        source_ref=_source_ref(),
        routes=[RouteScope(route_id="home", path="/")],
        build_context=BuildContextDraft(
            routes=[RouteBuildContext(route_id="home", path="/", brief_markdown="Build home.")]
        ),
        content_architect={"page_content_packs": [{"route_id": "home", "sections": []}]},
        needs=[],
        selections=[],
        qualifications=[],
        materialization=MaterializationResult(root_path="x", relative_root="x"),
    )
    assert report.handoff_eligible is False
    assert [issue.code for issue in report.issues] == ["ROUTE_PUBLIC_CONTENT_MISSING"]
