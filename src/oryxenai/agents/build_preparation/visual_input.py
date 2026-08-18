"""Deterministic Build Preparation visual-input normalization.

Visual Design Director owns creative direction when it supplies one.  This
module only fills presentation and retrieval intent that is absent from an
approved Content Architect handoff.  It never creates portfolio facts,
evidence, people, employers, metrics, or private media.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

VISUAL_INPUT_MODES = frozenset({"approved_vdd", "assumed_from_content", "merged_vdd_assumptions"})

_DEFAULT_ASSUMPTIONS = [
    "Editorial imagery is decorative and non-evidentiary.",
    "No portrait, screenshot, dashboard, logo, or project proof is allowed.",
    "Component roles are derived from approved route sections and interaction needs.",
    "All visual resources must be local, attributed, and usable without runtime provider calls.",
    "Reduced motion receives a complete static equivalent.",
]
_IMAGE_FORBIDDEN = [
    "portrait",
    "face",
    "screenshot",
    "dashboard",
    "logo",
    "project proof",
    "employer imagery",
    "private media",
    "testimonial",
]
_IMAGE_ROLE_SPECS = (
    (
        "hero",
        "Editorial opening atmosphere for backend and platform engineering; no person or product interface.",
        ["backend platform engineering", "editorial systems atmosphere", "abstract architecture"],
        "quiet, technical, high-contrast",
        "landscape",
        "16:9",
    ),
    (
        "capabilities",
        "Decorative systems-mapping atmosphere for capability groups; not a real topology.",
        ["backend services", "systems mapping", "network topology abstraction"],
        "structured, analytical, restrained",
        "landscape",
        "3:2",
    ),
    (
        "experience",
        "Editorial infrastructure and delivery atmosphere supporting an experience timeline.",
        ["infrastructure delivery", "deployment pipeline abstraction", "observability mood"],
        "calm, operational, editorial",
        "landscape",
        "3:2",
    ),
    (
        "selected-work",
        "Decorative data-flow atmosphere for selected technical work; no dashboard or screenshot.",
        ["data flow abstraction", "service architecture", "queues caching delivery"],
        "dense, precise, technical",
        "landscape",
        "4:3",
    ),
    (
        "education",
        "Quiet technical-editorial texture for supporting context, without personal imagery.",
        [
            "software engineering editorial texture",
            "abstract infrastructure signal",
            "technical material study",
        ],
        "quiet, spacious, reflective",
        "landscape",
        "3:2",
    ),
    (
        "connect",
        "Non-evidentiary closing atmosphere for a professional connection CTA.",
        [
            "engineering network connection abstraction",
            "platform signal lines",
            "editorial closing field",
        ],
        "open, focused, restrained",
        "landscape",
        "16:9",
    ),
)
_COMPONENT_PROVIDER_VOCABULARY: dict[str, tuple[str, ...]] = {
    "capability-grouping": (
        "accordion",
        "collapsible",
        "disclosure",
        "expandable",
        "progressive disclosure",
        "tabs",
    ),
    "experience-timeline": (
        "timeline",
        "stepper",
        "progression",
        "milestones",
        "chronology",
    ),
    "selected-work-detail": (
        "project detail",
        "expandable cards",
        "dialog",
        "drawer",
        "tabs",
        "case study",
    ),
    "navigation-disclosure": (
        "mobile navigation",
        "navigation disclosure",
        "menu",
        "drawer",
        "popover",
    ),
}


def component_provider_terms(role_id: str) -> list[str]:
    """Return provider-neutral interaction vocabulary for a semantic role."""
    return list(_COMPONENT_PROVIDER_VOCABULARY.get(role_id, ()))


@dataclass(frozen=True)
class NormalizedVisualInput:
    visual: dict[str, Any]
    mode: str
    assumption_hash: str
    assumptions: tuple[str, ...]


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
        ).encode("utf-8")
    ).hexdigest()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value or "")


def _approved_routes(content: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        route
        for route in _as_list(content.get("route_plan"))
        if isinstance(route, dict)
        and route.get("route_id")
        and str(route.get("publication_status", "approved") or "approved") == "approved"
    ]


def _content_sections(content: dict[str, Any], route_id: str) -> list[dict[str, Any]]:
    pack = next(
        (
            item
            for item in _as_list(content.get("page_content_packs"))
            if isinstance(item, dict) and str(item.get("route_id", "")) == route_id
        ),
        {},
    )
    return [item for item in _as_list(pack.get("sections")) if isinstance(item, dict)]


def _section_id(section: dict[str, Any], index: int) -> str:
    return str(section.get("section_id") or section.get("id") or f"section-{index}")


def _section_key(section_id: str) -> str:
    return section_id.casefold().replace("_", "-")


def _section_matches(section_id: str, words: tuple[str, ...]) -> bool:
    key = _section_key(section_id)
    return any(word in key for word in words)


def _route_scene(page: dict[str, Any], section_id: str, fallback: str) -> str:
    for scene in _as_list(page.get("scenes")):
        if not isinstance(scene, dict):
            continue
        refs = {str(item) for item in _as_list(scene.get("content_refs"))}
        if section_id in refs or section_id in str(scene.get("scene_id", "")):
            return str(scene.get("scene_id", "") or fallback)
    scenes = [scene for scene in _as_list(page.get("scenes")) if isinstance(scene, dict)]
    return str(scenes[0].get("scene_id", "") or fallback) if scenes else fallback


def _explicit_prohibits_visual_acquisition(content: dict[str, Any], visual: dict[str, Any]) -> bool:
    policy = _as_dict(visual.get("resource_policy"))
    for key in (
        "allow_editorial_images",
        "external_images_allowed",
        "external_acquisition_allowed",
    ):
        if key in policy and policy[key] is False:
            return True
    if "image_target_count" in policy and int(policy.get("image_target_count") or 0) <= 0:
        return True
    text = _flatten_text(
        [
            visual.get("must_not_fabricate"),
            visual.get("conflicts"),
            visual.get("compiler_handoff"),
            _as_dict(content.get("privacy_and_confidentiality")),
        ]
    ).casefold()
    return bool(
        re.search(
            r"(?:no|without|do not|never|禁止)[^.!?]{0,80}(?:stock|external|editorial|photographic|photo|imagery|images)",
            text,
        )
    )


def _explicitly_prohibits_components(visual: dict[str, Any]) -> bool:
    policy = _as_dict(visual.get("resource_policy"))
    for key in (
        "allow_components",
        "external_components_allowed",
        "component_acquisition_allowed",
    ):
        if key in policy and policy[key] is False:
            return True
    if "component_target_count" in policy and int(policy.get("component_target_count") or 0) <= 0:
        return True
    text = _flatten_text(
        [visual.get("must_not_fabricate"), visual.get("conflicts"), visual.get("compiler_handoff")]
    ).casefold()
    return bool(
        re.search(
            r"(?:no|without|do not|never)[^.!?]{0,80}(?:component|registry|interactive)",
            text,
        )
    )


def _has_meaningful_visual_input(visual: dict[str, Any]) -> bool:
    return bool(
        _as_list(visual.get("pages"))
        or _as_list(visual.get("asset_briefs"))
        or _as_list(visual.get("resource_candidates"))
        or _as_dict(visual.get("visual_language"))
        or _as_dict(visual.get("shared_visual_systems"))
        or _as_dict(visual.get("approved"))
    )


def _page_for(visual: dict[str, Any], route_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in _as_list(visual.get("pages"))
            if isinstance(item, dict) and str(item.get("route_id", "")) == route_id
        ),
        None,
    )


def _ensure_scene(page: dict[str, Any], section_id: str) -> dict[str, Any]:
    for scene in _as_list(page.get("scenes")):
        if isinstance(scene, dict) and section_id in {
            str(item) for item in _as_list(scene.get("content_refs"))
        }:
            return scene
    scene_id = f"{page.get('route_id', 'route')}-scene-{section_id}"
    scene = {
        "scene_id": scene_id,
        "route_id": page.get("route_id", ""),
        "narrative_goal": "Support the approved public section with a restrained, accessible composition.",
        "content_refs": [section_id],
        "asset_requirements": [],
        "resource_candidates": [],
        "responsive_behavior": "Stack on narrow screens and preserve all essential content in document flow.",
        "reduced_motion_behavior": "Render the complete static state without sequencing or movement.",
    }
    page.setdefault("scenes", []).append(scene)
    return scene


def _route_section_descriptors(
    content: dict[str, Any], visual: dict[str, Any]
) -> list[tuple[dict[str, Any], dict[str, Any], str, str]]:
    descriptors: list[tuple[dict[str, Any], dict[str, Any], str, str]] = []
    for route in _approved_routes(content):
        route_id = str(route["route_id"])
        page = _page_for(visual, route_id) or {"route_id": route_id, "path": route.get("path", "/")}
        sections = _content_sections(content, route_id)
        if not sections:
            sections = [
                {"section_id": section_id}
                for section_id in _as_list(route.get("section_sequence"))
                if str(section_id)
            ]
        for index, section in enumerate(sections):
            section_id = _section_id(section, index)
            descriptors.append(
                (
                    route,
                    page,
                    section_id,
                    _route_scene(page, section_id, f"{route_id}-scene-{section_id}"),
                )
            )
    return descriptors


def _section_for(content: dict[str, Any], route_id: str, section_id: str) -> dict[str, Any]:
    return next(
        (
            section
            for section in _content_sections(content, route_id)
            if _section_id(section, 0) == section_id
        ),
        {"section_id": section_id},
    )


def _semantic_item_count(value: Any) -> int:
    """Count approved repeatable content without interpreting its claims."""
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        total = 0
        for key, child in value.items():
            if str(key).casefold() in {
                "items",
                "entries",
                "groups",
                "skills",
                "capabilities",
                "milestones",
                "roles",
                "projects",
                "work",
                "case_studies",
            }:
                total += _semantic_item_count(child)
        return total
    return 0


def _semantic_component_intents(
    *,
    content: dict[str, Any],
    route: dict[str, Any],
    page: dict[str, Any],
    section_id: str,
    scene_id: str,
    route_count: int,
) -> list[dict[str, Any]]:
    """Compile only interaction roles justified by section semantics."""
    section = _section_for(content, str(route.get("route_id", "")), section_id)
    scene = next(
        (
            item
            for item in _as_list(page.get("scenes"))
            if isinstance(item, dict) and str(item.get("scene_id", "")) == scene_id
        ),
        {},
    )
    section_text = _flatten_text(
        [
            section.get("purpose"),
            section.get("content"),
            section.get("interaction_direction"),
            scene.get("narrative_goal"),
            scene.get("interaction_direction"),
            scene.get("interaction"),
        ]
    ).casefold()
    items = _semantic_item_count(section.get("content", {}))
    explicit_required = bool(re.search(r"\b(?:required|essential|must|primary)\b", section_text))
    direction_terms = {
        "capability-grouping": any(
            term in section_text
            for term in ("group", "disclos", "accordion", "collapsible", "expandable", "tabs")
        ),
        "experience-timeline": any(
            term in section_text
            for term in ("chronolog", "timeline", "progress", "milestone", "sequence")
        ),
        "selected-work-detail": any(
            term in section_text
            for term in ("detail", "expand", "drawer", "dialog", "case study", "explore")
        ),
        "navigation-disclosure": any(
            term in section_text for term in ("mobile nav", "navigation disclosure", "menu drawer")
        ),
    }
    candidates: list[tuple[str, str, bool]] = []
    if _section_matches(section_id, ("capabil", "skill", "service")) and (
        items >= 2 or direction_terms["capability-grouping"]
    ):
        candidates.append(
            (
                "capability-grouping",
                "Group capability items with progressive disclosure.",
                explicit_required,
            )
        )
    if _section_matches(section_id, ("experience", "career", "timeline")) and (
        items >= 2 or direction_terms["experience-timeline"]
    ):
        candidates.append(
            ("experience-timeline", "Show chronological experience progression.", explicit_required)
        )
    if _section_matches(section_id, ("work", "project", "proof", "case")) and (
        items >= 2 or direction_terms["selected-work-detail"]
    ):
        candidates.append(
            (
                "selected-work-detail",
                "Let visitors explore approved work details.",
                explicit_required,
            )
        )
    if _section_matches(section_id, ("nav", "navigation")) and (
        route_count > 1 or direction_terms["navigation-disclosure"]
    ):
        candidates.append(
            ("navigation-disclosure", "Disclose route navigation on narrow screens.", True)
        )

    result: list[dict[str, Any]] = []
    for role_id, outcome, required in candidates:
        role_terms = list(_COMPONENT_PROVIDER_VOCABULARY[role_id])
        interaction_class = {
            "capability-grouping": "disclosure",
            "experience-timeline": "progression",
            "selected-work-detail": "detail-exploration",
            "navigation-disclosure": "navigation-disclosure",
        }[role_id]
        result.append(
            {
                "role_id": role_id,
                "route_id": str(route.get("route_id", "")),
                "scene_id": scene_id,
                "section_id": section_id,
                "interaction_class": interaction_class,
                "interaction_outcome": outcome,
                "placement": f"{route.get('route_id', '')} / {section_id}",
                "purpose": outcome,
                "provider_terms": role_terms,
                "negative_concepts": ["dashboard", "screenshot", "invented project detail"],
                "required": required,
                "fallback_type": "semantic_local",
                "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
                "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation.",
                "expected_exports": [],
                "prohibitions": [
                    "Do not add an interaction to a section that does not contain the approved items."
                ],
            }
        )
    return result


def _image_target(image_target: int, image_maximum: int) -> int:
    return min(max(0, int(image_target)), max(0, min(6, int(image_maximum))))


def _component_target(component_target: int, component_maximum: int) -> int:
    return min(max(0, int(component_target)), max(0, min(6, int(component_maximum))))


def _existing_image_count(visual: dict[str, Any]) -> int:
    return sum(
        1
        for item in _as_list(visual.get("asset_briefs"))
        if isinstance(item, dict)
        and str(item.get("asset_type", "") or "").casefold()
        in {"image", "photo", "editorial_photo", "portrait"}
    )


def _ordered_descriptors(
    descriptors: list[tuple[dict[str, Any], dict[str, Any], str, str]],
) -> list[tuple[dict[str, Any], dict[str, Any], str, str, str]]:
    def role_for(section_id: str) -> str:
        if _section_matches(section_id, ("hero", "thesis", "intro")):
            return "hero"
        if _section_matches(section_id, ("capabil", "skill", "service")):
            return "capabilities"
        if _section_matches(section_id, ("experience", "career", "timeline")):
            return "experience"
        if _section_matches(section_id, ("work", "project", "proof", "case")):
            return "selected-work"
        if _section_matches(section_id, ("education", "about")):
            return "education"
        if _section_matches(section_id, ("connect", "contact", "cta")):
            return "connect"
        return "selected-work"

    rank = {name: index for index, (name, *_rest) in enumerate(_IMAGE_ROLE_SPECS)}
    decorated = [
        (route, page, section_id, scene_id, role_for(section_id))
        for route, page, section_id, scene_id in descriptors
    ]
    return sorted(
        decorated,
        key=lambda item: (rank.get(item[4], 99), str(item[0].get("route_id", "")), item[2]),
    )


def normalize_visual_input(
    content_architect: dict[str, Any] | None,
    visual_design_director: dict[str, Any] | None,
    *,
    image_target: int = 5,
    image_maximum: int = 6,
    component_target: int = 4,
    component_maximum: int = 6,
    enabled: bool = True,
) -> NormalizedVisualInput:
    """Merge explicit VDD fields with bounded, deterministic assumptions."""

    content = _as_dict(content_architect)
    original = _as_dict(visual_design_director)
    if original.get("_build_preparation_normalized") is True:
        assumptions = tuple(str(item) for item in _as_list(original.get("assumptions")))
        return NormalizedVisualInput(
            visual=original,
            mode=str(original.get("visual_input_mode", "approved_vdd") or "approved_vdd"),
            assumption_hash=str(original.get("assumption_hash", "") or ""),
            assumptions=assumptions,
        )

    visual = json.loads(json.dumps(original, ensure_ascii=False, default=str))
    visual.setdefault("pages", [])
    visual.setdefault("asset_briefs", [])
    visual.setdefault("resource_candidates", [])
    if not _as_dict(visual.get("visual_language")) and not _has_meaningful_visual_input(original):
        visual["visual_language"] = {
            "style": "technical editorial",
            "palette": ["charcoal", "mineral", "cobalt accent"],
            "layout": "asymmetric text-led sections with structured reading edges",
            "typography": {"display": "Space Grotesk", "body": "Inter"},
            "spacing": "generous opening space with denser evidence chapters",
        }
    if not _as_dict(visual.get("motion_system")) and not _has_meaningful_visual_input(original):
        visual["motion_system"] = {
            "behavior": "brief low-amplitude structural emphasis",
            "reduced_motion": "complete static state with no sequencing or parallax",
        }
    if not _as_dict(
        visual.get("accessibility_and_performance")
    ) and not _has_meaningful_visual_input(original):
        visual["accessibility_and_performance"] = {
            "responsive": "stack dense compositions on narrow screens",
            "touch": "essential content remains visible without hover",
            "reduced_motion": "static equivalent is complete",
        }
    explicit_policy = _as_dict(original.get("resource_policy"))
    requested_image_target = int(explicit_policy.get("image_target_count", image_target) or 0)
    requested_component_target = int(
        explicit_policy.get("component_target_count", component_target) or 0
    )
    approved_routes = _approved_routes(content)
    existing_route_ids = {
        str(page.get("route_id", ""))
        for page in _as_list(visual.get("pages"))
        if isinstance(page, dict) and page.get("route_id")
    }
    page_coverage_complete = (
        bool(approved_routes)
        and {str(route["route_id"]) for route in approved_routes}.issubset(existing_route_ids)
        and all(
            bool(_as_list(page.get("scenes")))
            for page in _as_list(visual.get("pages"))
            if isinstance(page, dict)
            and str(page.get("route_id", ""))
            in {str(route["route_id"]) for route in approved_routes}
        )
    )
    needs_assumed_direction = not _has_meaningful_visual_input(original) or (
        bool(approved_routes) and not page_coverage_complete
    )
    if not _as_dict(visual.get("visual_language")) and needs_assumed_direction:
        visual["visual_language"] = {
            "style": "technical editorial",
            "palette": ["charcoal", "mineral", "cobalt accent"],
            "layout": "asymmetric text-led sections with structured reading edges",
            "typography": {"display": "Space Grotesk", "body": "Inter"},
            "spacing": "generous opening space with denser evidence chapters",
        }
    if not _as_dict(visual.get("motion_system")) and needs_assumed_direction:
        visual["motion_system"] = {
            "behavior": "brief low-amplitude structural emphasis",
            "reduced_motion": "complete static state with no sequencing or parallax",
        }
    if not _as_dict(visual.get("accessibility_and_performance")) and needs_assumed_direction:
        visual["accessibility_and_performance"] = {
            "responsive": "stack dense compositions on narrow screens",
            "touch": "essential content remains visible without hover",
            "reduced_motion": "static equivalent is complete",
        }
    explicit_prohibition = _explicit_prohibits_visual_acquisition(content, visual)
    explicit_component_prohibition = _explicitly_prohibits_components(visual)
    assumptions = list(_DEFAULT_ASSUMPTIONS)
    if explicit_prohibition or explicit_component_prohibition:
        assumptions.append("Explicit upstream visual acquisition prohibitions were preserved.")

    descriptors = _route_section_descriptors(content, visual)
    derived_any = False
    if approved_routes:
        for route in approved_routes:
            route_id = str(route["route_id"])
            if _page_for(visual, route_id) is not None:
                continue
            visual["pages"].append(
                {
                    "route_id": route_id,
                    "path": str(route.get("path", "/") or "/"),
                    "purpose": str(route.get("purpose", "") or ""),
                    "publication_status": "approved",
                    "compilable": True,
                    "scenes": [],
                    "asset_briefs": [],
                    "resource_candidates": [],
                    "acceptance_criteria": [],
                    "responsive_summary": "Preserve approved content order; stack dense groups on narrow screens.",
                }
            )
            derived_any = True

    # Recompute after route pages were filled so every derived role has a page.
    descriptors = _route_section_descriptors(content, visual)
    existing_assets = {
        str(item.get("asset_id", ""))
        for item in _as_list(visual.get("asset_briefs"))
        if isinstance(item, dict)
    }
    existing_resources = {
        str(item.get("resource_id", ""))
        for item in _as_list(visual.get("resource_candidates"))
        if isinstance(item, dict)
    }
    needed_images = max(
        0,
        _image_target(requested_image_target, image_maximum) - _existing_image_count(visual),
    )
    if enabled and not explicit_prohibition and needed_images:
        for ordinal, (route, page, section_id, scene_id, role_name) in enumerate(
            _ordered_descriptors(descriptors)
        ):
            if needed_images <= 0:
                break
            role_spec = next(item for item in _IMAGE_ROLE_SPECS if item[0] == role_name)
            route_id = str(route["route_id"])
            asset_id = f"assumed-image:{route_id}:{section_id}:{ordinal}"
            if asset_id in existing_assets:
                continue
            _, purpose, terms, mood, orientation, aspect_ratio = role_spec
            asset = {
                "asset_id": asset_id,
                "purpose": purpose,
                "content_ref": section_id,
                "asset_type": "editorial_photo",
                "source_status": "needs_acquisition",
                "source_policy": "optional_external_acquisition",
                "importance": "important"
                if role_name in {"hero", "selected-work"}
                else "supporting",
                "orientation": orientation,
                "aspect_ratio_need": aspect_ratio,
                "composition_role": role_name,
                "desktop_treatment": "Decorative local image supporting the section hierarchy.",
                "mobile_treatment": "Stack below essential copy and crop without hiding content.",
                "fit_intent": "cover",
                "visual_treatment": "editorial, non-evidentiary, no interface or proof content",
                "quality_requirement": "HTTPS provider, decodable pixels, non-flat, locally materialized",
                "fallback_strategy": "Use the approved text-led/static composition without stock substitution.",
                "decorative_vs_informative": "decorative",
                "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
                "attribution_requirement": "Record provider, contributor, license, source URL, and SHA-256 in the pack.",
                "subject": " ".join(terms),
                "mood": mood,
                "color_relationship": "charcoal, mineral, cobalt accent",
                "negative_concepts": list(_IMAGE_FORBIDDEN),
                "section_id": section_id,
                "scene_id": scene_id,
                "minimum_width": 1200,
                "minimum_height": 700,
            }
            visual["asset_briefs"].append(asset)
            page.setdefault("asset_briefs", []).append(asset_id)
            scene = _ensure_scene(page, section_id)
            scene.setdefault("asset_requirements", []).append(asset_id)
            existing_assets.add(asset_id)
            needed_images -= 1
            derived_any = True

    if enabled and not explicit_component_prohibition:
        route_count = len(approved_routes)
        semantic_intents: list[dict[str, Any]] = []
        for route, page, section_id, scene_id in descriptors:
            semantic_intents.extend(
                _semantic_component_intents(
                    content=content,
                    route=route,
                    page=page,
                    section_id=section_id,
                    scene_id=scene_id,
                    route_count=route_count,
                )
            )
        # The configured target is a ceiling for optional enrichment, never a
        # reason to manufacture roles. Explicitly required roles always stay in
        # the closed set even when they exceed that ceiling.
        optional_ceiling = min(
            max(0, _component_target(requested_component_target, component_maximum)),
            max(0, int(component_maximum)),
        )
        selected_intents: list[dict[str, Any]] = [
            item for item in semantic_intents if bool(item.get("required"))
        ]
        optional_intents = [item for item in semantic_intents if not bool(item.get("required"))]
        selected_intents.extend(
            optional_intents[: max(0, optional_ceiling - len(selected_intents))]
        )
        for intent in selected_intents:
            route_id = str(intent["route_id"])
            section_id = str(intent["section_id"])
            role_id = str(intent["role_id"])
            resource_id = f"assumed-component:{route_id}:{section_id}:{role_id}"
            if resource_id in existing_resources:
                continue
            resource = {
                "resource_id": resource_id,
                "category": "visual_component",
                "why_it_matches": str(intent["interaction_outcome"]),
                "where_it_may_help": str(intent["placement"]),
                "priority": "important" if intent["required"] else "optional",
                "possible_use": str(intent["purpose"]),
                "adaptation_notes": "Use real registry source only; preserve keyboard access, responsive behavior, and reduced-motion static state.",
                "fallback": "Use the approved semantic section structure without a registry component.",
                "confidence": "build_preparation_semantic_intent",
                "lookup_status": "assumed_intent",
                "required_for_handoff": bool(intent["required"]),
                "section_id": section_id,
                "section_ids": [section_id],
                "scene_id": str(intent["scene_id"]),
                "interaction_role": role_id,
                "responsive_behavior": str(intent["responsive_behavior"]),
                "reduced_motion_behavior": str(intent["reduced_motion_behavior"]),
                "provider_terms": list(intent["provider_terms"]),
                "negative_concepts": list(intent["negative_concepts"]),
                "component_intent": intent,
            }
            visual["resource_candidates"].append(resource)
            page = _page_for(visual, route_id) or page
            page.setdefault("resource_candidates", []).append(resource_id)
            scene = _ensure_scene(page, section_id)
            scene.setdefault("resource_candidates", []).append(resource_id)
            existing_resources.add(resource_id)
            derived_any = True

    policy = _as_dict(visual.get("resource_policy"))
    if "image_target_count" not in policy:
        policy["image_target_count"] = (
            0 if explicit_prohibition else _image_target(image_target, image_maximum)
        )
    if "component_target_count" not in policy:
        policy["component_target_count"] = _component_target(
            0 if explicit_component_prohibition else requested_component_target, component_maximum
        )
    if enabled:
        policy["auto_derived_visual_resources"] = True
    visual["resource_policy"] = policy
    if not _has_meaningful_visual_input(original):
        mode = "assumed_from_content"
        assumptions.append(
            "No VDD output was present; visual direction was assumed by Build Preparation from approved Content Architect content."
        )
    elif derived_any or (bool(approved_routes) and not page_coverage_complete):
        mode = "merged_vdd_assumptions"
    else:
        mode = "approved_vdd"
    if not enabled:
        assumptions.append("Automatic visual-resource derivation is disabled by configuration.")
    material = {
        "mode": mode,
        "assumptions": assumptions,
        "asset_ids": [
            str(item.get("asset_id", ""))
            for item in _as_list(visual.get("asset_briefs"))
            if isinstance(item, dict)
        ],
        "resource_ids": [
            str(item.get("resource_id", ""))
            for item in _as_list(visual.get("resource_candidates"))
            if isinstance(item, dict)
        ],
        "policy": policy,
    }
    assumption_hash = _hash(material)
    visual.update(
        {
            "_build_preparation_normalized": True,
            "visual_input_mode": mode,
            "assumption_hash": assumption_hash,
            "assumptions": _unique(assumptions),
        }
    )
    return NormalizedVisualInput(
        visual=visual,
        mode=mode,
        assumption_hash=assumption_hash,
        assumptions=tuple(_unique(assumptions)),
    )
