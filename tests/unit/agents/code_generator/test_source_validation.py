from types import SimpleNamespace

from oryxenai.agents.code_generator.core.generation_orchestrator import (
    _invalidate_stale_route_batch_checkpoint,
)
from oryxenai.agents.code_generator.core.source_validation import (
    _canonical_visible_text,
    normalize_generated_route_contract,
    validate_local_imports,
    validate_repository,
    validate_route_batch_contract,
    validate_route_composer_contract,
)


def test_canonical_visible_text_collapses_source_wrapping() -> None:
    approved = "Approved copy that spans one rendered sentence."
    wrapped = "Approved copy that spans one\n    rendered sentence."

    assert _canonical_visible_text(wrapped) == _canonical_visible_text(approved)


def test_validate_local_imports_uses_repository_source_locations(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    (tmp_path / "src" / "content").mkdir(parents=True)
    (tmp_path / "src" / "content" / "generated-content.ts").write_text(
        "export const contentValue = '';", encoding="utf-8"
    )
    source = section / "Hero.tsx"
    source.write_text(
        'import { contentValue } from "../../../content/generated-content";\n'
        'import { missing } from "../../../../content/generated-content";\n',
        encoding="utf-8",
    )

    diagnostics = validate_local_imports(
        tmp_path,
        ["src/routes/home/sections/Hero.tsx"],
        work_unit_id="route-home-batch-1",
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "SOURCE_LOCAL_IMPORT_MISSING"
    assert "../../../../content/generated-content" in diagnostics[0].normalized_message


def test_validate_local_imports_rejects_missing_named_export(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    source = section / "Hero.tsx"
    source.write_text(
        'import { HeroSection } from "./Hero";\nexport default function Hero() { return null; }\n',
        encoding="utf-8",
    )

    diagnostics = validate_local_imports(
        tmp_path,
        ["src/routes/home/sections/Hero.tsx"],
        work_unit_id="route-home-batch-1",
    )

    assert diagnostics and diagnostics[0].code == "SOURCE_LOCAL_EXPORT_MISSING"
    assert "HeroSection" in diagnostics[0].normalized_message


def test_route_batch_rejects_spelled_out_css_lengths(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    (section / "Hero.tsx").write_text(
        '<section id="hero" data-content-id="home:hero" />\n',
        encoding="utf-8",
    )
    css = section / "Hero.css"
    css.write_text("#hero p { max-width: fiftych; }\n", encoding="utf-8")
    paths = [
        "src/routes/home/sections/Hero.tsx",
        "src/routes/home/sections/Hero.css",
    ]
    kwargs = {
        "route_id": "home",
        "section_ids": ["home:hero"],
        "section_selectors_by_section": {"home:hero": "#hero"},
        "work_unit_id": "route-home-batch-1",
    }

    diagnostics = validate_route_batch_contract(tmp_path, paths, **kwargs)

    assert [item.code for item in diagnostics] == ["SOURCE_CSS_INVALID_LENGTH"]
    assert diagnostics[0].file == "src/routes/home/sections/Hero.css"
    assert "fiftych" in diagnostics[0].normalized_message

    css.write_text(
        "/* the old fiftych typo is mentioned only in this comment */\n"
        ".fiftych { max-width: 50ch; }\n",
        encoding="utf-8",
    )
    assert not validate_route_batch_contract(tmp_path, paths, **kwargs)


def test_repository_policy_can_scope_progressive_batch_source(tmp_path) -> None:
    owned = tmp_path / "src" / "routes" / "home" / "sections" / "Hero.css"
    foreign = tmp_path / "src" / "routes" / "home" / "sections" / "Experience.css"
    owned.parent.mkdir(parents=True)
    owned.write_text("#hero { max-width: 50ch; }\n", encoding="utf-8")
    foreign.write_text("#experience { max-width: fiftych; }\n", encoding="utf-8")
    kwargs = {
        "allowed_packages": set(),
        "public_text": set(),
        "max_source_bytes": 100_000,
        "work_unit_id": "route-home-batch-1",
    }

    assert not validate_repository(
        tmp_path,
        source_paths=["src/routes/home/sections/Hero.css"],
        **kwargs,
    )
    diagnostics = validate_repository(tmp_path, **kwargs)

    assert [item.code for item in diagnostics] == ["SOURCE_CSS_INVALID_LENGTH"]
    assert diagnostics[0].file == "src/routes/home/sections/Experience.css"


def test_repository_policy_rejects_unbound_route_tokens_and_route_font_faces(tmp_path) -> None:
    design = tmp_path / "src" / "design"
    section = tmp_path / "src" / "routes" / "home" / "sections"
    design.mkdir(parents=True)
    section.mkdir(parents=True)
    tokens = design / "generated-tokens.css"
    tokens.write_text(":root { --space-5: 1.5rem; }\n", encoding="utf-8")
    source = section / "Hero.tsx"
    source.write_text(
        'const style = { "--runtime-size": "8rem" } as CSSProperties;\n',
        encoding="utf-8",
    )
    css = section / "Hero.css"
    css.write_text(
        """@font-face { font-family: "Space Grotesk"; }
#hero {
  gap: var(--space-5);
  width: var(--runtime-size);
  max-width: var(--size-container-width);
}
""",
        encoding="utf-8",
    )
    kwargs = {
        "allowed_packages": set(),
        "public_text": set(),
        "max_source_bytes": 100_000,
        "work_unit_id": "route-home-batch-1",
        "source_paths": [
            "src/routes/home/sections/Hero.tsx",
            "src/routes/home/sections/Hero.css",
        ],
    }

    diagnostics = validate_repository(tmp_path, **kwargs)

    assert {item.code for item in diagnostics} == {
        "SOURCE_CSS_CUSTOM_PROPERTY_UNBOUND",
        "SOURCE_ROUTE_FONT_FACE_FORBIDDEN",
    }
    unbound = next(
        item for item in diagnostics if item.code == "SOURCE_CSS_CUSTOM_PROPERTY_UNBOUND"
    )
    assert unbound.file == "src/routes/home/sections/Hero.css"
    assert "--size-container-width" in unbound.normalized_message

    tokens.write_text(
        ":root { --space-5: 1.5rem; --size-container-width: 68rem; }\n",
        encoding="utf-8",
    )
    css.write_text(
        "#hero { gap: var(--space-5); width: var(--runtime-size); "
        "max-width: var(--size-container-width); }\n",
        encoding="utf-8",
    )

    assert not validate_repository(tmp_path, **kwargs)


def test_validate_route_batch_contract_requires_blueprint_section_selectors(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    hero = section / "Hero.tsx"
    hero.write_text(
        '<section id="home:hero" data-content-id="home:hero" />\n',
        encoding="utf-8",
    )
    selected_work = section / "SelectedWork.tsx"
    selected_work.write_text(
        '<section id="selected-work" data-content-id="home:selected-work" />\n',
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        [
            "src/routes/home/sections/Hero.tsx",
            "src/routes/home/sections/SelectedWork.tsx",
        ],
        route_id="home",
        section_ids=["home:hero", "home:selected-work"],
        section_selectors_by_section={
            "home:hero": "#hero",
            "home:selected-work": "#selected-work",
        },
        work_unit_id="route-home-batch-1",
    )

    assert {item.code for item in diagnostics} == {"SOURCE_ROUTE_BATCH_DOM_ID_INVALID"}


def test_route_batch_selector_counts_static_jsx_not_query_selector_text(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    hero = section / "Hero.tsx"
    path = "src/routes/home/sections/Hero.tsx"
    common = {
        "route_id": "home",
        "section_ids": ["home:hero"],
        "section_selectors_by_section": {"home:hero": '[data-section="home:hero"]'},
        "work_unit_id": "route-home-batch-1",
    }
    hero.write_text(
        """const section = document.querySelector('[data-section="home:hero"]');
export default function Hero() {
  return <section data-section="home:hero" data-content-id="home:hero" />;
}
""",
        encoding="utf-8",
    )

    assert not validate_route_batch_contract(tmp_path, [path], **common)

    hero.write_text(
        """const section = document.querySelector('[data-section="home:hero"]');
export default function Hero() {
  return <section data-content-id="home:hero" />;
}
""",
        encoding="utf-8",
    )
    diagnostics = validate_route_batch_contract(tmp_path, [path], **common)
    assert [item.code for item in diagnostics] == ["SOURCE_ROUTE_BATCH_DOM_ID_INVALID"]

    hero.write_text(
        """export default function Hero() {
  return <section data-section="home:hero" data-content-id="home:hero">
    <div data-section="home:hero" />
  </section>;
}
""",
        encoding="utf-8",
    )
    diagnostics = validate_route_batch_contract(tmp_path, [path], **common)
    assert [item.code for item in diagnostics] == ["SOURCE_ROUTE_BATCH_DOM_ID_INVALID"]


def test_route_batch_contract_requires_exact_distinctive_move_css(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    hero = section / "Hero.tsx"
    css = section / "Hero.css"
    hero.write_text(
        '<section id="hero" data-content-id="home:hero" data-distinctive-move="hero-rail" />\n',
        encoding="utf-8",
    )
    css.write_text(
        ".hero-rail { display: grid; grid-template-columns: 2fr 1fr; }\n",
        encoding="utf-8",
    )
    paths = [
        "src/routes/home/sections/Hero.tsx",
        "src/routes/home/sections/Hero.css",
    ]
    kwargs = {
        "route_id": "home",
        "section_ids": ["home:hero"],
        "section_selectors_by_section": {"home:hero": "#hero"},
        "distinctive_moves": [
            {
                "move_id": "move-home-hero-rail",
                "section_id": "home:hero",
                "runtime_marker": 'data-distinctive-move="hero-rail"',
                "source_selector": "#hero .hero-rail",
                "required_css_properties": ["display", "grid-template-columns"],
            }
        ],
        "work_unit_id": "route-home-batch-1",
    }

    diagnostics = validate_route_batch_contract(tmp_path, paths, **kwargs)

    assert [item.code for item in diagnostics] == ["SOURCE_ROUTE_BATCH_DISTINCTIVE_MOVE_INVALID"]
    assert diagnostics[0].file == "src/routes/home/sections/Hero.css"

    css.write_text(
        "#hero .hero-rail { display: grid; grid-template-columns: 2fr 1fr; }\n",
        encoding="utf-8",
    )
    assert not validate_route_batch_contract(tmp_path, paths, **kwargs)

    css.write_text(
        '@media (min-width: 768px) { #hero .hero-rail[data-distinctive-move="hero-rail"] { '
        "display: grid; grid-template-columns: 2fr 1fr; } }\n",
        encoding="utf-8",
    )
    assert not validate_route_batch_contract(tmp_path, paths, **kwargs)


def test_route_batch_contract_allows_distinctive_move_css_scoped_under_an_ancestor(
    tmp_path,
) -> None:
    """Regression test for the 2026-09-05 live-discovered false positive
    (run cf762cfb-...): a model consistently, reasonably scoped distinctive-
    move CSS under the section's own ancestor selector (e.g.
    "#hero [data-region-id=...]") across 3 repair rounds, and the prior
    exact-string selector check rejected all three identically -- exhausting
    the repair budget on CSS that actually satisfied every required
    property, just not via the bare expected selector alone."""
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    hero = section / "Hero.tsx"
    css = section / "Hero.css"
    hero.write_text(
        '<section id="hero" data-content-id="home:hero" '
        'data-region-id="region:home:home:hero" data-move="move-home-hero-split" />\n',
        encoding="utf-8",
    )
    css.write_text(
        '#hero [data-region-id="region:home:home:hero"] { display: grid; align-items: center; }\n'
        '#hero [data-region-id="region:home:home:hero"][data-move="move-home-hero-split"] '
        "{ display: grid; grid-template-columns: minmax(0, 1fr); align-items: center; }\n",
        encoding="utf-8",
    )
    paths = [
        "src/routes/home/sections/Hero.tsx",
        "src/routes/home/sections/Hero.css",
    ]
    kwargs = {
        "route_id": "home",
        "section_ids": ["home:hero"],
        "section_selectors_by_section": {"home:hero": "#hero"},
        "distinctive_moves": [
            {
                "move_id": "move-home-hero-split",
                "section_id": "home:hero",
                "runtime_marker": 'data-move="move-home-hero-split"',
                "source_selector": '[data-region-id="region:home:home:hero"]',
                "required_css_properties": ["display", "grid-template-columns", "align-items"],
            }
        ],
        "work_unit_id": "route-home-batch-1",
    }

    assert not validate_route_batch_contract(tmp_path, paths, **kwargs)

    # A selector that only coincidentally shares a substring must still fail.
    css.write_text(
        '#hero [data-region-id="region:home:home:hero-other"] '
        "{ display: grid; grid-template-columns: minmax(0, 1fr); align-items: center; }\n",
        encoding="utf-8",
    )
    diagnostics = validate_route_batch_contract(tmp_path, paths, **kwargs)
    assert [item.code for item in diagnostics] == ["SOURCE_ROUTE_BATCH_DISTINCTIVE_MOVE_INVALID"]


def test_route_batch_contract_enforces_canonical_h1_section_owner(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    hero = section / "Hero.tsx"
    work = section / "Work.tsx"
    hero.write_text(
        '<section id="hero" data-content-id="home:hero"><h2>Heading</h2></section>\n',
        encoding="utf-8",
    )
    work.write_text(
        '<section id="work" data-content-id="home:work"><h1>Wrong owner</h1></section>\n',
        encoding="utf-8",
    )
    paths = [
        "src/routes/home/sections/Hero.tsx",
        "src/routes/home/sections/Work.tsx",
    ]
    kwargs = {
        "route_id": "home",
        "section_ids": ["home:hero", "home:work"],
        "section_selectors_by_section": {
            "home:hero": "#hero",
            "home:work": "#work",
        },
        "h1_owner_section_id": "home:hero",
        "work_unit_id": "route-home-batch-1",
    }

    diagnostics = validate_route_batch_contract(tmp_path, paths, **kwargs)
    assert {item.code for item in diagnostics} == {"SOURCE_ROUTE_BATCH_H1_OWNERSHIP_INVALID"}

    hero.write_text(
        '<section id="hero" data-content-id="home:hero"><h1>Heading</h1></section>\n',
        encoding="utf-8",
    )
    work.write_text(
        '<section id="work" data-content-id="home:work"><h2>Work</h2></section>\n',
        encoding="utf-8",
    )
    assert not validate_route_batch_contract(tmp_path, paths, **kwargs)


def test_validate_route_batch_contract_rejects_aggregated_sections(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    (section / "Hero.tsx").write_text(
        '<section id="home:hero" data-content-id="home:hero" />\n'
        '<section id="home:selected-work" data-content-id="home:selected-work" />\n',
        encoding="utf-8",
    )
    (section / "SelectedWork.tsx").write_text(
        "export default function SelectedWork() { return null; }\n",
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        [
            "src/routes/home/sections/Hero.tsx",
            "src/routes/home/sections/SelectedWork.tsx",
        ],
        route_id="home",
        section_ids=["home:hero", "home:selected-work"],
        work_unit_id="route-home-batch-1",
    )

    assert {item.code for item in diagnostics} == {"SOURCE_ROUTE_BATCH_SECTION_OWNERSHIP_INVALID"}


def test_route_batch_contract_checks_owned_content_and_interactions(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    hero = section / "Hero.tsx"
    hero.write_text(
        """const contentValue = (key: string) => key;
export default function Hero() {
  return <section id="hero" data-content-id="home:hero">
    <a data-interaction-id="interaction:home:hero:contact">
      {contentValue("content:home:hero:headline")}
    </a>
  </section>;
}
""",
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        ["src/routes/home/sections/Hero.tsx"],
        route_id="home",
        section_ids=["home:hero"],
        content_ids_by_section={
            "home:hero": ["content:home:hero:headline", "content:home:hero:kind"]
        },
        section_selectors_by_section={"home:hero": "#hero"},
        interaction_ids=["interaction:home:hero:contact"],
        interaction_markers={"interaction:home:hero:contact": 'data-interaction="hero-contact"'},
        work_unit_id="route-home-batch-1",
    )

    assert {item.code for item in diagnostics} == {
        "SOURCE_ROUTE_BATCH_CONTENT_KEY_MISSING",
        "SOURCE_ROUTE_BATCH_INTERACTION_MARKER_MISSING",
        "SOURCE_ROUTE_BATCH_INTERACTION_OUTCOME_MISSING",
    }

    hero.write_text(
        """const contentValue = (key: string) => key;
export default function Hero() {
  return <section id="hero" data-content-id="home:hero">
    <a href="#contact" data-interaction-id="interaction:home:hero:contact"
       data-interaction="hero-contact"
       data-content-kind={contentValue("content:home:hero:kind")}>
      {contentValue("content:home:hero:headline")}
    </a>
  </section>;
}
""",
        encoding="utf-8",
    )

    assert not validate_route_batch_contract(
        tmp_path,
        ["src/routes/home/sections/Hero.tsx"],
        route_id="home",
        section_ids=["home:hero"],
        content_ids_by_section={
            "home:hero": ["content:home:hero:headline", "content:home:hero:kind"]
        },
        section_selectors_by_section={"home:hero": "#hero"},
        interaction_ids=["interaction:home:hero:contact"],
        interaction_markers={"interaction:home:hero:contact": 'data-interaction="hero-contact"'},
        work_unit_id="route-home-batch-1",
    )


def test_route_batch_contract_requires_materialized_images_motion_and_state(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    hero = section / "Hero.tsx"
    css = section / "Hero.css"
    hero.write_text(
        """export default function Hero() {
  return <section id="hero" data-content-id="home:hero">
    <a href="#selected-work" data-interaction-id="interaction:hero"
       data-interaction="hero-primary">Work</a>
    <div data-motion-target="hero-copy" />
  </section>;
}
""",
        encoding="utf-8",
    )
    css.write_text("#hero .hero-copy { opacity: 1; }\n", encoding="utf-8")
    common = {
        "route_id": "home",
        "section_ids": ["home:hero"],
        "section_selectors_by_section": {"home:hero": "#hero"},
        "interaction_ids": ["interaction:hero"],
        "interaction_markers": {"interaction:hero": 'data-interaction="hero-primary"'},
        "interaction_contracts": {
            "interaction:hero": {
                "expected_navigation": "#selected-work",
                "expected_state_attribute": "aria-current",
                "expected_state_value": "page",
            }
        },
        "image_assets_by_slot": {
            "slot-hero": {
                "sizes": "(max-width: 720px) 100vw, 60vw",
                "loading": "eager",
                "fit": "cover",
                "focal_position": "center center",
                "alt_policy": "decorative",
                "element_marker": 'data-resource="hero-atmosphere"',
                "sources": [
                    {
                        "path": "resources/renditions/hero/hero-480w.webp",
                        "width": 480,
                        "height": 320,
                        "format": "webp",
                    },
                    {
                        "path": "resources/renditions/hero/hero-960w.webp",
                        "width": 960,
                        "height": 640,
                        "format": "webp",
                    },
                ],
            }
        },
        "motion_beats": [
            {
                "motion_id": "motion:hero",
                "section_id": "home:hero",
                "target_marker": 'data-motion-target="hero-copy"',
                "target_selector": "#hero .hero-copy",
                "trigger": "viewport",
                "changed_properties": [
                    {
                        "property_name": "opacity",
                        "before_value": "0",
                        "after_value": "1",
                    },
                    {
                        "property_name": "transform",
                        "before_value": "translateY(12px)",
                        "after_value": "translateY(0)",
                    },
                ],
            }
        ],
        "work_unit_id": "route-home-batch-1",
    }

    diagnostics = validate_route_batch_contract(
        tmp_path,
        [
            "src/routes/home/sections/Hero.tsx",
            "src/routes/home/sections/Hero.css",
        ],
        **common,
    )
    assert {item.code for item in diagnostics} == {
        "SOURCE_ROUTE_BATCH_IMAGE_BINDING_INVALID",
        "SOURCE_ROUTE_BATCH_INTERACTION_STATE_MISSING",
        "SOURCE_ROUTE_BATCH_MOTION_INVALID",
    }
    motion_diagnostic = next(
        item for item in diagnostics if item.code == "SOURCE_ROUTE_BATCH_MOTION_INVALID"
    )
    assert motion_diagnostic.file == "src/routes/home/sections/Hero.css"
    assert "src/routes/home/sections/Hero.tsx" in motion_diagnostic.normalized_message
    assert "src/routes/home/sections/Hero.css" in motion_diagnostic.normalized_message

    hero.write_text(
        """const observer = new IntersectionObserver(() => undefined);
const section = document.querySelector("#hero");
if (section && "IntersectionObserver" in window) {
  section.setAttribute("data-motion-ready", "true");
}
export default function Hero() {
  return <section id="hero" data-content-id="home:hero">
    <a href="#selected-work" aria-current="page"
       data-interaction-id="interaction:hero" data-interaction="hero-primary">Work</a>
    <div className="hero-copy" data-motion-target="hero-copy"
         data-resource="hero-atmosphere">
      <LocalImage resourceId="slot-hero"
        sizes="(max-width: 720px) 100vw, 60vw" loading="eager"
        fit="cover" focalPosition="center center" alt="" />
    </div>
  </section>;
}
""",
        encoding="utf-8",
    )
    css.write_text(
        """#hero .hero-copy { opacity: 1; transform: translateY(0); }
[data-motion-ready="true"] #hero .hero-copy { opacity: 0; transform: translateY(12px); }
[data-motion-ready="true"] #hero .hero-copy.is-visible { opacity: 1; transform: translateY(0); }
@media (prefers-reduced-motion: reduce) {
  #hero .hero-copy { opacity: 1; transform: translateY(0); }
}
""",
        encoding="utf-8",
    )

    assert not validate_route_batch_contract(
        tmp_path,
        [
            "src/routes/home/sections/Hero.tsx",
            "src/routes/home/sections/Hero.css",
        ],
        **common,
    )

    hero.write_text(
        hero.read_text(encoding="utf-8").replace('alt="" />', 'alt="" sources={[]} />'),
        encoding="utf-8",
    )
    diagnostics = validate_route_batch_contract(
        tmp_path,
        [
            "src/routes/home/sections/Hero.tsx",
            "src/routes/home/sections/Hero.css",
        ],
        **common,
    )
    assert [item.code for item in diagnostics] == ["SOURCE_ROUTE_BATCH_IMAGE_BINDING_INVALID"]
    assert "sources prop must be omitted" in diagnostics[0].normalized_message

    hero.write_text(
        hero.read_text(encoding="utf-8")
        .replace(" sources={[]}", "")
        .replace(' data-resource="hero-atmosphere"', "")
        .replace("export default", '// data-resource="hero-atmosphere"\nexport default'),
        encoding="utf-8",
    )
    diagnostics = validate_route_batch_contract(
        tmp_path,
        [
            "src/routes/home/sections/Hero.tsx",
            "src/routes/home/sections/Hero.css",
        ],
        **common,
    )
    assert [item.code for item in diagnostics] == ["SOURCE_ROUTE_BATCH_IMAGE_BINDING_INVALID"]
    assert 'data-resource="hero-atmosphere"' in diagnostics[0].normalized_message


def test_route_batch_disclosure_accepts_boolean_state_and_reports_its_owner(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    experience_path = "src/routes/home/sections/Experience.tsx"
    design_path = "src/routes/home/sections/DesignSystems.tsx"
    experience = tmp_path / experience_path
    design = tmp_path / design_path
    experience.write_text(
        'export default function Experience() { return <section id="experience" '
        'data-content-id="home:experience" />; }\n',
        encoding="utf-8",
    )
    valid_design = """export default function DesignSystems() {
  const expanded = true;
  const toggle = () => undefined;
  return <section id="design-systems" data-content-id="home:design-systems">
    <button type="button" aria-expanded={expanded}
      data-capability-disclosure
      data-interaction-id="interaction:home:design-systems:capabilities"
      data-interaction="capability-grouping" onClick={toggle}>Capabilities</button>
  </section>;
}
"""
    design.write_text(valid_design, encoding="utf-8")
    common = {
        "route_id": "home",
        "section_ids": ["home:experience", "home:design-systems"],
        "section_selectors_by_section": {
            "home:experience": "#experience",
            "home:design-systems": "#design-systems",
        },
        "interaction_ids": ["interaction:home:design-systems:capabilities"],
        "interaction_markers": {
            "interaction:home:design-systems:capabilities": (
                'data-interaction="capability-grouping"'
            )
        },
        "interaction_contracts": {
            "interaction:home:design-systems:capabilities": {
                "target_selector": "#design-systems [data-capability-disclosure]",
                "trigger": "disclosure",
                "expected_navigation": "No navigation; remain on home.",
                "expected_state_attribute": "aria-expanded",
                "expected_state_value": "true or false",
            }
        },
        "work_unit_id": "route-home-batch-2",
    }

    assert not validate_route_batch_contract(tmp_path, [experience_path, design_path], **common)

    design.write_text(valid_design.replace(" aria-expanded={expanded}", ""), encoding="utf-8")
    diagnostics = validate_route_batch_contract(tmp_path, [experience_path, design_path], **common)

    assert [item.code for item in diagnostics] == ["SOURCE_ROUTE_BATCH_INTERACTION_STATE_MISSING"]
    assert diagnostics[0].file == design_path


def test_route_batch_motion_diagnostic_names_the_beat_owner_stylesheet(tmp_path) -> None:
    sections = tmp_path / "src" / "routes" / "home" / "sections"
    sections.mkdir(parents=True)
    hero = sections / "Hero.tsx"
    selected = sections / "SelectedWork.tsx"
    hero_css = sections / "Hero.css"
    selected_css = sections / "SelectedWork.css"
    hero.write_text(
        'export default function Hero() { return <section id="hero" '
        'data-route-id="home" data-content-id="home:hero" />; }\n',
        encoding="utf-8",
    )
    selected.write_text(
        """const observer = new IntersectionObserver(() => undefined);
const section = document.querySelector("#selected-work");
if (section && "IntersectionObserver" in window) {
  section.setAttribute("data-motion-ready", "true");
}
export default function SelectedWork() {
  return <section id="selected-work" data-content-id="home:selected-work">
    <div className="lead-project" data-motion-target="lead-panels" />
  </section>;
}
""",
        encoding="utf-8",
    )
    hero_css.write_text("#hero { display: block; }\n", encoding="utf-8")
    selected_css.write_text(
        """#selected-work .lead-project { opacity: 1; }
#selected-work .lead-project.is-visible { opacity: 1; }
@media (prefers-reduced-motion: reduce) {
  #selected-work .lead-project { opacity: 1; }
}
""",
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        [
            "src/routes/home/sections/Hero.tsx",
            "src/routes/home/sections/Hero.css",
            "src/routes/home/sections/SelectedWork.tsx",
            "src/routes/home/sections/SelectedWork.css",
        ],
        route_id="home",
        section_ids=["home:hero", "home:selected-work"],
        section_selectors_by_section={
            "home:hero": "#hero",
            "home:selected-work": "#selected-work",
        },
        motion_beats=[
            {
                "motion_id": "motion:selected-work",
                "section_id": "home:selected-work",
                "target_marker": 'data-motion-target="lead-panels"',
                "target_selector": "#selected-work .lead-project",
                "trigger": "viewport",
                "changed_properties": [
                    {
                        "property_name": "opacity",
                        "before_value": "0",
                        "after_value": "1",
                    }
                ],
            }
        ],
        work_unit_id="route-home-batch-1",
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "SOURCE_ROUTE_BATCH_MOTION_INVALID"
    assert diagnostics[0].file == "src/routes/home/sections/SelectedWork.css"
    assert 'guarded [data-motion-ready="true"] opacity: 0' in (diagnostics[0].normalized_message)


def test_route_composer_contract_requires_complete_section_navigation(tmp_path) -> None:
    route = tmp_path / "src" / "routes" / "home"
    route.mkdir(parents=True)
    index = route / "index.tsx"
    index.write_text(
        'export default function Home() { return <RouteShell routeId="home" />; }\n',
        encoding="utf-8",
    )
    kwargs = {
        "section_selectors_by_section": {
            "home:hero": "#hero",
            "home:selected-work": "#selected-work",
        },
        "work_unit_id": "route-home-compose",
    }

    diagnostics = validate_route_composer_contract(
        tmp_path, ["src/routes/home/index.tsx"], **kwargs
    )
    assert diagnostics[0].code == "SOURCE_ROUTE_COMPOSER_NAVIGATION_MISSING"

    index.write_text(
        """export default function Home() {
  const navigation = <nav><a href="#hero">Home</a><a href="#selected-work">Work</a></nav>;
  return <RouteShell routeId="home" navigation={navigation} />;
}
""",
        encoding="utf-8",
    )
    assert not validate_route_composer_contract(tmp_path, ["src/routes/home/index.tsx"], **kwargs)


def test_stale_route_batch_checkpoint_reopens_route_composition(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    source = section / "Hero.tsx"
    source.write_text(
        'import { contentValue } from "../../../../content/generated-content";\n',
        encoding="utf-8",
    )
    batch = SimpleNamespace(
        unit_id="route-home-batch-1",
        kind="route_batch",
        owns_paths=["src/routes/home/sections/Hero.tsx"],
    )
    composer = SimpleNamespace(
        unit_id="route-home-compose",
        kind="route_compose",
        owns_paths=["src/routes/home/index.tsx"],
    )
    projection = SimpleNamespace(
        accepted_checkpoint=object(),
        work_units=[
            SimpleNamespace(
                unit_id=batch.unit_id,
                kind=batch.kind,
                status="checkpointed",
                checkpoint_after="old",
                call_receipt_id="old-call",
                repair_round=2,
            ),
            SimpleNamespace(
                unit_id=composer.unit_id,
                kind=composer.kind,
                status="model_requested",
                checkpoint_after="",
                call_receipt_id="",
                repair_round=1,
            ),
        ],
        phase="generating_routes",
        active_work_unit_id=composer.unit_id,
        source_ready=False,
        source_file_count=0,
        source_total_bytes=0,
    )
    plan = SimpleNamespace(work_graph=SimpleNamespace(units=[batch, composer]))

    diagnostics = _invalidate_stale_route_batch_checkpoint(
        projection,
        plan=plan,
        workspace=SimpleNamespace(repo_dir=tmp_path),
    )

    assert diagnostics and diagnostics[0].code == "SOURCE_LOCAL_IMPORT_MISSING"
    assert all(item.status == "pending" for item in projection.work_units)
    assert all(item.checkpoint_after == "" for item in projection.work_units)
    assert all(item.call_receipt_id == "" for item in projection.work_units)


def test_route_contract_normalizer_deduplicates_markers_and_restores_heading(tmp_path) -> None:
    route_dir = tmp_path / "src" / "routes" / "home"
    route_dir.mkdir(parents=True)
    route_file = route_dir / "index.tsx"
    route_file.write_text(
        """
<nav><a data-interaction-id="interaction:home:explore">Hidden</a></nav>
<main>
  <section data-content-id="home:capabilities"><h2>Tools</h2></section>
  <a data-interaction-id="interaction:home:explore">Visible</a>
</main>
""",
        encoding="utf-8",
    )

    changed = normalize_generated_route_contract(
        tmp_path,
        plan=SimpleNamespace(
            interactions=[
                SimpleNamespace(
                    interaction_id="interaction:home:explore",
                    route_id="home",
                    accessible_name="Explore selected work",
                )
            ]
        ),
        site_contract={
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "public_content": [
                {
                    "route_id": "home",
                    "sections": [
                        {
                            "section_id": "home:capabilities",
                            "content": {"heading": "Capabilities"},
                        }
                    ],
                }
            ],
        },
    )

    updated = route_file.read_text(encoding="utf-8")
    assert changed
    assert updated.count('data-interaction-id="interaction:home:explore"') == 1
    assert 'aria-label="Explore selected work"' in updated
    assert "<h2>Capabilities</h2>" in updated


def test_route_contract_normalizer_disambiguates_indexed_reusable_controls(tmp_path) -> None:
    route_dir = tmp_path / "src" / "routes" / "home"
    route_dir.mkdir(parents=True)
    route_file = route_dir / "sections.tsx"
    route_file.write_text(
        """
function CapabilityToggle({ groupIndex }: { groupIndex: number }) {
  return <button data-interaction-id="interaction:home:capability">Show more</button>;
}
""",
        encoding="utf-8",
    )

    changed = normalize_generated_route_contract(
        tmp_path,
        plan=SimpleNamespace(
            interactions=[
                SimpleNamespace(
                    interaction_id="interaction:home:capability",
                    route_id="home",
                    accessible_name="Show more",
                )
            ]
        ),
        site_contract={
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "public_content": [],
        },
    )

    updated = route_file.read_text(encoding="utf-8")
    assert changed
    assert (
        'data-interaction-id={groupIndex === 0 ? "interaction:home:capability" : undefined}'
        in updated
    )
    assert "OryxenAI interaction marker: interaction:home:capability" in updated


def test_route_contract_normalizer_adds_escape_close_to_stateful_trigger(tmp_path) -> None:
    route_dir = tmp_path / "src" / "routes" / "home"
    route_dir.mkdir(parents=True)
    route_file = route_dir / "index.tsx"
    route_file.write_text(
        """
function SiteNav() {
  const [open, setOpen] = useState(false);
  return <button aria-expanded={open} data-interaction-id="interaction:home:nav-toggle" onClick={() => setOpen((value) => !value)}>Menu</button>;
}
""",
        encoding="utf-8",
    )

    changed = normalize_generated_route_contract(
        tmp_path,
        plan=SimpleNamespace(
            interactions=[
                SimpleNamespace(
                    interaction_id="interaction:home:nav-toggle",
                    route_id="home",
                    accessible_name="Open navigation menu",
                    keyboard_behavior="Enter/Space/Escape; Escape closes and returns focus.",
                )
            ]
        ),
        site_contract={
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "public_content": [],
        },
    )

    updated = route_file.read_text(encoding="utf-8")
    assert changed
    assert 'if (event.key === "Escape")' in updated
    assert "setOpen(false)" in updated


def test_route_contract_normalizer_recovers_legacy_malformed_escape_patch(tmp_path) -> None:
    route_dir = tmp_path / "src" / "routes" / "home"
    route_dir.mkdir(parents=True)
    route_file = route_dir / "index.tsx"
    route_file.write_text(
        """
function SiteNav() {
  const [open, setOpen] = useState(false);
  return <button aria-expanded={open} data-interaction-id="interaction:home:nav-toggle"
    onClick={() = onKeyDown={(event) => { if (event.key === "Escape") { setOpen(false); } }}> setOpen((value) => !value)}>
    Menu
  </button>;
}
""",
        encoding="utf-8",
    )

    changed = normalize_generated_route_contract(
        tmp_path,
        plan=SimpleNamespace(
            interactions=[
                SimpleNamespace(
                    interaction_id="interaction:home:nav-toggle",
                    route_id="home",
                    accessible_name="Open navigation menu",
                    keyboard_behavior="Escape closes and returns focus.",
                )
            ]
        ),
        site_contract={
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "public_content": [],
        },
    )

    updated = route_file.read_text(encoding="utf-8")
    assert changed
    assert "onClick={() => setOpen((value) => !value)}" in updated
    assert updated.count("onKeyDown={(event) =>") == 1
