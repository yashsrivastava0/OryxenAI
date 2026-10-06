"""Test and CLI helpers around the themes' host renderers.

Rendering itself is owned by each theme contract (``render_body``) and used by the
production pipeline. This module adds the whole-document helper, the CLI ``--mock``
model client's golden output, and the symbolic exemplar embedded in the model prompt
for themes that still use the model path.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from oryxenai.themes import DEFAULT_THEME_ID, get_theme


def render_body(
    page_content: Mapping[str, Any],
    derived: Mapping[str, Any] | None = None,
    *,
    theme_id: str = DEFAULT_THEME_ID,
) -> str:
    """The host-rendered body for ``page_content`` (valid by construction)."""
    return get_theme(theme_id).contract.render_body(page_content, derived)  # type: ignore[attr-defined,no-any-return]


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
