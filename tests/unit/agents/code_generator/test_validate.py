"""Strict page validation: golden shapes pass, every planted defect is pinpointed."""

from __future__ import annotations

import re
from collections.abc import Callable

import pytest

from oryxenai.agents.code_generator.admission import content_admission_issues
from oryxenai.agents.code_generator.dev.reference_renderer import render_body
from oryxenai.agents.code_generator.validate import validate_page
from oryxenai.themes import get_theme
from tests.unit.agents.code_generator.helpers import sample_content, shapes

THEME = get_theme()
CONTENT = sample_content("01_strong_profile")
BODY = render_body(CONTENT)


@pytest.mark.parametrize("name", sorted(shapes()))
def test_every_content_shape_is_admitted_and_renders_a_valid_page(name: str) -> None:
    content = shapes()[name]
    assert content_admission_issues(content) == []
    report = validate_page(render_body(content), content, THEME)
    assert report.ok, [issue.to_dict() for issue in report.errors]
    assert report.warnings == []


def test_reference_body_is_clean() -> None:
    report = validate_page(BODY, CONTENT, THEME)
    assert report.ok and not report.issues


def _swap(old: str, new: str, *, last: bool = False) -> Callable[[str], str]:
    def mutate(body: str) -> str:
        assert old in body, f"mutation anchor not found: {old!r}"
        if last:
            head, _, tail = body.rpartition(old)
            return head + new + tail
        return body.replace(old, new, 1)

    return mutate


def _drop_footer(body: str) -> str:
    return re.sub(r"<footer.*?</footer>", "", body, flags=re.S)


def _move_footer_first(body: str) -> str:
    footer = re.search(r"<footer.*?</footer>", body, re.S)
    assert footer is not None
    return footer.group(0) + "\n" + body.replace(footer.group(0), "")


def _drop_section(body: str) -> str:
    return re.sub(r'<section class="scene scene--context".*?</section>', "", body, flags=re.S)


def _drop_hero_visual(body: str) -> str:
    return re.sub(r'<figure class="hero__visual".*?</figure>', "", body, flags=re.S)


def _drop_last_pillar(body: str) -> str:
    return re.sub(r'<li class="pillar" data-index="04">.*?</li>\n', "", body, flags=re.S)


def _drop_last_nav_item(body: str) -> str:
    return re.sub(
        r'      <li><a href="#connect"><span class="site-nav__index".*?</li>\n',
        "",
        body,
        count=1,
        flags=re.S,
    )


MUTATIONS: list[tuple[str, Callable[[str], str], str]] = [
    (
        "dropped_capability_item",
        _swap(
            '<ul class="capability-list"><li>Python</li><li>Go</li></ul>',
            '<ul class="capability-list"><li>Python</li></ul>',
        ),
        "COPY_COUNT_MISMATCH",
    ),
    (
        "pillar_title_replaced",
        _swap("<h3>Durable job systems</h3>", "<h3>Observability</h3>"),
        "COPY_MISMATCH",
    ),
    (
        "paraphrased_intro",
        _swap("designing the durable job infrastructure", "building durable job infrastructure"),
        "COPY_MISMATCH",
    ),
    (
        "smart_quote_in_headline",
        _swap("can&#39;t afford", "can" + chr(0x2019) + "t afford"),
        "COPY_MISMATCH",
    ),
    (
        "extra_text_added",
        _swap("<main>\n", "<main>\n  <p>Welcome to my site!</p>\n"),
        "TEXT_NOT_APPROVED",
    ),
    ("script_tag", _swap("</main>", "<script>alert(1)</script></main>"), "TAG_NOT_ALLOWED"),
    (
        "iframe_tag",
        _swap("</main>", '<iframe src="https://x.example"></iframe></main>'),
        "TAG_NOT_ALLOWED",
    ),
    (
        "inline_event_handler",
        _swap('<a class="text-link"', '<a onclick="x()" class="text-link"'),
        "ATTRIBUTE_FORBIDDEN",
    ),
    ("inline_style", _swap("<h1>", '<h1 style="color:red">'), "ATTRIBUTE_FORBIDDEN"),
    (
        "remote_hero_image",
        _swap("./assets/hero-visual.svg", "https://images.unsplash.com/x.jpg"),
        "URL_NOT_ALLOWED",
    ),
    (
        "data_uri_image",
        _swap("./assets/hero-visual.svg", "data:image/svg+xml,<svg/>"),
        "URL_NOT_ALLOWED",
    ),
    (
        "unknown_class",
        _swap('class="hero__intro"', 'class="hero__intro hero__lede"'),
        "CLASS_NOT_IN_THEME",
    ),
    ("duplicate_id", _swap('id="connect-title"', 'id="systems-title"'), "ID_DUPLICATE"),
    ("dead_anchor", _swap('href="#connect"', 'href="#contact"'), "ANCHOR_UNRESOLVED"),
    (
        "javascript_href",
        _swap(
            '<a class="text-link" href="#connect">',
            '<a class="text-link" href="javascript:alert(1)">',
        ),
        "URL_NOT_ALLOWED",
    ),
    (
        "cta_points_elsewhere",
        _swap(
            'class="button button--primary" href="#systems-practice"',
            'class="button button--primary" href="#connect"',
        ),
        "LINK_HREF_MISMATCH",
    ),
    (
        "external_link_without_new_tab",
        _swap(' target="_blank" rel="noopener noreferrer"', ""),
        "LINK_NEW_TAB_REQUIRED",
    ),
    (
        "destination_url_typo",
        _swap("https://github.com/priyanandan", "https://github.com/priyanandan2"),
        "URL_NOT_ALLOWED",
    ),
    ("unclosed_footer", _swap("</footer>", ""), "HTML_UNCLOSED_ELEMENT"),
    ("mismatched_end_tag", _swap("</nav>", "</div>"), "HTML_MISMATCHED_END_TAG"),
    (
        "self_closing_div",
        _swap(
            '<div class="grain" aria-hidden="true"></div>',
            '<div class="grain" aria-hidden="true"/>',
        ),
        "HTML_SELF_CLOSING_NON_VOID",
    ),
    ("doctype_in_body", lambda body: "<!doctype html>\n" + body, "BODY_HAS_DOCUMENT_TAGS"),
    ("markdown_fence", lambda body: "```html\n" + body + "\n```", "OUTPUT_NOT_HTML"),
    ("fourth_nav_link_missing", _drop_last_nav_item, "COPY_COUNT_MISMATCH"),
    ("only_three_pillars", _drop_last_pillar, "COPY_COUNT_MISMATCH"),
    ("headline_without_em", _swap("<em>downtime.</em>", "downtime."), "COPY_MISMATCH"),
    ("footer_missing", _drop_footer, "STRUCTURE_MISSING"),
    ("context_section_missing", _drop_section, "STRUCTURE_MISSING"),
    ("hero_visual_missing", _drop_hero_visual, "STRUCTURE_MISSING"),
    (
        "wrong_monogram",
        _swap('aria-hidden="true">PN</span>', 'aria-hidden="true">PX</span>'),
        "COPY_MISMATCH",
    ),
    (
        "marquee_lists_differ",
        _swap("<li>asyncio</li></ul>", "<li>asyncio2</li></ul>", last=True),
        "COPY_MISMATCH",
    ),
    (
        "featured_flag_wrong",
        _swap(
            '<li class="destination-list__featured"><a href="https://linkedin.com',
            '<li><a href="https://linkedin.com',
        ),
        "COPY_MISMATCH",
    ),
    (
        "unapproved_aria_label",
        _swap('aria-label="Portfolio sections"', 'aria-label="Main menu"'),
        "TEXT_NOT_APPROVED",
    ),
    (
        "nbsp_in_name",
        _swap("Priya Nandan</h1>", "Priya" + chr(0xA0) + "Nandan</h1>"),
        "COPY_MISMATCH",
    ),
    ("text_outside_structure", lambda body: body + "\nstray text", "TEXT_OUTSIDE_STRUCTURE"),
    ("heading_id_wrong", _swap('id="systems-title"', 'id="systems-heading"'), "ID_MISMATCH"),
    ("footer_before_main", _move_footer_first, "STRUCTURE_ORDER"),
]


@pytest.mark.parametrize(("name", "mutate", "code"), MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_planted_defect_is_caught_with_its_code(
    name: str, mutate: Callable[[str], str], code: str
) -> None:
    report = validate_page(mutate(BODY), CONTENT, THEME)
    assert not report.ok, name
    codes = {issue.code for issue in report.errors}
    assert code in codes, (name, sorted(codes))
    first = report.errors[0]
    assert first.message


def test_oversized_body_is_refused_before_parsing() -> None:
    report = validate_page(BODY, CONTENT, THEME, max_bytes=500)
    assert [issue.code for issue in report.errors] == ["SIZE_LIMIT"]


def test_html_comments_and_open_state_are_warnings_not_errors() -> None:
    commented = BODY.replace("<main>", "<!-- hero --><main>", 1)
    report = validate_page(commented, CONTENT, THEME)
    assert report.ok
    assert [issue.code for issue in report.warnings] == ["COMMENT_PRESENT"]

    closed = BODY.replace(
        '<details class="capability-group" open>', '<details class="capability-group">', 1
    )
    report = validate_page(closed, CONTENT, THEME)
    assert report.ok
    assert "ATTRIBUTE_MISMATCH" in {issue.code for issue in report.warnings}


def test_a_short_marquee_is_a_warning_but_the_words_and_order_stay_strict() -> None:
    keywords = CONTENT["marquee_keywords"]
    once = "".join(f"<li>{word}</li>" for word in keywords)
    twice = once + once
    assert twice in BODY
    shorter = BODY.replace(twice, once)
    report = validate_page(shorter, CONTENT, THEME)
    assert report.ok
    assert "MARQUEE_NARROW" in {issue.code for issue in report.warnings}
    reordered = BODY.replace(
        once + once, "".join(f"<li>{word}</li>" for word in reversed(keywords)) * 2
    )
    assert not validate_page(reordered, CONTENT, THEME).ok


def test_mismatch_evidence_makes_invisible_differences_visible() -> None:
    report = validate_page(
        _swap("Priya Nandan</h1>", "Priya" + chr(0xA0) + "Nandan</h1>")(BODY), CONTENT, THEME
    )
    mismatch = next(issue for issue in report.errors if issue.code == "COPY_MISMATCH")
    assert mismatch.path == "hero.name"
    payload = mismatch.to_dict()
    assert "\\u00a0" in str(payload["found"])
    assert "\\u00a0" not in str(payload["expected"])
    assert mismatch.line is not None


def test_report_is_bounded_and_serializable() -> None:
    broken = re.sub(r"<li>([^<]+)</li>", r"<li>X\1</li>", BODY)
    report = validate_page(broken, CONTENT, THEME)
    assert not report.ok
    data = report.to_dict()
    assert data["ok"] is False and data["error_count"] > 0
    assert len(data["issues"]) <= 80


def test_escaped_markup_in_approved_copy_is_text_not_tags() -> None:
    content = shapes()["injection"]
    body = render_body(content)
    assert "&lt;script" in body
    assert validate_page(body, content, THEME).ok
