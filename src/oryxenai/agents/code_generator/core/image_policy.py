"""Host-owned image obligations shared by planning, source, and runtime gates."""

from __future__ import annotations

from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import (
    ImagePolicySnapshotV1,
    ResourcePlacementV4,
    SitePlan,
)
from oryxenai.agents.code_generator.core.resource_policy import is_image_category


class ImagePolicyError(ValueError):
    """Raised when no selection can satisfy the approved image policy.

    Carries `.code`/`.message` following this codebase's existing
    ValueError-subclass convention (`SitePlanValidationError`,
    `GenerationError`) so callers that catch a broad `Exception` and read
    `getattr(exc, "code", ...)` still surface the specific contract failure
    instead of a generic fallback code.
    """

    def __init__(self, code: str) -> None:
        self.code = code
        self.message = code
        super().__init__(code)


def _approved_image_slots(
    projections: dict[str, dict[str, Any]] | None,
    plan: SitePlan | None = None,
) -> tuple[list[str], dict[str, str]]:
    execution = (projections or {}).get("execution/contract.json", {})
    if not isinstance(execution, dict):
        execution = {}
    routes: dict[str, str] = {}
    slot_ids: list[str] = []
    for raw_slot in execution.get("slots", []):
        if not isinstance(raw_slot, dict):
            continue
        slot_id = str(raw_slot.get("resource_slot_id", "")).strip()
        category = str(raw_slot.get("category", "")).strip()
        if not slot_id or not is_image_category(category):
            continue
        slot_ids.append(slot_id)
        routes[slot_id] = str(raw_slot.get("route_id", "")).strip()
    if slot_ids:
        return sorted(set(slot_ids)), routes

    # A few legacy detached harnesses expose the approved image slots only in
    # the resource projection. Keep that compatibility path deterministic; a
    # missing execution contract still produces the text-only exemption.
    resource_projection = (projections or {}).get("resources/projection.json", {})
    if isinstance(resource_projection, dict):
        for raw_slot in resource_projection.get("resource_needs", []):
            if not isinstance(raw_slot, dict):
                continue
            slot_id = str(raw_slot.get("resource_slot_id", "")).strip()
            if slot_id and is_image_category(str(raw_slot.get("category", ""))):
                slot_ids.append(slot_id)
                routes[slot_id] = str(raw_slot.get("route_id", "")).strip()
    if slot_ids:
        return sorted(set(slot_ids)), routes
    if plan is not None:
        blueprint = getattr(plan, "experience_blueprint", None)
        binding_categories = {
            str(getattr(item, "resource_slot_id", "")): str(getattr(item, "category", ""))
            for item in getattr(plan, "execution_bindings", []) or []
            if str(getattr(item, "resource_slot_id", ""))
        }
        for placement in getattr(blueprint, "resource_placements", []) or []:
            slot_id = str(getattr(placement, "resource_slot_id", "")).strip()
            route_id = str(getattr(placement, "route_id", "")).strip()
            if (
                slot_id
                and route_id
                and (
                    not binding_categories or is_image_category(binding_categories.get(slot_id, ""))
                )
            ):
                slot_ids.append(slot_id)
                routes[slot_id] = route_id
    return sorted(set(slot_ids)), routes


def _primary_route_id(
    projections: dict[str, dict[str, Any]] | None,
    plan: SitePlan | None,
) -> str:
    if plan is not None:
        primary = next((route for route in plan.routes if route.path == "/"), None)
        if primary is not None:
            return primary.route_id
        if plan.routes:
            return plan.routes[0].route_id
    routes = (projections or {}).get("site/contract.json", {}).get("routes", [])
    if isinstance(routes, list):
        primary_projection_route = next(
            (
                item
                for item in routes
                if isinstance(item, dict) and str(item.get("path", "")) == "/"
            ),
            None,
        )
        selected = primary_projection_route or next(
            (item for item in routes if isinstance(item, dict)), None
        )
        return str(selected.get("route_id", "")) if isinstance(selected, dict) else ""
    return ""


def build_image_policy_snapshot(
    settings: Any,
    *,
    projections: dict[str, dict[str, Any]] | None = None,
    plan: SitePlan | None = None,
) -> ImagePolicySnapshotV1:
    """Resolve configured image settings against the approved input scope.

    The result is the only image policy object downstream stages should use.
    Its hash binds the policy to a run, so changing settings while resuming a
    run cannot silently weaken the final route obligations.
    """

    development = settings.code_generator_development
    approved_ids, slot_routes = _approved_image_slots(projections, plan)
    configured_minimum = max(0, int(getattr(development, "minimum_visible_images", 0) or 0))
    configured_preferred = max(0, int(getattr(development, "preferred_visible_images", 0) or 0))
    configured_primary = bool(getattr(development, "require_primary_route_image", False))
    if not approved_ids:
        return ImagePolicySnapshotV1(
            minimum_visible_images=0,
            preferred_visible_images=0,
            require_primary_route_image=False,
            approved_image_slot_ids=[],
            primary_route_id=_primary_route_id(projections, plan),
            text_only_exemption=True,
        )
    primary_route_id = _primary_route_id(projections, plan)
    primary_has_slot = bool(
        primary_route_id and any(route == primary_route_id for route in slot_routes.values())
    )
    available_count = len(approved_ids)
    effective_minimum = min(configured_minimum, available_count)
    effective_preferred = min(
        max(configured_preferred, effective_minimum),
        available_count,
    )
    return ImagePolicySnapshotV1(
        minimum_visible_images=effective_minimum,
        preferred_visible_images=effective_preferred,
        require_primary_route_image=configured_primary and primary_has_slot,
        approved_image_slot_ids=approved_ids,
        primary_route_id=primary_route_id,
        text_only_exemption=False,
    )


def required_image_placements(
    placements: list[ResourcePlacementV4],
    policy: ImagePolicySnapshotV1,
) -> list[ResourcePlacementV4]:
    """Select the site-wide set of placements that satisfy the image policy.

    This chooses policy obligations only; it does not validate a placement's
    route/section authority (blueprint validation already does that) and does
    not download or otherwise touch resources. The blueprint is immutable
    after acceptance, so its placement order makes selection deterministic
    for one run. This deliberately counts distinct approved slot IDs; it does
    not guarantee distinct photographic bytes, which is a separate
    acquisition-quality concern.
    """

    if policy.text_only_exemption:
        return []

    approved = set(policy.approved_image_slot_ids)
    eligible = [placement for placement in placements if placement.resource_slot_id in approved]
    selected: list[ResourcePlacementV4] = []
    selected_slots: set[str] = set()

    if policy.require_primary_route_image:
        primary = next(
            (placement for placement in eligible if placement.route_id == policy.primary_route_id),
            None,
        )
        if primary is None:
            raise ImagePolicyError("IMAGE_POLICY_PRIMARY_PLACEMENT_MISSING")
        selected.append(primary)
        selected_slots.add(primary.resource_slot_id)

    for placement in eligible:
        if len(selected_slots) >= policy.minimum_visible_images:
            break
        if placement.resource_slot_id in selected_slots:
            continue
        selected.append(placement)
        selected_slots.add(placement.resource_slot_id)

    if len(selected_slots) < policy.minimum_visible_images:
        raise ImagePolicyError("IMAGE_POLICY_SITE_PLACEMENT_MINIMUM_MISSING")
    return selected


def coerce_image_policy(value: Any) -> ImagePolicySnapshotV1 | None:
    """Validate a persisted policy without turning old non-v4 runs into errors."""

    if value is None:
        return None
    if isinstance(value, ImagePolicySnapshotV1):
        return value
    if not isinstance(value, dict):
        return None
    try:
        return ImagePolicySnapshotV1.model_validate(value)
    except Exception:
        return None


__all__ = [
    "ImagePolicyError",
    "build_image_policy_snapshot",
    "coerce_image_policy",
    "required_image_placements",
]
