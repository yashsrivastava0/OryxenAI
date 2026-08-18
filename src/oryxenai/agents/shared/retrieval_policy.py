"""Deterministic reporting policy for live component retrieval.

The policy deliberately does not perform I/O, call a model, or retain results.
It reports semantic priority and the configured advisory ceiling.  It does not
drop an approved role: LLM query composition and candidate ranking remain
separate, closed-set steps and operational limits are enforced per role by the
provider/materialization layers.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ComponentRetrievalPlan:
    """Budget decision for one agent run or one acquisition attempt."""

    selected_ids: tuple[str, ...]
    required_ids: tuple[str, ...]
    deferred_optional_ids: tuple[str, ...]
    maximum: int
    required_over_maximum: bool

    @property
    def advisory_exceeded(self) -> bool:
        return len(self.selected_ids) > self.maximum

    @property
    def target_count(self) -> int:
        return len(self.selected_ids)

    def as_metadata(self) -> dict[str, Any]:
        return {
            "selected_ids": list(self.selected_ids),
            "required_ids": list(self.required_ids),
            "deferred_optional_ids": list(self.deferred_optional_ids),
            "target_count": self.target_count,
            "maximum": self.maximum,
            "required_over_maximum": self.required_over_maximum,
            "advisory_exceeded": self.advisory_exceeded,
            "strategy": "all-approved-roles-with-priority-reporting",
        }


def _value(item: Any, name: str, default: Any = "") -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _key(item: Any) -> str:
    return str(_value(item, "need_id") or _value(item, "request_id") or "")


def _required(item: Any) -> bool:
    return bool(
        _value(item, "required_for_handoff", False)
        or _value(item, "requiredness", "") == "required"
        or str(_value(item, "importance", "")).casefold() in {"critical", "required"}
    )


def _route_ids(item: Any) -> set[str]:
    route_ids = _value(item, "route_ids", [])
    if isinstance(route_ids, (list, tuple, set)):
        values = {str(value) for value in route_ids if str(value)}
    else:
        values = set()
    placement = _value(item, "placement", None)
    route_id = _value(placement, "route_id", "") if placement is not None else ""
    if route_id:
        values.add(str(route_id))
    return values


def _scene_count(item: Any) -> int:
    scene_ids = _value(item, "scene_ids", [])
    return len(scene_ids) if isinstance(scene_ids, (list, tuple, set)) else 0


def _role_tokens(item: Any) -> set[str]:
    values = [str(_value(item, "purpose", ""))]
    query_terms = _value(item, "query_terms", [])
    if isinstance(query_terms, (list, tuple, set)):
        values.extend(str(value) for value in query_terms)
    query = _value(item, "query", None)
    positive_terms = _value(query, "positive_terms", []) if query is not None else []
    if isinstance(positive_terms, (list, tuple, set)):
        values.extend(str(value) for value in positive_terms)
    return {
        token
        for token in re.findall(r"[a-z0-9]+", " ".join(values).casefold())
        if len(token) > 3
        and token not in {"component", "component_source", "resource", "custom", "use", "with"}
    }


def _priority(item: Any, index: int) -> tuple[int, int]:
    importance = str(_value(item, "importance", "")).casefold()
    importance_score = {
        "critical": 400,
        "required": 400,
        "important": 300,
        "supporting": 200,
        "optional": 100,
    }.get(importance, 150)
    required_score = 1000 if _required(item) else 0
    route_score = min(8, len(_route_ids(item))) * 40
    scene_score = min(8, _scene_count(item)) * 5
    # Earlier deterministic needs win only after semantic priority and route
    # coverage. This keeps output stable without pretending timestamps are a
    # meaningful quality signal for component registries.
    return required_score + importance_score + route_score + scene_score, -index


def _optional_priority(
    item: Any,
    index: int,
    *,
    covered_routes: set[str],
    covered_roles: set[str],
) -> tuple[int, int]:
    base, stable_order = _priority(item, index)
    route_gain = len(_route_ids(item) - covered_routes)
    role_gain = len(_role_tokens(item) - covered_roles)
    return base + route_gain * 80 + min(role_gain, 4) * 35, stable_order


def plan_component_retrieval(items: Iterable[Any], *, maximum: int) -> ComponentRetrievalPlan:
    """Report role priority without turning the configured maximum into quota.

    The maximum is retained as an advisory value for diagnostics and capacity
    review.  Every semantically justified approved role remains selected; the
    provider and materializer enforce only per-role safety limits.
    """

    entries = [(index, item, _key(item)) for index, item in enumerate(items) if _key(item)]
    maximum = max(0, int(maximum))
    required = sorted(
        (entry for entry in entries if _required(entry[1])),
        key=lambda entry: _priority(entry[1], entry[0]),
        reverse=True,
    )
    remaining_optional = [entry for entry in entries if not _required(entry[1])]
    covered_routes = {route_id for _, item, _ in required for route_id in _route_ids(item)}
    covered_roles = {token for _, item, _ in required for token in _role_tokens(item)}
    optional: list[tuple[int, Any, str]] = []
    while remaining_optional:
        index, item, key = max(
            remaining_optional,
            key=lambda entry: _optional_priority(
                entry[1],
                entry[0],
                covered_routes=covered_routes,
                covered_roles=covered_roles,
            ),
        )
        chosen = next(entry for entry in remaining_optional if entry[0] == index)
        remaining_optional.remove(chosen)
        optional.append((index, item, key))
        covered_routes.update(_route_ids(item))
        covered_roles.update(_role_tokens(item))
    selected = [*required, *optional]
    return ComponentRetrievalPlan(
        selected_ids=tuple(entry[2] for entry in selected),
        required_ids=tuple(entry[2] for entry in required),
        deferred_optional_ids=(),
        maximum=maximum,
        required_over_maximum=len(required) > maximum,
    )
