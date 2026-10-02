"""The strict HTML subset parser and the selector subset."""

from __future__ import annotations

import pytest

from oryxenai.themes.htmltree import normalize_text, parse_fragment, select, select_one
from oryxenai.themes.issues import bounded, escape_invisible

_DOC = (
    '<nav class="a b"><ul><li id="x"><a href="#y">One <em>two</em></a></li>'
    '<li><a href="#z">Three</a></li></ul></nav>'
    '<p class="note" data-k="v">T&amp;C &lt;ok&gt;<span aria-hidden="true">·</span> end</p>'
    '<img src="./a.svg" alt="">'
)


def test_well_formed_fragment_parses_and_decodes_entities() -> None:
    parsed = parse_fragment(_DOC)
    assert parsed.ok
    paragraph = select_one(parsed.root, "p.note")
    assert paragraph is not None
    assert paragraph.text() == "T&C <ok>· end"
    assert paragraph.text(skip_aria_hidden=True) == "T&C <ok> end"
    assert paragraph.get("data-k") == "v"


@pytest.mark.parametrize(
    ("source", "code"),
    [
        ("<div><p>x</div>", "HTML_MISMATCHED_END_TAG"),
        ("<div><p>x</p>", "HTML_UNCLOSED_ELEMENT"),
        ("</div>", "HTML_UNEXPECTED_END_TAG"),
        ("<div/>", "HTML_SELF_CLOSING_NON_VOID"),
        ("<img src='a'></img>", "HTML_END_TAG_FOR_VOID"),
        ('<p class="a" class="b">x</p>', "HTML_DUPLICATE_ATTRIBUTE"),
        ("<!DOCTYPE html><p>x</p>", "HTML_DECLARATION_NOT_ALLOWED"),
        ("<![CDATA[x]]>", "HTML_DECLARATION_NOT_ALLOWED"),
    ],
)
def test_structural_errors_are_reported_with_a_position(source: str, code: str) -> None:
    parsed = parse_fragment(source)
    assert not parsed.ok
    assert parsed.issues[0].code == code
    assert parsed.issues[0].line is not None and parsed.issues[0].column is not None


def test_void_elements_and_comments_are_accepted() -> None:
    parsed = parse_fragment("<p>a<br>b<br/>c</p><!-- note --><img src='x'>")
    assert parsed.ok
    assert [c[0].strip() for c in parsed.comments] == ["note"]


def test_text_nodes_merge_and_boolean_attributes_are_present() -> None:
    parsed = parse_fragment("<details open><summary>S</summary>a &amp; b</details>")
    details = select_one(parsed.root, "details")
    assert details is not None and details.has("open")
    assert details.text() == "S a & b" or details.text() == "Sa & b"


@pytest.mark.parametrize(
    ("selector", "expected"),
    [
        ("li", 2),
        ("nav > ul > li", 2),
        ("nav li", 2),
        ("ul > a", 0),
        ("li:first-child", 1),
        ("li:last-child a", 1),
        ("li:nth-child(2) a", 1),
        ("li#x", 1),
        ('a[href="#z"]', 1),
        ("a[href^='#']", 2),
        (".a.b", 1),
        (".a.zzz", 0),
        ("p[data-k]", 1),
        ("span:nth-child(1)", 1),
    ],
)
def test_selector_subset(selector: str, expected: int) -> None:
    parsed = parse_fragment(_DOC)
    assert len(select(parsed.root, selector)) == expected


def test_selector_scope_root_can_match_its_own_ancestors() -> None:
    parsed = parse_fragment('<a href="#h"><span>One</span><span>Two</span></a>')
    link = select_one(parsed.root, "a")
    assert link is not None
    second = select_one(link, "a > span:nth-child(2)")
    assert second is not None and second.text() == "Two"


def test_unsupported_selector_syntax_raises() -> None:
    with pytest.raises(ValueError):
        select(parse_fragment("<p></p>").root, "p:hover")


def test_normalize_text_keeps_nbsp_and_nfc() -> None:
    assert normalize_text("  a \n\t b ") == "a b"
    assert normalize_text("a" + chr(0xA0) + "b") == "a" + chr(0xA0) + "b"
    assert normalize_text("é") == "é"


def test_spaces_around_a_no_break_space_are_not_significant_but_the_nbsp_is() -> None:
    nbsp = chr(0xA0)
    assert normalize_text("fine " + nbsp + " ok") == "fine" + nbsp + "ok"
    assert normalize_text("fine" + nbsp + "ok") == "fine" + nbsp + "ok"
    assert normalize_text("fine " + nbsp + "ok") == normalize_text("fine" + nbsp + " ok")
    # Dropping the no-break space itself is still a copy difference.
    assert normalize_text("fine ok") != normalize_text("fine" + nbsp + "ok")


def test_evidence_makes_invisible_and_confusable_characters_visible() -> None:
    assert escape_invisible("a" + chr(0xA0) + "b" + chr(0x200B) + "c") == "a\\u00a0b\\u200bc"
    assert (
        escape_invisible("can" + chr(0x2019) + "t " + chr(0x2014) + " ok")
        == "can\\u2019t \\u2014 ok"
    )
    assert escape_invisible("Zoë 李") == "Zoë 李"
    assert bounded("x" * 400) is not None and len(bounded("x" * 400) or "") == 240
