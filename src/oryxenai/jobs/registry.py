"""Handler registry — maps job_kind to a JobHandler implementation."""

from __future__ import annotations

from datetime import UTC

from oryxenai.jobs.contracts import SYSTEM_PROBE_KIND, JobHandler

_registry: dict[str, JobHandler] = {}


def register(handler: JobHandler) -> None:
    """Register a handler for its declared kind."""
    if not handler.kind:
        raise ValueError("handler must declare a non-empty kind")
    _registry[handler.kind] = handler


def get(kind: str) -> JobHandler | None:
    """Return the handler for a given kind, or None if unregistered."""
    return _registry.get(kind)


def is_registered(kind: str) -> bool:
    return kind in _registry


def list_kinds() -> list[str]:
    return sorted(_registry.keys())


# ── Built-in handlers ───────────────────────────────────────────────────────


class WorkerProbeHandler:
    """Deterministic infrastructure probe. Never calls an agent or model."""

    kind: str = SYSTEM_PROBE_KIND

    async def execute(self, payload: dict[str, object], instance_id: str) -> dict[str, object]:
        from datetime import datetime

        message = str(payload.get("message", ""))
        return {
            "received_at": datetime.now(UTC).isoformat(),
            "worker_instance": instance_id,
            "echo_message": message,
        }


def _register_builtins() -> None:
    if not is_registered(SYSTEM_PROBE_KIND):
        register(WorkerProbeHandler())
    _register_discovery_handlers()
    _register_content_architect_handlers()
    _register_visual_design_director_handlers()
    _register_build_preparation_handlers()


def _register_discovery_handlers() -> None:
    from oryxenai.jobs.handlers.discovery import (
        DiscoveryBuildBriefHandler,
        DiscoveryBuildOrReviseBriefHandler,
        DiscoveryPrepareQuestionsHandler,
        DiscoveryUnderstandAndQuestionHandler,
    )

    for handler_cls in (
        DiscoveryUnderstandAndQuestionHandler,
        DiscoveryBuildOrReviseBriefHandler,
        DiscoveryPrepareQuestionsHandler,
        DiscoveryBuildBriefHandler,
    ):
        instance = handler_cls()
        if not is_registered(instance.kind):
            register(instance)


def _register_content_architect_handlers() -> None:
    from oryxenai.jobs.handlers.content_architect import ContentArchitectBuildHandler

    for handler_cls in (ContentArchitectBuildHandler,):
        instance = handler_cls()
        if not is_registered(instance.kind):
            register(instance)


def _register_visual_design_director_handlers() -> None:
    from oryxenai.jobs.handlers.visual_design_director import VisualDesignDirectorBuildHandler

    for handler_cls in (VisualDesignDirectorBuildHandler,):
        instance = handler_cls()
        if not is_registered(instance.kind):
            register(instance)


def _register_build_preparation_handlers() -> None:
    from oryxenai.jobs.handlers.build_preparation import BuildPreparationHandler

    instance = BuildPreparationHandler()
    if not is_registered(instance.kind):
        register(instance)


_register_builtins()
