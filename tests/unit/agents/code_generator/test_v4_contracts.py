from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from oryxenai.agents.code_generator.core.design_realization import compile_design_realization
from oryxenai.agents.code_generator.core.development_planner import (
    SitePlanValidationError,
    validate_v4_blueprint_identities,
)
from oryxenai.agents.code_generator.core.development_schemas import (
    CreativeDirectionSetV3,
    DesignTokenSystemV4,
    ExecutionBindingV2,
    ExperienceBlueprintV4,
    GenerationContextReceipt,
    QualityReviewDraftV1,
    ResourceSearchIntentV2,
    RoutePlan,
    SitePlan,
    SourceFileChange,
    SourceGenerationEnvelopeV2,
    WorkUnit,
)
from oryxenai.agents.code_generator.core.generation_contract import (
    build_generation_contract,
    render_contract_instructions,
)
from oryxenai.agents.code_generator.core.quality_review import (
    QualityReviewError,
    stamp_quality_review_receipt,
    validate_quality_review_receipt,
)
from oryxenai.agents.code_generator.core.resource_query import (
    compile_resource_queries,
    query_receipt,
)
from oryxenai.agents.code_generator.core.source_generation_adapter import (
    adapt_v4_generation_result,
)
from oryxenai.agents.code_generator.core.source_manifest import _materialize_image_assets
from oryxenai.agents.code_generator.core.token_compiler import compile_generated_tokens
from oryxenai.agents.code_generator.core.typescript_ast_audit import audit_typescript_source
from oryxenai.agents.code_generator.core.work_graph_compiler import compile_site_plan
from oryxenai.agents.shared.providers.schema_compatibility import schema_compatibility_issues


def _blueprint() -> ExperienceBlueprintV4:
    return ExperienceBlueprintV4(
        selected_concept_id="concept:proof",
        narrative_arc="positioning to evidence",
        tokens=DesignTokenSystemV4(
            colors=[
                {"name": "ink", "value": "#121212"},
                {"name": "paper", "value": "#f6f2ea"},
            ],
            spacing=[{"name": "section", "value": 4, "unit": "rem"}],
            typography_roles=[
                {
                    "role": "body",
                    "approved_font_slot": "font:body",
                    "family": "Local Sans",
                    "weights": [400, 700],
                    "local_files": ["resources/fonts/local/400-normal.woff2"],
                    "body_min_rem": 1,
                    "body_max_rem": 1.2,
                    "heading_ratio": 1.25,
                    "body_line_height": 1.5,
                }
            ],
            type_steps=[
                {
                    "name": "body",
                    "role": "body",
                    "minimum_rem": 1,
                    "maximum_rem": 1.2,
                    "line_height": 1.5,
                    "tracking_em": 0,
                },
                {
                    "name": "display",
                    "role": "body",
                    "minimum_rem": 2,
                    "maximum_rem": 3,
                    "line_height": 1.05,
                    "tracking_em": -0.02,
                },
            ],
            containers=[
                {
                    "name": "content",
                    "maximum": {
                        "name": "content-max",
                        "value": 1120,
                        "unit": "px",
                    },
                    "inline_padding": {"name": "content-pad", "value": 1, "unit": "rem"},
                }
            ],
            container_max_px=1120,
        ),
        route_shells=[
            {
                "route_id": "home",
                "storage_key": "home",
                "h1_owner": "hero",
                "section_order": ["hero"],
            }
        ],
        section_regions=[
            {
                "region_id": "region:hero",
                "route_id": "home",
                "section_id": "hero",
                "owner_id": "owner:hero",
                "section_selector": '[data-content-id="hero"]',
                "region_selector": '[data-region-id="region:hero"]',
                "order_mobile": 0,
                "order_tablet": 0,
                "order_desktop": 0,
                "columns_mobile": 1,
                "columns_tablet": 2,
                "columns_desktop": 2,
                "max_measure_ch": 68,
                "gap": {"name": "hero-gap", "value": 2, "unit": "rem"},
            }
        ],
        distinctive_moves=[
            {
                "move_id": "move:hero-rail",
                "route_id": "home",
                "section_id": "hero",
                "region_id": "region:hero",
                "implementation_kind": "asymmetric_width",
                "thesis": "The proof rail offsets the positioning headline.",
                "runtime_marker": 'data-distinctive-move-id="move:hero-rail"',
                "source_selector": '[data-distinctive-move-id="move:hero-rail"]',
                "target_selector": '[data-content-id="hero"]',
                "relationship": "width_ratio",
                "minimum_ratio": 0.25,
                "maximum_ratio": 1,
                "viewports": ["mobile", "tablet", "desktop"],
                "required_css_properties": ["grid-template-columns"],
            }
        ],
    )


def test_v4_contracts_are_closed_and_provider_compatible() -> None:
    assert schema_compatibility_issues(ExperienceBlueprintV4) == []


def test_v4_route_audit_reads_anchors_from_rendered_section_modules() -> None:
    plan = SitePlan(
        plan_id="audit",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                storage_key="home",
                section_ids=["hero"],
                section_order=["hero"],
                responsive_outcome="stacked on mobile",
                reduced_motion_outcome="static",
                interaction_outcome="keyboard accessible",
            )
        ],
        experience_blueprint=_blueprint(),
    )
    files = {
        "src/components/generated/SharedSystems.tsx": """export function RouteShell() { return <main />; }
export function SectionAnchor() { return publicSectionUrl('/'); }
export function useDisclosure() { return { close: () => {} }; }
export function Disclosure() { return <button aria-expanded={false}>x</button>; }
export function LocalImage() { return null; }
export const keyboardBehavior = \"Escape closes and returns focus\";
""",
        "src/routes/home/index.tsx": """import { RouteShell } from \"@/components/generated/SharedSystems\";
import Hero from \"@/routes/home/sections/hero\";
export default function HomeRoute() {
  return <RouteShell routeId=\"home\" routePath=\"/\"><Hero /></RouteShell>;
}
""",
        "src/routes/home/sections/hero.tsx": """export default function Hero() {
  return <section id=\"hero\" data-content-id=\"hero\" data-distinctive-move-id=\"move:hero-rail\"><h1>Proof</h1></section>;
}
""",
        "src/routes/home/route.css": '[data-distinctive-move-id=\"move:hero-rail\"] { grid-template-columns: 1fr 1fr; }',
    }

    diagnostics = audit_typescript_source(Path("."), files=files, plan=plan)
    assert not diagnostics, [
        (item.code, item.symbol, item.file, item.expected, item.observed)
        for item in diagnostics
    ]


def test_v4_typography_roles_require_explicit_role_values() -> None:
    token_data = _blueprint().tokens.model_dump(mode="python")
    token_data["typography_roles"][0].pop("role")

    with pytest.raises(ValidationError, match="role"):
        DesignTokenSystemV4.model_validate(token_data)


def test_v4_blueprint_must_echo_host_identity_manifest() -> None:
    blueprint = _blueprint()
    context = {
        "blueprint_identity_manifest": [
            {
                "route_id": "home",
                "section_id": "hero",
                "region_id": "region:hero",
                "owner_id": "owner:hero",
            }
        ]
    }

    validate_v4_blueprint_identities(blueprint, context)
    drifted = blueprint.model_copy(
        update={
            "section_regions": [
                blueprint.section_regions[0].model_copy(update={"owner_id": "owner:other"})
            ]
        }
    )
    with pytest.raises(SitePlanValidationError, match="echo the host identity"):
        validate_v4_blueprint_identities(drifted, context)
    assert schema_compatibility_issues(SourceGenerationEnvelopeV2) == []
    intent = ResourceSearchIntentV2(
        slot_id="image:hero",
        subject_terms=["editorial", "workspace"],
        contextual_modifiers=["quiet", "architectural"],
        alt_policy="decorative",
        query_variants=["editorial workspace", "quiet architectural workspace"],
    )
    assert intent.contextual_modifiers == ["quiet", "architectural"]
    assert compile_resource_queries(intent, provider="pixabay") == [
        "editorial workspace",
        "quiet architectural workspace",
    ]


def test_v4_compilation_preserves_unique_semantic_section_owners() -> None:
    blueprint = _blueprint()
    second_region = blueprint.section_regions[0].model_copy(
        update={
            "region_id": "region:proof",
            "section_id": "proof",
            "owner_id": "owner:proof",
            "section_selector": '[data-content-id="proof"]',
            "region_selector": '[data-region-id="region:proof"]',
            "order_mobile": 1,
            "order_tablet": 1,
            "order_desktop": 1,
        }
    )
    blueprint = blueprint.model_copy(
        update={
            "route_shells": [
                blueprint.route_shells[0].model_copy(update={"section_order": ["hero", "proof"]})
            ],
            "section_regions": [*blueprint.section_regions, second_region],
        }
    )
    plan = SitePlan(
        plan_id="v4-compiler-regression",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero", "proof"],
                responsive_outcome="Readable at every viewport",
                reduced_motion_outcome="Content remains visible without motion",
                interaction_outcome="Keyboard accessible",
            )
        ],
        experience_blueprint=blueprint,
    )

    compiled = compile_site_plan(
        plan,
        {
            "site/contract.json": {
                "routes": [
                    {
                        "route_id": "home",
                        "storage_key": "home",
                        "section_sequence": ["hero", "proof"],
                    }
                ]
            },
            "execution/contract.json": {"slots": []},
        },
        max_sections_per_unit=2,
    )

    assert compiled.experience_blueprint is not None
    assert [item.owner_id for item in compiled.experience_blueprint.section_regions] == [
        "owner:hero",
        "owner:proof",
    ]
    assert SitePlan.model_validate(compiled.model_dump(mode="json"))


def test_v4_composer_contract_delegates_content_to_completed_batches() -> None:
    plan = SitePlan(
        plan_id="composer-contract",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero"],
                responsive_outcome="Readable at every viewport",
                reduced_motion_outcome="Content remains visible without motion",
                interaction_outcome="Keyboard accessible",
            )
        ],
        experience_blueprint=_blueprint(),
    )
    composer = WorkUnit(
        unit_id="route-home-compose",
        kind="route_compose",
        route_id="home",
        route_ids=["home"],
        owns_paths=["src/routes/home/index.tsx", "src/routes/home/route.css"],
        depends_on=["foundation", "route-home-batch-1"],
    )
    contract = build_generation_contract(
        unit=composer,
        plan=plan,
        projections={
            "site/contract.json": {
                "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
                "public_content": [
                    {
                        "route_id": "home",
                        "sections": [
                            {"section_id": "hero", "content": {"headline": "Approved headline"}}
                        ],
                    }
                ],
                "facts": [],
            },
            "design/visual-direction.json": {"global": {"must_preserve": []}},
            "execution/contract.json": {"slots": []},
        },
        operation="route_compose",
        owned_paths=composer.owns_paths,
    )

    route = contract["routes"][0]
    assert route["content_keys_required"] is False
    assert route["section_ids"] == ["hero"]
    assert route["sections"][0]["content_ids"] == []
    assert "import and render the completed section batches" in render_contract_instructions(
        contract
    )


def test_v4_source_wire_envelope_adapts_without_losing_coverage() -> None:
    receipt = GenerationContextReceipt(
        receipt_id="context-test",
        operation_id="route_batch",
        role_profile="offline-test",
        output_schema_hash="schema",
        context_hash="context-hash",
    )
    envelope = SourceGenerationEnvelopeV2(
        result_tag="changes",
        files=[
            SourceFileChange(
                path="src/routes/home/index.tsx",
                operation="replace",
                complete_utf8_content="export {};\n",
            )
        ],
        exported_signatures=[],
        content_ids=["content:home:hero:title"],
        criterion_ids=["criterion:home:proof"],
        resource_slot_ids=["image:hero"],
        interaction_ids=["interaction:home:contact"],
        resource_requests=[],
        dependency_requests=[],
        failure_details=[],
    )

    result = adapt_v4_generation_result(
        envelope,
        operation_id="route_batch:home",
        context_receipt=receipt,
    )

    assert result.mode == "changes"
    assert result.based_on_context_receipt == receipt.context_hash
    assert result.changes is not None
    assert result.changes.content_coverage == ["content:home:hero:title"]
    assert result.changes.criterion_coverage == ["criterion:home:proof"]
    assert result.changes.resource_usage == ["image:hero"]
    assert result.changes.interaction_coverage == ["interaction:home:contact"]


def test_acquired_image_assets_do_not_require_pack_slots(tmp_path) -> None:
    execution = {
        "slots": [
            {
                "resource_slot_id": "image:hero",
                "route_id": "home",
                "section_ids": ["hero"],
                "category": "image",
            }
        ]
    }

    assets = _materialize_image_assets(
        type("Workspace", (), {"repo_dir": tmp_path})(),
        execution=execution,
        copied_resources=[],
        acquired_resources=[
            {
                "request_id": "request-image:hero",
                "category": "image",
                "local_path": "public/resources/acquired/hero.webp",
                "media_type": "image/webp",
                "sha256": "hero-hash",
                "inspection": {
                    "pixel_width": 1200,
                    "pixel_height": 800,
                    "rendition_format": "webp",
                },
                "placement": {"route_id": "home", "section_id": "hero"},
            }
        ],
        plan=type("Plan", (), {"experience_blueprint": None})(),
        settings=None,
    )

    assert assets[0]["resource_id"] == "image:hero"
    assert assets[0]["sources"][0]["width"] == 1200


def test_v4_rejects_non_distinct_creative_concepts() -> None:
    concept = {
        "concept_id": "one",
        "thesis": "proof",
        "hierarchy": "headline first",
        "composition": "split",
        "typography": "display",
        "color_logic": "ink",
        "motion_vocabulary": "quiet",
        "resource_use": "local evidence",
        "distinguishing_moves": ["rail"],
    }
    with pytest.raises(ValidationError):
        CreativeDirectionSetV3(
            concepts=[concept, {**concept, "concept_id": "two"}],
            recommended_concept_id="one",
            recommendation_basis="same",
        )


def test_v4_token_compiler_emits_aliases_and_font_metadata() -> None:
    blueprint = _blueprint()
    css = compile_generated_tokens(
        blueprint,
        [
            ExecutionBindingV2(
                resource_slot_id="font:body",
                route_id="",
                category="font",
                purpose="approved font",
                resolution_type="local_materialized",
                local_paths=["resources/fonts/local/400-normal.woff2"],
                font_family="Local Sans",
                font_weights=["400"],
            )
        ],
    )
    assert "--font-body" in css
    assert "--font-display" in css
    assert "font-weight: 400" in css
    assert 'format("woff2")' in css
    assert "var(--token," not in css
    assert css.count("--type-body-min:") == 1
    assert css.count("--type-display-min:") == 1


def test_v4_token_compiler_assigns_distinct_weights_per_font_file() -> None:
    """Regression test for the 2026-08-28 bug: every file in a multi-weight
    binding collapsed to the same font-weight, because the weight-extraction
    regex required a "-"/"_" left boundary that a "/" path separator never
    satisfies (materialized files are named "{weight}-{style}.ext" inside a
    resource directory, so the weight always follows a "/")."""
    blueprint = _blueprint()
    css = compile_generated_tokens(
        blueprint,
        [
            ExecutionBindingV2(
                resource_slot_id="font:body",
                route_id="",
                category="font",
                purpose="approved font",
                resolution_type="local_materialized",
                local_paths=[
                    "resources/fonts/resource-fontsource-abc123/400-normal.woff2",
                    "resources/fonts/resource-fontsource-abc123/500-normal.woff2",
                    "resources/fonts/resource-fontsource-abc123/600-normal.woff2",
                    "resources/fonts/resource-fontsource-abc123/700-normal.woff2",
                ],
                font_family="Local Sans",
                font_weights=["400", "500", "600", "700"],
            )
        ],
    )
    assert css.count("font-weight: 400;") == 1
    assert css.count("font-weight: 500;") == 1
    assert css.count("font-weight: 600;") == 1
    assert css.count("font-weight: 700;") == 1


def test_v4_token_compiler_does_not_double_prefix_group_named_tokens() -> None:
    """Regression test: a token already named with its group prefix (e.g. a
    spacing step literally named "space-5") must not be prefixed a second
    time into an unpredictable "--space-space-5" that generated source could
    never correctly reference."""
    from oryxenai.agents.code_generator.core.development_schemas import LengthTokenV4

    blueprint = _blueprint().model_copy(
        update={
            "tokens": _blueprint().tokens.model_copy(
                update={
                    "spacing": [
                        LengthTokenV4(name="space-5", value=1.5, unit="rem"),
                        LengthTokenV4(name="space-7", value=2, unit="rem"),
                    ]
                }
            )
        }
    )
    css = compile_generated_tokens(blueprint)
    assert "--space-5:" in css
    assert "--space-space-5" not in css
    assert "--space-7:" in css
    assert "--space-space-7" not in css


def test_v4_realization_is_hash_bound() -> None:
    realization = compile_design_realization(_blueprint(), route_id="home", section_order=["hero"])
    assert realization.signature_move_ids == ["move:hero-rail"]
    assert realization.contract_hash
    assert query_receipt(
        ResourceSearchIntentV2(
            slot_id="image:hero",
            subject_terms=["editorial", "workspace"],
            alt_policy="decorative",
        ),
        provider="pexels",
        sent_queries=["editorial workspace"],
    )["sent_queries"] == ["editorial workspace"]


def test_quality_receipt_rejects_stale_hashes() -> None:
    from oryxenai.agents.code_generator.core.development_schemas import QualityReviewReceiptV1

    receipt = QualityReviewReceiptV1(
        source_hash="source",
        plan_hash="plan",
        context_hash="context",
        hierarchy_score=4,
        composition_score=4,
        typography_score=4,
        resource_fit_score=4,
        motion_score=4,
        reviewer_receipt="reviewer",
        accepted=True,
    )
    with pytest.raises(QualityReviewError, match="different source hash"):
        validate_quality_review_receipt(
            receipt,
            source_hash="changed",
            plan_hash="plan",
            context_hash="context",
        )


def test_v4_quality_scores_require_exact_concrete_evidence() -> None:
    dimensions = ["hierarchy", "composition", "typography", "resource_fit", "motion"]
    evidence = [
        {
            "dimension": dimension,
            "score": 4,
            "owner_work_unit_id": f"work:{dimension}",
            "file": f"src/routes/home/{dimension}.tsx",
            "line": 12,
            "marker": f"data-quality-{dimension}",
            "evidence": f"Observed {dimension} evidence in the owned source.",
        }
        for dimension in dimensions
    ]
    draft = QualityReviewDraftV1(
        hierarchy_score=4,
        composition_score=4,
        typography_score=4,
        resource_fit_score=4,
        motion_score=4,
        score_evidence=evidence,
        review_summary="All dimensions have source-bound evidence.",
    )
    receipt = stamp_quality_review_receipt(
        draft,
        source_manifest_hash="source",
        plan_hash="plan",
        realization_hash="realization",
        review_context_hash="context",
        response_id="response",
        quality_gate_version="quality-v4",
    )
    assert [item.dimension for item in receipt.score_evidence] == dimensions
    assert receipt.receipt_hash

    with pytest.raises(ValidationError, match="score_evidence"):
        QualityReviewDraftV1(
            hierarchy_score=4,
            composition_score=4,
            typography_score=4,
            resource_fit_score=4,
            motion_score=4,
            score_evidence=evidence[:-1],
            review_summary="Missing one dimension.",
        )

    mismatched = [*evidence]
    mismatched[0] = {**mismatched[0], "score": 3}
    with pytest.raises(ValidationError, match="exact score"):
        QualityReviewDraftV1(
            hierarchy_score=4,
            composition_score=4,
            typography_score=4,
            resource_fit_score=4,
            motion_score=4,
            score_evidence=mismatched,
            review_summary="Mismatched dimension score.",
        )
