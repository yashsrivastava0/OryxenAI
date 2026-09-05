from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from oryxenai.agents.code_generator.core import final_source_validation
from oryxenai.agents.code_generator.core.blueprint_compiler import (
    _canonicalize_resource_placement_slots,
    canonicalize_generation_plan,
    canonicalize_v4_distinctive_move_selectors,
    canonicalize_v4_h1_owners,
    canonicalize_v4_resource_placement_selectors,
)
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
    ExportedSignature,
    GenerationChanges,
    GenerationContextReceipt,
    InteractionContract,
    NamedColorTokenV4,
    QualityReviewDraftV1,
    ResourcePlacementV4,
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
from oryxenai.agents.code_generator.core.generation_orchestrator import (
    _validate_v4_generation_coverage,
)
from oryxenai.agents.code_generator.core.quality_review import (
    QualityReviewError,
    stamp_quality_review_receipt,
    validate_quality_review_draft_evidence,
    validate_quality_review_receipt,
)
from oryxenai.agents.code_generator.core.resource_query import (
    compile_resource_queries,
    query_receipt,
)
from oryxenai.agents.code_generator.core.source_generation_adapter import (
    adapt_v4_generation_result,
)
from oryxenai.agents.code_generator.core.source_manifest import (
    _contract_meta,
    _materialize_image_assets,
    _public_runtime_data,
)
from oryxenai.agents.code_generator.core.source_validation import SourceValidationError
from oryxenai.agents.code_generator.core.token_compiler import (
    TokenCompilationError,
    compile_generated_tokens,
)
from oryxenai.agents.code_generator.core.typescript_ast_audit import (
    _selector_declarations,
    audit_typescript_source,
)
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


def test_v4_distinctive_move_rejects_weak_neutral_ratio_range() -> None:
    payload = _blueprint().model_dump(mode="python")
    payload["distinctive_moves"][0].update(minimum_ratio=0.95, maximum_ratio=1.05)

    with pytest.raises(ValidationError, match="deviate from neutral"):
        ExperienceBlueprintV4.model_validate(payload)


def test_v4_distinctive_move_rejects_narrow_ratio_range() -> None:
    payload = _blueprint().model_dump(mode="python")
    payload["distinctive_moves"][0].update(minimum_ratio=0.4, maximum_ratio=0.45)

    with pytest.raises(ValidationError, match="spread of at least"):
        ExperienceBlueprintV4.model_validate(payload)


def test_v4_sticky_move_allows_discrete_neutral_ratio() -> None:
    payload = _blueprint().model_dump(mode="python")
    payload["distinctive_moves"][0].update(
        relationship="sticky_within_section",
        minimum_ratio=1,
        maximum_ratio=1,
        required_css_properties=["position"],
    )

    parsed = ExperienceBlueprintV4.model_validate(payload)

    assert parsed.distinctive_moves[0].relationship == "sticky_within_section"


def test_v4_materialized_resource_ids_canonicalize_to_unique_execution_slots() -> None:
    payload = _blueprint().model_dump(mode="python")
    payload["resource_placements"] = [
        {
            "resource_slot_id": "resource-hero-photo",
            "route_id": "home",
            "section_id": "hero",
            "element_marker": 'data-resource-slot="slot-hero-photo"',
            "element_selector": '[data-resource-slot="slot-hero-photo"]',
            "alt_policy": "decorative",
            "fit": "cover",
            "focal_position": "center",
            "loading": "eager",
            "responsive_behavior": "Stack below approved hero copy.",
            "sizes": "(max-width: 48rem) 100vw, 40vw",
            "aspect_ratio_min": 1.2,
            "aspect_ratio_max": 1.8,
            "minimum_visible_ratio": 0.4,
        }
    ]
    blueprint = ExperienceBlueprintV4.model_validate(payload)

    canonical = _canonicalize_resource_placement_slots(
        blueprint,
        {
            "execution/contract.json": {
                "slots": [
                    {
                        "resource_slot_id": "slot-hero-photo",
                        "resolution": {"resource_id": "resource-hero-photo"},
                    }
                ]
            }
        },
    )

    assert canonical.resource_placements[0].resource_slot_id == "slot-hero-photo"


def test_v4_resource_selector_canonicalizes_to_generated_wrapper_marker() -> None:
    payload = _blueprint().model_dump(mode="python")
    payload["resource_placements"] = [
        {
            "resource_slot_id": "slot-hero-photo",
            "route_id": "home",
            "section_id": "hero",
            "element_marker": 'data-resource="hero-image"',
            "element_selector": "#hero-media img",
            "alt_policy": "decorative",
            "fit": "cover",
            "focal_position": "center",
            "loading": "eager",
            "responsive_behavior": "Stack below approved hero copy.",
            "sizes": "(max-width: 48rem) 100vw, 40vw",
            "aspect_ratio_min": 1.2,
            "aspect_ratio_max": 1.8,
            "minimum_visible_ratio": 0.4,
        }
    ]
    blueprint = ExperienceBlueprintV4.model_validate(payload)

    canonical = canonicalize_v4_resource_placement_selectors(blueprint)

    assert canonical.resource_placements[0].element_selector == '[data-resource="hero-image"]'


def test_v4_resource_sizes_require_concrete_browser_css_lengths() -> None:
    base = {
        "resource_slot_id": "slot-hero-photo",
        "route_id": "home",
        "section_id": "hero",
        "element_marker": 'data-resource="hero-image"',
        "element_selector": '[data-resource="hero-image"]',
        "alt_policy": "decorative",
        "fit": "cover",
        "focal_position": "center",
        "loading": "eager",
        "responsive_behavior": "Stack below approved hero copy.",
        "aspect_ratio_min": 1.2,
        "aspect_ratio_max": 1.8,
        "minimum_visible_ratio": 0.4,
    }

    valid = ResourcePlacementV4(
        **base,
        sizes=" (max-width: 40rem) 100vw, calc(72vw - 2rem) ",
    )
    assert valid.sizes == "(max-width: 40rem) 100vw, calc(72vw - 2rem)"

    # A spelled-out number is deterministically normalized rather than
    # rejected outright: the planner's own corrective-feedback retry already
    # failed on this exact mistake twice in a live run (2026-09-05), so a
    # host-side fix -- not more prompting -- is the right escalation for a
    # purely mechanical, unambiguous text transform.
    normalized = ResourcePlacementV4(
        **base,
        sizes="(max-width: sixtyrem) 100vw, 58vw",
    )
    assert normalized.sizes == "(max-width: 60rem) 100vw, 58vw"

    # A genuinely unparseable word still hits the same reject path -- the
    # normalizer is a safety net for the common case, not a guarantee.
    with pytest.raises(ValidationError, match="numeric CSS lengths"):
        ResourcePlacementV4(
            **base,
            sizes="(max-width: bloopvw) 100vw, 58vw",
        )

    with pytest.raises(ValidationError, match="concrete CSS lengths"):
        ResourcePlacementV4(
            **base,
            sizes="(max-width: 40furlong) 100vw, 58vw",
        )


def test_v4_page_heading_owner_canonicalizes_to_first_approved_section() -> None:
    blueprint = _blueprint()
    blueprint = blueprint.model_copy(
        update={
            "route_shells": [
                blueprint.route_shells[0].model_copy(
                    update={
                        "h1_owner": "trusted_shell",
                        "section_order": ["home:hero", "home:work"],
                    }
                )
            ]
        }
    )

    canonical = canonicalize_v4_h1_owners(blueprint)

    assert canonical.route_shells[0].h1_owner == "home:hero"
    assert blueprint.route_shells[0].h1_owner == "trusted_shell"

    plan = SitePlan(plan_id="canonical-stage-plan", routes=[], experience_blueprint=blueprint)
    canonical_plan = canonicalize_generation_plan(plan)

    assert canonical_plan.experience_blueprint.route_shells[0].h1_owner == "home:hero"
    assert plan.experience_blueprint.route_shells[0].h1_owner == "trusted_shell"


def test_v4_distinctive_move_source_canonicalizes_to_exact_layout_region() -> None:
    blueprint = _blueprint()
    move = blueprint.distinctive_moves[0].model_copy(
        update={"source_selector": blueprint.section_regions[0].section_selector}
    )
    blueprint = blueprint.model_copy(update={"distinctive_moves": [move]})

    canonical = canonicalize_v4_distinctive_move_selectors(blueprint)

    assert canonical.distinctive_moves[0].source_selector == ('[data-region-id="region:hero"]')
    assert blueprint.distinctive_moves[0].source_selector == '[data-content-id="hero"]'

    plan = SitePlan(plan_id="canonical-move-plan", routes=[], experience_blueprint=blueprint)
    canonical_plan = canonicalize_generation_plan(plan)
    assert canonical_plan.experience_blueprint.distinctive_moves[0].source_selector == (
        '[data-region-id="region:hero"]'
    )


def test_v4_route_audit_reads_anchors_from_rendered_section_modules() -> None:
    blueprint = _blueprint()
    blueprint = blueprint.model_copy(
        update={
            "route_shells": [
                blueprint.route_shells[0].model_copy(
                    update={"h1_owner": "home:hero", "section_order": ["home:hero"]}
                )
            ],
            "section_regions": [
                blueprint.section_regions[0].model_copy(
                    update={"section_id": "home:hero", "section_selector": "#hero"}
                )
            ],
            "distinctive_moves": [
                blueprint.distinctive_moves[0].model_copy(
                    update={
                        "section_id": "home:hero",
                        "runtime_marker": 'data-distinctive-move="hero-rail"',
                        "source_selector": '[data-distinctive-move="hero-rail"]',
                    }
                )
            ],
        }
    )
    plan = SitePlan(
        plan_id="audit",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                storage_key="home",
                section_ids=["home:hero"],
                section_order=["home:hero"],
                responsive_outcome="stacked on mobile",
                reduced_motion_outcome="static",
                interaction_outcome="keyboard accessible",
            )
        ],
        experience_blueprint=blueprint,
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
  return <section id=\"hero\" data-content-id=\"home:hero\" data-distinctive-move=\"hero-rail\"><h1>Proof</h1></section>;
}
""",
        "src/routes/home/route.css": '[data-distinctive-move="hero-rail"] { grid-template-columns: 1fr 1fr; }',
    }

    diagnostics = audit_typescript_source(Path("."), files=files, plan=plan)
    assert not diagnostics, [
        (item.code, item.symbol, item.file, item.expected, item.observed) for item in diagnostics
    ]


def test_v4_ast_audit_accepts_marker_qualified_move_selector() -> None:
    declarations = _selector_declarations(
        '[data-region="region:home:hero"][data-distinctive-move="hero-rail"] '
        "{ display: grid; grid-template-columns: 1fr 1fr; column-gap: 1rem; }",
        '[data-region="region:home:hero"]',
        runtime_marker='data-distinctive-move="hero-rail"',
    )

    assert declarations == {"display", "grid-template-columns", "column-gap"}


def test_v4_contract_meta_preserves_section_identity_selector_split() -> None:
    blueprint = _blueprint().model_copy(
        update={
            "section_regions": [
                _blueprint()
                .section_regions[0]
                .model_copy(update={"section_id": "home:hero", "section_selector": "#hero"})
            ]
        }
    )
    plan = SitePlan(plan_id="meta", routes=[], experience_blueprint=blueprint)

    assert _contract_meta(plan) == {
        "pipeline_contract_version": "code-generator-v4",
        "section_selectors": [
            {
                "route_id": "home",
                "section_id": "home:hero",
                "section_selector": "#hero",
            }
        ],
    }


def test_v4_typography_roles_require_explicit_role_values() -> None:
    token_data = _blueprint().tokens.model_dump(mode="python")
    token_data["typography_roles"][0].pop("role")

    with pytest.raises(ValidationError, match="role"):
        DesignTokenSystemV4.model_validate(token_data)


def test_v4_shadcn_theme_bindings_use_fixed_slots_and_approved_colors() -> None:
    token_data = _blueprint().tokens.model_dump(mode="python")
    token_data["shadcn_theme_bindings"] = {
        "background": "paper",
        "foreground": "ink",
        "primary": "ink",
        "primary-foreground": "paper",
    }

    tokens = DesignTokenSystemV4.model_validate(token_data)

    assert tokens.shadcn_theme_bindings == token_data["shadcn_theme_bindings"]
    with pytest.raises(ValidationError):
        DesignTokenSystemV4.model_validate(
            {**token_data, "shadcn_theme_bindings": {"brand-slot": "ink"}}
        )
    with pytest.raises(ValidationError, match="approved color token"):
        DesignTokenSystemV4.model_validate(
            {**token_data, "shadcn_theme_bindings": {"primary": "missing"}}
        )


def test_v4_shadcn_theme_bindings_reject_slot_names_colliding_with_a_color_token() -> None:
    """Regression test for the 2026-09-05 live-discovered bug: a raw color
    token and a shadcn binding slot with the same literal name (e.g. both
    named "accent") both compile to the identical --color-accent CSS custom
    property; the alias silently overwrote the raw color with no error,
    only surfacing as a whole-site quality-review finding after a full,
    costly generation pass."""
    token_data = _blueprint().tokens.model_dump(mode="python")
    token_data["colors"] = [*token_data["colors"], {"name": "accent", "value": "#b84a32"}]

    with pytest.raises(ValidationError, match="must not collide"):
        DesignTokenSystemV4.model_validate(
            {**token_data, "shadcn_theme_bindings": {"accent": "ink"}}
        )


def test_v4_token_names_are_lowercased_instead_of_rejected() -> None:
    """Regression test: token-name validators used to reject any mixed-case
    identifier outright (e.g. planner.md's own "Cobalt" example), forcing a
    whole extra planner round-trip for a purely cosmetic mistake. Case is
    not semantic for an internal token label, so it's normalized instead."""
    assert NamedColorTokenV4(name="Cobalt", value="#2457C5").name == "cobalt"
    assert NamedColorTokenV4(name="Deep_Blue", value="#123456").name == "deep-blue"
    with pytest.raises(ValidationError, match="lowercase semantic identifiers"):
        NamedColorTokenV4(name="Cobalt Blue", value="#2457C5")


def _shadow(*, offset_x: float, offset_y: float, blur: float, spread: float) -> dict:
    return {
        "name": "elevated",
        "offset_x": {"name": "shadow-x", "value": offset_x, "unit": "px"},
        "offset_y": {"name": "shadow-y", "value": offset_y, "unit": "px"},
        "blur": {"name": "shadow-blur", "value": blur, "unit": "px"},
        "spread": {"name": "shadow-spread", "value": spread, "unit": "px"},
        "color_token": "ink",
    }


def test_v4_shadow_tokens_allow_negative_offset_and_spread_but_not_blur() -> None:
    """CSS box-shadow offset-x/offset-y (direction) and spread-radius (shrink
    the shadow shape) are valid when negative; only blur-radius is not."""
    token_data = _blueprint().tokens.model_dump(mode="python")

    tokens = DesignTokenSystemV4.model_validate(
        {**token_data, "shadows": [_shadow(offset_x=-2, offset_y=-4, blur=8, spread=-1)]}
    )
    assert tokens.shadows[0].offset_x.value == -2
    assert tokens.shadows[0].offset_y.value == -4
    assert tokens.shadows[0].spread.value == -1

    with pytest.raises(ValidationError, match="non-negative"):
        DesignTokenSystemV4.model_validate(
            {**token_data, "shadows": [_shadow(offset_x=0, offset_y=2, blur=-1, spread=0)]}
        )


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


def test_v4_blueprint_rejects_media_only_distinctive_move_properties() -> None:
    blueprint = _blueprint()
    invalid = blueprint.model_copy(
        update={
            "distinctive_moves": [
                blueprint.distinctive_moves[0].model_copy(
                    update={"required_css_properties": ["display", "object-fit"]}
                )
            ]
        }
    )

    with pytest.raises(SitePlanValidationError, match="media-only properties"):
        validate_v4_blueprint_identities(invalid, {})
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
            "design/visual-direction.json": {
                "global": {"must_preserve": ["Aarav Mehta", "Senior Architect"]}
            },
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


def test_v4_generation_contract_exposes_exact_unit_coverage_arrays() -> None:
    plan = SitePlan(
        plan_id="batch-coverage-contract",
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
    batch = WorkUnit(
        unit_id="route-home-batch-1",
        kind="route_batch",
        route_id="home",
        route_ids=["home"],
        section_ids=["hero"],
        owns_paths=["src/routes/home/sections/hero.tsx"],
        criterion_ids=[],
        resource_slot_ids=["slot-hero"],
        interaction_ids=[],
    )
    contract = build_generation_contract(
        unit=batch,
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
        operation="route_batch",
        owned_paths=batch.owns_paths,
    )

    expected_content = contract["routes"][0]["sections"][0]["content_ids"]
    assert contract["contract_version"] == "code-generator-generation-contract-v4"
    assert contract["required_coverage"] == {
        "content_ids": expected_content,
        "criterion_ids": [],
        "resource_slot_ids": ["slot-hero"],
        "interaction_ids": [],
    }
    instructions = render_contract_instructions(contract)
    assert f"content_ids = {expected_content!r}".replace("'", '"') in instructions
    assert "criterion_ids = []" in instructions
    assert "canonical page heading section hero" in instructions
    assert "exactly one visible <h1>" in instructions


def test_v4_generation_contract_exposes_browser_images_and_motion() -> None:
    base = _blueprint()
    blueprint = ExperienceBlueprintV4.model_validate(
        {
            **base.model_dump(mode="json"),
            "resource_placements": [
                {
                    "resource_slot_id": "slot-hero",
                    "route_id": "home",
                    "section_id": "hero",
                    "element_marker": 'data-resource="hero"',
                    "element_selector": '[data-resource="hero"]',
                    "alt_policy": "decorative",
                    "fit": "cover",
                    "focal_position": "center center",
                    "loading": "eager",
                    "responsive_behavior": "Stack below copy on narrow screens.",
                    "sizes": "100vw",
                    "aspect_ratio_min": 1.2,
                    "aspect_ratio_max": 1.8,
                    "minimum_visible_ratio": 0.3,
                }
            ],
            "motion_beats": [
                {
                    "motion_id": "motion:hero",
                    "route_id": "home",
                    "section_id": "hero",
                    "target_marker": 'data-motion-target="hero-copy"',
                    "target_selector": "#hero .hero-copy",
                    "trigger_selector": "#hero",
                    "trigger": "viewport",
                    "changed_properties": [
                        {
                            "property_name": "opacity",
                            "before_value": "0",
                            "after_value": "1",
                        }
                    ],
                    "duration_min_ms": 300,
                    "duration_max_ms": 420,
                    "easing": "ease-out",
                    "purposeful_outcome": "Establish the opening hierarchy.",
                    "performance_budget_ms": 16,
                    "reduced_motion_replacement": "Render the complete final state.",
                }
            ],
        }
    )
    plan = SitePlan(
        plan_id="materialized-contract",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero"],
                responsive_outcome="Readable",
                reduced_motion_outcome="Static",
                interaction_outcome="Keyboard accessible",
            )
        ],
        experience_blueprint=blueprint,
    )
    unit = WorkUnit(
        unit_id="route-home-batch-1",
        kind="route_batch",
        route_id="home",
        route_ids=["home"],
        section_ids=["hero"],
        owns_paths=["src/routes/home/sections/hero.tsx"],
        resource_slot_ids=["slot-hero"],
    )
    contract = build_generation_contract(
        unit=unit,
        plan=plan,
        projections={
            "site/contract.json": {
                "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
                "public_content": [
                    {"route_id": "home", "sections": [{"section_id": "hero", "content": {}}]}
                ],
                "facts": [],
            },
            "design/visual-direction.json": {"global": {"must_preserve": []}},
            "execution/contract.json": {"slots": []},
            "generated/resource-assets.json": {
                "image_assets": [
                    {
                        "resource_id": "slot-hero",
                        "route_id": "home",
                        "section_ids": ["hero"],
                        "sizes": "100vw",
                        "loading": "eager",
                        "fit": "cover",
                        "focal_position": "center center",
                        "alt_policy": "decorative",
                        "sources": [
                            {
                                "path": "resources/renditions/hero-480w.webp",
                                "width": 480,
                                "height": 320,
                                "format": "webp",
                            }
                        ],
                    }
                ]
            },
        },
        operation="route_batch",
        owned_paths=unit.owns_paths,
    )

    instructions = render_contract_instructions(contract)
    assert contract["planned_image_assets"][0]["resource_id"] == "slot-hero"
    assert contract["planned_image_assets"][0]["manifest_source_count"] == 1
    assert "sources" not in contract["planned_image_assets"][0]
    assert contract["planned_image_assets"][0]["element_marker"] == 'data-resource="hero"'
    assert contract["must_preserve_text"] == []
    assert contract["motion_beats"][0]["motion_id"] == "motion:hero"
    assert "resources/renditions/hero-480w.webp" not in instructions
    assert "Aarav Mehta" not in instructions
    assert "Omit the sources prop" in instructions
    assert 'wrapperMarker=data-resource="hero"' in instructions
    assert "IntersectionObserver-driven state" in instructions
    assert 'data-motion-target="hero-copy"' in instructions
    assert (
        "A rule on an ancestor or descendant such as `source child` does not satisfy"
        in instructions
    )


def test_scaffold_font_fallback_precedes_generated_font_tokens() -> None:
    global_css = Path(
        "src/oryxenai/agents/code_generator/scaffolds/react-vite-v1/src/design/global.css"
    ).read_text(encoding="utf-8")

    assert global_css.index('@import "./fonts.css";') < global_css.index('@import "./tokens.css";')
    assert ":root { color-scheme: light; }" in global_css
    assert "color-scheme: light dark" not in global_css
    assert "@theme inline" in global_css
    for slot in (
        "background",
        "foreground",
        "card",
        "primary",
        "primary-foreground",
        "secondary",
        "muted",
        "muted-foreground",
        "accent",
        "destructive",
        "border",
        "input",
        "ring",
    ):
        assert f"--color-{slot}: var(--color-{slot});" in global_css


def test_scaffold_local_image_resolves_immutable_sources_from_manifest() -> None:
    scaffold = Path("src/oryxenai/agents/code_generator/scaffolds/react-vite-v1/src")
    shared = (scaffold / "components/generated/SharedSystems.tsx").read_text(encoding="utf-8")
    placeholder_manifest = (scaffold / "generated/resource-manifest.ts").read_text(encoding="utf-8")

    assert 'import { RESOURCE_MANIFEST } from "../../generated/resource-manifest";' in shared
    assert "sources?: readonly LocalImageSource[]" in shared
    assert "sources ?? manifestAsset?.sources ?? []" in shared
    assert '<picture style={{ display: "block", inlineSize: "100%", blockSize: "100%" }}>' in shared
    assert shared.count('inlineSize: "100%"') >= 2
    assert shared.count('blockSize: "100%"') >= 2
    assert "image_assets: []" in placeholder_manifest


def test_v4_public_runtime_data_excludes_internal_visual_fact_authority() -> None:
    site = {"site_title": "Arjun Mehta — Senior UI/UX Designer"}
    visual = {"global": {"must_preserve": ["Aarav Mehta", "Senior Architect"]}}
    target = {"framework": "react-vite"}

    v4 = _public_runtime_data(
        site=site,
        visual=visual,
        target=target,
        plan=SimpleNamespace(experience_blueprint=_blueprint()),
    )
    legacy = _public_runtime_data(
        site=site,
        visual=visual,
        target=target,
        plan=SimpleNamespace(experience_blueprint=None),
    )

    assert v4 == {"site": site, "target": target}
    assert legacy["visual_direction"] == visual


def test_v4_final_source_does_not_require_visual_direction_facts(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(final_source_validation, "validate_repository", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        final_source_validation, "audit_typescript_source", lambda *args, **kwargs: []
    )
    projections = {
        "site/contract.json": {"routes": [], "public_content": [], "facts": []},
        "design/visual-direction.json": {
            "global": {"must_preserve": ["Aarav Mehta", "Senior Architect"]}
        },
        "execution/contract.json": {"slots": []},
    }
    plan = SimpleNamespace(
        experience_blueprint=_blueprint(), acceptance_coverage=[], interactions=[]
    )

    diagnostics = final_source_validation.validate_final_source(
        tmp_path,
        plan=plan,
        projections=projections,
        allowed_packages=set(),
        public_text=set(),
    )

    assert "SOURCE_VISUAL_CONTRACT_MISSING" not in {item.code for item in diagnostics}


def test_v4_interaction_is_owned_by_its_selector_matched_section_batch() -> None:
    base_blueprint = _blueprint()
    contact_region = base_blueprint.section_regions[0].model_copy(
        update={
            "region_id": "region:contact",
            "section_id": "contact",
            "owner_id": "owner:contact",
            "section_selector": '[data-content-id="contact"]',
            "region_selector": '[data-region-id="region:contact"]',
            "order_mobile": 1,
            "order_tablet": 1,
            "order_desktop": 1,
        }
    )
    blueprint = ExperienceBlueprintV4.model_validate(
        {
            **base_blueprint.model_dump(),
            "route_shells": [
                base_blueprint.route_shells[0]
                .model_copy(update={"section_order": ["hero", "contact"]})
                .model_dump()
            ],
            "section_regions": [
                base_blueprint.section_regions[0].model_dump(),
                contact_region.model_dump(),
            ],
            "interaction_assignments": [
                {
                    "interaction_id": "interaction:home:hero:contact",
                    "route_id": "home",
                    "owner_work_unit_id": "owner:hero",
                    "literal_marker": 'data-interaction="hero-contact"',
                    "target_selector": '[data-content-id="hero"] a',
                    "outcome_selector": '[data-content-id="contact"]',
                    "trigger": "navigation",
                    "keyboard_behavior": "Enter activates the focused link.",
                    "state_transition": "idle to navigated",
                    "focus_behavior": "Focus remains visible.",
                    "expected_navigation": "Same-page navigation to #contact.",
                }
            ],
        }
    )
    plan = SitePlan(
        plan_id="interaction-owner",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero", "contact"],
                section_order=["hero", "contact"],
                responsive_outcome="Readable at every viewport",
                reduced_motion_outcome="Content remains visible without motion",
                interaction_outcome="Keyboard accessible",
            )
        ],
        interactions=[
            InteractionContract(
                interaction_id="interaction:home:hero:contact",
                route_id="home",
                trigger="navigation",
                outcome="idle to navigated",
                keyboard_behavior="Enter activates the focused link.",
                reduced_motion_behavior="No motion is required.",
                target='[data-content-id="hero"] a',
            )
        ],
        experience_blueprint=blueprint,
    )
    projections = {
        "site/contract.json": {
            "routes": [
                {
                    "route_id": "home",
                    "path": "/",
                    "storage_key": "home",
                    "section_sequence": ["hero", "contact"],
                }
            ],
            "public_content": [
                {
                    "route_id": "home",
                    "sections": [
                        {"section_id": "hero", "content": {"headline": "Approved headline"}},
                        {"section_id": "contact", "content": {"heading": "Contact"}},
                    ],
                }
            ],
            "facts": [],
        },
        "design/visual-direction.json": {"global": {"must_preserve": []}},
        "execution/contract.json": {"slots": []},
    }

    compiled = compile_site_plan(plan, projections)
    batch = next(
        item
        for item in compiled.work_graph.units
        if item.kind == "route_batch" and "hero" in item.section_ids
    )
    composer = next(item for item in compiled.work_graph.units if item.kind == "route_compose")

    assert batch.interaction_ids == ["interaction:home:hero:contact"]
    assert composer.interaction_ids == []
    assert compiled.experience_blueprint is not None
    assert compiled.experience_blueprint.interaction_assignments[0].owner_work_unit_id == (
        batch.unit_id
    )
    contract = build_generation_contract(
        unit=batch,
        plan=compiled,
        projections=projections,
        operation="route_batch",
        owned_paths=batch.owns_paths,
    )
    assert [item["interaction_id"] for item in contract["interactions"]] == [
        "interaction:home:hero:contact"
    ]
    assert contract["interactions"][0]["literal_marker"] == ('data-interaction="hero-contact"')
    assert contract["interactions"][0]["target_selector"] == ('[data-content-id="hero"] a')
    assert contract["interactions"][0]["outcome_selector"] == ('[data-content-id="contact"]')
    assert contract["routes"][0]["sections"][0]["section_selector"] == ('[data-content-id="hero"]')
    instructions = render_contract_instructions(contract)
    assert 'data-interaction="hero-contact"' in instructions
    assert '[data-content-id="contact"]' in instructions
    assert contract["required_coverage"]["interaction_ids"] == ["interaction:home:hero:contact"]


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


def test_v4_source_wire_coverage_is_stamped_from_trusted_work_unit() -> None:
    receipt = GenerationContextReceipt(
        receipt_id="context-stamp",
        operation_id="repair",
        role_profile="offline-test",
        output_schema_hash="schema",
        context_hash="context-stamp-hash",
    )
    envelope = SourceGenerationEnvelopeV2(
        result_tag="changes",
        files=[
            SourceFileChange(
                path="src/routes/home/hero.tsx",
                operation="replace",
                complete_utf8_content="export default function Hero() { return null; }\n",
            ),
            SourceFileChange(
                path="src/routes/home/hero.tsx",
                operation="replace",
                complete_utf8_content="export default function Hero() { return null; }\n",
            ),
        ],
        exported_signatures=[],
        # One character is transposed, matching the live integration-polish
        # failure that motivated deterministic host stamping.
        content_ids=["content:home:section-label-7cacd7b3"],
        criterion_ids=["wrong-criterion"],
        resource_slot_ids=[],
        interaction_ids=[],
        resource_requests=[],
        dependency_requests=[],
        failure_details=[],
    )

    result = adapt_v4_generation_result(
        envelope,
        operation_id="repair:home",
        context_receipt=receipt,
        required_coverage={
            "content_ids": ["content:home:section-label-7cac7d3b"],
            "criterion_ids": [],
            "resource_slot_ids": ["slot:hero"],
            "interaction_ids": ["interaction:hero"],
        },
    )

    assert result.changes is not None
    assert result.changes.content_coverage == ["content:home:section-label-7cac7d3b"]
    assert result.changes.criterion_coverage == []
    assert result.changes.resource_usage == ["slot:hero"]
    assert result.changes.interaction_coverage == ["interaction:hero"]
    assert [item.path for item in result.changes.files] == ["src/routes/home/hero.tsx"]


def test_v4_source_wire_discards_signatures_for_unchanged_sibling_files() -> None:
    receipt = GenerationContextReceipt(
        receipt_id="context-signature-scope",
        operation_id="repair",
        role_profile="offline-test",
        output_schema_hash="schema",
        context_hash="context-signature-scope-hash",
    )
    envelope = SourceGenerationEnvelopeV2(
        result_tag="changes",
        files=[
            SourceFileChange(
                path="src/routes/home/design-systems.css",
                operation="replace",
                complete_utf8_content=".design-systems { aspect-ratio: 3 / 2; }\n",
            ),
            SourceFileChange(
                path="src/routes/home/experience.tsx",
                operation="replace",
                complete_utf8_content=(
                    "export default function HomeExperience() { return <section />; }\n"
                ),
            ),
        ],
        exported_signatures=[
            ExportedSignature(
                path="src/routes/home/design-systems.tsx",
                export_name="HomeDesignSystems",
                kind="component",
            ),
            ExportedSignature(
                path="src/routes/home/experience.tsx",
                export_name="HomeExperience",
                kind="component",
            ),
        ],
        content_ids=[],
        criterion_ids=[],
        resource_slot_ids=[],
        interaction_ids=[],
        resource_requests=[],
        dependency_requests=[],
        failure_details=[],
    )

    result = adapt_v4_generation_result(
        envelope,
        operation_id="repair:home:batch-2",
        context_receipt=receipt,
        required_coverage={
            "content_ids": [],
            "criterion_ids": [],
            "resource_slot_ids": [],
            "interaction_ids": [],
        },
    )

    assert result.changes is not None
    assert [item.path for item in result.changes.exported_signatures] == [
        "src/routes/home/experience.tsx"
    ]


def test_v4_source_wire_derives_omitted_signature_from_changed_export() -> None:
    receipt = GenerationContextReceipt(
        receipt_id="context-signature-completion",
        operation_id="repair",
        role_profile="offline-test",
        output_schema_hash="schema",
        context_hash="context-signature-completion-hash",
    )
    path = "src/routes/home/approach.tsx"
    envelope = SourceGenerationEnvelopeV2(
        result_tag="changes",
        files=[
            SourceFileChange(
                path=path,
                operation="replace",
                complete_utf8_content=(
                    "export default function HomeApproach() { return <section />; }\n"
                ),
            )
        ],
        exported_signatures=[],
        content_ids=[],
        criterion_ids=[],
        resource_slot_ids=[],
        interaction_ids=[],
        resource_requests=[],
        dependency_requests=[],
        failure_details=[],
    )

    result = adapt_v4_generation_result(
        envelope,
        operation_id="repair:home:batch-1",
        context_receipt=receipt,
        required_coverage={
            "content_ids": [],
            "criterion_ids": [],
            "resource_slot_ids": [],
            "interaction_ids": [],
        },
    )

    assert result.changes is not None
    assert [item.model_dump(mode="json") for item in result.changes.exported_signatures] == [
        {"path": path, "export_name": "HomeApproach", "kind": "component"}
    ]


def test_v4_source_wire_keeps_conflicting_duplicate_files_for_rejection() -> None:
    receipt = GenerationContextReceipt(
        receipt_id="context-conflict",
        operation_id="route_batch",
        role_profile="offline-test",
        output_schema_hash="schema",
        context_hash="context-conflict-hash",
    )
    envelope = SourceGenerationEnvelopeV2(
        result_tag="changes",
        files=[
            SourceFileChange(
                path="src/routes/home/hero.tsx",
                operation="replace",
                complete_utf8_content="export default function Hero() { return null; }\n",
            ),
            SourceFileChange(
                path="src/routes/home/hero.tsx",
                operation="replace",
                complete_utf8_content="export default function Hero() { return <main />; }\n",
            ),
        ],
        exported_signatures=[],
        content_ids=[],
        criterion_ids=[],
        resource_slot_ids=[],
        interaction_ids=[],
        resource_requests=[],
        dependency_requests=[],
        failure_details=[],
    )

    result = adapt_v4_generation_result(
        envelope,
        operation_id="route_batch:home",
        context_receipt=receipt,
        required_coverage={
            "content_ids": [],
            "criterion_ids": [],
            "resource_slot_ids": [],
            "interaction_ids": [],
        },
    )

    assert result.changes is not None
    assert len(result.changes.files) == 2


def test_v4_css_only_route_polish_does_not_require_export_signatures() -> None:
    unit = WorkUnit(
        unit_id="route-home-batch-1",
        kind="route_batch",
        owns_paths=["src/routes/home/hero.css", "src/routes/home/hero.tsx"],
    )
    projections = {
        "site/contract.json": {"public_content": [], "facts": []},
    }
    css_changes = GenerationChanges(
        files=[
            SourceFileChange(
                path="src/routes/home/hero.css",
                operation="replace",
                complete_utf8_content="#hero { aspect-ratio: 1.7 / 1; }\n",
            )
        ],
        exported_signatures=[],
        content_coverage=[],
        criterion_coverage=[],
        resource_usage=[],
        interaction_coverage=[],
    )

    _validate_v4_generation_coverage(
        css_changes,
        unit,
        SimpleNamespace(),
        projections,
    )

    exported_source_changes = css_changes.model_copy(
        update={
            "files": [
                SourceFileChange(
                    path="src/routes/home/hero.tsx",
                    operation="replace",
                    complete_utf8_content=(
                        "export default function Hero() { return <section />; }\n"
                    ),
                )
            ]
        }
    )
    with pytest.raises(SourceValidationError) as exc_info:
        _validate_v4_generation_coverage(
            exported_source_changes,
            unit,
            SimpleNamespace(),
            projections,
        )

    assert exc_info.value.code == "SOURCE_EXPORT_SIGNATURE_MISSING"
    assert "src/routes/home/hero.tsx" in exc_info.value.message


def test_v4_duplicate_path_identifies_the_offending_file() -> None:
    """A repair model can't fix "duplicate paths" without being told which
    path is duplicated -- the diagnostic must carry it in `.file`, not just
    a generic message, so a repair round has something to act on."""
    unit = WorkUnit(
        unit_id="route-home-batch-1",
        kind="route_batch",
        owns_paths=["src/routes/home/hero.tsx"],
    )
    projections = {
        "site/contract.json": {"public_content": [], "facts": []},
    }
    duplicate_changes = GenerationChanges(
        files=[
            SourceFileChange(
                path="src/routes/home/hero.tsx",
                operation="replace",
                complete_utf8_content="export default function Hero() { return <section />; }\n",
            ),
            SourceFileChange(
                path="src/routes/home/hero.tsx",
                operation="replace",
                complete_utf8_content="export default function Hero() { return <div />; }\n",
            ),
        ],
        exported_signatures=[],
        content_coverage=[],
        criterion_coverage=[],
        resource_usage=[],
        interaction_coverage=[],
    )

    with pytest.raises(SourceValidationError) as exc_info:
        _validate_v4_generation_coverage(
            duplicate_changes,
            unit,
            SimpleNamespace(),
            projections,
        )

    assert exc_info.value.code == "SOURCE_DUPLICATE_PATH"
    assert exc_info.value.file == "src/routes/home/hero.tsx"
    assert "src/routes/home/hero.tsx" in exc_info.value.message


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
    blueprint = _blueprint().model_copy(
        update={
            "tokens": _blueprint().tokens.model_copy(
                update={
                    "shadcn_theme_bindings": {
                        "background": "paper",
                        "foreground": "ink",
                        "primary": "ink",
                        "primary-foreground": "paper",
                    }
                }
            )
        }
    )
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
    assert "--color-background: var(--color-paper);" in css
    assert "--color-primary: var(--color-ink);" in css
    assert "--color-primary-foreground: var(--color-paper);" in css
    assert "font-weight: 400" in css
    assert 'format("woff2")' in css
    assert "var(--token," not in css
    assert css.count("--type-body-min:") == 1
    assert css.count("--type-display-min:") == 1


def test_v4_token_compiler_rejects_shadcn_slot_colliding_with_a_color_token() -> None:
    """Defense-in-depth sibling of the schema-level collision test: even a
    blueprint that reached the compiler without going back through
    DesignTokenSystemV4's own validator (e.g. built via model_copy, which
    does not re-validate) must not silently emit two --color-accent
    declarations where the alias clobbers the real color."""
    tokens = _blueprint().tokens.model_copy(
        update={
            "colors": [
                *_blueprint().tokens.colors,
                NamedColorTokenV4(name="accent", value="#b84a32"),
            ],
            "shadcn_theme_bindings": {"accent": "ink"},
        }
    )
    blueprint = _blueprint().model_copy(update={"tokens": tokens})
    with pytest.raises(TokenCompilationError, match="collide"):
        compile_generated_tokens(blueprint)


def test_v4_token_compiler_deduplicates_font_faces_shared_across_roles() -> None:
    """Regression test: body and display commonly share one
    approved_font_slot/family. Each role's iteration independently re-matched
    the same binding, emitting every one of its @font-face rules a second
    time -- a duplicate the integration reviewer flags as blocking, but which
    no repair round could ever fix since this file is compiler-owned, never
    model-authored."""
    token_data = _blueprint().tokens.model_dump(mode="python")
    token_data["typography_roles"].append(
        {
            "role": "display",
            "approved_font_slot": "font:body",
            "family": "Local Sans",
            "weights": [700],
            "local_files": ["resources/fonts/local/700-bold.woff2"],
            "body_min_rem": 2,
            "body_max_rem": 3,
            "heading_ratio": 1.25,
            "body_line_height": 1.05,
        }
    )
    blueprint = _blueprint().model_copy(
        update={"tokens": DesignTokenSystemV4.model_validate(token_data)}
    )
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
                    "resources/fonts/local/400-normal.woff2",
                    "resources/fonts/local/700-bold.woff2",
                ],
                font_family="Local Sans",
                font_weights=["400", "700"],
            )
        ],
    )
    assert css.count("@font-face {") == 2
    assert css.count("font-weight: 400;") == 1
    assert css.count("font-weight: 700;") == 1


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


def test_v4_quality_review_evidence_must_exist_and_make_low_scores_actionable() -> None:
    dimensions = ["hierarchy", "composition", "typography", "resource_fit", "motion"]
    source_path = "src/routes/home/hero.tsx"
    source = "\n".join(f"<div data-quality-{dimension} />" for dimension in dimensions)
    evidence = [
        {
            "dimension": dimension,
            "score": 3 if dimension == "motion" else 4,
            "owner_work_unit_id": "route-home-batch-1",
            "file": source_path,
            "line": index + 1,
            "marker": f"data-quality-{dimension}",
            "evidence": f"Observed {dimension} evidence.",
        }
        for index, dimension in enumerate(dimensions)
    ]
    unrelated_blocker = {
        "finding_id": "finding-hierarchy",
        "severity": "blocking",
        "owner_work_unit_id": "route-home-batch-2",
        "code": "HIERARCHY_DEFECT",
        "file": source_path,
        "line": 1,
        "marker": "data-quality-hierarchy",
        "evidence": "The hierarchy needs correction.",
        "requested_outcome": "Correct the hierarchy.",
    }
    draft = QualityReviewDraftV1(
        hierarchy_score=4,
        composition_score=4,
        typography_score=4,
        resource_fit_score=4,
        motion_score=3,
        score_evidence=evidence,
        findings=[unrelated_blocker],
        review_summary="Motion remains below the acceptance floor.",
    )

    with pytest.raises(QualityReviewError, match="no blocking finding"):
        validate_quality_review_draft_evidence(
            draft,
            assembled_source={source_path: source},
        )

    motion_blocker = {
        "finding_id": "finding-motion",
        "severity": "blocking",
        "owner_work_unit_id": "route-home-batch-1",
        "code": "MOTION_DEFECT",
        "file": source_path,
        "line": 5,
        "marker": "data-quality-motion",
        "evidence": "The motion fallback needs correction.",
        "requested_outcome": "Correct the motion fallback.",
    }
    actionable = QualityReviewDraftV1(
        hierarchy_score=4,
        composition_score=4,
        typography_score=4,
        resource_fit_score=4,
        motion_score=3,
        score_evidence=evidence,
        findings=[motion_blocker],
        review_summary="Motion has one concrete blocking defect.",
    )
    canonical = validate_quality_review_draft_evidence(
        actionable,
        assembled_source={source_path: source},
    )
    assert canonical == actionable

    off_by_one_evidence = [dict(item) for item in evidence]
    off_by_one_evidence[-1]["line"] = 4
    off_by_one = QualityReviewDraftV1(
        hierarchy_score=4,
        composition_score=4,
        typography_score=4,
        resource_fit_score=4,
        motion_score=3,
        score_evidence=off_by_one_evidence,
        findings=[motion_blocker],
        review_summary="The host must stamp the unique marker's real line.",
    )
    canonical = validate_quality_review_draft_evidence(
        off_by_one,
        assembled_source={source_path: source},
    )
    assert canonical.score_evidence[-1].line == 5

    fabricated_evidence = [dict(item) for item in evidence]
    fabricated_evidence[-1]["file"] = "src/routes/home/fabricated.tsx"
    fabricated = QualityReviewDraftV1(
        hierarchy_score=4,
        composition_score=4,
        typography_score=4,
        resource_fit_score=4,
        motion_score=3,
        score_evidence=fabricated_evidence,
        findings=[motion_blocker],
        review_summary="Motion evidence uses a fabricated path.",
    )
    with pytest.raises(QualityReviewError, match="outside the assembled source"):
        validate_quality_review_draft_evidence(
            fabricated,
            assembled_source={source_path: source},
        )

    repeated_marker = "<div data-quality-motion />\n<div data-quality-motion />"
    canonical = validate_quality_review_draft_evidence(
        off_by_one,
        assembled_source={
            source_path: source.replace("<div data-quality-motion />", repeated_marker)
        },
    )
    assert canonical.score_evidence[-1].line == 5

    tied_evidence = [dict(item) for item in evidence]
    tied_evidence[-1]["line"] = 6
    tied = QualityReviewDraftV1(
        hierarchy_score=4,
        composition_score=4,
        typography_score=4,
        resource_fit_score=4,
        motion_score=3,
        score_evidence=tied_evidence,
        findings=[motion_blocker],
        review_summary="The repeated marker is equally close to two lines.",
    )
    tied_source = source.replace(
        "<div data-quality-motion />",
        '<div data-quality-motion />\n<div aria-hidden="true" />\n<div data-quality-motion />',
    )
    with pytest.raises(QualityReviewError, match="equally close"):
        validate_quality_review_draft_evidence(
            tied,
            assembled_source={source_path: tied_source},
        )

    with pytest.raises(QualityReviewError, match="non-repairable owner"):
        validate_quality_review_draft_evidence(
            actionable,
            assembled_source={source_path: source},
            repairable_owner_ids={"route-home-batch-2"},
        )
