"""Bounded layout recipes used by the V4 source and runtime contracts."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LayoutRecipeId = Literal[
    "text-with-supporting-media",
    "work-detail-list",
    "timeline-list",
]


class LayoutRecipeV1(BaseModel):
    """A small typed recipe surface the model can select safely."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["code-generator-layout-recipe-v1"] = "code-generator-layout-recipe-v1"
    recipe_id: LayoutRecipeId
    description: str
    direct_child_contract: str
    required_primitives: list[str] = Field(min_length=2, max_length=8)
    required_css_properties: list[str] = Field(min_length=2, max_length=8)
    mobile_css_properties: list[str] = Field(min_length=1, max_length=6)
    image_behavior: str
    motion_behavior: str
    fallback_behavior: str


_CATALOGUE: dict[LayoutRecipeId, LayoutRecipeV1] = {
    "text-with-supporting-media": LayoutRecipeV1(
        recipe_id="text-with-supporting-media",
        description="A text-led section paired with one supporting media frame.",
        direct_child_contract=(
            "The exact region selector owns the direct text and media children; use at least "
            "two direct children and keep the text measure readable."
        ),
        required_primitives=["RouteShell", "LocalImage", "Reveal"],
        required_css_properties=["display", "grid-template-columns", "column-gap", "align-items"],
        mobile_css_properties=["grid-template-columns", "row-gap", "max-width"],
        image_behavior="Render the approved LocalImage inside its own bounded frame; stack it below text on narrow viewports.",
        motion_behavior="Reveal content progressively with a readable default state and a complete reduced-motion state.",
        fallback_behavior="If no approved image is available, keep the text hierarchy and use a quiet CSS surface with no fake image URL.",
    ),
    "work-detail-list": LayoutRecipeV1(
        recipe_id="work-detail-list",
        description="A repeated work or case-study list with stable detail rows.",
        direct_child_contract=(
            "The exact region selector owns repeated direct item children; each item carries "
            "its approved content key and a stable item marker."
        ),
        required_primitives=["RouteShell", "Reveal", "Disclosure"],
        required_css_properties=[
            "display",
            "grid-template-columns",
            "row-gap",
            "border-block-start",
        ],
        mobile_css_properties=["grid-template-columns", "row-gap", "max-width"],
        image_behavior="Treat imagery as a supporting detail inside each item frame and keep every text row usable without it.",
        motion_behavior="Use progressive row reveals only when supported; preserve all rows and details when motion is reduced.",
        fallback_behavior="If optional imagery is unavailable, retain the item rows, labels, and approved details with a structural frame.",
    ),
    "timeline-list": LayoutRecipeV1(
        recipe_id="timeline-list",
        description="A chronological list with a clear spine and readable entries.",
        direct_child_contract=(
            "The exact region selector owns the direct timeline entries and their spine; "
            "do not use absolute positioning for essential entry text."
        ),
        required_primitives=["RouteShell", "Reveal", "Disclosure"],
        required_css_properties=[
            "display",
            "grid-template-columns",
            "row-gap",
            "border-inline-start",
        ],
        mobile_css_properties=["grid-template-columns", "row-gap", "max-width"],
        image_behavior="Use imagery only as optional supporting evidence; the chronology remains complete without it.",
        motion_behavior="Reveal entries in order while keeping the full timeline in normal flow under reduced motion.",
        fallback_behavior="When imagery is not admitted, preserve the spine, dates, and approved narrative as the complete composition.",
    ),
}


def get_layout_recipe(recipe_id: str) -> LayoutRecipeV1:
    """Return a defensive copy of a bounded recipe or the legacy default."""

    selected = recipe_id if recipe_id in _CATALOGUE else "text-with-supporting-media"
    return _CATALOGUE[selected].model_copy(deep=True)


def layout_recipe_catalogue() -> list[LayoutRecipeV1]:
    return [get_layout_recipe(recipe_id) for recipe_id in _CATALOGUE]


def layout_recipe_context(
    regions: Sequence[object],
    *,
    route_ids: set[str] | None = None,
    section_ids: set[str] | None = None,
) -> list[dict[str, object]]:
    """Compile blueprint regions into selector-bound model instructions."""

    result: list[dict[str, object]] = []
    for region in regions:
        route_id = str(getattr(region, "route_id", ""))
        section_id = str(getattr(region, "section_id", ""))
        if route_ids is not None and route_id not in route_ids:
            continue
        if section_ids is not None and section_id not in section_ids:
            continue
        recipe = get_layout_recipe(str(getattr(region, "layout_recipe", "")))
        result.append(
            {
                "route_id": route_id,
                "section_id": section_id,
                "region_id": str(getattr(region, "region_id", "")),
                "region_selector": str(getattr(region, "region_selector", "")),
                "recipe": recipe.model_dump(mode="json"),
                "required_marker": f'[data-region-id="{getattr(region, "region_id", "")}"]',
            }
        )
    return result


def compile_layout_recipe_css(regions: Iterable[object]) -> str:
    """Compile the small trusted layout surface for V4 region owners.

    The model still owns the section markup and visual treatment. These rules
    provide a safe structural floor on the canonical region marker so a
    recipe cannot silently lose its responsive grid, minimum track sizing, or
    readable fallback when a route stylesheet is incomplete.
    """

    lines = [
        "/* Trusted layout recipe floor compiled from the V4 blueprint. */",
    ]
    seen: set[str] = set()
    for region in regions:
        region_id = str(getattr(region, "region_id", "")).strip()
        if not region_id or region_id in seen:
            continue
        seen.add(region_id)
        escaped_id = region_id.replace("\\", "\\\\").replace('"', '\\"')
        selector = f'[data-region-id="{escaped_id}"]'
        gap = getattr(region, "gap", None)
        gap_value = f"{float(getattr(gap, 'value', 0) or 0):g}{getattr(gap, 'unit', 'px')}"
        recipe = get_layout_recipe(str(getattr(region, "layout_recipe", "")))
        lines.extend(
            [
                "",
                f"{selector} {{",
                "  min-width: 0;",
                "  max-width: 100%;",
                "  display: grid;",
                "  grid-template-columns: minmax(0, 1fr);",
                f"  row-gap: {gap_value};",
                f"  column-gap: {gap_value};",
                "  align-items: start;",
                "}",
                f"{selector} > * {{",
                "  min-width: 0;",
                "  max-width: 100%;",
                "}",
            ]
        )
        if recipe.recipe_id == "text-with-supporting-media":
            lines.extend(
                [
                    "",
                    "@media (min-width: 768px) {",
                    f"  {selector}:has(> :nth-child(2)) {{",
                    "    grid-template-columns: minmax(0, 1.12fr) minmax(0, 0.88fr);",
                    f"    column-gap: {gap_value};",
                    "  }",
                    "}",
                ]
            )
        elif recipe.recipe_id == "work-detail-list":
            lines.extend(
                [
                    f"{selector} {{",
                    "  border-block-start: 1px solid currentColor;",
                    "}",
                    "",
                    "@media (min-width: 768px) {",
                    f"  {selector}:has(> :nth-child(2)) {{",
                    "    grid-template-columns: repeat(2, minmax(0, 1fr));",
                    f"    row-gap: {gap_value};",
                    "  }",
                    "}",
                ]
            )
        else:
            lines.extend(
                [
                    f"{selector} {{",
                    "  border-inline-start: 1px solid currentColor;",
                    "  padding-inline-start: 1rem;",
                    "}",
                    "",
                    "@media (min-width: 768px) {",
                    f"  {selector}:has(> :nth-child(2)) {{",
                    "    grid-template-columns: minmax(0, 0.25fr) minmax(0, 1fr);",
                    f"    row-gap: {gap_value};",
                    "  }",
                    "}",
                ]
            )
        lines.extend(
            [
                "",
                "@media (max-width: 767px) {",
                f"  {selector} {{",
                "    grid-template-columns: minmax(0, 1fr);",
                f"    row-gap: {gap_value};",
                "    max-width: 100%;",
                "  }",
                "}",
            ]
        )
    return "\n".join(lines) + ("\n" if len(lines) > 1 else "")


__all__ = [
    "LayoutRecipeId",
    "LayoutRecipeV1",
    "compile_layout_recipe_css",
    "get_layout_recipe",
    "layout_recipe_catalogue",
    "layout_recipe_context",
]
