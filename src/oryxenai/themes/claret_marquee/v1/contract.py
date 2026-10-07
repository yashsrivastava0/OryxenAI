"""Exact generated-markup contract for Claret Marquee v1.

The page body is a pure function of ``page_content`` (host-rendered, no model call) and is
then validated like any other body: closed-world visible text, allow-listed tags and
attributes, a class vocabulary taken from ``style.css`` and the route/copy rules below.
"""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from oryxenai.agents.content_architect.page_content import (
    atlas_sample_groups,
    resolve_field_path,
)
from oryxenai.themes.editorial_forest.v1.contract import _css_classes, monogram
from oryxenai.themes.htmltree import Element, normalize_text, select, select_one
from oryxenai.themes.issues import Issue
from oryxenai.themes.placeholders import placeholderize

THEME_ID = "claret-marquee/v1"
SAMPLE_LABEL = "Sample content — replace with your own details."
ILLUSTRATIVE_LABEL = "Illustrative concept — not real client work"

_LANG = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,3}$")
_RTL_LANGUAGES = frozenset({"ar", "he", "fa", "ur", "ps", "sd", "ug", "yi", "dv"})
_ARTS = ("aperture", "reel", "strata", "ribbon", "grid", "halftone")
_TONES = frozenset({"1", "2", "3", "4"})
_SIZES = frozenset({"xs", "s", "m", "l", "xl"})
_SCENES = frozenset({"hero"})

# Character-count ceilings for the host-derived ``data-len`` size classes (xs, s, m, l; else xl).
_NAME_LIMITS = (10, 14, 20, 32)
_HEADLINE_LIMITS = (28, 48, 90, 140)
_TEXT_LIMITS = (24, 40, 80, 140)

_TAGS = frozenset(
    {
        "a",
        "article",
        "blockquote",
        "dd",
        "div",
        "dl",
        "dt",
        "em",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "header",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "section",
        "span",
        "strong",
        "ul",
    }
)
_ATTRS: Mapping[str, frozenset[str]] = {
    "*": frozenset(
        {"class", "id", "aria-hidden", "aria-label", "aria-labelledby", "role", "data-field"}
    ),
    "a": frozenset({"href", "target", "rel"}),
    "article": frozenset({"data-view", "data-title"}),
    "div": frozenset({"data-art", "data-tone", "data-count"}),
    "figure": frozenset({"data-initials"}),
    "h1": frozenset({"data-len"}),
    "h2": frozenset({"data-len"}),
    "h3": frozenset({"data-len"}),
    "ol": frozenset({"data-count"}),
    "p": frozenset({"data-len"}),
    "section": frozenset({"data-scene", "data-chapter"}),
    "span": frozenset({"aria-live"}),
    "ul": frozenset({"data-count"}),
}
_CHROME = frozenset(
    {
        "Skip to content",
        "Main navigation",
        "Footer navigation",
        "Home",
        "Work",
        "About",
        "Contact",
        "Let's talk",
        "Explore selected work",
        "Get to know me",
        "Get in touch",
        "Back to top",
        "Areas of practice",
        "Selected results",
        "Selected work",
        "Selected project",
        "Case study",
        "View case study",
        "Visit project",
        "Illustrative concept — not real client work",
        "Work in progress",
        "Your story can grow here.",
        "Project details can be added whenever you're ready.",
        "Experience",
        "Education",
        "Next",
        "See the work",
        "Explore all work",
        "All work",
        "Role",
        "Period",
        "Problem",
        "Approach",
        "Outcome",
        "Abstract artwork",
        "Conceptual artwork — illustrative, not a product screenshot.",
        SAMPLE_LABEL,
    }
)

# Where the visible sample label must appear exactly once (when a section holds sample rows).
_SAMPLE_HOSTS = {
    "statistics": "#home .proof-head > .meta",
    "experience": "#about .experience .section-head > .meta",
    "education": "#about .education .section-head > .meta",
}


def _region(content: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = content.get(key)
    return value if isinstance(value, Mapping) else {}


def _projects(content: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = _region(content, "atlas").get("projects", [])
    return [item for item in raw if isinstance(item, Mapping)] if isinstance(raw, list) else []


def _size(length: int, limits: tuple[int, int, int, int]) -> str:
    for label, ceiling in zip(("xs", "s", "m", "l"), limits, strict=True):
        if length <= ceiling:
            return label
    return "xl"


class MarqueeContract:
    theme_id = THEME_ID
    default_language = "en"
    allowed_tags = _TAGS
    allowed_attributes = _ATTRS
    chrome_strings = _CHROME

    def __init__(self, root: Path) -> None:
        self.root = root
        self._env = Environment(
            loader=FileSystemLoader(str(root)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )

    def class_vocabulary(self) -> frozenset[str]:
        return _css_classes((self.root / "style.css").read_text(encoding="utf-8"))

    def valid_language(self, lang: str) -> bool:
        return bool(_LANG.fullmatch(lang))

    def asset_paths(self) -> frozenset[str]:
        return frozenset()

    def derive(self, page_content: Mapping[str, Any]) -> dict[str, Any]:
        hero = _region(page_content, "hero")
        name = str(hero.get("name", ""))
        headline = " ".join(
            part
            for part in (
                str(hero.get("headline_prefix", "")),
                str(hero.get("headline_emphasis", "")),
            )
            if part
        )
        atlas = _region(page_content, "atlas")
        return {
            "monogram": "{derived.monogram}" if name == "{hero.name}" else monogram(name),
            "home_label": f"{name}, home",
            "arts": _ARTS,
            "sample": atlas_sample_groups(dict(page_content)),
            "len": {
                "name": _size(len(name), _NAME_LIMITS),
                "headline": _size(len(headline), _HEADLINE_LIMITS),
                "thesis": _size(
                    len(str(_region(page_content, "systems_practice").get("heading", ""))),
                    _TEXT_LIMITS,
                ),
                "about": _size(len(str(atlas.get("about_heading", ""))), _TEXT_LIMITS),
                "connect": _size(
                    len(str(_region(page_content, "connect").get("heading", ""))), _TEXT_LIMITS
                ),
                "titles": [
                    _size(len(str(project.get("title", ""))), _TEXT_LIMITS)
                    for project in _projects(page_content)
                ],
            },
        }

    def approved_text(
        self, page_content: Mapping[str, Any], derived: Mapping[str, Any]
    ) -> set[str]:
        approved = set(_CHROME)

        def collect(value: Any, key: str = "") -> None:
            if key in {"url", "external_url"}:
                return
            if isinstance(value, str):
                if normalized := normalize_text(value):
                    approved.add(normalized)
            elif isinstance(value, Mapping):
                for child_key, child in value.items():
                    collect(child, str(child_key))
            elif isinstance(value, list):
                for child in value:
                    collect(child)

        collect(page_content)
        approved.update(
            normalize_text(str(value)) for value in derived.values() if isinstance(value, str)
        )
        for project in _projects(page_content):
            approved.add(normalize_text(f"{project.get('title', '')} case study"))
        return approved

    def approved_urls(self, page_content: Mapping[str, Any]) -> set[str]:
        urls = {
            str(item.get("url", ""))
            for item in _region(page_content, "connect").get("destinations", [])
            if isinstance(item, Mapping)
        }
        urls.update(str(item.get("external_url", "")) for item in _projects(page_content))
        return {url for url in urls if url}

    def render_head(
        self, page_content: Mapping[str, Any], derived: Mapping[str, Any], lang: str
    ) -> str:
        del derived
        safe_lang = lang if self.valid_language(lang) else self.default_language
        direction = ' dir="rtl"' if safe_lang.split("-")[0].lower() in _RTL_LANGUAGES else ""
        metadata = _region(page_content, "metadata")
        title = html.escape(str(metadata.get("title", "")))
        description = html.escape(str(metadata.get("description", "")), quote=True)
        return (
            f'<!doctype html>\n<html lang="{html.escape(safe_lang, quote=True)}"{direction}>\n'
            '<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<meta name="color-scheme" content="dark light">\n'
            '<meta name="theme-color" content="#f6eee3" media="(prefers-color-scheme: light)">\n'
            '<meta name="theme-color" content="#170910" media="(prefers-color-scheme: dark)">\n'
            f'<meta name="description" content="{description}">\n<title>{title}</title>\n'
            '<link rel="icon" href="data:,">\n<link rel="stylesheet" href="./style.css">\n'
            '<script src="./theme.js" defer></script>\n</head>\n<body>\n'
        )

    def render_tail(self) -> str:
        return "\n</body>\n</html>\n"

    def render_body(
        self, page_content: Mapping[str, Any], derived: Mapping[str, Any] | None = None
    ) -> str:
        del derived
        return self.render_reference_body(page_content)

    def render_reference_body(self, page_content: Mapping[str, Any]) -> str:
        return (
            self._env.get_template("body.html.j2")
            .render(c=page_content, d=self.derive(page_content))
            .strip()
            + "\n"
        )

    def prompt_contract(self) -> str:
        return (self.root / "contract_rules.md").read_text(encoding="utf-8").strip() + (
            "\n\n<exemplar>\n" + self.render_reference_body(exemplar_content()) + "</exemplar>"
        )

    def validate_body(
        self, root: Element, page_content: Mapping[str, Any], derived: Mapping[str, Any]
    ) -> list[Issue]:
        del derived
        issues: list[Issue] = []
        projects = _projects(page_content)
        expected_routes = ["home", "about"] + [
            f"case-{index}"
            for index, project in enumerate(projects, 1)
            if project.get("problem") and project.get("approach")
        ]
        views = [
            node for node in select(root, "article.route-view") if node.get("data-view") is not None
        ]
        found_routes = [node.get("id") for node in views]
        if found_routes != expected_routes:
            issues.append(
                Issue(
                    "MARQUEE_ROUTES",
                    "error",
                    "The route list differs from approved content.",
                    expected=str(expected_routes),
                    found=str(found_routes),
                )
            )
        for view in views:
            if len(select(view, "h1")) != 1:
                issues.append(
                    Issue(
                        "MARQUEE_H1",
                        "error",
                        "Each route needs exactly one h1.",
                        found=str(view.get("id")),
                    )
                )
            expected_title = self._route_title(view.get("id") or "", page_content)
            if view.get("data-title") != expected_title:
                issues.append(
                    Issue(
                        "MARQUEE_TITLE",
                        "error",
                        f"The data-title of route #{view.get('id')} differs from approved copy.",
                        expected=expected_title,
                        found=str(view.get("data-title")),
                    )
                )
        if select_one(root, "#work") is None or select_one(root, "#contact") is None:
            issues.append(
                Issue("MARQUEE_SECTION", "error", "Home needs Work and Contact sections.")
            )
        issues.extend(self._check_attributes(root, page_content))
        issues.extend(self._check_labels(root, page_content))
        return issues

    def _check_attributes(self, root: Element, page_content: Mapping[str, Any]) -> list[Issue]:
        issues: list[Issue] = []
        for node in root.iter_descendants():
            permitted = _ATTRS["*"] | _ATTRS.get(node.tag, frozenset())
            for attr in node.attrs:
                if attr not in permitted:
                    issues.append(
                        Issue("MARQUEE_ATTRIBUTE", "error", f"{attr} is not a Marquee attribute.")
                    )
            if node.get("data-art") and node.get("data-art") not in _ARTS:
                issues.append(Issue("MARQUEE_ART", "error", "Unknown artwork variant."))
            if node.get("data-tone") and node.get("data-tone") not in _TONES:
                issues.append(Issue("MARQUEE_TONE", "error", "Unknown artwork tone."))
            if node.get("data-len") and node.get("data-len") not in _SIZES:
                issues.append(Issue("MARQUEE_SIZE", "error", "Unknown size class."))
            if node.get("data-count") is not None and not (node.get("data-count") or "").isdigit():
                issues.append(Issue("MARQUEE_COUNT", "error", "data-count must be a number."))
            if node.get("data-scene") is not None and node.get("data-scene") not in _SCENES:
                issues.append(Issue("MARQUEE_SCENE", "error", "Unknown scene."))
            field = node.get("data-field")
            if field:
                value = resolve_field_path(dict(page_content), field)
                if not isinstance(value, str) or node.text() != normalize_text(value):
                    issues.append(
                        Issue(
                            "MARQUEE_FIELD",
                            "error",
                            f"{field} differs from approved copy.",
                            path=field,
                        )
                    )
        return issues

    def _check_labels(self, root: Element, page_content: Mapping[str, Any]) -> list[Issue]:
        issues: list[Issue] = []
        for group, has_samples in atlas_sample_groups(dict(page_content)).items():
            labels = select(root, _SAMPLE_HOSTS[group])
            expected_count = 1 if has_samples else 0
            if len(labels) != expected_count or any(
                label.text() != SAMPLE_LABEL for label in labels
            ):
                issues.append(
                    Issue(
                        "MARQUEE_SAMPLE_LABEL",
                        "error",
                        "Every section with sample rows needs the visible sample label, once.",
                        selector=_SAMPLE_HOSTS[group],
                        expected=f"{expected_count} x {SAMPLE_LABEL}",
                        found="; ".join(label.text() for label in labels),
                    )
                )
        for index, project in enumerate(_projects(page_content), 1):
            if project.get("kind") != "illustrative":
                continue
            card = select_one(root, f".work-list .project:nth-child({index})")
            case = select_one(root, f"#case-{index}")
            for location in (card, case):
                if location is not None and ILLUSTRATIVE_LABEL not in location.text():
                    issues.append(
                        Issue(
                            "MARQUEE_ILLUSTRATIVE_LABEL",
                            "error",
                            "Illustrative work needs a visible label.",
                        )
                    )
        return issues

    @staticmethod
    def _route_title(route_id: str, content: Mapping[str, Any]) -> str:
        name = str(_region(content, "hero").get("name", ""))
        if route_id == "home":
            return str(_region(content, "metadata").get("title", ""))
        if route_id == "about":
            return f"About — {name}"
        if route_id.startswith("case-"):
            try:
                index = int(route_id.removeprefix("case-")) - 1
                return f"{_projects(content)[index].get('title', '')} — {name}"
            except (ValueError, IndexError):
                pass
        return ""


def exemplar_content() -> dict[str, Any]:
    """Placeholder content (``{path}`` strings) the prompt exemplar is rendered from."""
    link_only = {
        "kind": "real",
        "title": "Title",
        "summary": "Summary",
        "role": "",
        "period": "Period",
        "problem": "",
        "approach": "",
        "outcome": "",
        "external_url": "https://example.com",
    }
    full = {
        "kind": "real",
        "title": "Project",
        "summary": "A project summary.",
        "role": "Role",
        "period": "Period",
        "problem": "A concrete problem.",
        "approach": "A grounded approach.",
        "outcome": "Outcome",
        "external_url": "",
    }
    illustrative = dict(full, kind="illustrative", role="", period="", outcome="")
    sample: dict[str, Any] = {
        "hero": {
            "name": "Example Name",
            "eyebrow_primary": "Field of work",
            "eyebrow_secondary": "Focus",
            "headline_prefix": "Useful",
            "headline_emphasis": "work",
            "intro": "An approved introduction.",
            "location": "Location",
        },
        "metadata": {
            "title": "Example Name — Portfolio",
            "description": "An approved description.",
        },
        "marquee_keywords": ["Practice", "Practice"],
        "systems_practice": {
            "eyebrow": "Practice",
            "heading": "A clear point of view",
            "intro": "An approved statement.",
            "pillars": [{"title": "Approach", "description": "Grounded description."}] * 4,
        },
        "technical_capabilities": {
            "eyebrow": "Toolkit",
            "heading": "Capabilities",
            "intro": "",
            "groups": [{"heading": "Skills", "items": ["Skill", "Skill"]}] * 2,
        },
        "professional_context": {
            "eyebrow": "Background",
            "heading": "Where the work happened",
            "intro": "",
            "organizations": ["Organization", "Organization"],
        },
        "connect": {
            "eyebrow": "Connect",
            "heading": "Let's connect",
            "intro": "An approved invitation.",
            "destinations": [{"label": "Label", "url": "https://example.com"}] * 2,
        },
        "atlas": {
            "about_heading": "About this work",
            "about_intro": "An approved biography.",
            "about_quote": "Quote",
            "experience": [
                {
                    "dates": "Dates",
                    "role": "Role",
                    "organization": "Organization",
                    "description": "Text",
                }
            ]
            * 2,
            "education": [
                {"credential": "Credential", "institution": "Institution", "dates": "Dates"}
            ]
            * 2,
            "statistics": [{"value": "Value", "label": "Label"}] * 2,
            "projects": [full, link_only, illustrative],
        },
    }
    content: dict[str, Any] = placeholderize(sample)
    content["atlas"]["statistics"][0]["kind"] = "sample"
    content["atlas"]["experience"][0]["kind"] = "sample"
    content["atlas"]["education"][0]["kind"] = "sample"
    for index, kind in enumerate(("real", "real", "illustrative")):
        content["atlas"]["projects"][index]["kind"] = kind
    return content
