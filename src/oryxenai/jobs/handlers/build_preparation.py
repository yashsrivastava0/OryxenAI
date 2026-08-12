"""Durable Build Preparation worker handler for Stage 0 through Phase 3."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from oryxenai.agents.build_preparation.agent import (
    BuildPreparationAgent,
)
from oryxenai.agents.build_preparation.compiler import build_source_ref
from oryxenai.agents.build_preparation.packager import PackageError
from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    BuildPreparationStatus,
    FetchedResource,
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
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import Agent, AgentKey
from oryxenai.agents.shared.providers.errors import ProviderConfigError, ProviderError
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


def _build_build_preparation_agent(override_profile_name: str = "") -> Agent:
    """Create the live Build Preparation agent from the configured profile."""
    from oryxenai.agents.shared.model_client import build_provider_client
    from oryxenai.core.settings import get_settings

    settings = get_settings()
    client = build_provider_client(
        "build_preparation", settings.models, override_profile_name=override_profile_name
    )
    if client is None:
        raise ProviderConfigError(
            "Build Preparation requires a configured model profile and API key. "
            "Check config/models.toml and .env."
        )
    return BuildPreparationAgent(model_client=client, settings=settings)


class BuildPreparationHandler:
    kind = _BUILD_KIND

    def __init__(self, agent_factory: Callable[[], Agent] | None = None) -> None:
        self._agent_factory = agent_factory

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute_persisted(payload, instance_id, agent_factory=self._agent_factory)


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
        repo = BuildPreparationRepository(db)
        run = await repo.get_run(run_id)
        session = await repo.get_session(session_id)
        if run is None or session is None:
            raise BuildPreparationJobError(
                "BUILD_PREPARATION_RUN_NOT_FOUND",
                "Build Preparation run or session was not found.",
            )
        state = await repo.get_state(session_id)
        if state.status is BuildPreparationStatus.READY and state.run_id == str(run_id):
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

    try:
        agent = (
            agent_factory()
            if agent_factory is not None
            else _build_build_preparation_agent(str(input_payload.get("model_profile", "") or ""))
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
    except BuildPreparationValidationError as exc:
        error = {"code": exc.code, "message": exc.message, "details": exc.details}
        await _persist_failure(sessionmaker, session_id, run_id, error, attempt, max_attempts)
        raise BuildPreparationJobError(exc.code, exc.message, exc.details) from exc
    except ProviderError as exc:
        error = {"code": exc.code, "message": exc.message, "details": exc.details}
        await _persist_failure(sessionmaker, session_id, run_id, error, attempt, max_attempts)
        raise BuildPreparationJobError(
            exc.code, exc.message, exc.details, retryable=exc.retryable
        ) from exc
    except ArtifactStorageError as exc:
        error = {"code": exc.code, "message": exc.message, "details": exc.details}
        await _persist_failure(sessionmaker, session_id, run_id, error, attempt, max_attempts)
        raise BuildPreparationJobError(
            exc.code, exc.message, exc.details, retryable=exc.retryable
        ) from exc
    except PackageError as exc:
        error = {"code": exc.code, "message": exc.message, "details": exc.details}
        await _persist_failure(sessionmaker, session_id, run_id, error, attempt, max_attempts)
        raise BuildPreparationJobError(exc.code, exc.message, exc.details) from exc
    except Exception as exc:
        logger.warning("build_preparation phase 3 failed with %s", type(exc).__name__)
        stage_error: dict[str, Any] = {
            "code": "BUILD_PREPARATION_FAILED",
            "message": "Build Preparation could not complete.",
            "details": {},
        }
        await _persist_failure(sessionmaker, session_id, run_id, stage_error, attempt, max_attempts)
        raise BuildPreparationJobError(
            stage_error["code"], stage_error["message"], stage_error["details"], retryable=True
        ) from exc

    return await _apply_result(sessionmaker, session_id, run_id, result, attempt)


def _approved_source_ref(content_architect: Any, visual_design_director: Any) -> Any:
    return build_source_ref(
        {
            "approved": content_architect.approved.model_dump(mode="json")
            if content_architect.approved
            else {},
            "route_plan": [route.model_dump(mode="json") for route in content_architect.route_plan],
            "page_content_packs": [
                {**pack.model_dump(mode="json"), "internal_notes": {}}
                for pack in content_architect.page_content_packs
            ],
            "public_content_manifest": content_architect.public_content_manifest,
        },
        {
            "approved": visual_design_director.approved.model_dump(mode="json")
            if visual_design_director.approved
            else {},
            "pages": [page.model_dump(mode="json") for page in visual_design_director.pages],
            "asset_briefs": [
                asset.model_dump(mode="json") for asset in visual_design_director.asset_briefs
            ],
            "resource_candidates": [
                resource.model_dump(mode="json")
                for resource in visual_design_director.resource_candidates
            ],
        },
    )


async def _apply_result(
    sessionmaker: Any,
    session_id: UUID,
    run_id: UUID,
    result: Any,
    attempt: int,
) -> dict[str, Any]:
    async with sessionmaker() as db:
        repo = BuildPreparationRepository(db)
        session = await repo.get_session(session_id)
        if session is None:
            raise BuildPreparationJobError("SESSION_NOT_FOUND", "Portfolio session was not found.")
        state = await repo.get_state(session_id)
        content_architect = await repo.get_content_architect_snapshot(session_id)
        visual_design_director = await repo.get_visual_design_director_snapshot(session_id)
        current_ref = _approved_source_ref(content_architect, visual_design_director)
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
            model_metadata={**result.model_metadata, "result_status": "succeeded"},
        )
        await db.commit()
        return {"status": "succeeded", "run_id": str(run_id), "operation": operation}


async def _persist_failure(
    sessionmaker: Any,
    session_id: UUID,
    run_id: UUID,
    error: dict[str, Any],
    attempt: int,
    max_attempts: int,
) -> None:
    async with sessionmaker() as db:
        repo = BuildPreparationRepository(db)
        session = await repo.get_session(session_id)
        if session is None:
            return
        state = await repo.get_state(session_id)
        if attempt >= max_attempts and state.status is not BuildPreparationStatus.READY:
            next_state = apply_needs_attention(state, error)
            next_state.attempt = attempt
            await repo.save_state(session_id, next_state, session.revision)
        await repo.mark_run_failed(run_id, error)
        await db.commit()
