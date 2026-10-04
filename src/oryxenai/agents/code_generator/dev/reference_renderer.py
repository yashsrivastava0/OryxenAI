"""Deterministic reference renderer for the Editorial Forest v1 theme.

Dev/test utility only. It renders valid body markup for any approved
``page_content`` so validators, worker tests and the CLI ``--mock`` mode have a
trustworthy golden output, and it generates the symbolic exemplar embedded in
the model prompt so the example can never drift from the validators.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from oryxenai.themes import DEFAULT_THEME_ID, get_theme
from oryxenai.themes.cobalt_atlas.v2.contract import AtlasContract
from oryxenai.themes.prototype_contract import PrototypeContract

_ENV = Environment(
    loader=FileSystemLoader(str(Path(__file__).resolve().parent / "templates")),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
    undefined=StrictUndefined,
    keep_trailing_newline=False,
)
_TEMPLATE = "editorial_forest_v1.body.html.j2"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _region(content: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = content.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def render_body(
    page_content: Mapping[str, Any],
    derived: Mapping[str, Any] | None = None,
    *,
    theme_id: str = DEFAULT_THEME_ID,
) -> str:
    """Render the page body for ``page_content`` (valid by construction)."""
    theme = get_theme(theme_id)
    if isinstance(theme.contract, PrototypeContract):
        return theme.contract.render_reference_body(page_content)
    if isinstance(theme.contract, AtlasContract):
        return theme.contract.render_reference_body(page_content)
    values = dict(derived) if derived is not None else theme.contract.derive(page_content)
    hero = {key: _text(value) for key, value in _region(page_content, "hero").items()}
    for key in (
        "name",
        "eyebrow_primary",
        "eyebrow_secondary",
        "headline_prefix",
        "headline_emphasis",
        "intro",
        "location",
        "primary_cta_label",
        "secondary_cta_label",
    ):
        hero.setdefault(key, "")
    section_keys = {
        "systems": "systems_practice",
        "capabilities": "technical_capabilities",
        "context": "professional_context",
        "connect": "connect",
    }
    sections = {
        name: {
            field: _text(_region(page_content, key).get(field))
            for field in ("eyebrow", "heading", "intro")
        }
        for name, key in section_keys.items()
    }
    return _ENV.get_template(_TEMPLATE).render(
        d=values,
        hero=hero,
        eyebrow=[part for part in (hero["eyebrow_primary"], hero["eyebrow_secondary"]) if part],
        headline_prefix=hero["headline_prefix"],
        headline_emphasis=hero["headline_emphasis"],
        **sections,
    )


def render_document(
    page_content: Mapping[str, Any],
    *,
    lang: str = "en",
    theme_id: str = DEFAULT_THEME_ID,
) -> str:
    """Host head + reference body + tail: a complete, valid ``index.html``."""
    theme = get_theme(theme_id)
    derived = theme.contract.derive(page_content)
    return (
        theme.contract.render_head(page_content, derived, lang)
        + render_body(page_content, derived, theme_id=theme_id)
        + theme.contract.render_tail()
    )


# ── symbolic exemplar (what the model sees) ──────────────────────────────────


def symbolic_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    """Content whose every string is its own ``{path}`` placeholder, plus derived values."""

    def region(prefix: str, **extra: Any) -> dict[str, Any]:
        base = {
            "eyebrow": f"{{{prefix}.eyebrow}}",
            "heading": f"{{{prefix}.heading}}",
            "intro": f"{{{prefix}.intro}}",
        }
        base.update(extra)
        return base

    content: dict[str, Any] = {
        "hero": {
            "name": "{hero.name}",
            "eyebrow_primary": "{hero.eyebrow_primary}",
            "eyebrow_secondary": "{hero.eyebrow_secondary}",
            "headline_prefix": "{hero.headline_prefix}",
            "headline_emphasis": "{hero.headline_emphasis}",
            "intro": "{hero.intro}",
            "location": "{hero.location}",
            "primary_cta_label": "{hero.primary_cta_label}",
            "secondary_cta_label": "{hero.secondary_cta_label}",
        },
        "metadata": {"title": "{metadata.title}", "description": "{metadata.description}"},
        "marquee_keywords": [
            "{derived.marquee.items[0]}",
            "{derived.marquee.items[1]}",
            "{derived.marquee.items[2]}",
        ],
        "systems_practice": region("systems_practice"),
        "technical_capabilities": region("technical_capabilities"),
        "professional_context": region("professional_context"),
        "connect": region("connect"),
    }
    derived: dict[str, Any] = {
        "lang": "en",
        "monogram": "{derived.monogram}",
        "nav": [
            {"id": "systems-practice", "label": "{systems_practice.eyebrow}", "index": "01"},
            {
                "id": "technical-capabilities",
                "label": "{technical_capabilities.eyebrow}",
                "index": "02",
            },
            {
                "id": "professional-context",
                "label": "{professional_context.eyebrow}",
                "index": "03",
            },
            {"id": "connect", "label": "{connect.eyebrow}", "index": "04"},
        ],
        "marquee": {
            "items": [
                "{derived.marquee.items[0]}",
                "{derived.marquee.items[1]}",
                "{derived.marquee.items[2]}",
            ],
            "keywords": [
                "{derived.marquee.items[0]}",
                "{derived.marquee.items[1]}",
                "{derived.marquee.items[2]}",
            ],
            "repeat": 1,
        },
        "pillars": [
            {
                "index": f"{n:02d}",
                "title": f"{{systems_practice.pillars[{n - 1}].title}}",
                "description": f"{{systems_practice.pillars[{n - 1}].description}}",
            }
            for n in range(1, 5)
        ],
        "groups": [
            {
                "index": f"{n:02d}",
                "open": True,
                "heading": f"{{technical_capabilities.groups[{n - 1}].heading}}",
                "items": [
                    f"{{technical_capabilities.groups[{n - 1}].items[{k}]}}" for k in range(2)
                ],
            }
            for n in range(1, 3)
        ],
        "organizations": [
            "{professional_context.organizations[0]}",
            "{professional_context.organizations[1]}",
        ],
        "destinations": [
            {
                "label": "{connect.destinations[0].label}",
                "url": "{connect.destinations[0].url}",
                "featured": True,
                "external": True,
                "new_tab": True,
            },
            {
                "label": "{connect.destinations[1].label}",
                "url": "{connect.destinations[1].url}",
                "featured": False,
                "external": True,
                "new_tab": True,
            },
        ],
        "footer": {"name": "{hero.name}", "location": "{hero.location}"},
        "hero_asset": "./assets/hero-visual.svg",
    }
    return content, derived


def render_symbolic_body() -> str:
    content, derived = symbolic_inputs()
    return render_body(content, derived).strip() + "\n"
