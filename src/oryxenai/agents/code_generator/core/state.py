"""Small pure state-transition helpers for the standalone generation stage."""

from __future__ import annotations

from oryxenai.agents.code_generator.core.development_schemas import DevelopmentRunStatus


class GenerationStateError(ValueError):
    pass


_ALLOWED: dict[str, set[str]] = {
    DevelopmentRunStatus.ACQUIRED.value: {DevelopmentRunStatus.QUEUED.value},
    DevelopmentRunStatus.QUEUED.value: {
        DevelopmentRunStatus.GENERATING_FOUNDATION.value,
        DevelopmentRunStatus.NEEDS_ATTENTION.value,
    },
    DevelopmentRunStatus.GENERATING_FOUNDATION.value: {
        DevelopmentRunStatus.GENERATING_FOUNDATION.value,
        DevelopmentRunStatus.GENERATING_ROUTES.value,
        DevelopmentRunStatus.INTEGRATING.value,
        DevelopmentRunStatus.NEEDS_ATTENTION.value,
    },
    DevelopmentRunStatus.GENERATING_ROUTES.value: {
        DevelopmentRunStatus.GENERATING_ROUTES.value,
        DevelopmentRunStatus.INTEGRATING.value,
        DevelopmentRunStatus.NEEDS_ATTENTION.value,
    },
    DevelopmentRunStatus.INTEGRATING.value: {
        DevelopmentRunStatus.INTEGRATING.value,
        DevelopmentRunStatus.SOURCE_READY.value,
        DevelopmentRunStatus.NEEDS_ATTENTION.value,
    },
    DevelopmentRunStatus.SOURCE_READY.value: {
        DevelopmentRunStatus.QUEUED.value,
        DevelopmentRunStatus.BUILDING.value,
        DevelopmentRunStatus.NEEDS_ATTENTION.value,
    },
    DevelopmentRunStatus.BUILDING.value: {
        DevelopmentRunStatus.BUILDING.value,
        DevelopmentRunStatus.SMOKE_TESTING.value,
        DevelopmentRunStatus.REPAIRING.value,
        DevelopmentRunStatus.READY.value,
        DevelopmentRunStatus.NEEDS_ATTENTION.value,
    },
    DevelopmentRunStatus.SMOKE_TESTING.value: {
        DevelopmentRunStatus.SMOKE_TESTING.value,
        DevelopmentRunStatus.REPAIRING.value,
        DevelopmentRunStatus.READY.value,
        DevelopmentRunStatus.NEEDS_ATTENTION.value,
    },
    DevelopmentRunStatus.REPAIRING.value: {
        DevelopmentRunStatus.REPAIRING.value,
        DevelopmentRunStatus.BUILDING.value,
        DevelopmentRunStatus.SMOKE_TESTING.value,
        DevelopmentRunStatus.NEEDS_ATTENTION.value,
    },
    DevelopmentRunStatus.READY.value: {
        DevelopmentRunStatus.QUEUED.value,
        DevelopmentRunStatus.NEEDS_ATTENTION.value,
    },
    DevelopmentRunStatus.NEEDS_ATTENTION.value: {
        DevelopmentRunStatus.QUEUED.value,
        DevelopmentRunStatus.GENERATING_FOUNDATION.value,
        DevelopmentRunStatus.BUILDING.value,
    },
}


def transition(current: str, next_status: str) -> str:
    if next_status not in _ALLOWED.get(current, set()):
        raise GenerationStateError(f"Invalid Code Generator transition: {current} -> {next_status}")
    return next_status


def can_transition(current: str, next_status: str) -> bool:
    return next_status in _ALLOWED.get(current, set())
