"""Exact generated-markup contract for Cobalt Atlas v2."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from oryxenai.agents.content_architect.page_content import resolve_field_path
from oryxenai.themes.editorial_forest.v1.contract import _css_classes, monogram
from oryxenai.themes.htmltree import Element, normalize_text, select, select_one
from oryxenai.themes.issues import Issue

_LANG = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,3}$")
_ARTS = ("orbit", "bars", "grid", "waves", "stack", "dots")
_TAGS = frozenset(
    {
        "a",
        "article",
        "b",
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
    "div": frozenset({"data-art", "data-tone"}),
    "figure": frozenset({"data-initials"}),
    "span": frozenset({"aria-live"}),
}
_CHROME = frozenset(
    {
        "Skip to content",
        "Home",
        "Work",
        "About",
        "Contact",
        "Main navigation",
        "Let's talk",
        "Explore selected work",
        "Get to know me",
        "01 / Introduction",
        "Fig. 01",
        "Abstract artwork",
        "Areas of practice",
        "The through line",
        "01 / Selected work",
        "Selected",
        "work.",
        "Projects and ideas shaped by this portfolio.",
        "Project",
        "Illustrative concept",
        "Illustrative concept — not real client work",
        "Work in progress",
        "Your story can grow here.",
        "Project details can be added whenever you're ready.",
        "02 / Measured moments",
        "results.",
        "03 / How I work",
        "Ways of",
        "working.",
        "04 / Let's connect",
        "02 / About",
        "Get in touch",
        "01 / Journey",
        "Experience.",
        "02 / Practice",
        "03 / Foundation",
        "Education.",
        "Next / Selected work",
        "See the work",
        "01 / The opportunity",
        "Problem",
        "02 / The approach",
        "Approach",
        "03 / Outcome",
        "← All work",
        "Back / Selected work",
        "Explore all work",
        "Conceptual artwork",
        "Conceptual artwork — illustrative, not a product screenshot.",
        "Back to top ↑",
        "Role",
        "↗",
        "✳",
        ".",
        "01",
        "02",
        "03",
        "04",
    }
)


def _region(content: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = content.get(key)
    return value if isinstance(value, Mapping) else {}


def _projects(content: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = _region(content, "atlas").get("projects", [])
    return [item for item in raw if isinstance(item, Mapping)] if isinstance(raw, list) else []


class AtlasContract:
    theme_id = "cobalt-atlas/v2"
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
        name = str(_region(page_content, "hero").get("name", ""))
        return {"monogram": monogram(name), "home_label": f"{name}, home", "arts": _ARTS}

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
        for group in _region(page_content, "technical_capabilities").get("groups", []):
            if isinstance(group, Mapping) and isinstance(group.get("items"), list):
                approved.add(normalize_text(" · ".join(str(item) for item in group["items"])))
        for index, project in enumerate(_projects(page_content), 1):
            title = str(project.get("title", ""))
            approved.update(
                {
                    f"{title} case study",
                    f"{title} — {_region(page_content, 'hero').get('name', '')}",
                }
            )
            approved.add(f"0{index} / Selected project")
            approved.add(f"0{index} / Illustrative concept")
            approved.add(f"0{index} / Conceptual artwork")
            approved.add(f"0{index} — Project")
            approved.add(f"0{index} — Illustrative concept — not real client work")
        approved.update(f"0{index}" for index in range(1, 10))
        approved.update(f"Case 0{index}" for index in range(1, 10))
        approved.update(
            f"Case 0{index} / Illustrative concept — not real client work"
            for index, project in enumerate(_projects(page_content), 1)
            if project.get("kind") == "illustrative"
        )
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
        metadata = _region(page_content, "metadata")
        title = html.escape(str(metadata.get("title", "")))
        description = html.escape(str(metadata.get("description", "")), quote=True)
        return (
            f'<!doctype html>\n<html lang="{html.escape(safe_lang, quote=True)}">\n<head>\n'
            '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<meta name="description" content="{description}">\n<title>{title}</title>\n'
            '<link rel="icon" href="data:,">\n<link rel="stylesheet" href="./style.css">\n'
            '<script src="./theme.js" defer></script>\n</head>\n<body>\n'
        )

    def render_tail(self) -> str:
        return "\n</body>\n</html>\n"

    def render_reference_body(self, page_content: Mapping[str, Any]) -> str:
        return (
            self._env.get_template("body.html.j2")
            .render(c=page_content, d=self.derive(page_content))
            .strip()
            + "\n"
        )

    def prompt_contract(self) -> str:
        return (self.root / "contract_rules.md").read_text(encoding="utf-8").strip() + (
            "\n\n<exemplar>\n" + self.render_reference_body(_symbolic_content()) + "</exemplar>"
        )

    def validate_body(
        self, root: Element, page_content: Mapping[str, Any], derived: Mapping[str, Any]
    ) -> list[Issue]:
        del derived
        issues: list[Issue] = []
        expected_routes = ["home", "about"] + [
            f"case-{index}"
            for index, project in enumerate(_projects(page_content), 1)
            if project.get("problem") and project.get("approach")
        ]
        views = [
            node for node in select(root, "article.route-view") if node.get("data-view") is not None
        ]
        found_routes = [node.get("id") for node in views]
        if found_routes != expected_routes:
            issues.append(
                Issue(
                    "ATLAS_ROUTES",
                    "error",
                    "Atlas route list differs from approved content.",
                    expected=str(expected_routes),
                    found=str(found_routes),
                )
            )
        for view in views:
            headings = select(view, "h1")
            if len(headings) != 1:
                issues.append(
                    Issue(
                        "ATLAS_H1",
                        "error",
                        "Each route needs exactly one h1.",
                        found=str(view.get("id")),
                    )
                )
            expected_title = self._route_title(view.get("id") or "", page_content)
            if view.get("data-title") != expected_title:
                issues.append(
                    Issue(
                        "ATLAS_TITLE",
                        "error",
                        "Route title differs from approved copy.",
                        found=str(view.get("id")),
                    )
                )
        if select_one(root, "#work") is None or select_one(root, "#contact") is None:
            issues.append(Issue("ATLAS_SECTION", "error", "Home needs Work and Contact sections."))
        for node in root.iter_descendants():
            for attr in node.attrs:
                if attr not in _ATTRS.get("*", frozenset()) | _ATTRS.get(node.tag, frozenset()):
                    issues.append(
                        Issue("ATLAS_ATTRIBUTE", "error", f"{attr} is not an Atlas attribute.")
                    )
            if node.get("data-art") and node.get("data-art") not in _ARTS:
                issues.append(Issue("ATLAS_ART", "error", "Unknown artwork variant."))
            if node.get("data-tone") and node.get("data-tone") not in {"1", "2", "3", "4"}:
                issues.append(Issue("ATLAS_TONE", "error", "Unknown artwork tone."))
            field = node.get("data-field")
            if field:
                value = resolve_field_path(dict(page_content), field)
                if not isinstance(value, str) or node.text() != normalize_text(value):
                    issues.append(
                        Issue(
                            "ATLAS_FIELD",
                            "error",
                            f"{field} differs from approved copy.",
                            path=field,
                        )
                    )
        for index, project in enumerate(_projects(page_content), 1):
            if project.get("kind") == "illustrative":
                card = select_one(root, f".project-list .project-card:nth-child({index})")
                case = select_one(root, f"#case-{index}")
                for location in (card, case):
                    if (
                        location is not None
                        and "Illustrative concept — not real client work" not in location.text()
                    ):
                        issues.append(
                            Issue(
                                "ATLAS_ILLUSTRATIVE_LABEL",
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


def _symbolic_content() -> dict[str, Any]:
    return {
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
        "marquee_keywords": ["Practice"],
        "systems_practice": {
            "heading": "A clear point of view",
            "intro": "An approved statement.",
            "pillars": [{"title": "Approach", "description": "Grounded description."}],
        },
        "technical_capabilities": {
            "heading": "Capabilities",
            "groups": [{"heading": "Skills", "items": ["Skill"]}],
        },
        "connect": {
            "heading": "Let's connect",
            "intro": "An approved invitation.",
            "destinations": [],
        },
        "atlas": {
            "about_heading": "About this work",
            "about_intro": "An approved biography.",
            "about_quote": "",
            "experience": [],
            "education": [],
            "statistics": [],
            "projects": [
                {
                    "kind": "real",
                    "title": "Project",
                    "summary": "A project summary.",
                    "role": "",
                    "period": "",
                    "problem": "A concrete problem.",
                    "approach": "A grounded approach.",
                    "outcome": "",
                    "external_url": "",
                }
            ],
        },
    }
