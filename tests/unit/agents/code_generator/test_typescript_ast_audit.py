from __future__ import annotations

from oryxenai.agents.code_generator.core.development_schemas import (
    DesignTokenSystemV4,
    ExperienceBlueprintV4,
    SitePlan,
)
from oryxenai.agents.code_generator.core.source_lexing import strip_source_comments
from oryxenai.agents.code_generator.core.typescript_ast_audit import (
    _audit_v4_anti_slop,
    _audit_v4_cross_route_sameness,
    _marker_present,
    _route_source_path,
    _selector_declarations,
    _selector_has_reduced_motion,
    _selector_targets_contract,
    audit_typescript_source,
)


def _v4_plan_with_motion_beat(motion_beat: dict) -> SitePlan:
    """A minimal, valid V4 SitePlan with one route/section and one motion beat."""

    plan = SitePlan.model_validate(
        {
            "plan_id": "motion-plan",
            "routes": [
                {
                    "route_id": "home",
                    "path": "/",
                    "storage_key": "home",
                    "section_ids": ["home:hero"],
                    "responsive_outcome": "stack on mobile",
                    "reduced_motion_outcome": "static equivalent",
                    "interaction_outcome": "keyboard accessible",
                    "composition": {
                        "hierarchy": "headline before evidence",
                        "layout_strategy": "text-led asymmetry",
                        "visual_anchor": "evidence panel",
                    },
                    "responsive_behavior": {
                        "mobile_strategy": "stack sections",
                        "breakpoint_strategy": "collapse at readable measure",
                        "overflow_strategy": "wrap controls",
                        "touch_target_strategy": "large targets",
                    },
                }
            ],
            "creative_thesis": {
                "thesis": "evidence-first systems",
                "distinction": "proof-led rather than card-led",
                "narrative_arc": "positioning to evidence",
            },
            "visual_system": {
                "typography": "confident display and calm body",
                "color_strategy": "single evidence accent",
                "spacing_rhythm": "editorial pauses",
                "motion_vocabulary": "subtle optional reveals",
            },
            "shell": {
                "navigation": "semantic anchor navigation",
                "main_landmark": "one main landmark",
                "focus_treatment": "visible focus ring",
            },
            "shared_component_contracts": [],
            "interactions": [],
            "acceptance_coverage": [],
            "work_graph": {
                "units": [
                    {"unit_id": "foundation", "kind": "foundation"},
                    {
                        "unit_id": "route-home",
                        "kind": "route",
                        "route_id": "home",
                        "section_ids": ["home:hero"],
                        "depends_on": ["foundation"],
                    },
                ]
            },
        }
    )
    plan.experience_blueprint = ExperienceBlueprintV4(
        selected_concept_id="concept:proof",
        narrative_arc="positioning to evidence",
        tokens=DesignTokenSystemV4(
            colors=[{"name": "ink", "value": "#121212"}],
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
                    "maximum": {"name": "content-max", "value": 1120, "unit": "px"},
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
        motion_beats=[motion_beat],
    )
    return plan


def _trusted_reveal_hero_files(*, render_reveal: bool) -> dict[str, str]:
    reveal_element = (
        '<Reveal data-motion-target="hero-lifecycle"><span>Endpoint</span></Reveal>'
        if render_reveal
        else '<div data-motion-target="hero-lifecycle"><span>Endpoint</span></div>'
    )
    return {
        "src/routes/home/index.tsx": (
            'import "./route.css";\n'
            'import { Reveal } from "@/components/generated/SharedSystems";\n\n'
            "export default function RoutePage() {\n"
            '  return <main data-route-id="home">\n'
            f'    <section id="hero" data-content-id="home:hero">{reveal_element}</section>\n'
            "  </main>;\n"
            "}\n"
        ),
        "src/routes/home/route.css": "#hero { padding-block: 1rem; }\n",
    }


def test_motion_marker_accepts_a_static_conditional_jsx_attribute() -> None:
    source = '<article data-motion={index === 0 ? "current-role" : undefined} />'

    assert _marker_present('data-motion="current-role"', source)


def test_route_source_path_does_not_rehash_planner_storage_key() -> None:
    route = {
        "route_id": "home",
        "storage_key": "home-4ea140588150-4859f06d",
    }

    assert _route_source_path(route, semantic=True) == (
        "src/routes/home-4ea140588150-4859f06d/index.tsx"
    )


def test_route_source_path_semanticizes_route_id_without_storage_key() -> None:
    assert _route_source_path({"route_id": "home"}, semantic=True).startswith("src/routes/home-")


def test_comment_stripping_preserves_https_literals_and_removes_real_comments() -> None:
    source = (
        '<a href="https://example.test/profile" data-interaction="hero-secondary">'
        '{contentValue("content:hero:secondary-href")}</a> // marker-only comment\n'
        "/* content:comment-only */ export const ready = true;"
    )

    clean = strip_source_comments(source)

    assert "https://example.test/profile" in clean
    assert 'data-interaction="hero-secondary"' in clean
    assert "content:hero:secondary-href" in clean
    assert "marker-only comment" not in clean
    assert "content:comment-only" not in clean
    assert "export const ready = true" in clean


def test_motion_selector_audit_accepts_runtime_state_qualifiers() -> None:
    css = """
#hero[data-motion-ready="true"] .hero-copy {
  animation: hero-entry 400ms ease both;
  opacity: 0;
  transform: translateY(12px);
}
@media (prefers-reduced-motion: reduce) {
  #hero[data-motion-ready="true"] .hero-copy {
    animation: none;
    opacity: 1;
    transform: none;
  }
}
"""

    assert "animation" in _selector_declarations(css, "#hero .hero-copy")
    assert _selector_targets_contract(
        '#hero [data-region-id="region:home:home:hero"][data-move="move-home-hero-split"]',
        '[data-region-id="region:home:home:hero"][data-move="move-home-hero-split"]',
    )
    assert not _selector_targets_contract(
        '#hero [data-region-id="region:home:home:hero-other"]',
        '[data-region-id="region:home:home:hero"]',
    )
    assert _selector_has_reduced_motion(css, "#hero .hero-copy")
    assert not _selector_has_reduced_motion(css, "#other .hero-copy")
    assert not _selector_has_reduced_motion(
        css.replace("prefers-reduced-motion: reduce", "prefers-reduced-motion: no-preference"),
        "#hero .hero-copy",
    )


def test_blanket_reveal_audit_counts_affected_sections_not_declarations() -> None:
    files = {
        f"src/routes/home/sections/section-{index}.tsx": (
            f'export const Section{index} = () => <section><div data-index="{index}" /></section>;'
        )
        for index in range(6)
    }
    files["src/routes/home/sections/section-0.css"] = """
.one { opacity: 0; transform: translateY(12px); }
.two { opacity: 0; transform: translateY(16px); }
.three { opacity: 0; transform: translateY(20px); }
"""

    diagnostics = _audit_v4_anti_slop(
        route_id="home",
        route_file="src/routes/home/index.tsx",
        route_prefix="src/routes/home/",
        files=files,
        visual_direction={},
    )
    assert "SOURCE_BLANKET_REVEAL_MOTION" not in {item.code for item in diagnostics}

    for index in range(1, 5):
        files[f"src/routes/home/sections/section-{index}.css"] = (
            f".section-{index} {{ opacity: 0; transform: translateY(12px); }}"
        )
    diagnostics = _audit_v4_anti_slop(
        route_id="home",
        route_file="src/routes/home/index.tsx",
        route_prefix="src/routes/home/",
        files=files,
        visual_direction={},
    )
    assert "SOURCE_BLANKET_REVEAL_MOTION" in {item.code for item in diagnostics}


def test_cross_route_audit_rejects_identical_section_sequences() -> None:
    routes = [
        {"route_id": "home", "storage_key": "home"},
        {"route_id": "work", "storage_key": "work"},
    ]
    files = {
        f"src/routes/{route}/sections/section-{index}.tsx": (
            f"export const Section{index} = () => "
            '<section className="same-shell"><div className="same-content" /></section>;'
        )
        for route in ("home", "work")
        for index in range(3)
    }

    diagnostics = _audit_v4_cross_route_sameness(routes=routes, files=files)

    matches = [item for item in diagnostics if item.code == "SOURCE_CROSS_ROUTE_SAMENESS"]
    assert len(matches) == 1
    assert matches[0].route_id == "work"
    assert matches[0].expected == "distinct from route home"


_TRUSTED_MOTION_BEAT = {
    "motion_id": "motion:home:hero-lifecycle-reveal",
    "route_id": "home",
    "section_id": "hero",
    "target_marker": 'data-motion-target="hero-lifecycle"',
    "target_selector": '#hero [data-motion-target="hero-lifecycle"]',
    "trigger": "viewport",
    "trigger_selector": "#hero",
    "pattern_id": "reveal-fade-rise",
    "duration_min_ms": 600,
    "duration_max_ms": 900,
    "easing": "ease-out",
    "performance_budget_ms": 50,
    "purposeful_outcome": (
        "Reveal the subordinate conceptual lifecycle cue after the readable "
        "hero group is available."
    ),
    "reduced_motion_replacement": (
        "Render the lifecycle line, markers, and labels immediately in "
        "their final visible positions."
    ),
    "changed_properties": [
        {"property_name": "opacity", "before_value": "0", "after_value": "1"},
        {
            "property_name": "transform",
            "before_value": "translateY(28px)",
            "after_value": "translateY(0)",
        },
    ],
}


def test_final_motion_audit_accepts_a_trusted_reveal_pattern_with_no_hand_authored_css(
    tmp_path,
) -> None:
    """Live-discovered 2026-09-10: a beat bound to a catalogue pattern_id
    delegates its entire animation (opacity/transform states, reduced
    motion, data-motion-ready wiring) to motion.css/SharedSystems.tsx --
    trusted files never included in a section's own owned source. This
    final gate used to demand those implementation details verbatim in the
    section's own CSS regardless of pattern_id (unlike source_validation.py's
    pre-gate, which already carried this exception), so a correct, trusted
    <Reveal> usage with no hand-authored animation was rejected at the very
    last verification step with SOURCE_MOTION_BEAT_UNIMPLEMENTED /
    SOURCE_MOTION_REDUCED_MOTION_MISSING even though nothing was wrong."""

    plan = _v4_plan_with_motion_beat(_TRUSTED_MOTION_BEAT)
    files = _trusted_reveal_hero_files(render_reveal=True)

    diagnostics = audit_typescript_source(tmp_path, files=files, plan=plan)

    motion_codes = {item.code for item in diagnostics if "MOTION" in item.code}
    assert motion_codes == set(), diagnostics


def test_final_motion_audit_still_rejects_a_trusted_pattern_missing_its_component(
    tmp_path,
) -> None:
    plan = _v4_plan_with_motion_beat(_TRUSTED_MOTION_BEAT)
    files = _trusted_reveal_hero_files(render_reveal=False)

    diagnostics = audit_typescript_source(tmp_path, files=files, plan=plan)

    assert any(item.code == "SOURCE_MOTION_BEAT_UNIMPLEMENTED" for item in diagnostics), diagnostics
    assert not any(item.code == "SOURCE_MOTION_REDUCED_MOTION_MISSING" for item in diagnostics)
