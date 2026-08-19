"""Deterministic ownership checks for design-neutral generation."""

from __future__ import annotations

from collections import Counter

from oryxenai.agents.code_generator.core.development_schemas import SitePlan, WorkUnit


class OwnershipError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def validate_work_ownership(plan: SitePlan, *, design_neutral: bool = False) -> None:
    """Fail closed on overlapping writes, shells, or interaction owners."""

    units = [item for item in plan.work_graph.units if not item.terminal]
    paths: dict[str, str] = {}
    for unit in units:
        for path in unit.owns_paths:
            owner = paths.get(path)
            if owner is not None and owner != unit.unit_id:
                raise OwnershipError(
                    "WORK_PATH_OVERLAP",
                    f"Owned path {path!r} is assigned to both {owner!r} and {unit.unit_id!r}.",
                )
            paths[path] = unit.unit_id
        if design_neutral and unit.kind == "route_batch":
            forbidden = tuple(path for path in unit.owns_paths if "/sections/" not in path)
            if forbidden:
                raise OwnershipError(
                    "ROUTE_BATCH_SHELL_OWNERSHIP",
                    "Design-neutral route batches may own section fragments only.",
                )
    shells = [item for item in units if item.owns_route_shell]
    if design_neutral:
        for route_id in {route.route_id for route in plan.routes}:
            route_shells = [item for item in shells if route_id in item.route_ids]
            if len(route_shells) != 1:
                raise OwnershipError(
                    "ROUTE_SHELL_OWNER_COUNT",
                    "Every approved route must have exactly one route-shell composer.",
                )
    interaction_owners = [item.interaction_ids for item in units]
    counts = Counter(interaction_id for values in interaction_owners for interaction_id in values)
    if any(count != 1 for count in counts.values()):
        raise OwnershipError(
            "INTERACTION_OWNER_COUNT",
            "Every interaction must have exactly one generated work owner.",
        )
    expected = {item.interaction_id for item in plan.interactions}
    if expected and set(counts) != expected:
        raise OwnershipError(
            "INTERACTION_OWNER_MISSING",
            "The WorkGraph does not assign every declared interaction.",
        )


def owned_paths_by_unit(units: list[WorkUnit]) -> dict[str, tuple[str, ...]]:
    return {
        unit.unit_id: tuple(sorted(unit.owns_paths))
        for unit in sorted(units, key=lambda item: item.unit_id)
    }
