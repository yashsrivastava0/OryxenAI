"""Discovery agent background job handlers.

Registered job kinds:
  - discovery.prepare_questions
  - discovery.build_brief

Each handler creates a DiscoveryAgent wired to the real OpenCode Go
adapter, invokes the appropriate operation, and returns the structured
result.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from oryxenai.agents.discovery.schemas import DiscoveryAnalysisResult, DiscoveryBrief
from oryxenai.agents.discovery.service import (
    DiscoveryOperationError,
    assign_stable_analysis_ids,
)
from oryxenai.agents.discovery.state import (
    apply_brief_review,
    apply_brief_running,
    apply_needs_attention,
    apply_questions_ready,
    apply_questions_running,
)
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey, AgentResult
from oryxenai.agents.shared.providers.errors import ProviderError
from oryxenai.core.logging import get_logger
from oryxenai.db.repositories.discovery import DiscoveryRepository
from oryxenai.db.session import get_sessionmaker

logger = get_logger("oryxenai.jobs.handlers.discovery")

_AGENT_KEY = AgentKey.DISCOVERY
_PREPARE_QUESTIONS_KIND = "discovery.prepare_questions"
_BUILD_BRIEF_KIND = "discovery.build_brief"


def _build_discovery_agent() -> Any:
    """Create a DiscoveryAgent with the real OpenCode Go adapter.

    Returns the agent instance. Raises ProviderError if the adapter
    cannot be built (missing key, bad config).
    """
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


async def _invoke_agent(
    context: Any,
    handler_id: str,
) -> dict[str, Any]:
    """Invoke the Discovery agent and return its output dict.

    Raises ProviderError subclasses from the model adapter layer.
    These are caught by the worker and mapped to JobError.
    """
    agent = _build_discovery_agent()
    result: AgentResult = await agent.run(context)
    logger.info(
        "discovery handler=%s operation=%s prompt_version=%s succeeded",
        handler_id,
        context.agent_input.get("operation", "unknown"),
        result.prompt_version,
    )
    return result.output


class DiscoveryPrepareQuestionsHandler:
    """Worker handler for discovery.prepare_questions."""

    kind: str = _PREPARE_QUESTIONS_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        if payload.get("agent_run_id"):
            return await _execute_persisted(payload, instance_id, "prepare_questions")
        _validate_discovery_payload(payload)

        context = build_context(
            portfolio_session_id=payload["portfolio_session_id"],
            agent_key=_AGENT_KEY,
            current_state=payload.get("session_state", {}),
            agent_input={
                "operation": "prepare_questions",
                "intake": payload["intake"],
            },
            request_id=payload.get("request_id", ""),
            attempt=payload.get("attempt", 1),
        )

        try:
            return await _invoke_agent(context, "prepare_questions")
        except ProviderError as exc:
            raise _to_job_error(exc) from exc


class DiscoveryBuildBriefHandler:
    """Worker handler for discovery.build_brief."""

    kind: str = _BUILD_BRIEF_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        if payload.get("agent_run_id"):
            return await _execute_persisted(payload, instance_id, "build_brief")
        _validate_discovery_payload(payload)

        context = build_context(
            portfolio_session_id=payload["portfolio_session_id"],
            agent_key=_AGENT_KEY,
            current_state=payload.get("session_state", {}),
            agent_input={
                "operation": "build_brief",
                "intake": payload["intake"],
                "analysis": payload.get("analysis", {}),
                "answers": payload.get("answers", {}),
            },
            request_id=payload.get("request_id", ""),
            attempt=payload.get("attempt", 1),
        )

        try:
            return await _invoke_agent(context, "build_brief")
        except ProviderError as exc:
            raise _to_job_error(exc) from exc


def _validate_discovery_payload(payload: dict[str, Any]) -> None:
    """Validate required fields are present in the payload."""
    missing: list[str] = []
    for field in ("portfolio_session_id", "intake"):
        if not payload.get(field):
            missing.append(field)
    if missing:
        raise ValueError(f"Missing required payload fields: {', '.join(missing)}")


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

    async with sessionmaker() as db:
        repo = DiscoveryRepository(db)
        run = await repo.get_run(run_id)
        session = await repo.get_session(session_id)
        if run is None or session is None:
            raise ValueError("Discovery run or session was not found")
        await repo.mark_run_started(run_id)
        state = await repo.get_discovery_state(session_id)
        expected_source = int(payload.get("expected_source_revision", 0))
        expected_session = int(payload.get("expected_session_revision", session.revision))
        can_mark_running = (
            session.revision == expected_session
            and state.source_revision == expected_source
            and _status_matches_queued(state.status.value, operation)
        )
        if can_mark_running:
            try:
                running = (
                    apply_questions_running(state)
                    if operation == "prepare_questions"
                    else apply_brief_running(state)
                )
                updated = await repo.save_discovery_state(session_id, running, session.revision)
                if updated is not None:
                    state = running
            except Exception as exc:
                # A late retry may already have moved the state to running.
                logger.debug(
                    "discovery state already moved before worker start: %s", type(exc).__name__
                )
        await db.commit()
        input_payload = dict(run.input_payload)
        state_snapshot = dict(session.current_state)

    try:
        agent = _build_discovery_agent()
        agent_input: dict[str, Any] = {
            "operation": operation,
            "intake": input_payload.get("intake", {}),
        }
        if operation == "build_brief":
            async with sessionmaker() as db:
                repo = DiscoveryRepository(db)
                analysis_run_id = input_payload.get("analysis_run_id")
                analysis_run = (
                    await repo.get_run(UUID(str(analysis_run_id))) if analysis_run_id else None
                )
                analysis = (
                    (analysis_run.output_payload or {}).get("analysis", {}) if analysis_run else {}
                )
            input_payload["analysis"] = analysis
            agent_input["analysis"] = analysis
            agent_input["answers"] = input_payload.get("answers", {})
        context = build_context(
            portfolio_session_id=session_id,
            agent_key=_AGENT_KEY,
            current_state=state_snapshot,
            agent_input=agent_input,
            request_id=payload.get("request_id", ""),
            attempt=int(payload.get("attempt", 1)),
            run_id=run_id,
        )
        result = await agent.run(context)
    except asyncio.CancelledError:
        await _persist_failure(
            sessionmaker,
            session_id,
            run_id,
            payload,
            DiscoveryOperationError(
                "MODEL_OPERATION_CANCELLED",
                "The Discovery model operation was cancelled.",
            ),
        )
        raise
    except ProviderError as exc:
        await _persist_failure(sessionmaker, session_id, run_id, payload, exc)
        raise
    except Exception as exc:
        await _persist_failure(
            sessionmaker,
            session_id,
            run_id,
            payload,
            DiscoveryOperationError("MODEL_OPERATION_FAILED", "Discovery model operation failed."),
        )
        logger.warning("discovery operation=%s failed with %s", operation, type(exc).__name__)
        raise

    return await _apply_persisted_result(
        sessionmaker,
        session_id,
        run_id,
        payload,
        operation,
        result,
        input_payload,
    )


async def _apply_persisted_result(
    sessionmaker: Any,
    session_id: UUID,
    run_id: UUID,
    payload: dict[str, Any],
    operation: str,
    result: AgentResult,
    input_payload: dict[str, Any],
) -> dict[str, Any]:
    from oryxenai.agents.discovery.validators import validate_call_a_result, validate_call_b_result
    from oryxenai.core.settings import get_settings

    async with sessionmaker() as db:
        repo = DiscoveryRepository(db)
        session = await repo.get_session(session_id)
        if session is None:
            raise ValueError("Discovery session was not found")
        state = await repo.get_discovery_state(session_id)
        expected_source = int(payload.get("expected_source_revision", 0))
        expected_answer = int(payload.get("expected_answer_revision", 0))
        stale = state.source_revision != expected_source or (
            operation == "build_brief" and state.answers.revision != expected_answer
        )
        output = dict(result.output)
        output["stale_result"] = stale
        if stale:
            await repo.mark_run_succeeded(
                run_id,
                output,
                dict(session.current_state),
                prompt_version=result.prompt_version,
                model_metadata={**result.model_metadata, "result_status": "stale"},
            )
            await db.commit()
            return {"status": "stale", "run_id": str(run_id), "operation": operation}

        if output.get("status") == "failed":
            error: dict[str, Any] = {
                "code": "MODEL_OPERATION_FAILED",
                "message": "The Discovery model did not return a usable result.",
            }
            await _mark_needs_attention(repo, session, state, error)
            await repo.mark_run_failed(run_id, error, model_metadata=result.model_metadata)
            await db.commit()
            return {"status": "failed", "run_id": str(run_id), "operation": operation}

        config = get_settings().discovery
        try:
            if operation == "prepare_questions":
                analysis = assign_stable_analysis_ids(
                    DiscoveryAnalysisResult.model_validate(output.get("analysis", {}))
                )
                source_texts = {
                    "main_prompt": input_payload.get("intake", {}).get("main_prompt") or "",
                    "resume_text": input_payload.get("intake", {}).get("resume_text") or "",
                }
                validation = validate_call_a_result(analysis, source_texts, config)
                if not validation.is_valid:
                    error = {
                        "code": "MODEL_OUTPUT_INVALID",
                        "message": "Discovery analysis failed validation.",
                    }
                    await _mark_needs_attention(repo, session, state, error)
                    await repo.mark_run_failed(run_id, error, model_metadata=result.model_metadata)
                    await db.commit()
                    return {"status": "failed", "run_id": str(run_id), "operation": operation}
                if state.status.value != "questions_running":
                    raise ValueError("Discovery questions result is no longer current")
                ready = apply_questions_ready(
                    state,
                    analysis.questions,
                    str(run_id),
                    expected_source,
                )
                output["analysis"] = analysis.model_dump(mode="json")
                updated = await repo.save_discovery_state(session_id, ready, session.revision)
            else:
                brief = DiscoveryBrief.model_validate(output.get("brief", {}))
                analysis = DiscoveryAnalysisResult.model_validate(input_payload.get("analysis", {}))
                fact_ids = {fact.local_key for fact in analysis.fact_candidates}
                project_ids = {project.title for project in analysis.normalized_profile.projects}
                validation = validate_call_b_result(brief, fact_ids, project_ids, config)
                if not validation.is_valid:
                    error = {
                        "code": "MODEL_OUTPUT_INVALID",
                        "message": "Discovery brief failed validation.",
                    }
                    await _mark_needs_attention(repo, session, state, error)
                    await repo.mark_run_failed(run_id, error, model_metadata=result.model_metadata)
                    await db.commit()
                    return {"status": "failed", "run_id": str(run_id), "operation": operation}
                if state.status.value != "brief_running":
                    raise ValueError("Discovery brief result is no longer current")
                review = apply_brief_review(state, brief, str(run_id))
                review.brief.generated_from_source_revision = expected_source
                review.brief.generated_from_answer_revision = expected_answer
                output["brief"] = brief.model_dump(mode="json")
                updated = await repo.save_discovery_state(session_id, review, session.revision)
        except Exception:
            error = {"code": "MODEL_OUTPUT_INVALID", "message": "Discovery output was not usable."}
            await _mark_needs_attention(repo, session, state, error)
            await repo.mark_run_failed(run_id, error, model_metadata=result.model_metadata)
            await db.commit()
            return {"status": "failed", "run_id": str(run_id), "operation": operation}

        if updated is None:
            output["stale_result"] = True
            await repo.mark_run_succeeded(
                run_id,
                output,
                dict(session.current_state),
                prompt_version=result.prompt_version,
                model_metadata={**result.model_metadata, "result_status": "stale"},
            )
            await db.commit()
            return {"status": "stale", "run_id": str(run_id), "operation": operation}
        state_after = dict(session.current_state)
        state_after["discovery"] = updated.current_state.get("discovery", {})
        await repo.mark_run_succeeded(
            run_id,
            output,
            state_after,
            prompt_version=result.prompt_version,
            model_metadata={**result.model_metadata, "result_status": "succeeded"},
        )
        await db.commit()
        return {"status": "succeeded", "run_id": str(run_id), "operation": operation}


def _status_matches_queued(status: str, operation: str) -> bool:
    return status == ("questions_queued" if operation == "prepare_questions" else "brief_queued")


async def _mark_needs_attention(
    repo: DiscoveryRepository,
    session: Any,
    state: Any,
    error: dict[str, Any],
) -> None:
    if state.status.value not in {"questions_running", "brief_running"}:
        return
    updated = apply_needs_attention(state, error)
    await repo.save_discovery_state(session.id, updated, session.revision)


async def _persist_failure(
    sessionmaker: Any,
    session_id: UUID,
    run_id: UUID,
    payload: dict[str, Any],
    error: Any,
) -> None:
    async with sessionmaker() as db:
        repo = DiscoveryRepository(db)
        session = await repo.get_session(session_id)
        if session is None:
            return
        retryable = bool(getattr(error, "retryable", False))
        safe_error = {
            "code": getattr(error, "code", "MODEL_OPERATION_FAILED"),
            "message": getattr(error, "message", "Discovery model operation failed."),
            "retryable": retryable,
        }
        state = await repo.get_discovery_state(session_id)
        if not retryable:
            await _mark_needs_attention(repo, session, state, safe_error)
        await repo.mark_run_failed(run_id, safe_error)
        await db.commit()


def _to_job_error(exc: ProviderError) -> Exception:
    """Map a ProviderError to a structured error that the worker understands.

    ProviderError already has a retryable flag and structured details.
    The worker's _fail_job() accepts dict[str, Any] for error payloads.
    """
    return (
        exc  # ProviderError is already structured — worker maps it via its existing error handling
    )
