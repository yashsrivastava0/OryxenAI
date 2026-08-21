from __future__ import annotations

import pytest
from pydantic import ValidationError

from oryxenai.agents.code_generator.core.design_realization import compile_design_realization
from oryxenai.agents.code_generator.core.development_schemas import (
    CreativeDirectionSetV3,
    DesignTokenSystemV4,
    ExecutionBindingV2,
    ExperienceBlueprintV4,
    ResourceSearchIntentV2,
    SourceGenerationEnvelopeV2,
)
from oryxenai.agents.code_generator.core.quality_review import (
    QualityReviewError,
    validate_quality_review_receipt,
)
from oryxenai.agents.code_generator.core.resource_query import (
    compile_resource_queries,
    query_receipt,
)
from oryxenai.agents.code_generator.core.token_compiler import compile_generated_tokens
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
            typography={
                "approved_font_slot": "font:body",
                "family": "Local Sans",
                "weights": [400, 700],
                "body_min_rem": 1,
                "body_max_rem": 1.2,
                "heading_ratio": 1.25,
                "body_line_height": 1.5,
            },
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
                "runtime_marker": "data-distinctive-move-id=move:hero-rail",
                "observable_relationship": "headline measure is narrower than proof rail",
                "css_evidence": "grid-template-columns",
            }
        ],
    )


def test_v4_contracts_are_closed_and_provider_compatible() -> None:
    assert schema_compatibility_issues(ExperienceBlueprintV4) == []
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
