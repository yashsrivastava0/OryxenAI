"""Visual Design Director agent background job handler.

Registered job kind:
  - visual_design_director.build

One handler runs the whole adaptive workflow (the agent itself makes up to
3 sequential model calls internally — see agents/visual_design_director/agent.py).
Applies the resulting state transition and always surfaces failures to the
visual_design_director state so the API can show them. Mirrors
jobs/handlers/content_architect.py exactly, one stage down the pipeline.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.agents.shared.observability import durable_model_metadata
from oryxenai.agents.shared.providers.errors import (
    ModelOutputInvalidError,
    ProviderError,
    stable_provider_failure,
)
from oryxenai.agents.visual_design_director.agent import VisualDesignDirectorModelOutputError
from oryxenai.agents.visual_design_director.schemas import (
    AssetBrief,
    PageVisualDirection,
    ResourceCandidate,
)
from oryxenai.agents.visual_design_director.service import compute_route_publication_hash
from oryxenai.agents.visual_design_director.state import (
    apply_build_result,
    apply_build_running,
    apply_needs_attention,
)
from oryxenai.auth.worker_fence import WorkerAuthorizationFence
from oryxenai.core.logging import get_logger
from oryxenai.db.repositories.visual_design_director import VisualDesignDirectorRepository
from oryxenai.db.session import get_sessionmaker

logger = get_logger("oryxenai.jobs.handlers.visual_design_director")

_AGENT_KEY = AgentKey.VISUAL_DESIGN_DIRECTOR
_BUILD_KIND = "visual_design_director.build"

_VALIDATION_CATEGORY_MARKERS = {
    "mode": ("'mode'", "pages_included"),
    "visual_language": ("'visual_language'", "'shared_visual_systems'"),
    "page_routes": ("'pages'", "page ", "route_id"),
    "scenes": ("scene", "responsive_behavior", "motion_intent"),
    "assets": ("asset",),
    "resources": ("resource",),
    "compiler_handoff": ("compiler_handoff",),
    "references": ("section", "claim", "content_ref"),
}


def _validation_error_categories(errors: list[str]) -> list[str]:
    """Reduce generated validation messages to fixed, privacy-safe labels."""
    categories = {
        category
        for error in errors
        for category, markers in _VALIDATION_CATEGORY_MARKERS.items()
        if any(marker in error.casefold() for marker in markers)
    }
    return sorted(categories or {"other"})


class VisualDesignDirectorBuildHandler:
    """Worker handler for visual_design_director.build."""

    kind: str = _BUILD_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute_persisted(payload, instance_id)

    async def on_timeout(self, payload: dict[str, Any], error: dict[str, Any]) -> None:
        """Called by the worker when the outer job-handler timeout fires.

        asyncio.wait_for cancels the execute() coroutine from outside, so its
        own try/except (which calls _persist_failure) never runs — this is
        the only chance to reflect a terminal timeout into the
        visual_design_director session state instead of leaving it stuck at
        "build_running" forever (live-reproduced during local testing).
        The worker supplies the same retryable/will_retry decision used for
        queue rescheduling, so the session cannot report a terminal failure
        while another automatic attempt is pending.
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


def _build_visual_design_director_agent(override_profile_name: str = "") -> Any:
    """Create a VisualDesignDirectorAgent with the live provider adapter.

    override_profile_name is the validated, session-sticky model/provider
    choice inherited from Content Architect (see
    VisualDesignDirectorService.start). Unknown or unselectable values fail
    closed in the shared runtime.
    """
    from oryxenai.agents.shared.model_runtime import get_model_runtime
    from oryxenai.agents.visual_design_director.agent import VisualDesignDirectorAgent
    from oryxenai.core.settings import get_settings

    settings = get_settings()
    runtime = get_model_runtime(settings.models)
    resolved_profile = runtime.resolve_profile_name("visual_design_director", override_profile_name)
    return VisualDesignDirectorAgent(
        model_client=runtime.resolve("visual_design_director", override_profile_name),
        profile_name=resolved_profile,
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
        await WorkerAuthorizationFence(db).validate_payload(payload)
        repo = VisualDesignDirectorRepository(db)
        run = await repo.get_run(run_id)
        session = await repo.get_session(session_id)
        if run is None or session is None:
            raise ValueError("Visual Design Director run or session was not found")
        await repo.mark_run_started(run_id)
        state = await repo.get_visual_design_director_state(session_id)
        running = apply_build_running(state, str(run_id), state.job_id or "")
        running.attempt = attempt
        running.max_attempts = max_attempts
        expected_revision = int(payload.get("expected_session_revision", session.revision))
        await repo.save_visual_design_director_state(session_id, running, expected_revision)
        await db.commit()
        state_snapshot = dict(session.current_state)
        input_payload = dict(run.input_payload)

    from oryxenai.agents.shared.model_runtime import get_model_runtime

    input_payload["runtime_profile_id"] = get_model_runtime(settings.models).resolve_profile_name(
        "visual_design_director", str(input_payload.get("model_profile", "") or "")
    )

    async with sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_payload(payload)
    agent = _build_visual_design_director_agent(str(input_payload.get("model_profile", "") or ""))
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
    except VisualDesignDirectorModelOutputError as exc:
        # A one-off generation-quality issue on the same input, not a permanent
        # condition — retry it like any other transient provider error, bounded
        # by the same max_attempts budget. Do not log validation detail: it can
        # contain generated portfolio content rather than safe diagnostics.
        logger.warning(
            "visual_design_director build produced invalid output type=%s operation=%s "
            "validation_error_count=%d validation_categories=%s",
            type(exc).__name__,
            exc.operation,
            len(exc.errors),
            _validation_error_categories(exc.errors),
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
        logger.warning("visual_design_director build failed with %s", type(exc).__name__)
        await _persist_failure(
            sessionmaker,
            session_id,
            run_id,
            payload,
            ProviderError(
                code="MODEL_OPERATION_FAILED",
                message="Visual Design Director build failed.",
                retryable=False,
            ),
            attempt,
            max_attempts,
        )
        raise

    return await _apply_result(
        sessionmaker,
        session_id,
        run_id,
        payload,
        result,
        attempt,
        str(input_payload["runtime_profile_id"]),
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
        repo = VisualDesignDirectorRepository(db)
        session = await repo.get_session(session_id)
        if session is None:
            raise ValueError("Visual Design Director session was not found")
        state = await repo.get_visual_design_director_state(session_id)

        content_architect = await repo.get_content_architect_snapshot(session_id)
        current_hash = content_architect.approved.content_hash if content_architect.approved else ""
        current_route_publication_hash = compute_route_publication_hash(
            [route.model_dump(mode="json") for route in content_architect.route_plan]
        )
        if (
            current_hash != state.source_ref.content_architect_content_hash
            or current_route_publication_hash != state.source_ref.route_publication_hash
        ):
            safe_error = {
                "code": "VISUAL_DESIGN_DIRECTOR_STALE_SOURCE",
                "message": "Content Architect changed while this Visual Design Director build was running.",
                "retryable": False,
            }
            next_state = apply_needs_attention(state, safe_error)
            next_state.attempt = attempt
            await repo.save_visual_design_director_state(session_id, next_state, session.revision)
            await repo.mark_run_failed(run_id, safe_error)
            await db.commit()
            return {"status": "failed", "run_id": str(run_id), "operation": "build"}

        output = result.output
        pages = [PageVisualDirection.model_validate(item) for item in (output.get("pages") or [])]
        asset_briefs = [
            AssetBrief.model_validate(item) for item in (output.get("asset_briefs") or [])
        ]
        resource_candidates = [
            ResourceCandidate.model_validate(item)
            for item in (output.get("resource_candidates") or [])
        ]
        next_state = apply_build_result(
            state,
            version=result.prompt_version,
            run_id=str(run_id),
            user_summary=output.get("user_summary", "") or "",
            meta=output.get("meta", {}) or {},
            source_refs=output.get("source_refs", {}) or {},
            visual_language=output.get("visual_language", {}) or {},
            shared_visual_systems=output.get("shared_visual_systems", {}) or {},
            navigation_direction=output.get("navigation_direction", {}) or {},
            motion_system=output.get("motion_system", {}) or {},
            interaction_system=output.get("interaction_system", {}) or {},
            pages=pages,
            asset_briefs=asset_briefs,
            resource_candidates=resource_candidates,
            accessibility_and_performance=output.get("accessibility_and_performance", {}) or {},
            must_preserve=output.get("must_preserve", []) or [],
            must_not_fabricate=output.get("must_not_fabricate", []) or [],
            conflicts=output.get("conflicts", []) or [],
            warnings=output.get("warnings", []) or [],
            compiler_handoff=output.get("compiler_handoff", {}) or {},
            stages_run=output.get("stages_run", []) or [],
            memory_update=output.get("memory_update", {}) or {},
        )
        next_state.attempt = attempt

        updated = await repo.save_visual_design_director_state(
            session_id, next_state, session.revision
        )
        if updated is None:
            raise ValueError("Visual Design Director state changed while the job was running")
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

    Mirrors content_architect's jobs/handlers/content_architect.py::_persist_failure
    exactly: the worker independently decides whether to reschedule this job
    with backoff, so flipping status to needs_attention here would race a
    silent automatic retry. Only surface once no further retry will happen.
    """
    async with sessionmaker() as db:
        await WorkerAuthorizationFence(db).validate_payload(payload)
        repo = VisualDesignDirectorRepository(db)
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
        state = await repo.get_visual_design_director_state(session_id)
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
        await repo.save_visual_design_director_state(session_id, next_state, session.revision)
        await repo.mark_run_failed(run_id, safe_error)
        await db.commit()
