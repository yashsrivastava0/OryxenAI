"""Durable Build Preparation worker handler.

Runs the single Build Preparation agent invocation (deterministic scope,
deterministic resource research, at most one bounded model call) and persists
its two Markdown briefs.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from oryxenai.agents.build_preparation.agent import (
    BuildPreparationAgent,
    BuildPreparationModelOutputError,
)
from oryxenai.agents.build_preparation.input_integrator import (
    BuildPreparationInputIntegrator,
)
from oryxenai.agents.build_preparation.schemas import (
    BuildPreparationStatus,
    ComponentBriefEntry,
    ResourceBriefEntry,
    ResourceNeed,
    RouteScope,
    StageEvent,
)
from oryxenai.agents.build_preparation.state import (
    apply_build_running,
    apply_needs_attention,
    apply_result,
)
from oryxenai.agents.build_preparation.validators import BuildPreparationValidationError
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import Agent, AgentKey
from oryxenai.agents.shared.model_cache import build_result_cache
from oryxenai.agents.shared.observability import durable_model_metadata
from oryxenai.agents.shared.output_export import export_agent_result
from oryxenai.agents.shared.providers.errors import ProviderError, stable_provider_failure
from oryxenai.auth.worker_fence import WorkerAuthorizationFence
from oryxenai.core.logging import get_logger
from oryxenai.db.repositories.build_preparation import BuildPreparationRepository
from oryxenai.db.session import get_sessionmaker

logger = get_logger("oryxenai.jobs.handlers.build_preparation")

_AGENT_KEY = AgentKey.BUILD_PREPARATION
_BUILD_KIND = "build_preparation.prepare"


class BuildPreparationJobError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        *,
        retryable: bool = False,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = retryable
        super().__init__(message)


def _build_build_preparation_agent(
    override_profile_name: str = "",
    *,
    event_sink: Callable[[StageEvent], Awaitable[None]] | None = None,
    result_cache: Any = None,
    profile_fingerprint: str = "",
) -> Agent:
    """Create the live Build Preparation agent from the configured profile."""
    from oryxenai.agents.shared.model_runtime import get_model_runtime
    from oryxenai.core.settings import get_settings

    settings = get_settings()
    runtime = get_model_runtime(settings.models)
    return BuildPreparationAgent(
        model_client=runtime.resolve("build_preparation", override_profile_name),
        settings=settings,
        profile_name=runtime.resolve_profile_name("build_preparation", override_profile_name),
        event_sink=event_sink,
        result_cache=result_cache,
        profile_fingerprint=profile_fingerprint,
    )


class BuildPreparationHandler:
    kind = _BUILD_KIND

    def __init__(self, agent_factory: Callable[[], Agent] | None = None) -> None:
        self._agent_factory = agent_factory

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute_persisted(payload, instance_id, agent_factory=self._agent_factory)

    async def on_timeout(self, payload: dict[str, Any], error: dict[str, Any]) -> None:
        """Called by the worker when the outer job-handler timeout fires.

        asyncio.wait_for cancels the execute() coroutine from outside, so its
        own try/except blocks (which call _persist_failure) never run — this
        is the only chance to reflect a terminal timeout into the
        build_preparation session state instead of leaving it stuck at
        "running" forever.
        """
        from oryxenai.core.settings import get_settings

        session_id = UUID(str(payload["portfolio_session_id"]))
        run_id = UUID(str(payload["agent_run_id"]))
        settings = get_settings()
        sessionmaker = get_sessionmaker(settings)
        attempt = int(payload.get("attempt", 1))
        max_attempts = int(payload.get("max_attempts", settings.worker_retry.max_attempts))
        await _persist_failure(
            sessionmaker,
            session_id,
            run_id,
            payload,
            error,
            attempt,
            max_attempts,
            retryable=bool(error.get("retryable", True)),
        )


async def _execute_persisted(
    payload: dict[str, Any],
    instance_id: str,
    *,
    agent_factory: Callable[[], Agent] | None = None,
) -> dict[str, Any]:
    from oryxenai.core.settings import get_settings

    session_id = UUID(str(payload["portfolio_session_id"]))
    run_id = UUID(str(payload["agent_run_id"]))
    settings = get_settings()
    sessionmaker = get_sessionmaker(settings)
    attempt = int(payload.get("attempt", 1))
    max_attempts = int(payload.get("max_attempts", settings.worker_retry.max_attempts))

    async with sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_payload(payload)
        repo = BuildPreparationRepository(db)
        run = await repo.get_run(run_id)
        session = await repo.get_session(session_id)
        if run is None or session is None:
            raise BuildPreparationJobError(
                "BUILD_PREPARATION_RUN_NOT_FOUND",
                "Build Preparation run or session was not found.",
            )
        state = await repo.get_state(session_id)
        if (
            state.status in {BuildPreparationStatus.READY, BuildPreparationStatus.NEEDS_ATTENTION}
            and state.run_id == str(run_id)
            and state.content_brief_markdown
        ):
            # A lease can expire after the result was committed but before the
            # queue acknowledgement. Replaying the same run is a no-op.
            return {"status": "succeeded", "run_id": str(run_id)}
        await repo.mark_run_started(run_id)
        if state.status is BuildPreparationStatus.RUNNING and state.run_id == str(run_id):
            # A stale lease can replay a run after its first attempt already
            # persisted the running marker.
            pass
        else:
            running = apply_build_running(state, str(run_id), state.job_id, attempt, max_attempts)
            expected_revision = int(payload.get("expected_session_revision", session.revision))
            updated = await repo.save_state(session_id, running, expected_revision)
            if updated is None:
                raise BuildPreparationJobError(
                    "BUILD_PREPARATION_REVISION_CONFLICT",
                    "Build Preparation state changed while the worker was starting.",
                )
        await db.commit()
        input_payload = dict(run.input_payload)

    async def persist_event(event: StageEvent) -> None:
        async with sessionmaker() as event_db:
            await WorkerAuthorizationFence(event_db).validate_payload(payload)
            event_repo = BuildPreparationRepository(event_db)
            event_session = await event_repo.get_session(session_id)
            if event_session is None:
                return
            event_state = await event_repo.get_state(session_id)
            if (
                event_state.status is not BuildPreparationStatus.RUNNING
                or event_state.run_id != str(run_id)
            ):
                return
            event_state.current_stage = event.stage
            event_key = (event.event_id, event.stage, event.timestamp)
            if not any(
                (item.event_id, item.stage, item.timestamp) == event_key
                for item in event_state.events
            ):
                event_state.events = [*event_state.events, event][-100:]
            updated = await event_repo.save_state(session_id, event_state, event_session.revision)
            if updated is not None:
                await event_db.commit()

    from oryxenai.agents.shared.model_runtime import get_model_runtime

    runtime = get_model_runtime(settings.models)
    requested_profile = str(input_payload.get("model_profile", "") or "")
    runtime_profile_id = runtime.resolve_profile_name("build_preparation", requested_profile)
    input_payload["runtime_profile_id"] = runtime_profile_id

    try:
        async with sessionmaker() as db:
            await WorkerAuthorizationFence(db).validate_payload(payload)
        agent = (
            agent_factory()
            if agent_factory is not None
            else _build_build_preparation_agent(
                requested_profile,
                event_sink=persist_event,
                result_cache=build_result_cache(
                    settings,
                    owner_user_id=run.owner_user_id if run is not None else None,
                    portfolio_session_id=session_id,
                ),
                profile_fingerprint=runtime.profile_fingerprint(runtime_profile_id),
            )
        )
        context = build_context(
            portfolio_session_id=session_id,
            agent_key=_AGENT_KEY,
            current_state={},
            agent_input=input_payload,
            request_id=str(payload.get("request_id", "") or ""),
            attempt=attempt,
            run_id=run_id,
        )
        result = await agent.run(context)
    except BuildPreparationModelOutputError as exc:
        # A model response that failed the output contract is almost always a
        # one-off generation-quality issue on the same input (truncated JSON,
        # a malformed field), not a permanent condition — retry it like any
        # other transient provider error, bounded by max_attempts.
        logger.warning("build_preparation model output invalid: %s", type(exc).__name__)
        error = {"code": exc.code, "message": exc.message, "details": exc.details}
        await _persist_failure(
            sessionmaker, session_id, run_id, payload, error, attempt, max_attempts, retryable=True
        )
        raise BuildPreparationJobError(exc.code, exc.message, exc.details, retryable=True) from exc
    except BuildPreparationValidationError as exc:
        error = {"code": exc.code, "message": exc.message, "details": exc.details}
        await _persist_failure(
            sessionmaker, session_id, run_id, payload, error, attempt, max_attempts, retryable=False
        )
        raise BuildPreparationJobError(exc.code, exc.message, exc.details) from exc
    except ProviderError as exc:
        code, message = stable_provider_failure(exc)
        error = {"code": code, "message": message, "details": {}}
        await _persist_failure(
            sessionmaker,
            session_id,
            run_id,
            payload,
            error,
            attempt,
            max_attempts,
            retryable=exc.retryable,
        )
        raise BuildPreparationJobError(code, message, {}, retryable=exc.retryable) from exc
    except Exception as exc:
        # Everything with a known transient/classifiable shape is already
        # handled above. An exception that reaches here is unclassified —
        # treat it as a real bug rather than blindly retrying it.
        logger.warning("build_preparation failed with %s", type(exc).__name__)
        stage_error: dict[str, Any] = {
            "code": "BUILD_PREPARATION_FAILED",
            "message": "Build Preparation could not complete.",
            "details": {},
        }
        await _persist_failure(
            sessionmaker,
            session_id,
            run_id,
            payload,
            stage_error,
            attempt,
            max_attempts,
            retryable=False,
        )
        raise BuildPreparationJobError(
            stage_error["code"], stage_error["message"], stage_error["details"], retryable=False
        ) from exc

    applied = await _apply_result(
        sessionmaker, session_id, run_id, payload, result, attempt, runtime_profile_id
    )
    if applied.get("status") == "succeeded":
        export_agent_result(
            settings,
            agent_key=_AGENT_KEY.value,
            run_id=run_id,
            output=result.output,
            model_metadata=result.model_metadata,
        )
    return applied


def _approved_source_ref(content_architect: Any, visual_design_director: Any, settings: Any) -> Any:
    return (
        BuildPreparationInputIntegrator(settings)
        .compose(content_architect, visual_design_director)
        .source_ref
    )


async def _apply_result(
    sessionmaker: Any,
    session_id: UUID,
    run_id: UUID,
    payload: dict[str, Any],
    result: Any,
    attempt: int,
    runtime_profile_id: str,
) -> dict[str, Any]:
    async with sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_payload(payload)
        repo = BuildPreparationRepository(db)
        session = await repo.get_session(session_id)
        if session is None:
            raise BuildPreparationJobError("SESSION_NOT_FOUND", "Portfolio session was not found.")
        state = await repo.get_state(session_id)
        content_architect = await repo.get_content_architect_snapshot(session_id)
        visual_design_director = await repo.get_visual_design_director_snapshot(session_id)
        from oryxenai.core.settings import get_settings

        current_ref = _approved_source_ref(
            content_architect, visual_design_director, get_settings()
        )
        if (
            current_ref.visual_design_director_direction_hash
            != state.source_ref.visual_design_director_direction_hash
            or current_ref.input_projection_hash != state.source_ref.input_projection_hash
        ):
            error = {
                "code": "BUILD_PREPARATION_STALE_SOURCE",
                "message": "Approved upstream content or visual direction changed while Build Preparation was running.",
                "details": {},
            }
            next_state = apply_needs_attention(state, error)
            next_state.attempt = attempt
            await repo.save_state(session_id, next_state, session.revision)
            await repo.mark_run_failed(run_id, error)
            await db.commit()
            return {"status": "failed", "run_id": str(run_id)}

        output = dict(result.output)
        routes = [RouteScope.model_validate(item) for item in output["routes"]]
        needs = [ResourceNeed.model_validate(item) for item in output["resource_needs"]]
        resource_index = [
            ResourceBriefEntry.model_validate(item) for item in output.get("resource_index", [])
        ]
        component_index = [
            ComponentBriefEntry.model_validate(item) for item in output.get("component_index", [])
        ]
        warnings = [str(item) for item in output.get("warnings", [])]
        events = [StageEvent.model_validate(item) for item in output.get("events", [])]
        next_state = apply_result(
            state,
            scope_hash=str(output["scope_hash"]),
            routes=routes,
            resource_needs=needs,
            resource_index=resource_index,
            component_index=component_index,
            content_brief_markdown=str(output.get("content_brief_markdown", "")),
            visual_brief_markdown=str(output.get("visual_brief_markdown", "")),
            content_brief_hash=_hash_text(str(output.get("content_brief_markdown", ""))),
            visual_brief_hash=_hash_text(str(output.get("visual_brief_markdown", ""))),
            target_contract=str(output.get("target_contract", "react-vite-v1")),
            recommended_dependencies=[
                str(item) for item in output.get("recommended_dependencies", [])
            ],
            debug_mirror_path=str(output.get("debug_mirror_path", "")),
            warnings=warnings,
            events=events,
            model_calls=int(output.get("model_calls", 0)),
            provider_calls=int(output.get("provider_calls", 0)),
        )
        next_state.attempt = attempt
        updated = await repo.save_state(session_id, next_state, session.revision)
        if updated is None:
            raise BuildPreparationJobError(
                "BUILD_PREPARATION_REVISION_CONFLICT",
                "Build Preparation state changed while the worker was completing.",
            )
        await repo.mark_run_succeeded(
            run_id,
            output,
            dict(updated.current_state),
            prompt_version=str(result.prompt_version or "compose_visual_brief"),
            model_metadata=durable_model_metadata(
                {**result.model_metadata, "result_status": "succeeded"},
                profile_id=runtime_profile_id,
                attempt=attempt,
            ),
        )
        await db.commit()
        return {"status": "succeeded", "run_id": str(run_id)}


async def _persist_failure(
    sessionmaker: Any,
    session_id: UUID,
    run_id: UUID,
    payload: dict[str, Any],
    error: dict[str, Any],
    attempt: int,
    max_attempts: int,
    *,
    retryable: bool,
) -> None:
    async with sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_payload(payload)
        repo = BuildPreparationRepository(db)
        session = await repo.get_session(session_id)
        if session is None:
            return
        state = await repo.get_state(session_id)
        will_retry = bool(
            error.get("will_retry")
            if "will_retry" in error
            else retryable and attempt < max_attempts
        )
        if not will_retry and state.status is not (BuildPreparationStatus.READY):
            next_state = apply_needs_attention(state, error)
            next_state.attempt = attempt
            await repo.save_state(session_id, next_state, session.revision)
        await repo.mark_run_failed(run_id, error)
        await db.commit()


def _hash_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()
