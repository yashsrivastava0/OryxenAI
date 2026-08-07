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
from oryxenai.agents.shared.providers.errors import ProviderError
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


class DiscoveryUnderstandAndQuestionHandler:
    """Worker handler for discovery.understand_and_question."""

    kind: str = _UNDERSTAND_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute_persisted(payload, instance_id, "understand_and_question")


class DiscoveryBuildOrReviseBriefHandler:
    """Worker handler for discovery.build_or_revise_brief."""

    kind: str = _BUILD_BRIEF_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute_persisted(payload, instance_id, "build_or_revise_brief")


class DiscoveryPrepareQuestionsHandler:
    """Legacy alias handler for discovery.prepare_questions."""

    kind: str = _PREPARE_QUESTIONS_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute_persisted(payload, instance_id, "prepare_questions")


class DiscoveryBuildBriefHandler:
    """Legacy alias handler for discovery.build_brief."""

    kind: str = _BUILD_BRIEF_LEGACY_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute_persisted(payload, instance_id, "build_brief")


def _build_discovery_agent() -> Any:
    """Create a DiscoveryAgent with the live provider adapter."""
    from oryxenai.agents.discovery.agent import DiscoveryAgent
    from oryxenai.agents.shared.model_client import build_provider_client
    from oryxenai.core.settings import get_settings

    settings = get_settings()
    client = build_provider_client("discovery", settings.models)
    if client is None:
        from oryxenai.agents.shared.providers.errors import ProviderConfigError

        raise ProviderConfigError(
            "Discovery agent requires a configured model profile. "
            "Check config/models.toml [profiles.discovery] and ensure "
            "OPENCODE_GO_API_KEY is set in .env"
        )
    return DiscoveryAgent(model_client=client)


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

    agent = _build_discovery_agent()
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

    try:
        result = await agent.run(context)
    except ProviderError as exc:
        await _persist_failure(sessionmaker, session_id, run_id, payload, exc, attempt)
        raise
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
        )
        raise

    return await _apply_result(
        sessionmaker,
        session_id,
        run_id,
        payload,
        operation,
        result,
        attempt,
    )


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
) -> dict[str, Any]:
    async with sessionmaker() as db:
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
            model_metadata={**result.model_metadata, "result_status": "succeeded"},
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
) -> None:
    async with sessionmaker() as db:
        repo = DiscoveryRepository(db)
        session = await repo.get_session(session_id)
        if session is None:
            return
        safe_error = {
            "code": getattr(error, "code", "MODEL_OPERATION_FAILED"),
            "message": getattr(error, "message", "Discovery model operation failed."),
            "retryable": bool(getattr(error, "retryable", False)),
        }
        state = await repo.get_discovery_state(session_id)
        try:
            next_state = apply_needs_attention(state, safe_error)
        except Exception:
            next_state = state
        next_state.attempt = attempt
        await repo.save_discovery_state(session_id, next_state, session.revision)
        await repo.mark_run_failed(run_id, safe_error)
        await db.commit()
