"""Durable Build Preparation worker handler for Stage 0 through Phase 3."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from oryxenai.agents.build_preparation.agent import (
    BuildPreparationAgent,
    BuildPreparationModelOutputError,
)
from oryxenai.agents.build_preparation.checkpoint import (
    BuildPreparationCheckpoint,
    source_binding_hash,
)
from oryxenai.agents.build_preparation.compiler import build_source_ref
from oryxenai.agents.build_preparation.packager import PackageError
from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    BuildPreparationStatus,
    FetchedResource,
    HandoffQualityReport,
    MaterializationResult,
    PackageResult,
    ResourceNeed,
    RouteScope,
    Stage0Result,
    Stage1QueryPlan,
    Stage2SelectionPlan,
    StageEvent,
)
from oryxenai.agents.build_preparation.state import (
    apply_build_running,
    apply_needs_attention,
    apply_phase2_result,
    apply_phase3_result,
    apply_result,
)
from oryxenai.agents.build_preparation.validators import BuildPreparationValidationError
from oryxenai.agents.build_preparation.visual_input import normalize_visual_input
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import Agent, AgentKey
from oryxenai.agents.shared.observability import durable_model_metadata
from oryxenai.agents.shared.providers.errors import ProviderError, stable_provider_failure
from oryxenai.auth.worker_fence import WorkerAuthorizationFence
from oryxenai.core.logging import get_logger
from oryxenai.db.repositories.build_preparation import BuildPreparationRepository
from oryxenai.db.session import get_sessionmaker
from oryxenai.storage.artifacts import ArtifactStorageError

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
    checkpoint_sink: Callable[[BuildPreparationCheckpoint], Awaitable[None]] | None = None,
) -> Agent:
    """Create the live Build Preparation agent from the configured profile."""
    from oryxenai.agents.shared.model_runtime import get_model_runtime
    from oryxenai.core.settings import get_settings

    settings = get_settings()
    runtime = get_model_runtime(settings.models)
    return BuildPreparationAgent(
        model_client=runtime.resolve("build_preparation", override_profile_name),
        settings=settings,
        event_sink=event_sink,
        checkpoint_sink=checkpoint_sink,
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
        "running" forever (live-reproduced during local testing).
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
    from oryxenai.agents.shared.model_runtime import get_model_runtime

    runtime = get_model_runtime(settings.models)

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
            and state.package is not None
        ):
            # A lease can expire after the result was committed but before the
            # queue acknowledgement. Replaying the same run is a no-op.
            return {"status": "succeeded", "run_id": str(run_id), "operation": "build"}
        await repo.mark_run_started(run_id)
        if state.status is BuildPreparationStatus.RUNNING and state.run_id == str(run_id):
            # A stale lease can replay a run after its first attempt already
            # persisted the running marker. Reuse that snapshot instead of
            # trying to CAS the same revision a second time.
            state_snapshot = dict(session.current_state)
        else:
            running = apply_build_running(state, str(run_id), state.job_id, attempt, max_attempts)
            expected_revision = int(payload.get("expected_session_revision", session.revision))
            updated = await repo.save_state(session_id, running, expected_revision)
            if updated is None:
                raise BuildPreparationJobError(
                    "BUILD_PREPARATION_REVISION_CONFLICT",
                    "Build Preparation state changed while the worker was starting.",
                )
            state_snapshot = dict(updated.current_state)
        await db.commit()
        input_payload = dict(run.input_payload)

        requested_profile = str(input_payload.get("model_profile", "") or "")
        runtime_profile_id = runtime.resolve_profile_name("build_preparation", requested_profile)
        profile_fingerprint = runtime.profile_fingerprint(runtime_profile_id)
        raw_source_ref = input_payload.get("source_ref")
        source_hash = source_binding_hash(
            raw_source_ref if isinstance(raw_source_ref, dict) else {}
        )
        checkpoint: BuildPreparationCheckpoint | None = None
        if isinstance(run.checkpoint_payload, dict):
            try:
                candidate_checkpoint = BuildPreparationCheckpoint.model_validate(
                    run.checkpoint_payload
                )
            except ValueError:
                candidate_checkpoint = None
            if candidate_checkpoint is not None and candidate_checkpoint.compatible_with(
                run_id=str(run_id),
                approved_source_hash=source_hash,
                profile_fingerprint=profile_fingerprint,
            ):
                checkpoint = candidate_checkpoint
        if run.checkpoint_payload is not None and checkpoint is None:
            await repo.save_checkpoint(run_id, None)
            await db.commit()

    checkpoint_binding = {
        "run_id": str(run_id),
        "approved_source_hash": source_hash,
        "profile_fingerprint": profile_fingerprint,
    }
    input_payload.update(
        {
            "runtime_profile_id": runtime_profile_id,
            "checkpoint_binding": checkpoint_binding,
            "checkpoint_payload": (
                checkpoint.model_dump(mode="json") if checkpoint is not None else None
            ),
        }
    )

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

    async def persist_checkpoint(value: BuildPreparationCheckpoint) -> None:
        if not value.compatible_with(
            run_id=str(run_id),
            approved_source_hash=source_hash,
            profile_fingerprint=profile_fingerprint,
        ):
            raise BuildPreparationJobError(
                "BUILD_PREPARATION_CHECKPOINT_MISMATCH",
                "Build Preparation rejected an incompatible checkpoint.",
            )
        async with sessionmaker() as checkpoint_db:
            await WorkerAuthorizationFence(checkpoint_db).validate_payload(payload)
            checkpoint_repo = BuildPreparationRepository(checkpoint_db)
            checkpoint_run = await checkpoint_repo.get_run(run_id)
            checkpoint_state = await checkpoint_repo.get_state(session_id)
            if (
                checkpoint_run is None
                or checkpoint_run.status != "running"
                or checkpoint_state.status is not BuildPreparationStatus.RUNNING
                or checkpoint_state.run_id != str(run_id)
            ):
                return
            await checkpoint_repo.save_checkpoint(run_id, value.model_dump(mode="json"))
            await checkpoint_db.commit()

    try:
        async with sessionmaker() as db:
            await WorkerAuthorizationFence(db).validate_payload(payload)
        agent = (
            agent_factory()
            if agent_factory is not None
            else _build_build_preparation_agent(
                str(input_payload.get("model_profile", "") or ""),
                event_sink=persist_event,
                checkpoint_sink=persist_checkpoint,
            )
        )
        context = build_context(
            portfolio_session_id=session_id,
            agent_key=_AGENT_KEY,
            current_state=state_snapshot,
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
        # other transient provider error, bounded by max_attempts. Mirrors
        # Discovery's DiscoveryModelOutputError handling. Must be checked
        # before the broader BuildPreparationValidationError branch below,
        # since this is a subclass of it.
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
    except ArtifactStorageError as exc:
        error = {"code": exc.code, "message": exc.message, "details": exc.details}
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
        raise BuildPreparationJobError(
            exc.code, exc.message, exc.details, retryable=exc.retryable
        ) from exc
    except PackageError as exc:
        error = {"code": exc.code, "message": exc.message, "details": exc.details}
        await _persist_failure(
            sessionmaker, session_id, run_id, payload, error, attempt, max_attempts, retryable=False
        )
        raise BuildPreparationJobError(exc.code, exc.message, exc.details) from exc
    except Exception as exc:
        # Everything with a known transient/classifiable shape is already
        # handled by the typed except clauses above (model output, provider,
        # artifact storage, package errors). An exception that reaches here
        # is unclassified — treat it as a real bug rather than blindly
        # retrying it up to max_attempts times at full 5-stage cost.
        logger.warning("build_preparation phase 3 failed with %s", type(exc).__name__)
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

    return await _apply_result(
        sessionmaker,
        session_id,
        run_id,
        payload,
        result,
        attempt,
        runtime_profile_id,
    )


def _approved_source_ref(content_architect: Any, visual_design_director: Any, settings: Any) -> Any:
    content_projection = {
        "approved": content_architect.approved.model_dump(mode="json")
        if content_architect.approved
        else {},
        "route_plan": [route.model_dump(mode="json") for route in content_architect.route_plan],
        "page_content_packs": [
            {**pack.model_dump(mode="json"), "internal_notes": {}}
            for pack in content_architect.page_content_packs
        ],
        "public_content_manifest": content_architect.public_content_manifest,
    }
    visual_projection = {
        "approved": visual_design_director.approved.model_dump(mode="json")
        if visual_design_director.approved
        else {},
        "visual_language": visual_design_director.visual_language,
        "resource_policy": visual_design_director.resource_policy,
        "visual_input_mode": getattr(visual_design_director, "visual_input_mode", ""),
        "assumption_hash": getattr(visual_design_director, "assumption_hash", ""),
        "assumptions": getattr(visual_design_director, "assumptions", []),
        "pages": [page.model_dump(mode="json") for page in visual_design_director.pages],
        "asset_briefs": [
            asset.model_dump(mode="json") for asset in visual_design_director.asset_briefs
        ],
        "resource_candidates": [
            resource.model_dump(mode="json")
            for resource in visual_design_director.resource_candidates
        ],
    }
    normalized = normalize_visual_input(
        content_projection,
        visual_projection,
        image_target=int(settings.build_preparation.editorial_image_budget),
        image_maximum=int(settings.build_preparation.editorial_image_maximum),
        component_target=int(settings.build_preparation.visual_component_budget),
        component_maximum=int(settings.build_preparation.visual_component_maximum),
        enabled=bool(settings.build_preparation.auto_derive_visual_resources),
    )
    return build_source_ref(content_projection, normalized.visual)


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
            return {"status": "failed", "run_id": str(run_id), "operation": "build"}

        output = dict(result.output)
        if output.get("stage") == "stage_0" or "query_plan" not in output:
            stage0 = Stage0Result.model_validate(output)
            next_state = apply_result(
                state,
                scope_hash=stage0.scope_hash,
                routes=stage0.routes,
                resource_needs=stage0.resource_needs,
                warnings=stage0.warnings,
                events=stage0.events,
            )
            operation = "stage_0"
            persisted_output = stage0.model_dump(mode="json")
        else:
            query_plan = Stage1QueryPlan.model_validate(output["query_plan"])
            candidates = [
                FetchedResource.model_validate(item) for item in output["fetched_candidates"]
            ]
            selection_plan = Stage2SelectionPlan.model_validate(output["selection_plan"])
            build_context_result = BuildContextDraft.model_validate(output["build_context"])
            materialization = MaterializationResult.model_validate(output["materialization"])
            routes = [RouteScope.model_validate(item) for item in output["routes"]]
            needs = [ResourceNeed.model_validate(item) for item in output["resource_needs"]]
            warnings = [str(item) for item in output.get("warnings", [])]
            events = [StageEvent.model_validate(item) for item in output.get("events", [])]
            model_calls = int(output.get("model_calls", 0))
            provider_calls = int(output.get("provider_calls", 0))
            if output.get("package") is not None:
                handoff_report = (
                    HandoffQualityReport.model_validate(output["handoff_report"])
                    if isinstance(output.get("handoff_report"), dict)
                    else None
                )
                next_state = apply_phase3_result(
                    state,
                    scope_hash=str(output["scope_hash"]),
                    routes=routes,
                    resource_needs=needs,
                    query_plan=query_plan,
                    fetched_candidates=candidates,
                    selection_plan=selection_plan,
                    build_context=build_context_result,
                    materialization=materialization,
                    package=PackageResult.model_validate(output["package"]),
                    warnings=warnings,
                    events=events,
                    model_calls=model_calls,
                    provider_calls=provider_calls,
                    handoff_report=handoff_report,
                )
            else:
                next_state = apply_phase2_result(
                    state,
                    scope_hash=str(output["scope_hash"]),
                    routes=routes,
                    resource_needs=needs,
                    query_plan=query_plan,
                    fetched_candidates=candidates,
                    selection_plan=selection_plan,
                    build_context=build_context_result,
                    materialization=materialization,
                    warnings=warnings,
                    events=events,
                    model_calls=model_calls,
                    provider_calls=provider_calls,
                )
            operation = "build"
            persisted_output = output
        next_state.attempt = attempt
        updated = await repo.save_state(session_id, next_state, session.revision)
        if updated is None:
            raise BuildPreparationJobError(
                "BUILD_PREPARATION_REVISION_CONFLICT",
                "Build Preparation state changed while the worker was completing.",
            )
        await repo.mark_run_succeeded(
            run_id,
            persisted_output,
            dict(updated.current_state),
            prompt_version=str(result.prompt_version or "phase2"),
            model_metadata=durable_model_metadata(
                {**result.model_metadata, "result_status": "succeeded"},
                profile_id=runtime_profile_id,
                attempt=attempt,
            ),
        )
        await db.commit()
        return {"status": "succeeded", "run_id": str(run_id), "operation": operation}


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
        # A non-retryable failure is exactly as terminal as one that has
        # exhausted max_attempts — either way, no further worker attempt
        # will ever run. Only checking attempt >= max_attempts left the
        # session stuck reporting "running" forever on a fail-fast attempt
        # 1 failure (live-reproduced: a PermissionError classified
        # non-retryable never advanced past "running").
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
