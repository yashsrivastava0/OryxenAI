from types import SimpleNamespace

from oryxenai.agents.code_generator.core.development_schemas import (
    GenerationChanges,
    SourceFileChange,
)
from oryxenai.agents.code_generator.core.generation_orchestrator import (
    _invalidate_stale_route_batch_checkpoint,
)
from oryxenai.agents.code_generator.core.source_validation import (
    _canonical_visible_text,
    normalize_generated_route_contract,
    normalize_route_batch_motion_changes,
    normalize_route_batch_motion_sources,
    normalize_route_batch_selected_work_sources,
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


def test_route_batch_contract_names_near_miss_content_key_for_repair(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    path = "src/routes/home/sections/Featured.tsx"
    expected = "content:home:featured:summary-7620e261"
    near_miss = "content:home:featured:summary-7620ec24"
    (tmp_path / path).write_text(
        f'''const contentValue = (key: string) => key;
export default function Featured() {{
  return <section id="featured" data-content-id="home:featured">
    <p>{{contentValue("{near_miss}")}}</p>
  </section>;
}}
''',
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        [path],
        route_id="home",
        section_ids=["home:featured"],
        content_ids_by_section={"home:featured": [expected]},
        section_selectors_by_section={"home:featured": "#featured"},
        work_unit_id="route-home-batch-1",
    )

    missing = [
        item for item in diagnostics if item.code == "SOURCE_ROUTE_BATCH_CONTENT_KEY_MISSING"
    ]
    assert len(missing) == 1
    assert expected in missing[0].normalized_message
    assert near_miss in missing[0].normalized_message


def test_route_batch_contract_accepts_content_ids_mapped_from_a_literal_array(tmp_path) -> None:
    """Live-discovered 2026-09: an approved key rendered via a statically
    known `const IDS = ["a", "b"]; IDS.map(id => contentValue(id))` array is
    a genuine, safe binding -- scripts/audit-source.mjs's real TS-AST check
    already resolves it (staticLiteralValue's mappedCollection branch), but
    this Python-side pre-toolchain gate used to demand the literal call
    verbatim and reject it before npm's real check ever ran."""

    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    hero = section / "Hero.tsx"
    hero.write_text(
        """const contentValue = (key: string) => key;
const CARD_IDS = ["content:home:hero:headline", "content:home:hero:kind"];
export default function Hero() {
  return <section id="hero" data-content-id="home:hero">
    <a data-interaction-id="interaction:home:hero:contact"
       data-interaction="hero-contact">
      {CARD_IDS.map((id) => <span key={id}>{contentValue(id)}</span>)}
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

    assert not any(item.code == "SOURCE_ROUTE_BATCH_CONTENT_KEY_MISSING" for item in diagnostics)


def test_route_batch_contract_accepts_literal_object_and_tuple_maps(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    path = "src/routes/home/sections/Featured.tsx"
    expected_name = "content:home:featured:name-7620e261"
    expected_tag = "content:home:featured:tag-2db10e4a"
    expected_body = "content:home:featured:body-b221191c"
    (tmp_path / path).write_text(
        f'''const contentValue = (key: string) => key;
const cards = [{{ name: "{expected_name}", tags: ["{expected_tag}"] }}] as const;
const rows = [["{expected_body}", "unused"]] as const;
export default function Featured() {{
  return <section id="featured" data-content-id="home:featured">
    {{cards.map((card) => <p>{{contentValue(card.name)}}{{card.tags.map((tag) => contentValue(tag))}}</p>)}}
    {{rows.map(([body, _unused]) => <p>{{contentValue(body)}}</p>)}}
  </section>;
}}
''',
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        [path],
        route_id="home",
        section_ids=["home:featured"],
        content_ids_by_section={"home:featured": [expected_name, expected_tag, expected_body]},
        section_selectors_by_section={"home:featured": "#featured"},
        work_unit_id="route-home-batch-1",
    )

    assert not any(item.code == "SOURCE_ROUTE_BATCH_CONTENT_KEY_MISSING" for item in diagnostics)


def test_route_batch_contract_accepts_indexed_tuple_maps(tmp_path) -> None:
    """Generated section rows may pass approved tuple cells by index."""

    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    path = "src/routes/home/sections/Experience.tsx"
    values = [
        "content:home:experience:dates-12345678",
        "content:home:experience:description-23456789",
        "content:home:experience:organization-3456789a",
        "content:home:experience:role-456789ab",
    ]
    (tmp_path / path).write_text(
        f"""const contentValue = (key: string) => key;
const entries = [[{", ".join(f'"{value}"' for value in values)}]] as const;
export default function Experience() {{
  return <section id="experience" data-content-id="home:experience">
    {{entries.map((item, index) => <article key={{index}}>
      <time>{{contentValue(item[0])}}</time>
      <p>{{contentValue(item[1])}}</p>
      <p>{{contentValue(item[2])}}</p>
      <p>{{contentValue(item[3])}}</p>
    </article>)}}
  </section>;
}}
""",
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        [path],
        route_id="home",
        section_ids=["home:experience"],
        content_ids_by_section={"home:experience": values},
        section_selectors_by_section={"home:experience": "#experience"},
        work_unit_id="route-home-batch-1",
    )

    assert not any(item.code == "SOURCE_ROUTE_BATCH_CONTENT_KEY_MISSING" for item in diagnostics)


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


def test_route_batch_rejects_empty_disclosure_panel(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    education_path = "src/routes/home/sections/Education.tsx"
    education = tmp_path / education_path
    education.write_text(
        """export default function Education() {
  return <section id=\"education\" data-content-id=\"home:education\">
    <Disclosure label=\"Details\"><span aria-hidden=\"true\" /></Disclosure>
  </section>;
}
""",
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        [education_path],
        route_id="home",
        section_ids=["home:education"],
        section_selectors_by_section={"home:education": "#education"},
        work_unit_id="route-home-batch-2",
    )

    assert [item.code for item in diagnostics] == ["SOURCE_NONINFORMATIVE_DISCLOSURE"]
    assert diagnostics[0].file == education_path
    assert diagnostics[0].line == 3

    # The integration workflow keeps this observation available to the model
    # review, but does not spend a source-repair round on an optional panel.
    assert not any(
        item.code == "SOURCE_NONINFORMATIVE_DISCLOSURE"
        for item in validate_route_batch_contract(
            tmp_path,
            [education_path],
            route_id="home",
            section_ids=["home:education"],
            section_selectors_by_section={"home:education": "#education"},
            work_unit_id="route-home-batch-2",
            include_noninformative_disclosures=False,
        )
    )
    education.write_text(
        education.read_text(encoding="utf-8").replace(
            '<span aria-hidden="true" />',
            '{contentValue("content:home:education:details-abc123")}',
        ),
        encoding="utf-8",
    )
    assert not any(
        item.code == "SOURCE_NONINFORMATIVE_DISCLOSURE"
        for item in validate_route_batch_contract(
            tmp_path,
            [education_path],
            route_id="home",
            section_ids=["home:education"],
            section_selectors_by_section={"home:education": "#education"},
            work_unit_id="route-home-batch-2",
        )
    )


def test_route_batch_rejects_approved_content_hidden_in_unplanned_disclosure(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    path = "src/routes/home/sections/Experience.tsx"
    content_id = "content:home:experience:leadership-9e720e53"
    (tmp_path / path).write_text(
        f'''export default function Experience() {{
  return <section id="experience" data-content-id="home:experience">
    <Disclosure label="Read leadership context">
      <p>{{contentValue("{content_id}")}}</p>
    </Disclosure>
  </section>;
}}
''',
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        [path],
        route_id="home",
        section_ids=["home:experience"],
        content_ids_by_section={"home:experience": [content_id]},
        section_selectors_by_section={"home:experience": "#experience"},
        interaction_ids=[],
        work_unit_id="route-home-batch-1",
    )

    hidden = [item for item in diagnostics if item.code == "SOURCE_HIDDEN_APPROVED_CONTENT"]
    assert len(hidden) == 1
    assert content_id in hidden[0].normalized_message
    assert hidden[0].file == path


def test_route_batch_allows_visible_duplicate_or_planned_disclosure_content(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    path = "src/routes/home/sections/Experience.tsx"
    content_id = "content:home:experience:leadership-9e720e53"
    (tmp_path / path).write_text(
        f'''export default function Experience() {{
  return <section id="experience" data-content-id="home:experience">
    <p>{{contentValue("{content_id}")}}</p>
    <Disclosure label="Read leadership context">
      <p>{{contentValue("{content_id}")}}</p>
    </Disclosure>
  </section>;
}}
''',
        encoding="utf-8",
    )
    common = {
        "route_id": "home",
        "section_ids": ["home:experience"],
        "content_ids_by_section": {"home:experience": [content_id]},
        "section_selectors_by_section": {"home:experience": "#experience"},
        "interaction_ids": [],
        "work_unit_id": "route-home-batch-1",
    }

    assert not any(
        item.code == "SOURCE_HIDDEN_APPROVED_CONTENT"
        for item in validate_route_batch_contract(tmp_path, [path], **common)
    )

    planned = (
        (tmp_path / path)
        .read_text(encoding="utf-8")
        .replace(
            '<Disclosure label="Read leadership context">',
            '<Disclosure label="Read leadership context" '
            'data-interaction-id="interaction:home:experience:leadership">',
        )
    )
    (tmp_path / path).write_text(planned, encoding="utf-8")
    common["interaction_ids"] = ["interaction:home:experience:leadership"]
    assert not any(
        item.code == "SOURCE_HIDDEN_APPROVED_CONTENT"
        for item in validate_route_batch_contract(tmp_path, [path], **common)
    )


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


def test_route_batch_contract_accepts_a_trusted_reveal_pattern_with_no_hand_authored_css(
    tmp_path,
) -> None:
    """Live-discovered 2026-09: a beat bound to a catalogue pattern_id
    delegates its entire animation (opacity/transform states, reduced
    motion, data-motion-ready wiring) to motion.css/SharedSystems.tsx --
    trusted files never included in a section's own owned source. The old
    checker demanded those implementation details verbatim in the section's
    own files regardless of pattern_id, so a correct, trusted <Reveal>
    usage with no hand-authored animation was always rejected."""

    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    hero = section / "Hero.tsx"
    hero.write_text(
        """import { Reveal } from "../../../components/generated/SharedSystems";
export default function Hero() {
  return <section id="hero" data-content-id="home:hero">
    <Reveal data-motion-target="hero-copy">
      <h1>Approved headline</h1>
    </Reveal>
  </section>;
}
""",
        encoding="utf-8",
    )
    hero_css = section / "Hero.css"
    hero_css.write_text(
        '#hero [data-motion-target="hero-copy"] { max-width: 60ch; }\n', encoding="utf-8"
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        ["src/routes/home/sections/Hero.tsx", "src/routes/home/sections/Hero.css"],
        route_id="home",
        section_ids=["home:hero"],
        section_selectors_by_section={"home:hero": "#hero"},
        motion_beats=[
            {
                "motion_id": "motion:hero",
                "section_id": "home:hero",
                "target_marker": 'data-motion-target="hero-copy"',
                "target_selector": '#hero [data-motion-target="hero-copy"]',
                "trigger": "viewport",
                "pattern_id": "reveal-fade-rise",
                "changed_properties": [
                    {"property_name": "opacity", "before_value": "0", "after_value": "1"}
                ],
            }
        ],
        work_unit_id="route-home-batch-1",
    )

    assert not any(item.code == "SOURCE_ROUTE_BATCH_MOTION_INVALID" for item in diagnostics)


def test_route_batch_motion_accepts_css_id_selector_from_jsx_id(tmp_path) -> None:
    """A CSS ``#id`` target may be proven by the owner JSX id attribute."""

    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    path = "src/routes/home/sections/Featured.tsx"
    (tmp_path / path).write_text(
        """import { Reveal } from "../../../components/generated/SharedSystems";
export default function Featured() {
  return <Reveal id="featured-projects" data-content-id="home:featured-projects"
    data-motion="projects-orientation"><p>Approved</p></Reveal>;
}
""",
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        [path],
        route_id="home",
        section_ids=["home:featured-projects"],
        section_selectors_by_section={"home:featured-projects": "#featured-projects"},
        motion_beats=[
            {
                "motion_id": "motion:home:projects-orientation",
                "section_id": "home:featured-projects",
                "target_marker": 'data-motion="projects-orientation"',
                "target_selector": "#featured-projects",
                "pattern_id": "reveal-fade-rise",
            }
        ],
        work_unit_id="route-home-batch-1",
    )

    assert not any(item.code == "SOURCE_ROUTE_BATCH_MOTION_INVALID" for item in diagnostics)


def test_route_batch_motion_accepts_a_static_conditional_marker(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    path = "src/routes/home/sections/Experience.tsx"
    css_path = "src/routes/home/sections/Experience.css"
    (tmp_path / path).write_text(
        """const entries = [\"current\", \"previous\"] as const;
const observer = new IntersectionObserver(() => undefined);
export default function Experience() {
  return <section id="experience" data-content-id="home:experience">
    {entries.map((entry, index) => <article data-motion={index === 0 ? "current-role" : undefined}>{entry}</article>)}
  </section>;
}
""",
        encoding="utf-8",
    )
    (tmp_path / css_path).write_text(
        """#experience [data-motion="current-role"] { border-color: var(--color-accent-mark); transform: translateX(0); }
#experience [data-motion-ready="true"][data-motion="current-role"] { border-color: var(--color-line-subtle); transform: translateX(-8px); transition: border-color 240ms ease-out, transform 240ms ease-out; }
@media (prefers-reduced-motion: reduce) { #experience [data-motion="current-role"] { border-color: var(--color-accent-mark); transform: translateX(0); transition: none; } }
""",
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        [path, css_path],
        route_id="home",
        section_ids=["home:experience"],
        section_selectors_by_section={"home:experience": "#experience"},
        motion_beats=[
            {
                "motion_id": "motion:home:experience:current-role",
                "section_id": "home:experience",
                "target_marker": 'data-motion="current-role"',
                "target_selector": '#experience [data-motion="current-role"]',
                "trigger": "viewport",
                "changed_properties": [
                    {
                        "property_name": "border-color",
                        "before_value": "line-subtle",
                        "after_value": "accent-mark",
                    },
                    {
                        "property_name": "transform",
                        "before_value": "translateX(-8px)",
                        "after_value": "translateX(0)",
                    },
                ],
            }
        ],
        work_unit_id="route-home-batch-1",
    )

    assert not any(item.code == "SOURCE_ROUTE_BATCH_MOTION_INVALID" for item in diagnostics)


def test_route_batch_motion_normalizer_repairs_live_shaped_route_sources(tmp_path) -> None:
    """Keep mechanically checkable route motion defects out of model repair."""

    sections = tmp_path / "src" / "routes" / "home" / "sections"
    sections.mkdir(parents=True)
    sources = {
        "src/routes/home/sections/Hero.tsx": """export default function Hero() {
  return <section id="hero" data-content-id="home:hero">
    <Reveal data-motion="hero-text" />
  </section>;
}
""",
        "src/routes/home/sections/Hero.css": """#hero { max-width: fiftych; }
.home-hero__copy { max-width: sixtyfivech; }
""",
        "src/routes/home/sections/SelectedWork.tsx": """import { useEffect, useRef, useState } from "react";

export default function SelectedWork() {
  const ref = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") {
      setReady(true);
      return;
    }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setReady(true);
        observer.disconnect();
      }
    });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return <section id="selected-work" data-content-id="home:selected-work">
    <div ref={ref} data-motion="work-marker" className="home-work__marker" />
  </section>;
}
""",
        "src/routes/home/sections/SelectedWork.css": """#selected-work [data-motion="work-marker"] {
  opacity: 1;
  transform: translateX(0);
}
#selected-work:has(.work-ready) [data-motion="work-marker"] {
  opacity: 1;
}
""",
    }
    beats = [
        {
            "motion_id": "motion:home:hero:reveal",
            "section_id": "home:hero",
            "target_marker": 'data-motion="hero-text"',
            "target_selector": '#hero [data-motion="hero-text"]',
            "trigger": "viewport",
            "pattern_id": "reveal-fade-rise",
            "changed_properties": [
                {"property_name": "opacity", "before_value": "0", "after_value": "1"}
            ],
        },
        {
            "motion_id": "motion:home:selected-work:orientation",
            "section_id": "home:selected-work",
            "target_marker": 'data-motion="work-marker"',
            "target_selector": '#selected-work [data-motion="work-marker"]',
            "trigger": "viewport",
            "trigger_selector": "#selected-work",
            "changed_properties": [
                {"property_name": "opacity", "before_value": "0", "after_value": "1"},
                {
                    "property_name": "transform",
                    "before_value": "translateX(-12px)",
                    "after_value": "translateX(0)",
                },
            ],
        },
    ]

    changes = GenerationChanges(
        files=[
            SourceFileChange(path=path, operation="create", complete_utf8_content=body)
            for path, body in sources.items()
        ]
    )
    assert normalize_route_batch_motion_changes(changes, motion_beats=beats)
    sources = {change.path: change.complete_utf8_content for change in changes.files}
    assert "fiftych" not in sources["src/routes/home/sections/Hero.css"]
    assert "max-width: 50ch" in sources["src/routes/home/sections/Hero.css"]
    assert "max-width: 65ch" in sources["src/routes/home/sections/Hero.css"]
    assert '#hero [data-motion="hero-text"] {}' in sources["src/routes/home/sections/Hero.css"]
    selected_source = sources["src/routes/home/sections/SelectedWork.tsx"]
    assert "useEffect" in selected_source
    assert "IntersectionObserver" in selected_source
    assert 'setAttribute("data-motion-ready", "true")' in selected_source
    selected_styles = sources["src/routes/home/sections/SelectedWork.css"]
    assert '#selected-work [data-motion="work-marker"] {' in selected_styles
    assert '[data-motion-ready="true"]' in selected_styles
    assert "opacity: 0" in selected_styles
    assert "prefers-reduced-motion" in selected_styles
    assert "@keyframes oyx-motion-motion-home-selected-work-orientation" in selected_styles

    first_pass = dict(sources)
    assert not normalize_route_batch_motion_sources(sources, motion_beats=beats)
    assert sources == first_pass
    for path, body in sources.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

    diagnostics = validate_route_batch_contract(
        tmp_path,
        list(sources),
        route_id="home",
        section_ids=["home:hero", "home:selected-work"],
        section_selectors_by_section={
            "home:hero": "#hero",
            "home:selected-work": "#selected-work",
        },
        motion_beats=beats,
        work_unit_id="route-home-batch-1",
    )
    assert not any(
        item.code in {"SOURCE_CSS_INVALID_LENGTH", "SOURCE_ROUTE_BATCH_MOTION_INVALID"}
        for item in diagnostics
    )


def test_route_batch_motion_normalizer_only_rewrites_css_declarations() -> None:
    changes = GenerationChanges(
        files=[
            SourceFileChange(
                path="src/routes/home/sections/Hero.css",
                operation="create",
                complete_utf8_content=(
                    "/* max-width: fiftych */\n"
                    ".hero { max-width: fiftych; margin: twenty-fivepx; }\n"
                ),
            )
        ]
    )

    assert normalize_route_batch_motion_changes(changes, motion_beats=[])
    body = changes.files[0].complete_utf8_content
    assert "/* max-width: fiftych */" in body
    assert "max-width: 50ch" in body
    assert "margin: 25px" in body


def test_route_batch_selected_work_normalizer_materializes_lifecycle_cue() -> None:
    """Live-discovered 2026-09-10 (run 0b56cda5, slot 4): color token names
    are chosen per run by the model's own creative direction ("ink-muted"/
    "signal" in one run, "ink"/"paper" in another), never a fixed system
    contract. The normalizer used to hardcode assumed color names
    (--color-ink-secondary/--color-border-subtle/--color-accent-signal)
    that did not exist in this run's actual generated tokens, so the
    deterministic fix for one gap (a missing lifecycle cue) introduced a
    new one (SOURCE_CSS_CUSTOM_PROPERTY_UNBOUND). It must resolve against
    whatever color tokens this run actually generated instead."""

    sources = {
        "src/routes/home/sections/SelectedWork.tsx": """export default function SelectedWork() {
  return <section id="selected-work" data-content-id="home:selected-work">
    <Reveal className="selected-work-intro" />
    <article className="work-item" />
  </section>;
}
""",
        "src/routes/home/sections/SelectedWork.css": """#selected-work {
  padding-block: var(--space-8);
}
""",
        "src/design/generated-tokens.css": """:root {
  --color-ink-strong: #121212;
  --color-ink-muted: #5a5a5a;
  --color-signal: #2b6cff;
  --color-border: #d9d9d9;
}
""",
    }

    assert normalize_route_batch_selected_work_sources(sources)
    selected_work = sources["src/routes/home/sections/SelectedWork.tsx"]
    assert 'data-distinctive-move="selected-work-lifecycle"' in selected_work
    assert "observe" in selected_work
    assert "shape" in selected_work
    assert "deliver" in selected_work
    styles = sources["src/routes/home/sections/SelectedWork.css"]
    assert ".selected-work-lifecycle" in styles
    assert "--color-border-subtle" not in styles
    assert "--color-ink-secondary" not in styles
    assert "--color-accent-signal" not in styles
    assert "var(--color-ink-muted)" in styles
    assert "var(--color-border)" in styles
    assert "var(--color-signal)" in styles

    first_pass = dict(sources)
    assert not normalize_route_batch_selected_work_sources(sources)
    assert sources == first_pass


def test_route_batch_selected_work_normalizer_omits_color_when_none_resolve() -> None:
    """No design-tokens file at all: the normalizer must degrade gracefully
    (omit the color/background declarations) rather than emit a var()
    reference to a token it invented and cannot prove exists."""

    sources = {
        "src/routes/home/sections/SelectedWork.tsx": """export default function SelectedWork() {
  return <section id="selected-work" data-content-id="home:selected-work">
    <article className="work-item" />
  </section>;
}
""",
        "src/routes/home/sections/SelectedWork.css": "#selected-work { padding-block: var(--space-8); }\n",
    }

    assert normalize_route_batch_selected_work_sources(sources)
    styles = sources["src/routes/home/sections/SelectedWork.css"]
    assert ".selected-work-lifecycle" in styles
    assert "--color-" not in styles


def test_route_batch_contract_accepts_any_valid_css_attribute_selector_quote_style(
    tmp_path,
) -> None:
    """Live-discovered 2026-09-07 (run e624bd75, motion:home:approach-progress):
    a custom (non-catalogued) viewport-reveal beat exhausted its full repair
    budget on `[data-motion-target="approach-spine"]` never being found,
    even though the same attribute selector with single or no quotes --
    `[data-motion-target='approach-spine']` / `[data-motion-target=approach-spine]`
    -- is valid, functionally identical CSS. The checker required the exact
    quote character the blueprint literal happened to use; a model choosing
    a different (still correct) quote style was indistinguishable from one
    that never wrote the selector at all, and had no way to diagnose why."""

    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    approach = section / "Approach.tsx"
    approach.write_text(
        """const spine = document.querySelector("#approach");
if (spine && "IntersectionObserver" in window) {
  new IntersectionObserver(() => spine.setAttribute("data-motion-ready", "true"));
}
export default function Approach() {
  return <section id="approach" data-content-id="home:approach">
    <div data-motion-target="approach-spine" />
  </section>;
}
""",
        encoding="utf-8",
    )
    css = section / "Approach.css"
    css.write_text(
        """[data-motion-target='approach-spine'] { opacity: 1; }
[data-motion-ready="true"][data-motion-target=approach-spine] { opacity: 0; }
@media (prefers-reduced-motion: reduce) {
  [data-motion-target='approach-spine'] { opacity: 1; }
}
""",
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        ["src/routes/home/sections/Approach.tsx", "src/routes/home/sections/Approach.css"],
        route_id="home",
        section_ids=["home:approach"],
        section_selectors_by_section={"home:approach": "#approach"},
        motion_beats=[
            {
                "motion_id": "motion:home:approach-progress",
                "section_id": "home:approach",
                "target_marker": 'data-motion-target="approach-spine"',
                "target_selector": '[data-motion-target="approach-spine"]',
                "trigger": "viewport",
                "changed_properties": [
                    {"property_name": "opacity", "before_value": "0", "after_value": "1"}
                ],
            }
        ],
        work_unit_id="route-home-batch-1",
    )

    assert not any(item.code == "SOURCE_ROUTE_BATCH_MOTION_INVALID" for item in diagnostics)


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
