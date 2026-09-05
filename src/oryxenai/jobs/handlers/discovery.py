"""Discovery agent background job handlers.

Registered job kinds:
  - discovery.understand_and_question
  - discovery.build_or_revise_brief

Legacy aliases (still registered so in-flight jobs keep working):
  - discovery.prepare_questions -> understand_and_question
  - discovery.build_brief -> build_or_revise_brief

Each handler runs the agent with the live provider adapter, applies the
resulting state transition, and always surfaces failures to the discovery
state so the UI can show them.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from oryxenai.agents.discovery.schemas import (
    DiscoveryQuestion,
    DiscoveryStatus,
    OperationMode,
)
from oryxenai.agents.discovery.state import (
    apply_brief_review,
    apply_brief_running,
    apply_needs_attention,
    apply_questions_ready,
    apply_questions_running,
    apply_start,
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
from oryxenai.db.repositories.discovery import DiscoveryRepository
from oryxenai.db.session import get_sessionmaker

logger = get_logger("oryxenai.jobs.handlers.discovery")

_AGENT_KEY = AgentKey.DISCOVERY
_UNDERSTAND_KIND = "discovery.understand_and_question"
_BUILD_BRIEF_KIND = "discovery.build_or_revise_brief"
_PREPARE_QUESTIONS_KIND = "discovery.prepare_questions"
_BUILD_BRIEF_LEGACY_KIND = "discovery.build_brief"

_QUESTIONS_OPS = {"understand_and_question", "prepare_questions"}
_BRIEF_OPS = {"build_or_revise_brief", "build_brief"}


async def _on_timeout_persisted(payload: dict[str, Any], error: dict[str, Any]) -> None:
    """Shared by every Discovery handler kind (worker.py calls this when the
    outer job-handler timeout fires). asyncio.wait_for cancels execute() from
    outside, so its own try/except (which calls _persist_failure) never
    runs — this is the only chance to reflect a terminal timeout into the
    discovery session state instead of leaving it stuck at a "*_running"
    status forever. See visual_design_director.py's identical hook for the
    same live-reproduced issue.
    """
    from oryxenai.core.settings import get_settings

    session_id = UUID(str(payload["portfolio_session_id"]))
    run_id = UUID(str(payload["agent_run_id"]))
    settings = get_settings()
    sessionmaker = get_sessionmaker(settings)
    attempt = int(payload.get("attempt", 1))
    max_attempts = int(payload.get("max_attempts", settings.worker_retry.max_attempts))
    await _persist_failure(sessionmaker, session_id, run_id, payload, error, attempt, max_attempts)


class DiscoveryUnderstandAndQuestionHandler:
    """Worker handler for discovery.understand_and_question."""

    kind: str = _UNDERSTAND_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute_persisted(payload, instance_id, "understand_and_question")

    async def on_timeout(self, payload: dict[str, Any], error: dict[str, Any]) -> None:
        await _on_timeout_persisted(payload, error)


class DiscoveryBuildOrReviseBriefHandler:
    """Worker handler for discovery.build_or_revise_brief."""

    kind: str = _BUILD_BRIEF_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute_persisted(payload, instance_id, "build_or_revise_brief")

    async def on_timeout(self, payload: dict[str, Any], error: dict[str, Any]) -> None:
        await _on_timeout_persisted(payload, error)


class DiscoveryPrepareQuestionsHandler:
    """Legacy alias handler for discovery.prepare_questions."""

    kind: str = _PREPARE_QUESTIONS_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute_persisted(payload, instance_id, "prepare_questions")

    async def on_timeout(self, payload: dict[str, Any], error: dict[str, Any]) -> None:
        await _on_timeout_persisted(payload, error)


class DiscoveryBuildBriefHandler:
    """Legacy alias handler for discovery.build_brief."""

    kind: str = _BUILD_BRIEF_LEGACY_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute_persisted(payload, instance_id, "build_brief")

    async def on_timeout(self, payload: dict[str, Any], error: dict[str, Any]) -> None:
        await _on_timeout_persisted(payload, error)


def _build_discovery_agent(
    override_profile_name: str = "",
    *,
    result_cache: Any = None,
    profile_fingerprint: str = "",
) -> Any:
    """Create a DiscoveryAgent with the live provider adapter.

    override_profile_name is the user's validated, session-sticky
    model/provider choice from the detached-development selector, if any.
    Unknown or unselectable values fail closed in the shared runtime.
    """
    from oryxenai.agents.discovery.agent import DiscoveryAgent
    from oryxenai.agents.shared.model_runtime import get_model_runtime
    from oryxenai.core.settings import get_settings

    settings = get_settings()
    runtime = get_model_runtime(settings.models)
    resolved_profile = runtime.resolve_profile_name("discovery", override_profile_name)
    return DiscoveryAgent(
        model_client=runtime.resolve("discovery", override_profile_name),
        profile_name=resolved_profile,
        result_cache=result_cache,
        profile_fingerprint=profile_fingerprint,
    )


async def _execute_persisted(
    payload: dict[str, Any],
    instance_id: str,
    operation: str,
) -> dict[str, Any]:
    """Execute an API-created run without holding a DB transaction open."""
    from oryxenai.core.settings import get_settings

    session_id = UUID(str(payload["portfolio_session_id"]))
    run_id = UUID(str(payload["agent_run_id"]))
    settings = get_settings()
    sessionmaker = get_sessionmaker(settings)
    attempt = int(payload.get("attempt", 1))
    max_attempts = int(payload.get("max_attempts", settings.worker_retry.max_attempts))

    async with sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_payload(payload)
        repo = DiscoveryRepository(db)
        run = await repo.get_run(run_id)
        session = await repo.get_session(session_id)
        if run is None or session is None:
            raise ValueError("Discovery run or session was not found")
        await repo.mark_run_started(run_id)
        state = await repo.get_discovery_state(session_id)
        running = _running_state(state, operation, run_id)
        running.attempt = attempt
        running.max_attempts = max_attempts
        expected_revision = int(payload.get("expected_session_revision", session.revision))
        await repo.save_discovery_state(session_id, running, expected_revision)
        await db.commit()
        state_snapshot = dict(session.current_state)
        input_payload = dict(run.input_payload)

    from oryxenai.agents.shared.model_runtime import get_model_runtime

    runtime = get_model_runtime(settings.models)
    requested_profile = str(input_payload.get("model_profile", "") or "")
    runtime_profile_id = runtime.resolve_profile_name("discovery", requested_profile)
    input_payload["runtime_profile_id"] = runtime_profile_id
    result_cache = build_result_cache(
        settings,
        owner_user_id=run.owner_user_id if run is not None else None,
        portfolio_session_id=session_id,
    )

    agent = _build_discovery_agent(
        requested_profile,
        result_cache=result_cache,
        profile_fingerprint=runtime.profile_fingerprint(runtime_profile_id),
    )
    agent_input: dict[str, Any] = {
        "operation": operation,
        "intake": input_payload.get("intake", {}),
        "prior_memory": input_payload.get("prior_memory", {}),
    }
    if operation in _BRIEF_OPS:
        agent_input["answers"] = input_payload.get("answers", {})
        agent_input["existing_brief"] = input_payload.get("existing_brief", "")
        agent_input["revision_request"] = input_payload.get("revision_request", "")
    context = build_context(
        portfolio_session_id=session_id,
        agent_key=_AGENT_KEY,
        current_state=state_snapshot,
        agent_input=agent_input,
        request_id=payload.get("request_id", ""),
        attempt=attempt,
        run_id=run_id,
    )

    from oryxenai.agents.discovery.agent import DiscoveryModelOutputError

    try:
        result = await agent.run(context)
    except ProviderError as exc:
        await _persist_failure(
            sessionmaker, session_id, run_id, payload, exc, attempt, max_attempts
        )
        raise
    except DiscoveryModelOutputError as exc:
        # The model produced a response that failed the output contract. This
        # is almost always a one-off generation-quality issue on the same
        # input, not a permanent condition — retry it like any other
        # transient provider error, bounded by the same max_attempts budget.
        logger.warning(
            "discovery operation=%s produced invalid output type=%s",
            operation,
            type(exc).__name__,
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
        logger.warning("discovery operation=%s failed with %s", operation, type(exc).__name__)
        await _persist_failure(
            sessionmaker,
            session_id,
            run_id,
            payload,
            ProviderError(
                code="MODEL_OPERATION_FAILED",
                message=f"Discovery {operation} failed.",
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
        operation,
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


def _running_state(state: Any, operation: str, run_id: UUID) -> Any:
    if operation in _QUESTIONS_OPS:
        if state.status == DiscoveryStatus.NEEDS_ATTENTION:
            return apply_questions_running(apply_start(state))
        if state.status == DiscoveryStatus.QUESTIONS_QUEUED:
            return apply_questions_running(state)
        return state.model_copy(deep=True)

    if state.status in {
        DiscoveryStatus.ANSWERS_IN_PROGRESS,
        DiscoveryStatus.NEEDS_ATTENTION,
        DiscoveryStatus.BRIEF_REVIEW,
    }:
        return apply_brief_running(
            state,
            str(run_id),
            state.brief.job_id or "",
        )
    return state.model_copy(deep=True)


async def _apply_result(
    sessionmaker: Any,
    session_id: UUID,
    run_id: UUID,
    payload: dict[str, Any],
    operation: str,
    result: Any,
    attempt: int,
    runtime_profile_id: str,
) -> dict[str, Any]:
    async with sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_payload(payload)
        repo = DiscoveryRepository(db)
        session = await repo.get_session(session_id)
        if session is None:
            raise ValueError("Discovery session was not found")
        state = await repo.get_discovery_state(session_id)

        if operation in _QUESTIONS_OPS:
            questions = [
                DiscoveryQuestion.model_validate(item)
                for item in (result.output.get("questions") or [])
            ]
            next_state = apply_questions_ready(
                state,
                items=questions,
                version=result.prompt_version,
                run_id=str(run_id),
                mode=OperationMode(result.output.get("mode", OperationMode.ASK_QUESTIONS.value)),
                assistant_message=result.output.get("assistant_message", ""),
                memory_update=result.output.get("memory_update", {}) or {},
            )
        else:
            run = await repo.get_run(run_id)
            revision_request = ""
            if run is not None:
                revision_request = str(run.input_payload.get("revision_request", "") or "")
            next_state = apply_brief_review(
                state,
                version=result.prompt_version,
                run_id=str(run_id),
                title=result.output.get("brief_title", ""),
                markdown=result.output.get("brief_markdown", ""),
                open_items=result.output.get("open_items", []) or [],
                memory_update=result.output.get("memory_update", {}) or {},
                revision_request=revision_request,
                user_summary=result.output.get("user_summary", ""),
                profile=result.output.get("profile", {}) or {},
            )
        next_state.attempt = attempt

        updated = await repo.save_discovery_state(session_id, next_state, session.revision)
        if updated is None:
            raise ValueError("Discovery state changed while the job was running")
        state_after = dict(updated.current_state)
        await repo.mark_run_succeeded(
            run_id,
            result.output,
            state_after,
            prompt_version=result.prompt_version,
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
    error: Any,
    attempt: int,
    max_attempts: int,
) -> None:
    """Record a failed attempt. Only surface it to the user once it's final.

    The worker (worker.py::_fail_job) independently decides whether to
    reschedule this same job with backoff, using this exact
    retryable/attempt/max_attempts combination. When it will reschedule,
    flipping discovery.status to needs_attention here would be premature —
    the UI would show a dead-end error and a manual "Try again" while the
    backend is about to silently retry on its own, racing the two. So this
    only becomes user-visible once no further automatic retry will happen.
    """
    async with sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_payload(payload)
        repo = DiscoveryRepository(db)
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
        state = await repo.get_discovery_state(session_id)
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
        await repo.save_discovery_state(session_id, next_state, session.revision)
        await repo.mark_run_failed(run_id, safe_error)
        await db.commit()
