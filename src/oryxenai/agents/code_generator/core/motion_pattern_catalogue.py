"""Deterministic motion pattern catalogue.

Extends this codebase's proven "deterministic catalogue + model selects by
ID, never free invention" pattern -- already used for image/font/component
resources in Build Preparation and Visual Design Director -- to motion. A
`MotionBeatV4` may optionally set `pattern_id` to one of these entries;
when set, the generation contract instructs route_batch/route_compose to
apply the named trusted CSS class/component from the scaffold's
`SharedSystems.tsx`/`motion.css` exactly, instead of hand-authoring new
CSS/JS for that beat. Beats without a `pattern_id` keep the prior,
fully free-form behavior -- this catalogue is a per-beat menu the planner
may reach for, never a default or blanket instruction.

Deliberately small (3 entries): these cover the large majority of what
real reference sites use section-to-section and need no rAF loop or
scroll-progress math, keeping implementation and verification risk low.
A follow-up pass can add count-up, parallax-drift, and hover patterns.
"""

from __future__ import annotations

from typing import NamedTuple


class MotionPattern(NamedTuple):
    pattern_id: str
    description: str
    trusted_binding: str


MOTION_PATTERN_CATALOGUE: tuple[MotionPattern, ...] = (
    MotionPattern(
        pattern_id="reveal-fade-rise",
        description=(
            "Viewport trigger; opacity 0->1 and translateY(28px->0); "
            "easeOutCubic-family, ~600-900ms, plays once."
        ),
        trusted_binding="the trusted <Reveal> component from SharedSystems.tsx",
    ),
    MotionPattern(
        pattern_id="reveal-clip-lines",
        description=(
            "Viewport/load trigger; text wrapped in an overflow:hidden clip "
            "box, inner span translateY(115%->0) and opacity 0->1, staggered "
            "per line/word; easeOutExpo-family."
        ),
        trusted_binding=(
            'the trusted <Reveal pattern="reveal-clip-lines"> component from '
            "SharedSystems.tsx (same component as reveal-fade-rise, different pattern prop)"
        ),
    ),
    MotionPattern(
        pattern_id="stagger-group",
        description=(
            "Viewport trigger on a list; each child gets reveal-fade-rise "
            "with an index-driven transition-delay."
        ),
        trusted_binding=(
            "the trusted <StaggerGroup> component from SharedSystems.tsx, "
            "which sets --stagger-index on each child automatically"
        ),
    ),
)

MOTION_PATTERN_IDS: frozenset[str] = frozenset(item.pattern_id for item in MOTION_PATTERN_CATALOGUE)

_MOTION_PATTERN_BY_ID: dict[str, MotionPattern] = {
    item.pattern_id: item for item in MOTION_PATTERN_CATALOGUE
}


def get_motion_pattern(pattern_id: str) -> MotionPattern | None:
    return _MOTION_PATTERN_BY_ID.get(pattern_id)


def describe_motion_pattern_catalogue() -> str:
    """Render the catalogue as prompt-ready menu text: one line per
    pattern, id plus its one-line mechanical description."""

    return "\n".join(
        f"- `{item.pattern_id}`: {item.description}" for item in MOTION_PATTERN_CATALOGUE
    )


__all__ = [
    "MOTION_PATTERN_CATALOGUE",
    "MOTION_PATTERN_IDS",
    "MotionPattern",
    "describe_motion_pattern_catalogue",
    "get_motion_pattern",
]
