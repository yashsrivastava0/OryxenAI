"""Content Architect agent background job handler.

Registered job kind:
  - content_architect.build

One handler runs the whole adaptive workflow (the agent itself makes up to
3 sequential model calls internally — see agents/content_architect/agent.py).
Applies the resulting state transition and always surfaces failures to the
content_architect state so the API can show them.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from oryxenai.agents.content_architect.agent import ContentArchitectModelOutputError
from oryxenai.agents.content_architect.schemas import (
    ClaimGrounding,
    DecisionRecord,
    PageContentPack,
    RoutePlanEntry,
)
from oryxenai.agents.content_architect.state import (
    apply_build_result,
    apply_build_running,
    apply_needs_attention,
)
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.agents.shared.model_cache import build_result_cache
from oryxenai.agents.shared.observability import durable_model_metadata
from oryxenai.agents.shared.output_export import export_agent_result
from oryxenai.agents.shared.providers.errors import (
    ModelOutputInvalidError,
    ProviderError,
    stable_provider_failure,
)
from oryxenai.auth.worker_fence import WorkerAuthorizationFence
from oryxenai.core.logging import get_logger
from oryxenai.db.repositories.content_architect import ContentArchitectRepository
from oryxenai.db.session import get_sessionmaker
from oryxenai.jobs.contracts import JobStatus
from oryxenai.jobs.repository import JobRepository

logger = get_logger("oryxenai.jobs.handlers.content_architect")

_AGENT_KEY = AgentKey.CONTENT_ARCHITECT
_BUILD_KIND = "content_architect.build"


class ContentArchitectBuildHandler:
    """Worker handler for content_architect.build."""

    kind: str = _BUILD_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute_persisted(payload, instance_id)

    async def on_timeout(self, payload: dict[str, Any], error: dict[str, Any]) -> None:
        """Called by the worker when the outer job-handler timeout fires.

        asyncio.wait_for cancels the execute() coroutine from outside, so its
        own try/except (which calls _persist_failure) never runs — this is
        the only chance to reflect a terminal timeout into the
        content_architect session state instead of leaving it stuck at
        "build_running" forever. See visual_design_director.py's identical
        hook for the same live-reproduced issue one stage up the pipeline.
        """
        from oryxenai.core.settings import get_settings

        session_id = UUID(str(payload["portfolio_session_id"]))
        run_id = UUID(str(payload["agent_run_id"]))
        settings = get_settings()
        sessionmaker = get_sessionmaker(settings)
        attempt = int(payload.get("attempt", 1))
        max_attempts = int(payload.get("max_attempts", settings.worker_retry.max_attempts))
        await _persist_failure(
            sessionmaker, session_id, run_id, payload, error, attempt, max_attempts
        )


def _build_content_architect_agent(
    override_profile_name: str = "",
    *,
    result_cache: Any = None,
    profile_fingerprint: str = "",
) -> Any:
    """Create a ContentArchitectAgent with the live provider adapter.

    override_profile_name is the validated, session-sticky model/provider
    choice inherited from Discovery (see ContentArchitectService.start).
    Unknown or unselectable values fail closed in the shared runtime.
    """
    from oryxenai.agents.content_architect.agent import ContentArchitectAgent
    from oryxenai.agents.shared.model_runtime import get_model_runtime
    from oryxenai.core.settings import get_settings

    settings = get_settings()
    runtime = get_model_runtime(settings.models)
    resolved_profile = runtime.resolve_profile_name("content_architect", override_profile_name)
    return ContentArchitectAgent(
        model_client=runtime.resolve("content_architect", override_profile_name),
        profile_name=resolved_profile,
        result_cache=result_cache,
        profile_fingerprint=profile_fingerprint,
    )


async def _execute_persisted(payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
    """Execute an API-created run without holding a DB transaction open."""
    from oryxenai.core.settings import get_settings

    session_id = UUID(str(payload["portfolio_session_id"]))
    run_id = UUID(str(payload["agent_run_id"]))
    settings = get_settings()
    sessionmaker = get_sessionmaker(settings)
    attempt = int(payload.get("attempt", 1))
    max_attempts = int(payload.get("max_attempts", settings.worker_retry.max_attempts))
    raw_job_id = payload.get("job_id")
    job_id = UUID(str(raw_job_id)) if raw_job_id else None

    async with sessionmaker() as db:
        if job_id is not None and await _job_is_cancelled(db, job_id):
            return {"status": "cancelled", "job_id": str(job_id)}
        await WorkerAuthorizationFence(db).validate_payload(payload)
        repo = ContentArchitectRepository(db)
        run = await repo.get_run(run_id)
        session = await repo.get_session(session_id)
        if run is None or session is None:
            raise ValueError("Content Architect run or session was not found")
        await repo.mark_run_started(run_id)
        state = await repo.get_content_architect_state(session_id)
        if not _job_owns_active_state(state, run_id, job_id):
            return {"status": "cancelled", "job_id": str(job_id or "")}
        running = apply_build_running(state, str(run_id), str(job_id or state.job_id or ""))
        running.attempt = attempt
        running.max_attempts = max_attempts
        expected_revision = int(payload.get("expected_session_revision", session.revision))
        await repo.save_content_architect_state(session_id, running, expected_revision)
        await db.commit()
        state_snapshot = dict(session.current_state)
        input_payload = dict(run.input_payload)

    from oryxenai.agents.shared.model_runtime import get_model_runtime

    runtime = get_model_runtime(settings.models)
    async with sessionmaker() as db:
        if job_id is not None and await _job_is_cancelled(db, job_id):
            return {"status": "cancelled", "job_id": str(job_id)}
    requested_profile = str(input_payload.get("model_profile", "") or "")
    runtime_profile_id = runtime.resolve_profile_name("content_architect", requested_profile)
    input_payload["runtime_profile_id"] = runtime_profile_id
    result_cache = build_result_cache(
        settings,
        owner_user_id=run.owner_user_id if run is not None else None,
        portfolio_session_id=session_id,
    )

    async with sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_payload(payload)
    agent = _build_content_architect_agent(
        requested_profile,
        result_cache=result_cache,
        profile_fingerprint=runtime.profile_fingerprint(runtime_profile_id),
    )
    agent_input: dict[str, Any] = {
        "operation": "build",
        "intake": input_payload.get("intake", {}),
        "preferences": input_payload.get("preferences", {}),
        "prior_output": input_payload.get("prior_output", {}),
        "revision_request": input_payload.get("revision_request", ""),
    }
    context = build_context(
        portfolio_session_id=session_id,
        agent_key=_AGENT_KEY,
        current_state=state_snapshot,
        agent_input=agent_input,
        request_id=payload.get("request_id", ""),
        attempt=attempt,
        run_id=run_id,
    )

    try:
        result = await agent.run(context)
    except ProviderError as exc:
        await _persist_failure(
            sessionmaker, session_id, run_id, payload, exc, attempt, max_attempts
        )
        raise
    except ContentArchitectModelOutputError as exc:
        # A one-off generation-quality issue on the same input, not a permanent
        # condition — retry it like any other transient provider error, bounded
        # by the same max_attempts budget.
        logger.warning(
            "content_architect build produced invalid output type=%s", type(exc).__name__
        )
        retry_error = ModelOutputInvalidError()
        await _persist_failure(
            sessionmaker,
            session_id,
            run_id,
            payload,
            retry_error,
            attempt,
            max_attempts,
        )
        raise retry_error from exc
    except Exception as exc:
        logger.warning("content_architect build failed with %s", type(exc).__name__)
        await _persist_failure(
            sessionmaker,
            session_id,
            run_id,
            payload,
            ProviderError(
                code="MODEL_OPERATION_FAILED",
                message="Content Architect build failed.",
                retryable=False,
            ),
            attempt,
            max_attempts,
        )
        raise

    applied = await _apply_result(
        sessionmaker,
        session_id,
        run_id,
        payload,
        result,
        attempt,
        str(input_payload["runtime_profile_id"]),
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
        raw_job_id = payload.get("job_id")
        job_id = UUID(str(raw_job_id)) if raw_job_id else None
        if job_id is not None and await _job_is_cancelled(db, job_id):
            return {"status": "cancelled", "job_id": str(job_id)}
        await WorkerAuthorizationFence(db).validate_payload(payload)
        repo = ContentArchitectRepository(db)
        session = await repo.get_session(session_id)
        if session is None:
            raise ValueError("Content Architect session was not found")
        state = await repo.get_content_architect_state(session_id)
        if not _job_owns_active_state(state, run_id, job_id):
            return {"status": "cancelled", "job_id": str(job_id or "")}

        discovery = await repo.get_discovery_snapshot(session_id)
        current_hash = discovery.brief.approved.brief_hash if discovery.brief.approved else ""
        if current_hash != state.source_ref.discovery_brief_hash:
            safe_error = {
                "code": "CONTENT_ARCHITECT_STALE_SOURCE",
                "message": "Discovery changed while this Content Architect build was running.",
                "retryable": False,
            }
            next_state = apply_needs_attention(state, safe_error)
            next_state.attempt = attempt
            await repo.save_content_architect_state(session_id, next_state, session.revision)
            await repo.mark_run_failed(run_id, safe_error)
            await db.commit()
            return {"status": "failed", "run_id": str(run_id), "operation": "build"}

        output = result.output
        route_plan = [
            RoutePlanEntry.model_validate(item) for item in (output.get("route_plan") or [])
        ]
        claim_grounding = [
            ClaimGrounding.model_validate(item) for item in (output.get("claim_grounding") or [])
        ]
        page_content_packs = [
            PageContentPack.model_validate(item)
            for item in (output.get("page_content_packs") or [])
        ]
        decision_basis = [
            DecisionRecord.model_validate(item) for item in (output.get("decision_basis") or [])
        ]
        next_state = apply_build_result(
            state,
            version=result.prompt_version,
            run_id=str(run_id),
            user_summary=output.get("user_summary", "") or "",
            site_story_strategy=output.get("site_story_strategy", {}) or {},
            decision_basis=decision_basis,
            route_plan=route_plan,
            page_content_packs=page_content_packs,
            public_content_manifest=output.get("public_content_manifest", {}) or {},
            claim_grounding=claim_grounding,
            omissions=output.get("omissions", []) or [],
            unresolved_issues=output.get("unresolved_issues", []) or [],
            privacy_and_confidentiality=output.get("privacy_and_confidentiality", []) or [],
            media_status=output.get("media_status", {}) or {},
            visual_director_handoff=output.get("visual_director_handoff", {}) or {},
            warnings=output.get("warnings", []) or [],
            stages_run=output.get("stages_run", []) or [],
            memory_update=output.get("memory_update", {}) or {},
        )
        next_state.attempt = attempt

        updated = await repo.save_content_architect_state(session_id, next_state, session.revision)
        if updated is None:
            if job_id is not None and await _job_is_cancelled(db, job_id):
                return {"status": "cancelled", "job_id": str(job_id)}
            raise ValueError("Content Architect state changed while the job was running")
        state_after = dict(updated.current_state)
        await repo.mark_run_succeeded(
            run_id,
            output,
            state_after,
            prompt_version=result.prompt_version,
            model_metadata=durable_model_metadata(
                {**result.model_metadata, "result_status": "succeeded"},
                profile_id=runtime_profile_id,
                attempt=attempt,
            ),
        )
        await db.commit()
        return {"status": "succeeded", "run_id": str(run_id), "operation": "build"}


async def _persist_failure(
    sessionmaker: Any,
    session_id: UUID,
    run_id: UUID,
    payload: dict[str, Any],
    error: Any,
    attempt: int,
    max_attempts: int,
) -> None:
    """Record a failed attempt. Only surface it to the user once it's final.

    Mirrors discovery's jobs/handlers/discovery.py::_persist_failure exactly:
    the worker independently decides whether to reschedule this job with
    backoff, so flipping status to needs_attention here would race a silent
    automatic retry. Only surface once no further retry will happen.
    """
    async with sessionmaker() as db:
        raw_job_id = payload.get("job_id")
        job_id = UUID(str(raw_job_id)) if raw_job_id else None
        if job_id is not None and await _job_is_cancelled(db, job_id):
            return
        await WorkerAuthorizationFence(db).validate_payload(payload)
        repo = ContentArchitectRepository(db)
        session = await repo.get_session(session_id)
        if session is None:
            return
        code, message = stable_provider_failure(error)
        safe_error = {
            "code": code,
            "message": message,
            "retryable": bool(
                error.get("retryable", False)
                if isinstance(error, dict)
                else getattr(error, "retryable", False)
            ),
        }
        state = await repo.get_content_architect_state(session_id)
        will_retry = bool(
            error.get("will_retry")
            if isinstance(error, dict) and "will_retry" in error
            else safe_error["retryable"] and attempt < max_attempts
        )
        is_final = not will_retry
        if is_final:
            try:
                next_state = apply_needs_attention(state, safe_error)
            except Exception:
                next_state = state
        else:
            next_state = state.model_copy(deep=True)
        next_state.attempt = attempt
        await repo.save_content_architect_state(session_id, next_state, session.revision)
        await repo.mark_run_failed(run_id, safe_error)
        await db.commit()


async def _job_is_cancelled(db: Any, job_id: UUID) -> bool:
    job = await JobRepository(db).get_by_id(job_id)
    return job is None or job.status == JobStatus.CANCELLED.value


def _job_owns_active_state(state: Any, run_id: UUID, job_id: UUID | None) -> bool:
    from oryxenai.agents.content_architect.schemas import ContentArchitectStatus

    return (
        state.status is ContentArchitectStatus.BUILD_RUNNING
        and state.run_id == str(run_id)
        and (job_id is None or state.job_id == str(job_id))
    )
