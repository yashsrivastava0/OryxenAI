"""Strict one-page contract shared by the two independent prototype designs."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from oryxenai.themes.editorial_forest.v1.contract import _css_classes, monogram
from oryxenai.themes.htmltree import Element, normalize_text, select_one
from oryxenai.themes.issues import Issue

_LANG = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,3}$")
_TAGS = frozenset(
    {
        "a",
        "article",
        "aside",
        "div",
        "em",
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
_ATTRS = {
    "*": frozenset(
        {
            "class",
            "id",
            "aria-hidden",
            "aria-label",
            "aria-labelledby",
            "role",
            "tabindex",
            "data-field",
            "data-step",
            "data-css-progress",
        }
    ),
    "a": frozenset({"href", "target", "rel"}),
}
_CHROME = frozenset(
    {
        "Skip to content",
        "Practice",
        "Practice areas",
        "Capabilities",
        "About",
        "Contact",
        "Portfolio",
        "01",
        "02",
        "03",
        "04",
        "↗",
        "↘",
        "Selected focus",
        "Explore",
        "Back to top",
    }
)
_SECTION_KEYS = (
    ("systems_practice", "practice"),
    ("technical_capabilities", "capabilities"),
    ("professional_context", "about"),
    ("connect", "contact"),
)


def _string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _region(content: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = content.get(key)
    return value if isinstance(value, Mapping) else {}


class PrototypeContract:
    default_language = "en"
    allowed_tags = _TAGS
    allowed_attributes: Mapping[str, frozenset[str]] = _ATTRS
    chrome_strings = _CHROME

    def __init__(
        self,
        root: Path,
        *,
        theme_id: str,
        body_class: str,
        theme_color: str,
        section_classes: Mapping[str, str],
    ) -> None:
        self.root = root
        self.theme_id = theme_id
        self.body_class = body_class
        self.theme_color = theme_color
        self.section_classes = section_classes
        self._env = Environment(
            loader=FileSystemLoader(str(root)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )

    def class_vocabulary(self) -> frozenset[str]:
        return _css_classes((self.root / "styles.css").read_text(encoding="utf-8"))

    def valid_language(self, lang: str) -> bool:
        return bool(_LANG.fullmatch(lang))

    def asset_paths(self) -> frozenset[str]:
        return frozenset()

    def derive(self, page_content: Mapping[str, Any]) -> dict[str, Any]:
        hero = _region(page_content, "hero")
        destinations = _region(page_content, "connect").get("destinations")
        return {
            "monogram": (
                "{derived.monogram}"
                if _string(hero.get("name")) == "{hero.name}"
                else monogram(_string(hero.get("name")))
            ),
            "destinations": [
                {
                    "label": _string(item.get("label")),
                    "url": _string(item.get("url")),
                    "external": _string(item.get("url")).lower().startswith(("http://", "https://"))
                    or _string(item.get("url")).startswith("{connect.destinations["),
                }
                for item in (destinations if isinstance(destinations, list) else [])
                if isinstance(item, Mapping)
            ],
        }

    def approved_text(
        self, page_content: Mapping[str, Any], derived: Mapping[str, Any]
    ) -> set[str]:
        approved = set(_CHROME)

        def collect(node: Any, key: str = "") -> None:
            if key == "url":
                return
            if isinstance(node, str):
                value = normalize_text(node)
                if value:
                    approved.add(value)
            elif isinstance(node, Mapping):
                for child_key, value in node.items():
                    collect(value, str(child_key))
            elif isinstance(node, list):
                for item in node:
                    collect(item)

        collect(page_content)
        approved.add(str(derived.get("monogram", "")))
        approved.update(f"{index:02d}" for index in range(1, 9))
        return approved

    def approved_urls(self, page_content: Mapping[str, Any]) -> set[str]:
        return {item["url"] for item in self.derive(page_content)["destinations"] if item["url"]}

    def render_head(
        self, page_content: Mapping[str, Any], derived: Mapping[str, Any], lang: str
    ) -> str:
        metadata = _region(page_content, "metadata")
        safe_lang = lang if self.valid_language(lang) else self.default_language
        return (
            "<!doctype html>\n"
            f'<html lang="{html.escape(safe_lang, quote=True)}">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<meta name="theme-color" content="{self.theme_color}">\n'
            f'<meta name="description" content="{html.escape(_string(metadata.get("description")), quote=True)}">\n'
            f"<title>{html.escape(_string(metadata.get('title')))}</title>\n"
            '<link rel="icon" href="data:,">\n'
            '<link rel="stylesheet" href="./styles.css">\n'
            f'</head>\n<body class="{self.body_class}">\n'
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
        rules = (self.root / "contract_rules.md").read_text(encoding="utf-8").strip()
        exemplar = self.render_reference_body(_symbolic_content())
        return f"{rules}\n\n<exemplar>\n{exemplar}</exemplar>"

    def validate_body(
        self, root: Element, page_content: Mapping[str, Any], derived: Mapping[str, Any]
    ) -> list[Issue]:
        issues: list[Issue] = []
        positions: list[int] = []
        nodes = list(root.iter_descendants())
        for section_id in ("top", "practice", "capabilities", "about", "contact"):
            node = select_one(root, f"#{section_id}")
            if node is None:
                issues.append(Issue("THEME_SECTION_MISSING", "error", f"Missing #{section_id}."))
                continue
            positions.append(nodes.index(node))
            expected_class = self.section_classes[section_id]
            if expected_class not in node.classes:
                issues.append(
                    Issue("THEME_SECTION_CLASS", "error", f"#{section_id} needs {expected_class}.")
                )
        if positions != sorted(positions):
            issues.append(
                Issue("THEME_SECTION_ORDER", "error", "Portfolio sections are out of order.")
            )

        expected = _expected_fields(page_content)
        found: dict[str, list[Element]] = {}
        for node in nodes:
            path = node.get("data-field")
            if path is not None:
                found.setdefault(path, []).append(node)
        for path, (value, section_id) in expected.items():
            matches = found.pop(path, [])
            if len(matches) != 1:
                issues.append(
                    Issue("CONTENT_BINDING_COUNT", "error", f"{path} must appear once.", path=path)
                )
                continue
            node = matches[0]
            if node.text() != normalize_text(value):
                issues.append(
                    Issue(
                        "CONTENT_BINDING_VALUE",
                        "error",
                        f"{path} differs from approved copy.",
                        path=path,
                    )
                )
            ancestor: Element | None = node
            while ancestor is not None and ancestor.get("id") != section_id:
                if ancestor.get("aria-hidden") == "true":
                    break
                ancestor = ancestor.parent
            if ancestor is None or ancestor.get("aria-hidden") == "true":
                issues.append(
                    Issue(
                        "CONTENT_BINDING_SECTION",
                        "error",
                        f"{path} is outside #{section_id} or hidden.",
                        path=path,
                    )
                )
            if path.startswith("connect.destinations[") and node.get("href") != _destination_url(
                page_content, path
            ):
                issues.append(
                    Issue("CONTENT_BINDING_URL", "error", f"{path} has the wrong URL.", path=path)
                )
        for path in found:
            issues.append(Issue("CONTENT_BINDING_EXTRA", "error", f"Unexpected data-field {path}."))
        return issues


def _destination_url(content: Mapping[str, Any], path: str) -> str:
    index = int(path.split("[")[1].split("]")[0])
    destinations = _region(content, "connect").get("destinations")
    if not isinstance(destinations, list) or index >= len(destinations):
        return ""
    item = destinations[index]
    return _string(item.get("url")) if isinstance(item, Mapping) else ""


def _expected_fields(content: Mapping[str, Any]) -> dict[str, tuple[str, str]]:
    fields: dict[str, tuple[str, str]] = {}

    def add(path: str, value: Any, section: str) -> None:
        if _string(value):
            fields[path] = (_string(value), section)

    for key, value in _region(content, "hero").items():
        add(f"hero.{key}", value, "top")
    for index, value in enumerate(content.get("marquee_keywords", [])):
        add(f"marquee_keywords[{index}]", value, "practice")
    for key, section in _SECTION_KEYS:
        region = _region(content, key)
        for field in ("eyebrow", "heading", "intro"):
            add(f"{key}.{field}", region.get(field), section)
    for index, pillar in enumerate(_region(content, "systems_practice").get("pillars", [])):
        if isinstance(pillar, Mapping):
            for field in ("title", "description"):
                add(f"systems_practice.pillars[{index}].{field}", pillar.get(field), "practice")
    for index, group in enumerate(_region(content, "technical_capabilities").get("groups", [])):
        if isinstance(group, Mapping):
            add(
                f"technical_capabilities.groups[{index}].heading",
                group.get("heading"),
                "capabilities",
            )
            for item_index, item in enumerate(group.get("items", [])):
                add(
                    f"technical_capabilities.groups[{index}].items[{item_index}]",
                    item,
                    "capabilities",
                )
    for index, item in enumerate(_region(content, "professional_context").get("organizations", [])):
        add(f"professional_context.organizations[{index}]", item, "about")
    for index, item in enumerate(_region(content, "connect").get("destinations", [])):
        if isinstance(item, Mapping):
            add(f"connect.destinations[{index}].label", item.get("label"), "contact")
    return fields


def _symbolic_content() -> dict[str, Any]:
    def region(name: str) -> dict[str, Any]:
        return {field: f"{{{name}.{field}}}" for field in ("eyebrow", "heading", "intro")}

    hero = {
        field: f"{{hero.{field}}}"
        for field in (
            "name",
            "eyebrow_primary",
            "eyebrow_secondary",
            "headline_prefix",
            "headline_emphasis",
            "intro",
            "location",
            "primary_cta_label",
            "secondary_cta_label",
        )
    }
    return {
        "hero": hero,
        "metadata": {"title": "{metadata.title}", "description": "{metadata.description}"},
        "marquee_keywords": [f"{{marquee_keywords[{i}]}}" for i in range(3)],
        "systems_practice": {
            **region("systems_practice"),
            "pillars": [
                {
                    field: f"{{systems_practice.pillars[{i}].{field}}}"
                    for field in ("title", "description")
                }
                for i in range(4)
            ],
        },
        "technical_capabilities": {
            **region("technical_capabilities"),
            "groups": [
                {
                    "heading": f"{{technical_capabilities.groups[{i}].heading}}",
                    "items": [
                        f"{{technical_capabilities.groups[{i}].items[{j}]}}" for j in range(2)
                    ],
                }
                for i in range(2)
            ],
        },
        "professional_context": {
            **region("professional_context"),
            "organizations": [f"{{professional_context.organizations[{i}]}}" for i in range(2)],
        },
        "connect": {
            **region("connect"),
            "destinations": [
                {
                    "label": f"{{connect.destinations[{i}].label}}",
                    "url": f"{{connect.destinations[{i}].url}}",
                }
                for i in range(2)
            ],
        },
    }
