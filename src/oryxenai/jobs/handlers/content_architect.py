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
from oryxenai.agents.shared.providers.errors import ProviderError
from oryxenai.core.logging import get_logger
from oryxenai.db.repositories.content_architect import ContentArchitectRepository
from oryxenai.db.session import get_sessionmaker

logger = get_logger("oryxenai.jobs.handlers.content_architect")

_AGENT_KEY = AgentKey.CONTENT_ARCHITECT
_BUILD_KIND = "content_architect.build"


class ContentArchitectBuildHandler:
    """Worker handler for content_architect.build."""

    kind: str = _BUILD_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute_persisted(payload, instance_id)


def _build_content_architect_agent(override_profile_name: str = "") -> Any:
    """Create a ContentArchitectAgent with the live provider adapter.

    override_profile_name is the session-sticky model/provider choice
    inherited from Discovery (see ContentArchitectService.start), if any.
    build_provider_client falls back to the default "content_architect"
    profile on its own if the override isn't usable.
    """
    from oryxenai.agents.content_architect.agent import ContentArchitectAgent
    from oryxenai.agents.shared.model_client import build_provider_client
    from oryxenai.core.settings import get_settings

    settings = get_settings()
    client = build_provider_client(
        "content_architect", settings.models, override_profile_name=override_profile_name
    )
    if client is None:
        from oryxenai.agents.shared.providers.errors import ProviderConfigError

        raise ProviderConfigError(
            "Content Architect agent requires a configured model profile. "
            "Check config/models.toml [profiles.content_architect] and ensure "
            "the matching API key is set in .env"
        )
    return ContentArchitectAgent(
        model_client=client, profile_name=override_profile_name or "content_architect"
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

    async with sessionmaker() as db:
        repo = ContentArchitectRepository(db)
        run = await repo.get_run(run_id)
        session = await repo.get_session(session_id)
        if run is None or session is None:
            raise ValueError("Content Architect run or session was not found")
        await repo.mark_run_started(run_id)
        state = await repo.get_content_architect_state(session_id)
        running = apply_build_running(state, str(run_id), state.job_id or "")
        running.attempt = attempt
        running.max_attempts = max_attempts
        expected_revision = int(payload.get("expected_session_revision", session.revision))
        await repo.save_content_architect_state(session_id, running, expected_revision)
        await db.commit()
        state_snapshot = dict(session.current_state)
        input_payload = dict(run.input_payload)

    agent = _build_content_architect_agent(str(input_payload.get("model_profile", "") or ""))
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
        await _persist_failure(sessionmaker, session_id, run_id, exc, attempt, max_attempts)
        raise
    except ContentArchitectModelOutputError as exc:
        # A one-off generation-quality issue on the same input, not a permanent
        # condition — retry it like any other transient provider error, bounded
        # by the same max_attempts budget.
        logger.warning("content_architect build produced invalid output: %s", exc)
        await _persist_failure(
            sessionmaker,
            session_id,
            run_id,
            ProviderError(code="MODEL_OUTPUT_INVALID", message=str(exc), retryable=True),
            attempt,
            max_attempts,
        )
        raise
    except Exception as exc:
        logger.warning("content_architect build failed with %s", type(exc).__name__)
        await _persist_failure(
            sessionmaker,
            session_id,
            run_id,
            ProviderError(
                code="MODEL_OPERATION_FAILED",
                message="Content Architect build failed.",
                retryable=False,
            ),
            attempt,
            max_attempts,
        )
        raise

    return await _apply_result(sessionmaker, session_id, run_id, result, attempt)


async def _apply_result(
    sessionmaker: Any,
    session_id: UUID,
    run_id: UUID,
    result: Any,
    attempt: int,
) -> dict[str, Any]:
    async with sessionmaker() as db:
        repo = ContentArchitectRepository(db)
        session = await repo.get_session(session_id)
        if session is None:
            raise ValueError("Content Architect session was not found")
        state = await repo.get_content_architect_state(session_id)

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
            raise ValueError("Content Architect state changed while the job was running")
        state_after = dict(updated.current_state)
        await repo.mark_run_succeeded(
            run_id,
            output,
            state_after,
            prompt_version=result.prompt_version,
            model_metadata={**result.model_metadata, "result_status": "succeeded"},
        )
        await db.commit()
        return {"status": "succeeded", "run_id": str(run_id), "operation": "build"}


async def _persist_failure(
    sessionmaker: Any,
    session_id: UUID,
    run_id: UUID,
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
        repo = ContentArchitectRepository(db)
        session = await repo.get_session(session_id)
        if session is None:
            return
        safe_error = {
            "code": getattr(error, "code", "MODEL_OPERATION_FAILED"),
            "message": getattr(error, "message", "Content Architect model operation failed."),
            "retryable": bool(getattr(error, "retryable", False)),
        }
        state = await repo.get_content_architect_state(session_id)
        is_final = not safe_error["retryable"] or attempt >= max_attempts
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
