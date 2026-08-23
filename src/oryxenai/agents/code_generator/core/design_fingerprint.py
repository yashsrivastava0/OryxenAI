"""Content-free v4 design fingerprints and bounded regeneration similarity."""

from __future__ import annotations

import colorsys
import re

from oryxenai.agents.code_generator.core.development_schemas import (
    DesignFingerprintV1,
    ExperienceBlueprintV4,
)


def compile_design_fingerprint(blueprint: ExperienceBlueprintV4) -> DesignFingerprintV1:
    """Normalize design relationships without route, section, copy, or source identities."""

    layout_topology = [
        (
            f"orders:{item.order_mobile}/{item.order_tablet}/{item.order_desktop};"
            f"columns:{item.columns_mobile}/{item.columns_tablet}/{item.columns_desktop};"
            f"measure:{_bucket(item.max_measure_ch, (40, 64, 84))};"
            f"width:{_ratio_bucket(item.width_ratio_min)}-{_ratio_bucket(item.width_ratio_max)};"
            f"overlap:{_ratio_bucket(item.overlap_ratio_max)};sticky:{int(item.sticky_allowed)}"
        )
        for item in blueprint.section_regions
    ]
    colors = [_color_character(item.value) for item in blueprint.tokens.colors]
    spacing = [item.value for item in blueprint.tokens.spacing]
    radii = [item.value for item in blueprint.tokens.radii]
    token_relationships = (
        [f"color:{value}" for value in sorted(colors)]
        + [f"spacing-ratio:{value}" for value in _normalized_ratios(spacing)]
        + [f"radius-ratio:{value}" for value in _normalized_ratios(radii)]
    )
    typography_roles = [
        (
            f"{item.role}:{_family_class(item.family)}:"
            f"weights-{','.join(str(weight) for weight in item.weights)}:"
            f"scale-{_ratio_bucket(item.heading_ratio / 3)}:"
            f"tracking-{_tracking_bucket(item.tracking_em)}"
        )
        for item in blueprint.tokens.typography_roles
    ]
    distinctive_moves = [
        (
            f"{item.implementation_kind}:{item.relationship}:"
            f"{_ratio_bucket(item.minimum_ratio)}-{_ratio_bucket(item.maximum_ratio)}:"
            f"viewports-{','.join(sorted(item.viewports))}"
        )
        for item in blueprint.distinctive_moves
    ]
    motion_vocabulary = [
        (
            f"{item.trigger}:"
            f"{','.join(sorted(change.property_name for change in item.changed_properties))}:"
            f"duration-{_bucket(item.duration_max_ms, (150, 350, 700))}"
        )
        for item in blueprint.motion_beats
    ]
    resource_placement_topology = [
        (
            f"{item.fit}:{item.loading}:"
            f"aspect-{_ratio_bucket(item.aspect_ratio_min)}-"
            f"{_ratio_bucket(item.aspect_ratio_max)}"
        )
        for item in blueprint.resource_placements
    ]
    return DesignFingerprintV1(
        layout_topology=layout_topology,
        token_relationships=token_relationships or ["color:none", "spacing-ratio:none"],
        typography_roles=typography_roles,
        distinctive_moves=distinctive_moves,
        motion_vocabulary=motion_vocabulary,
        resource_placement_topology=resource_placement_topology,
    )


def fingerprint_similarity(left: DesignFingerprintV1, right: DesignFingerprintV1) -> float:
    """Return a weighted Jaccard score across the six normalized dimensions."""

    weighted = (
        ("layout_topology", 0.25),
        ("token_relationships", 0.15),
        ("typography_roles", 0.15),
        ("distinctive_moves", 0.25),
        ("motion_vocabulary", 0.1),
        ("resource_placement_topology", 0.1),
    )
    score = 0.0
    for field_name, weight in weighted:
        first = set(getattr(left, field_name))
        second = set(getattr(right, field_name))
        union = first | second
        dimension = 1.0 if not union else len(first & second) / len(union)
        score += dimension * weight
    return round(score, 6)


def most_similar_fingerprint(
    candidate: DesignFingerprintV1,
    prior: list[DesignFingerprintV1],
) -> tuple[float, DesignFingerprintV1 | None]:
    matches = [(fingerprint_similarity(candidate, item), item) for item in prior]
    return max(matches, key=lambda item: item[0]) if matches else (0.0, None)


def _normalized_ratios(values: list[float]) -> list[str]:
    positive = sorted({float(value) for value in values if float(value) > 0})
    if not positive:
        return []
    basis = positive[0]
    return [f"{value / basis:.2f}" for value in positive]


def _family_class(value: str) -> str:
    normalized = value.casefold()
    if "mono" in normalized:
        return "monospace"
    if "serif" in normalized and "sans" not in normalized:
        return "serif"
    if "sans" in normalized or "grotesk" in normalized or "geist" in normalized:
        return "sans"
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "custom"


def _color_character(value: str) -> str:
    normalized = value.casefold().strip()
    match = re.fullmatch(r"#([0-9a-f]{6})", normalized)
    if match is None:
        return re.sub(r"\s+", "", normalized)[:32]
    red, green, blue = (int(match.group(1)[index : index + 2], 16) / 255 for index in (0, 2, 4))
    hue, saturation, lightness = colorsys.rgb_to_hls(red, green, blue)
    return (
        f"h{int(hue * 12) % 12}:"
        f"s{_bucket(saturation, (0.15, 0.4, 0.7))}:"
        f"l{_bucket(lightness, (0.2, 0.45, 0.7))}"
    )


def _ratio_bucket(value: float) -> str:
    return _bucket(float(value), (0.25, 0.5, 0.75, 1.0))


def _tracking_bucket(value: float) -> str:
    if value < -0.01:
        return "tight"
    if value > 0.02:
        return "open"
    return "neutral"


def _bucket(value: float, boundaries: tuple[float, ...]) -> str:
    for index, boundary in enumerate(boundaries):
        if value <= boundary:
            return str(index)
    return str(len(boundaries))


__all__ = [
    "compile_design_fingerprint",
    "fingerprint_similarity",
    "most_similar_fingerprint",
]
