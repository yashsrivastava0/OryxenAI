"""Executable markup contract for the Editorial Forest v1 theme.

Everything the generic Code Generator needs to know about this one fixed
template lives here: the host-derived values, the technical ``<head>``, the
closed set of legal tags/attributes/strings, and the region-by-region
placement checks that bind approved copy to DOM elements.

The model writes the page **body**; the host owns the head. Approved copy is
compared by decoded text (NFC, ASCII-whitespace collapsed), never by source
bytes, so entity spelling (``&amp;`` vs ``&``) can never cause a false alarm.
"""

from __future__ import annotations

import html
import json
import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from oryxenai.themes.htmltree import Element, Text, normalize_text, select, select_one
from oryxenai.themes.issues import Issue, Severity

THEME_ID = "editorial-forest/v1"
HERO_ASSET = "./assets/hero-visual.svg"
THEME_COLOR = "#14231c"
MARQUEE_MIN_KEYWORDS = 3
MARQUEE_TARGET_ITEMS = 10
OPEN_ALL_GROUPS_UP_TO_ITEMS = 24

CHROME_STRINGS = frozenset(
    {"Skip to main content", "Portfolio sections", "Location", "Scroll", "Back to top"}
)
GLYPHS = frozenset({"·", "↓", "↗", "↑"})

_HONORIFICS = frozenset({"dr", "prof", "mr", "mrs", "ms", "mx", "sir", "dame", "eng", "er"})
_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "phd", "md"})
_LANG = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,3}$")


@dataclass(frozen=True, slots=True)
class Section:
    key: str  # page_content region
    dom_id: str
    title_id: str
    modifier: str  # scene--*


SECTIONS = (
    Section("systems_practice", "systems-practice", "systems-title", "scene--systems"),
    Section(
        "technical_capabilities",
        "technical-capabilities",
        "capabilities-title",
        "scene--capabilities",
    ),
    Section("professional_context", "professional-context", "context-title", "scene--context"),
    Section("connect", "connect", "connect-title", "scene--connect"),
)

_ALLOWED_TAGS = frozenset(
    {
        "a", "div", "span", "p", "h1", "h2", "h3", "ul", "li", "nav", "main", "header",
        "footer", "section", "figure", "img", "em", "details", "summary",
    }
)  # fmt: skip
_ALLOWED_ATTRIBUTES: Mapping[str, frozenset[str]] = {
    "*": frozenset(
        {
            "class",
            "id",
            "tabindex",
            "aria-hidden",
            "aria-label",
            "aria-labelledby",
            "role",
            "data-index",
        }
    ),
    "a": frozenset({"href", "target", "rel"}),
    "img": frozenset({"src", "width", "height", "alt", "decoding", "fetchpriority", "loading"}),
    "details": frozenset({"open"}),
}


def _s(value: Any) -> str:
    """A stripped string, or '' for anything that is not text."""
    return value.strip() if isinstance(value, str) else ""


def _region(content: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = content.get(key)
    return value if isinstance(value, Mapping) else {}


def _strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [text for text in (_s(item) for item in values) if text]


def _first_grapheme(token: str) -> str:
    """First visible character plus its combining marks."""
    for index, char in enumerate(token):
        if char.isalnum():
            end = index + 1
            while end < len(token) and unicodedata.category(token[end]) in {"Mn", "Mc", "Me"}:
                end += 1
            return token[index:end]
    return token[:1]


def monogram(name: str) -> str:
    """Initials for the wordmark/badge: honorifics, suffixes and particles skipped."""
    tokens = [token for token in name.split() if token]
    core = [t for t in tokens if t.lower().rstrip(".") not in _HONORIFICS | _SUFFIXES] or tokens
    capitalized = [t for t in core if t[:1].isupper() or not t[:1].isalpha()]
    used = capitalized or core
    letters = [_first_grapheme(token).upper() for token in used]
    if not letters:
        return ""
    if len(letters) <= 3:
        return "".join(letters)
    return letters[0] + letters[1] + letters[-1]


def _marquee(content: Mapping[str, Any]) -> dict[str, Any] | None:
    keywords = _strings(content.get("marquee_keywords"))
    if len(keywords) < MARQUEE_MIN_KEYWORDS:
        return None
    repeat = (
        1
        if len(keywords) >= MARQUEE_TARGET_ITEMS
        else math.ceil(MARQUEE_TARGET_ITEMS / len(keywords))
    )
    return {"items": keywords * repeat, "repeat": repeat, "keywords": keywords}


@lru_cache(maxsize=4)
def _css_classes(css: str) -> frozenset[str]:
    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    stripped = re.sub(r"url\((?:[^()]|\([^)]*\))*\)", "url()", stripped)
    classes: set[str] = set()
    for selector in re.findall(r"([^{}]+)\{", stripped):
        if selector.strip().startswith("@"):
            continue
        classes.update(re.findall(r"\.([A-Za-z_][\w-]*)", selector))
    return frozenset(classes)


class EditorialForestContract:
    theme_id = THEME_ID
    default_language = "en"
    allowed_tags = _ALLOWED_TAGS
    allowed_attributes = _ALLOWED_ATTRIBUTES
    chrome_strings = CHROME_STRINGS

    def __init__(self, root: Path) -> None:
        self._root = root

    # ── static facts ───────────────────────────────────────────────────────

    def class_vocabulary(self) -> frozenset[str]:
        css = (self._root / "styles.css").read_text(encoding="utf-8")
        manifest = json.loads((self._root / "manifest.json").read_text(encoding="utf-8"))
        return _css_classes(css) | frozenset(manifest.get("hook_classes", []))

    def asset_paths(self) -> frozenset[str]:
        return frozenset({HERO_ASSET})

    def valid_language(self, lang: str) -> bool:
        return bool(_LANG.match(lang))

    # ── host-derived values ────────────────────────────────────────────────

    def derive(self, page_content: Mapping[str, Any]) -> dict[str, Any]:
        hero = _region(page_content, "hero")
        name = _s(hero.get("name"))
        location = _s(hero.get("location"))
        groups_in = _region(page_content, "technical_capabilities").get("groups")
        groups: list[dict[str, Any]] = [
            {"heading": _s(group.get("heading")), "items": _strings(group.get("items"))}
            for group in (groups_in if isinstance(groups_in, list) else [])
            if isinstance(group, Mapping)
        ]
        total_items = sum(len(group["items"]) for group in groups)
        open_all = total_items <= OPEN_ALL_GROUPS_UP_TO_ITEMS
        for index, group in enumerate(groups):
            group["index"] = f"{index + 1:02d}"
            group["open"] = open_all or index == 0
        pillars_in = _region(page_content, "systems_practice").get("pillars")
        pillars = [
            {
                "index": f"{index + 1:02d}",
                "title": _s(pillar.get("title")),
                "description": _s(pillar.get("description")),
            }
            for index, pillar in enumerate(pillars_in if isinstance(pillars_in, list) else [])
            if isinstance(pillar, Mapping)
        ]
        destinations_in = _region(page_content, "connect").get("destinations")
        destinations = []
        for item in destinations_in if isinstance(destinations_in, list) else []:
            if not isinstance(item, Mapping):
                continue
            url = _s(item.get("url"))
            external = url.lower().startswith(("http://", "https://"))
            destinations.append(
                {
                    "label": _s(item.get("label")),
                    "url": url,
                    "featured": bool(item.get("featured")),
                    "external": external,
                    "new_tab": external,
                }
            )
        organizations = _strings(_region(page_content, "professional_context").get("organizations"))
        return {
            "lang": self.default_language,
            "monogram": monogram(name),
            "nav": [
                {
                    "id": section.dom_id,
                    "label": _s(_region(page_content, section.key).get("eyebrow")),
                    "index": f"{index + 1:02d}",
                }
                for index, section in enumerate(SECTIONS)
            ],
            "marquee": _marquee(page_content),
            "pillars": pillars,
            "groups": groups,
            "organizations": organizations,
            "destinations": destinations,
            "footer": {"name": name, "location": location},
            "hero_asset": HERO_ASSET,
        }

    # ── closed-world sets ──────────────────────────────────────────────────

    def approved_text(
        self, page_content: Mapping[str, Any], derived: Mapping[str, Any]
    ) -> set[str]:
        approved: set[str] = set(CHROME_STRINGS) | set(GLYPHS)

        def collect(node: Any) -> None:
            if isinstance(node, str):
                text = normalize_text(node)
                if text:
                    approved.add(text)
            elif isinstance(node, Mapping):
                for key, value in node.items():
                    if key != "url":
                        collect(value)
            elif isinstance(node, list):
                for item in node:
                    collect(item)

        collect(dict(page_content))
        approved.add(str(derived.get("monogram", "")))
        for entry in derived.get("nav", []):
            approved.add(str(entry["index"]))
        for entry in derived.get("pillars", []):
            approved.add(str(entry["index"]))
        for group in derived.get("groups", []):
            approved.add(str(group["index"]))
        approved.discard("")
        return approved

    def approved_urls(self, page_content: Mapping[str, Any]) -> set[str]:
        destinations = _region(page_content, "connect").get("destinations")
        return {
            _s(item.get("url"))
            for item in (destinations if isinstance(destinations, list) else [])
            if isinstance(item, Mapping) and _s(item.get("url"))
        }

    # ── host-owned document shell ──────────────────────────────────────────

    def render_head(
        self, page_content: Mapping[str, Any], derived: Mapping[str, Any], lang: str
    ) -> str:
        metadata = _region(page_content, "metadata")
        safe_lang = lang if _LANG.match(lang) else self.default_language
        title = html.escape(_s(metadata.get("title")), quote=True)
        description = html.escape(_s(metadata.get("description")), quote=True)
        return (
            "<!doctype html>\n"
            f'<html lang="{html.escape(safe_lang, quote=True)}">\n'
            "<head>\n"
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<meta name="theme-color" content="{THEME_COLOR}">\n'
            f'<meta name="description" content="{description}">\n'
            f"<title>{title}</title>\n"
            '<link rel="icon" href="data:,">\n'
            '<link rel="stylesheet" href="./styles.css">\n'
            "</head>\n"
            "<body>\n"
        )

    def render_tail(self) -> str:
        return "\n</body>\n</html>\n"

    # ── prompt material ────────────────────────────────────────────────────

    def prompt_contract(self) -> str:
        rules = (self._root / "contract_rules.md").read_text(encoding="utf-8").strip()
        exemplar = (self._root / "exemplar.html").read_text(encoding="utf-8").strip()
        return f"{rules}\n\n<exemplar>\n{exemplar}\n</exemplar>"

    # ── validation ─────────────────────────────────────────────────────────

    def validate_body(
        self, root: Element, page_content: Mapping[str, Any], derived: Mapping[str, Any]
    ) -> list[Issue]:
        validator = _BodyValidator(root, page_content, derived)
        validator.run()
        return validator.issues


class _BodyValidator:
    """Region-by-region binding of approved copy to the parsed body."""

    def __init__(
        self, root: Element, content: Mapping[str, Any], derived: Mapping[str, Any]
    ) -> None:
        self.root = root
        self.content = content
        self.derived = derived
        self.issues: list[Issue] = []

    # helpers ----------------------------------------------------------------

    def issue(
        self,
        code: str,
        message: str,
        *,
        severity: Severity = "error",
        path: str | None = None,
        selector: str | None = None,
        expected: str | None = None,
        found: str | None = None,
        node: Element | None = None,
    ) -> None:
        self.issues.append(
            Issue(
                code,
                severity,
                message,
                path=path,
                selector=selector,
                expected=expected,
                found=found,
                line=node.line if node is not None else None,
                column=node.column if node is not None else None,
            )
        )

    def expect_text(
        self,
        node: Element | None,
        expected: str,
        *,
        path: str,
        selector: str,
        visible: bool = False,
    ) -> None:
        if node is None:
            self.issue(
                "COPY_MISSING",
                f"No element carries {path}.",
                path=path,
                selector=selector,
                expected=expected,
            )
            return
        found = node.text(skip_aria_hidden=visible)
        if found != normalize_text(expected):
            self.issue(
                "COPY_MISMATCH",
                f"The text for {path} differs from the approved copy.",
                path=path,
                selector=selector,
                expected=normalize_text(expected),
                found=found,
                node=node,
            )

    def expect_absent(
        self, nodes: Sequence[Element], *, path: str, selector: str, why: str
    ) -> None:
        if nodes:
            self.issue(
                "COPY_UNEXPECTED",
                f"{selector} must be omitted because {why}.",
                severity="warning",
                path=path,
                selector=selector,
                found=nodes[0].text(),
                node=nodes[0],
            )

    def expect_list(
        self, nodes: Sequence[Element], expected: Sequence[str], *, path: str, selector: str
    ) -> None:
        if len(nodes) != len(expected):
            self.issue(
                "COPY_COUNT_MISMATCH",
                f"{path} has {len(expected)} approved items but the page shows {len(nodes)}.",
                path=path,
                selector=selector,
                expected=str(len(expected)),
                found=str(len(nodes)),
                node=nodes[0] if nodes else None,
            )
            return
        for index, (node, value) in enumerate(zip(nodes, expected, strict=True)):
            self.expect_text(node, value, path=f"{path}[{index}]", selector=selector)

    def one(self, scope: Element, selector: str, *, what: str) -> Element | None:
        found = select(scope, selector)
        if not found:
            self.issue("STRUCTURE_MISSING", f"Missing {what}.", selector=selector)
            return None
        if len(found) > 1:
            self.issue(
                "STRUCTURE_COUNT",
                f"Expected exactly one {what}, found {len(found)}.",
                selector=selector,
                expected="1",
                found=str(len(found)),
                node=found[1],
            )
        return found[0]

    def expect_href(self, node: Element, expected: str, *, path: str) -> None:
        if node.get("href") != expected:
            self.issue(
                "LINK_HREF_MISMATCH",
                f"The link for {path} points to the wrong target.",
                path=path,
                expected=expected,
                found=node.get("href"),
                node=node,
            )

    # run --------------------------------------------------------------------

    def run(self) -> None:
        self.check_top_level()
        nav = select_one(self.root, "nav.site-nav")
        if nav is not None:
            self.check_nav(nav)
        main = select_one(self.root, "main")
        if main is None:
            return
        hero = self.one(main, "header.hero", what='hero <header class="hero">')
        if hero is not None:
            self.check_hero(hero)
        self.check_marquee(main)
        for section in SECTIONS:
            node = self.one(
                main, f"section#{section.dom_id}", what=f'<section id="{section.dom_id}">'
            )
            if node is not None:
                self.check_section_frame(node, section)
        self.check_systems(main)
        self.check_capabilities(main)
        self.check_context(main)
        self.check_connect(main)
        footer = select_one(self.root, "footer.site-footer")
        if footer is not None:
            self.check_footer(footer)

    def check_top_level(self) -> None:
        for child in self.root.children:
            if isinstance(child, Text) and child.value.strip():
                self.issue(
                    "TEXT_OUTSIDE_STRUCTURE",
                    "Text appears outside the page structure.",
                    found=normalize_text(child.value),
                )
        spec: list[tuple[str, str, bool, str]] = [
            ("a", "skip-link", False, "skip link"),
            ("div", "reading-progress", False, "reading-progress bar"),
            ("div", "grain", False, "grain overlay"),
            ("nav", "site-nav", True, "navigation"),
            ("main", "", True, "<main>"),
            ("footer", "site-footer", True, "footer"),
        ]
        position = 0
        for element in self.root.elements():
            matched = None
            for index in range(position, len(spec)):
                tag, klass, _required, _label = spec[index]
                if element.tag == tag and (not klass or element.has_class(klass)):
                    matched = index
                    break
            if matched is None:
                self.issue(
                    "STRUCTURE_UNEXPECTED",
                    f"<{element.tag}> is not allowed here; the body is: skip link, progress bar, "
                    "grain, nav, main, footer, in that order.",
                    found=f'<{element.tag} class="{element.get("class") or ""}">',
                    node=element,
                )
                continue
            for skipped in range(position, matched):
                if spec[skipped][2]:
                    self.issue(
                        "STRUCTURE_ORDER",
                        f"The {spec[skipped][3]} must come before this element.",
                        node=element,
                    )
            position = matched + 1
        for index in range(position, len(spec)):
            if spec[index][2] and not select(
                self.root, f"{spec[index][0]}{'.' + spec[index][1] if spec[index][1] else ''}"
            ):
                self.issue("STRUCTURE_MISSING", f"Missing the {spec[index][3]}.")
        skip = select_one(self.root, "a.skip-link")
        if skip is not None:
            self.expect_text(
                skip, "Skip to main content", path="chrome.skip_link", selector="a.skip-link"
            )
            if skip.get("href") != "#home":
                self.issue(
                    "LINK_HREF_MISMATCH",
                    "The skip link must target #home.",
                    expected="#home",
                    found=skip.get("href"),
                    node=skip,
                )

    def check_nav(self, nav: Element) -> None:
        derived = self.derived
        if nav.get("aria-label") != "Portfolio sections":
            self.issue(
                "ARIA_LABEL_MISMATCH",
                'The navigation needs aria-label="Portfolio sections".',
                severity="warning",
                expected="Portfolio sections",
                found=nav.get("aria-label"),
                node=nav,
            )
        hero = _region(self.content, "hero")
        wordmark = self.one(nav, "a.wordmark", what="wordmark link")
        if wordmark is not None:
            self.expect_href(wordmark, "#home", path="nav.wordmark")
            self.expect_text(
                select_one(wordmark, "span.wordmark__monogram"),
                str(derived["monogram"]),
                path="derived.monogram",
                selector="a.wordmark span.wordmark__monogram",
            )
            self.expect_text(
                select_one(wordmark, "span.wordmark__name"),
                _s(hero.get("name")),
                path="hero.name",
                selector="a.wordmark span.wordmark__name",
            )
        items = select(nav, "ul.site-nav__links > li")
        expected_nav = derived["nav"]
        if len(items) != len(expected_nav):
            self.issue(
                "COPY_COUNT_MISMATCH",
                f"The navigation needs {len(expected_nav)} links, found {len(items)}.",
                selector="ul.site-nav__links > li",
                expected=str(len(expected_nav)),
                found=str(len(items)),
            )
            return
        for item, entry in zip(items, expected_nav, strict=True):
            link = select_one(item, "a")
            if link is None:
                self.issue("STRUCTURE_MISSING", "A navigation item has no link.", node=item)
                continue
            self.expect_href(link, f"#{entry['id']}", path=f"nav[{entry['index']}]")
            self.expect_text(
                select_one(link, "span.site-nav__index"),
                str(entry["index"]),
                path=f"nav[{entry['index']}].index",
                selector="span.site-nav__index",
            )
            self.expect_text(
                select_one(link, "a > span:nth-child(2)"),
                str(entry["label"]),
                path=f"{_section_key(entry['id'])}.eyebrow",
                selector="a > span:nth-child(2)",
            )

    def check_hero(self, hero: Element) -> None:
        h = _region(self.content, "hero")
        if hero.get("id") != "home":
            self.issue(
                "ID_MISMATCH",
                'The hero header needs id="home".',
                expected="home",
                found=hero.get("id"),
                node=hero,
            )
        self.expect_text(
            self.one(hero, "h1", what="<h1>"),
            _s(h.get("name")),
            path="hero.name",
            selector="header.hero h1",
        )
        parts = [p for p in (_s(h.get("eyebrow_primary")), _s(h.get("eyebrow_secondary"))) if p]
        eyebrow = select(hero, "p.hero__eyebrow")
        if parts:
            self.expect_text(
                eyebrow[0] if eyebrow else None,
                " ".join(parts),
                path="hero.eyebrow_primary"
                if len(parts) == 1
                else "hero.eyebrow_primary+eyebrow_secondary",
                selector="p.hero__eyebrow",
                visible=True,
            )
        else:
            self.expect_absent(
                eyebrow,
                path="hero.eyebrow_primary",
                selector="p.hero__eyebrow",
                why="both eyebrows are empty",
            )
        headline_parts = [
            p for p in (_s(h.get("headline_prefix")), _s(h.get("headline_emphasis"))) if p
        ]
        headline = select(hero, "p.hero__headline")
        if headline_parts:
            node = headline[0] if headline else None
            self.expect_text(
                node,
                " ".join(headline_parts),
                path="hero.headline_prefix+headline_emphasis",
                selector="p.hero__headline",
            )
            if node is not None:
                ems = select(node, "em")
                emphasis = _s(h.get("headline_emphasis"))
                if emphasis:
                    if len(ems) != 1:
                        self.issue(
                            "COPY_MISMATCH",
                            "The headline emphasis must be wrapped in exactly one <em>.",
                            path="hero.headline_emphasis",
                            selector="p.hero__headline em",
                            expected="1",
                            found=str(len(ems)),
                            node=node,
                        )
                    else:
                        self.expect_text(
                            ems[0],
                            emphasis,
                            path="hero.headline_emphasis",
                            selector="p.hero__headline em",
                        )
                elif ems:
                    self.issue(
                        "COPY_UNEXPECTED",
                        "No <em> is allowed when headline_emphasis is empty.",
                        severity="warning",
                        path="hero.headline_emphasis",
                        node=ems[0],
                    )
        self.expect_text(
            select_one(hero, "p.hero__intro"),
            _s(h.get("intro")),
            path="hero.intro",
            selector="p.hero__intro",
        )
        location = select(hero, "p.hero__location")
        if _s(h.get("location")):
            if not location:
                self.issue(
                    "COPY_MISSING",
                    "No element carries hero.location.",
                    path="hero.location",
                    selector="p.hero__location",
                    expected=_s(h.get("location")),
                )
            else:
                self.expect_text(
                    select_one(location[0], "span:nth-child(1)"),
                    "Location",
                    path="chrome.location_label",
                    selector="p.hero__location span:nth-child(1)",
                )
                self.expect_text(
                    select_one(location[0], "span:nth-child(2)"),
                    _s(h.get("location")),
                    path="hero.location",
                    selector="p.hero__location span:nth-child(2)",
                )
        else:
            self.expect_absent(
                location, path="hero.location", selector="p.hero__location", why="location is empty"
            )
        primary, secondary = _s(h.get("primary_cta_label")), _s(h.get("secondary_cta_label"))
        button = select(hero, "a.button--primary")
        link = select(hero, "a.text-link")
        if primary:
            if not button:
                self.issue(
                    "COPY_MISSING",
                    "No button carries hero.primary_cta_label.",
                    path="hero.primary_cta_label",
                    selector="a.button--primary",
                    expected=primary,
                )
            else:
                self.expect_text(
                    select_one(button[0], "span.button__label"),
                    primary,
                    path="hero.primary_cta_label",
                    selector="a.button--primary span.button__label",
                )
                self.expect_href(button[0], "#systems-practice", path="hero.primary_cta_label")
        else:
            self.expect_absent(
                button,
                path="hero.primary_cta_label",
                selector="a.button--primary",
                why="the primary CTA label is empty",
            )
        if secondary:
            if not link:
                self.issue(
                    "COPY_MISSING",
                    "No link carries hero.secondary_cta_label.",
                    path="hero.secondary_cta_label",
                    selector="a.text-link",
                    expected=secondary,
                )
            else:
                self.expect_text(
                    link[0],
                    secondary,
                    path="hero.secondary_cta_label",
                    selector="a.text-link",
                    visible=True,
                )
                self.expect_href(link[0], "#connect", path="hero.secondary_cta_label")
        else:
            self.expect_absent(
                link,
                path="hero.secondary_cta_label",
                selector="a.text-link",
                why="the secondary CTA label is empty",
            )
        figure = select_one(hero, "figure.hero__visual")
        if figure is None:
            self.issue(
                "STRUCTURE_MISSING",
                'Missing the hero visual <figure class="hero__visual">.',
                selector="figure.hero__visual",
            )
        else:
            image = select_one(figure, "img")
            if image is None or image.get("src") != HERO_ASSET:
                self.issue(
                    "ASSET_MISMATCH",
                    f"The hero image must be {HERO_ASSET}.",
                    expected=HERO_ASSET,
                    found=image.get("src") if image else None,
                    node=image or figure,
                )
            elif image.get("alt") != "":
                self.issue(
                    "ALT_NOT_EMPTY",
                    'The decorative hero image needs alt="".',
                    severity="warning",
                    expected="",
                    found=image.get("alt"),
                    node=image,
                )
            self.expect_text(
                select_one(figure, "span.hero__badge"),
                str(self.derived["monogram"]),
                path="derived.monogram",
                selector="figure.hero__visual span.hero__badge",
            )

    def check_marquee(self, main: Element) -> None:
        marquee = select(main, "main > div.marquee")
        expected = self.derived["marquee"]
        if expected is None:
            self.expect_absent(
                marquee,
                path="marquee_keywords",
                selector="div.marquee",
                why=f"fewer than {MARQUEE_MIN_KEYWORDS} keywords were approved",
            )
            return
        if not marquee:
            self.issue(
                "STRUCTURE_MISSING",
                "Missing the keyword marquee.",
                selector="main > div.marquee",
                path="marquee_keywords",
            )
            return
        if marquee[0].get("aria-hidden") != "true":
            self.issue(
                "ARIA_HIDDEN_MISSING",
                'The marquee is decorative and needs aria-hidden="true".',
                severity="warning",
                node=marquee[0],
            )
        lists = select(marquee[0], "div.marquee__track > ul.marquee__list")
        if len(lists) != 2:
            self.issue(
                "STRUCTURE_COUNT",
                "The marquee needs two identical lists for a seamless loop.",
                selector="ul.marquee__list",
                expected="2",
                found=str(len(lists)),
                node=marquee[0],
            )
            return
        keywords: list[str] = expected["keywords"]
        sequences = [[node.text() for node in select(lst, "li")] for lst in lists]
        if sequences[0] != sequences[1]:
            self.issue(
                "COPY_MISMATCH",
                "The two marquee lists must be identical for a seamless loop.",
                path="marquee_keywords",
                selector="ul.marquee__list",
                expected=" | ".join(sequences[0][:12]),
                found=" | ".join(sequences[1][:12]),
                node=lists[1],
            )
        for index, texts in enumerate(sequences):
            # The ticker repeats the approved keywords; how many times is cosmetic, but the
            # words and their order are copy and must match exactly.
            whole = len(texts) >= len(keywords) and len(texts) % len(keywords) == 0
            if not whole or texts != keywords * (len(texts) // len(keywords)):
                self.issue(
                    "COPY_MISMATCH",
                    f"marquee list {index + 1} must be the approved keywords in order, repeated as a whole.",
                    path="marquee_keywords",
                    selector="ul.marquee__list > li",
                    expected=" | ".join(expected["items"][:12]),
                    found=" | ".join(texts[:12]),
                    node=lists[index],
                )
            elif len(texts) < len(expected["items"]):
                self.issue(
                    "MARQUEE_NARROW",
                    "The marquee is shorter than recommended and may leave a gap on wide screens.",
                    severity="warning",
                    path="marquee_keywords",
                    expected=f"{len(expected['items'])} items",
                    found=f"{len(texts)} items",
                    node=lists[index],
                )

    def check_section_frame(self, node: Element, section: Section) -> None:
        for klass in ("scene", section.modifier):
            if not node.has_class(klass):
                self.issue(
                    "CLASS_REQUIRED",
                    f'<section id="{section.dom_id}"> needs class "{klass}".',
                    selector=f"section#{section.dom_id}",
                    expected=klass,
                    found=node.get("class"),
                    node=node,
                )
        if node.get("aria-labelledby") != section.title_id:
            self.issue(
                "ARIA_LABEL_MISMATCH",
                f'aria-labelledby must be "{section.title_id}".',
                severity="warning",
                expected=section.title_id,
                found=node.get("aria-labelledby"),
                node=node,
            )
        heading_selector = f"section#{section.dom_id} h2"
        heading = select(node, "h2")
        region = _region(self.content, section.key)
        if len(heading) != 1:
            self.issue(
                "STRUCTURE_COUNT",
                f"Section {section.dom_id} needs exactly one <h2>.",
                selector=heading_selector,
                expected="1",
                found=str(len(heading)),
                node=node,
            )
        else:
            if heading[0].get("id") != section.title_id:
                self.issue(
                    "ID_MISMATCH",
                    f'The <h2> needs id="{section.title_id}".',
                    expected=section.title_id,
                    found=heading[0].get("id"),
                    node=heading[0],
                )
            self.expect_text(
                heading[0],
                _s(region.get("heading")),
                path=f"{section.key}.heading",
                selector=heading_selector,
            )
        eyebrow_scope = "div.connect-copy" if section.key == "connect" else "div.section-heading"
        eyebrow = select(node, f"{eyebrow_scope} > p.eyebrow:first-child")
        self.expect_text(
            eyebrow[0] if eyebrow else None,
            _s(region.get("eyebrow")),
            path=f"{section.key}.eyebrow",
            selector=f"section#{section.dom_id} {eyebrow_scope} > p.eyebrow:first-child",
        )

    def _intro(
        self, section: Section, node_selector: str, scope: str, *, nth: int | None = None
    ) -> None:
        region = _region(self.content, section.key)
        intro = _s(region.get("intro"))
        node = select_one(self.root, f"section#{section.dom_id}")
        if node is None:
            return
        paragraphs = select(node, node_selector)
        if intro:
            index = 0 if nth is None else nth
            self.expect_text(
                paragraphs[index] if len(paragraphs) > index else None,
                intro,
                path=f"{section.key}.intro",
                selector=f"section#{section.dom_id} {node_selector}",
            )
        else:
            self.expect_absent(
                paragraphs,
                path=f"{section.key}.intro",
                selector=node_selector,
                why=f"{section.key}.intro is empty",
            )

    def check_systems(self, main: Element) -> None:
        section = SECTIONS[0]
        node = select_one(main, f"section#{section.dom_id}")
        if node is None:
            return
        self._intro(section, "div.section-heading > p.section-heading__intro", "")
        items = select(node, "ul.pillar-grid > li.pillar")
        expected = self.derived["pillars"]
        if len(items) != len(expected):
            self.issue(
                "COPY_COUNT_MISMATCH",
                f"The pillar grid needs exactly {len(expected)} pillars, found {len(items)}.",
                path="systems_practice.pillars",
                selector="ul.pillar-grid > li.pillar",
                expected=str(len(expected)),
                found=str(len(items)),
                node=node,
            )
            return
        for item, entry in zip(items, expected, strict=True):
            base = f"systems_practice.pillars[{int(entry['index']) - 1}]"
            if item.get("data-index") != entry["index"]:
                self.issue(
                    "ATTRIBUTE_MISMATCH",
                    "Each pillar needs data-index with its two-digit number.",
                    severity="warning",
                    path=base,
                    expected=entry["index"],
                    found=item.get("data-index"),
                    node=item,
                )
            self.expect_text(
                select_one(item, "span.pillar__index"),
                str(entry["index"]),
                path=f"{base}.index",
                selector="li.pillar span.pillar__index",
            )
            self.expect_text(
                select_one(item, "h3"),
                str(entry["title"]),
                path=f"{base}.title",
                selector="li.pillar h3",
            )
            self.expect_text(
                select_one(item, "p"),
                str(entry["description"]),
                path=f"{base}.description",
                selector="li.pillar p",
            )

    def check_capabilities(self, main: Element) -> None:
        section = SECTIONS[1]
        node = select_one(main, f"section#{section.dom_id}")
        if node is None:
            return
        self._intro(section, "div.section-heading > p.section-heading__intro", "")
        groups = select(node, "div.inventory-grid > details.capability-group")
        expected = self.derived["groups"]
        if len(groups) != len(expected):
            self.issue(
                "COPY_COUNT_MISMATCH",
                f"The page needs {len(expected)} capability groups, found {len(groups)}.",
                path="technical_capabilities.groups",
                selector="div.inventory-grid > details.capability-group",
                expected=str(len(expected)),
                found=str(len(groups)),
                node=node,
            )
            return
        for position, (group, entry) in enumerate(zip(groups, expected, strict=True)):
            base = f"technical_capabilities.groups[{position}]"
            self.expect_text(
                select_one(group, "span.capability-group__heading > span:nth-child(2)"),
                str(entry["heading"]),
                path=f"{base}.heading",
                selector="details.capability-group span.capability-group__heading > span:nth-child(2)",
            )
            self.expect_text(
                select_one(group, "span.capability-group__index"),
                str(entry["index"]),
                path=f"{base}.index",
                selector="span.capability-group__index",
            )
            self.expect_list(
                select(group, "ul.capability-list > li"),
                entry["items"],
                path=f"{base}.items",
                selector="ul.capability-list > li",
            )
            if group.has("open") != bool(entry["open"]):
                self.issue(
                    "ATTRIBUTE_MISMATCH",
                    f"This group should be {'open' if entry['open'] else 'closed'} by default.",
                    severity="warning",
                    path=base,
                    expected="open" if entry["open"] else "closed",
                    found="open" if group.has("open") else "closed",
                    node=group,
                )

    def check_context(self, main: Element) -> None:
        section = SECTIONS[2]
        node = select_one(main, f"section#{section.dom_id}")
        if node is None:
            return
        self._intro(section, "div.context-content > p", "")
        organizations = self.derived["organizations"]
        lists = select(node, "div.context-content > ul.organization-list")
        if organizations:
            if not lists:
                self.issue(
                    "COPY_MISSING",
                    "No list carries professional_context.organizations.",
                    path="professional_context.organizations",
                    selector="ul.organization-list",
                    expected=", ".join(organizations),
                )
            else:
                self.expect_list(
                    select(lists[0], "li"),
                    organizations,
                    path="professional_context.organizations",
                    selector="ul.organization-list > li",
                )
        else:
            self.expect_absent(
                lists,
                path="professional_context.organizations",
                selector="ul.organization-list",
                why="no organizations were approved",
            )

    def check_connect(self, main: Element) -> None:
        section = SECTIONS[3]
        node = select_one(main, f"section#{section.dom_id}")
        if node is None:
            return
        intro = _s(_region(self.content, "connect").get("intro"))
        paragraphs = select(node, "div.connect-copy > p")
        # eyebrow paragraph is the first <p>; the intro, when present, is the second.
        if intro:
            self.expect_text(
                paragraphs[1] if len(paragraphs) > 1 else None,
                intro,
                path="connect.intro",
                selector="section#connect div.connect-copy > p:last-child",
            )
        else:
            self.expect_absent(
                paragraphs[1:],
                path="connect.intro",
                selector="div.connect-copy > p",
                why="connect.intro is empty",
            )
        destinations = self.derived["destinations"]
        lists = select(node, "ul.destination-list")
        if not destinations:
            self.expect_absent(
                lists,
                path="connect.destinations",
                selector="ul.destination-list",
                why="no destinations were approved",
            )
            return
        if not lists:
            self.issue(
                "COPY_MISSING",
                "No list carries connect.destinations.",
                path="connect.destinations",
                selector="ul.destination-list",
            )
            return
        items = select(lists[0], "ul.destination-list > li")
        if len(items) != len(destinations):
            self.issue(
                "COPY_COUNT_MISMATCH",
                f"connect.destinations has {len(destinations)} links but the page shows {len(items)}.",
                path="connect.destinations",
                selector="ul.destination-list > li",
                expected=str(len(destinations)),
                found=str(len(items)),
                node=lists[0],
            )
            return
        for index, (item, entry) in enumerate(zip(items, destinations, strict=True)):
            base = f"connect.destinations[{index}]"
            link = select_one(item, "a")
            if link is None:
                self.issue("STRUCTURE_MISSING", f"{base} has no link.", path=base, node=item)
                continue
            self.expect_href(link, str(entry["url"]), path=f"{base}.url")
            self.expect_text(
                select_one(link, "a > span:nth-child(1)"),
                str(entry["label"]),
                path=f"{base}.label",
                selector="ul.destination-list a > span:nth-child(1)",
            )
            if item.has_class("destination-list__featured") != bool(entry["featured"]):
                self.issue(
                    "COPY_MISMATCH",
                    f"{base}.featured is {entry['featured']}, so the item {'needs' if entry['featured'] else 'must not have'} class destination-list__featured.",
                    path=f"{base}.featured",
                    expected=str(entry["featured"]),
                    found=str(item.has_class("destination-list__featured")),
                    node=item,
                )
            if entry["new_tab"]:
                rel = set((link.get("rel") or "").split())
                if link.get("target") != "_blank" or not {"noopener", "noreferrer"} <= rel:
                    self.issue(
                        "LINK_NEW_TAB_REQUIRED",
                        'External links must use target="_blank" rel="noopener noreferrer" so the preview frame never navigates away.',
                        path=f"{base}.url",
                        expected='target="_blank" rel="noopener noreferrer"',
                        found=f'target="{link.get("target")}" rel="{link.get("rel")}"',
                        node=link,
                    )

    def check_footer(self, footer: Element) -> None:
        info = self.derived["footer"]
        paragraph = select_one(footer, ".site-footer__inner > p")
        expected = " ".join(part for part in (info["name"], info["location"]) if part)
        self.expect_text(
            paragraph,
            expected,
            path="hero.name+hero.location",
            selector="footer.site-footer .site-footer__inner > p",
            visible=True,
        )
        link = select_one(footer, 'a[href="#home"]')
        if link is None:
            self.issue(
                "STRUCTURE_MISSING",
                'The footer needs a "Back to top" link to #home.',
                selector='footer a[href="#home"]',
            )
        else:
            self.expect_text(
                link,
                "Back to top",
                path="chrome.back_to_top",
                selector='footer a[href="#home"]',
                visible=True,
            )


def _section_key(dom_id: str) -> str:
    for section in SECTIONS:
        if section.dom_id == dom_id:
            return section.key
    return dom_id
