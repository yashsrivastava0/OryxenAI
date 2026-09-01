from __future__ import annotations

from oryxenai.agents.code_generator.core.source_lexing import strip_source_comments
from oryxenai.agents.code_generator.core.typescript_ast_audit import (
    _audit_v4_anti_slop,
    _audit_v4_cross_route_sameness,
    _route_source_path,
    _selector_declarations,
    _selector_has_reduced_motion,
)


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
