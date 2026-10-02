"""Code Generator background job handler.

Registered job kind:
  - code_generator.build

One handler runs the whole build (generate -> validate -> seal -> promote). It
never retries and never repairs: any failure is persisted as one exact
what / where / why envelope on the version row and the session state, and the
handler returns a ``failed`` result so the job row ends terminal. The page the
user already has is only ever replaced inside the single promote transaction.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from oryxenai.agents.code_generator import messages
from oryxenai.agents.code_generator.diagnostics import (
    failure_from_provider_error,
    failure_unexpected,
    reference_for,
)
from oryxenai.agents.code_generator.pipeline import BuildOutcome, build_page
from oryxenai.agents.code_generator.schemas import CodeGeneratorFailure, FailureEnvelope
from oryxenai.agents.code_generator.state import (
    apply_build_failed,
    apply_build_succeeded,
    in_flight_matches,
)
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.agents.shared.observability import durable_model_metadata
from oryxenai.agents.shared.providers.errors import ProviderError
from oryxenai.auth.worker_fence import WorkerAuthorizationFence
from oryxenai.core.logging import get_logger
from oryxenai.db.repositories.site_versions import SiteVersionRepository
from oryxenai.db.session import get_sessionmaker
from oryxenai.jobs.contracts import JobStatus
from oryxenai.jobs.repository import JobRepository
from oryxenai.themes import DEFAULT_THEME_ID, get_theme

logger = get_logger("oryxenai.jobs.handlers.code_generator")

_AGENT_KEY = AgentKey.CODE_GENERATOR
_BUILD_KIND = "code_generator.build"
_TERMINAL_VERSION_STATUSES = frozenset({"ready", "failed", "cancelled", "no_change"})


class _BuildStopped(Exception):
    """The job was cancelled (Stop) while the build was running; nothing to persist."""


class CodeGeneratorBuildHandler:
    """Worker handler for code_generator.build."""

    kind: str = _BUILD_KIND

    async def execute(self, payload: dict[str, Any], instance_id: str) -> dict[str, Any]:
        return await _execute(payload)

    async def on_timeout(self, payload: dict[str, Any], error: dict[str, Any]) -> None:
        """The outer job timeout fired: cancellation skipped the handler's own error path."""
        envelope = FailureEnvelope(
            code="JOB_TIMEOUT",
            stage="generate",
            summary="The build took too long and was stopped.",
            cause="The background job exceeded its time limit before the page was finished.",
            owner="infrastructure",
            retryable=True,
            action="Your last verified page is unchanged. Start the build again.",
            reference=reference_for(payload.get("agent_run_id", "")),
        )
        await _persist_failure_from_payload(payload, envelope, {})

    async def on_terminal_failure(self, payload: dict[str, Any], error: dict[str, Any]) -> None:
        """The worker gave up on the job. A no-op when the handler already reported."""
        envelope = FailureEnvelope(
            code=str(error.get("code") or "JOB_FAILED"),
            stage="generate",
            summary="The build stopped unexpectedly.",
            cause="The background job ended with an error before the page was finished.",
            owner="infrastructure",
            retryable=True,
            action="Your last verified page is unchanged. Start the build again.",
            reference=reference_for(payload.get("agent_run_id", "")),
        )
        await _persist_failure_from_payload(payload, envelope, {})


def _build_code_generator_agent(
    *,
    input_classification: str = "personal",
    theme_id: str = DEFAULT_THEME_ID,
) -> Any:
    """Create the Code Generator agent with the live, policy-routed model client."""
    from oryxenai.agents.code_generator.agent import CodeGeneratorAgent
    from oryxenai.agents.shared.model_runtime import get_model_runtime
    from oryxenai.core.settings import get_settings

    settings = get_settings()
    runtime = get_model_runtime(settings.models)
    return CodeGeneratorAgent(
        model_client=runtime.routed_client(
            "code_generator", input_classification=input_classification
        ),
        theme_id=theme_id,
        profile_name=runtime.policy_profile_name("code_generator", "generate_page"),
    )


def _build_verifier() -> Any:
    """The browser verifier for this deployment, or ``None`` when verification is off."""
    return None


async def _execute(payload: dict[str, Any]) -> dict[str, Any]:
    from oryxenai.core.settings import get_settings

    settings = get_settings()
    sessionmaker = get_sessionmaker(settings)
    session_id = UUID(str(payload["portfolio_session_id"]))
    run_id = UUID(str(payload["agent_run_id"]))
    version_id = UUID(str(payload["version_id"]))
    attempt = int(payload.get("attempt", 1))
    raw_job_id = payload.get("job_id")
    job_id = UUID(str(raw_job_id)) if raw_job_id else None
    reference = reference_for(run_id)
    trace: dict[str, Any] = {"run_id": str(run_id), "reference": reference}

    # ── 1. claim: confirm this job still owns the in-flight build, create the version ──
    async with sessionmaker() as db:
        if not await _job_is_ours(db, payload):
            return {"status": "cancelled", "job_id": str(job_id or "")}
        await WorkerAuthorizationFence(db).validate_payload(payload)
        repo = SiteVersionRepository(db)
        run = await repo.get_run(run_id)
        session = await repo.lock_session(session_id)
        if run is None or session is None:
            raise ValueError("Code Generator run or session was not found")
        state = await repo.get_state(session_id)
        if not in_flight_matches(state, run_id, job_id):
            return {"status": "cancelled", "job_id": str(job_id or "")}
        await repo.mark_run_started(run_id)
        input_payload: dict[str, Any] = dict(run.input_payload)
        page_content: dict[str, Any] = dict(input_payload.get("page_content") or {})
        existing = await repo.get_version(version_id, session_id=session_id, light=True)
        if existing is not None and existing.status in _TERMINAL_VERSION_STATUSES:
            return {"status": "cancelled", "job_id": str(job_id or "")}
        if existing is None:
            await repo.create_version(
                version_id=version_id,
                session_id=session_id,
                origin=str(input_payload.get("origin", "initial")),
                status="generating",
                instruction=str(input_payload.get("instruction", "")),
                content_snapshot=page_content,
                content_sha256=str(input_payload.get("content_sha256", "")),
                theme_id=str(input_payload.get("theme_id", DEFAULT_THEME_ID)),
                run_id=run_id,
                job_id=job_id,
            )
        else:
            await repo.set_version_status(version_id, "generating")
        await db.commit()
        state_snapshot = dict(session.current_state)

    theme_id = str(input_payload.get("theme_id") or DEFAULT_THEME_ID)
    trace["theme_id"] = theme_id
    trace["content_sha256"] = str(input_payload.get("content_sha256", ""))

    async def on_stage(stage: str) -> None:
        async with sessionmaker() as stage_db:
            if not await _job_is_ours(stage_db, payload):
                raise _BuildStopped
            await SiteVersionRepository(stage_db).set_version_status(version_id, stage)
            await stage_db.commit()

    # ── 2. build: generate -> validate -> seal (-> verify) ──
    try:
        theme = get_theme(theme_id)
        agent = _build_code_generator_agent(
            input_classification=str(input_payload.get("input_classification", "personal")),
            theme_id=theme_id,
        )
        context = build_context(
            portfolio_session_id=session_id,
            agent_key=_AGENT_KEY,
            current_state=state_snapshot,
            agent_input={
                "operation": "generate_page",
                "routing_policy_snapshot": input_payload.get("routing_policy_snapshot", {}),
            },
            request_id=str(payload.get("request_id", "")),
            attempt=attempt,
            run_id=run_id,
        )
        outcome = await build_page(
            page_content=page_content,
            agent=agent,
            context=context,
            theme=theme,
            max_body_bytes=settings.code_generator.max_body_bytes,
            trace=trace,
            reference=reference,
            on_stage=on_stage,
            verifier=_build_verifier(),
        )
    except _BuildStopped:
        return {"status": "cancelled", "job_id": str(job_id or "")}
    except CodeGeneratorFailure as exc:
        return await _fail(payload, exc.envelope, trace)
    except ProviderError as exc:
        envelope = failure_from_provider_error(exc, stage="generate", reference=reference)
        return await _fail(payload, envelope, trace)
    except Exception as exc:
        logger.warning("code_generator build failed with %s", type(exc).__name__)
        return await _fail(
            payload, failure_unexpected(exc, stage="generate", reference=reference), trace
        )

    # ── 3. promote: one transaction swaps the live page ──
    try:
        return await _promote(sessionmaker, payload, outcome, trace, input_payload)
    except Exception as exc:
        logger.warning("code_generator promote failed with %s", type(exc).__name__)
        return await _fail(
            payload, failure_unexpected(exc, stage="promote", reference=reference), trace
        )


async def _promote(
    sessionmaker: Any,
    payload: dict[str, Any],
    outcome: BuildOutcome,
    trace: dict[str, Any],
    input_payload: dict[str, Any],
) -> dict[str, Any]:
    session_id = UUID(str(payload["portfolio_session_id"]))
    run_id = UUID(str(payload["agent_run_id"]))
    version_id = UUID(str(payload["version_id"]))
    raw_job_id = payload.get("job_id")
    job_id = UUID(str(raw_job_id)) if raw_job_id else None
    async with sessionmaker() as db:
        repo = SiteVersionRepository(db)
        session = await repo.lock_session(session_id)
        if session is None:
            return {"status": "cancelled", "job_id": str(job_id or "")}
        if not await _job_is_ours(db, payload):
            return {"status": "cancelled", "job_id": str(job_id or "")}
        await WorkerAuthorizationFence(db).validate_payload(payload)
        state = await repo.get_state(session_id)
        if not in_flight_matches(state, run_id, job_id):
            return {"status": "cancelled", "job_id": str(job_id or "")}
        version = await repo.get_version(version_id, session_id=session_id)
        if version is None or version.status in _TERMINAL_VERSION_STATUSES:
            return {"status": "cancelled", "job_id": str(job_id or "")}

        number = await repo.next_version_number(session_id)
        bundle = outcome.bundle
        await repo.mark_version_ready(
            version,
            version_number=number,
            lang=bundle.lang,
            index_html=bundle.index_html,
            index_sha256=bundle.index_sha256,
            theme_sha256=bundle.css_sha256,
            manifest=bundle.manifest,
            receipt=outcome.receipt,
            trace=trace,
        )
        next_state = apply_build_succeeded(state, version_id=str(version_id), version_number=number)
        saved = await repo.save_state(session_id, next_state, session.revision)
        if saved is None:
            raise ValueError("Code Generator state changed while the job was running")
        call = trace["calls"][-1] if trace.get("calls") else {}
        await repo.mark_run_succeeded(
            run_id,
            {
                "version_id": str(version_id),
                "version_number": number,
                "lang": bundle.lang,
                "index_sha256": bundle.index_sha256,
                "index_bytes": outcome.receipt.get("index_bytes", 0),
            },
            {"code_generator": next_state.model_dump(mode="json")},
            prompt_version=str(call.get("prompt_version", "")) or None,
            model_metadata=durable_model_metadata(
                {
                    "operation": call.get("operation", "generate_page"),
                    "model": call.get("model", ""),
                    "response_id": call.get("response_id", ""),
                    "usage": call.get("usage", {}),
                    "latency_ms": call.get("latency_ms", 0.0),
                    "finish_reason": call.get("finish_reason", ""),
                    "prompt_modules": call.get("prompt_modules", {}),
                    "telemetry": call.get("telemetry", {}),
                    "result_status": "succeeded",
                },
                profile_id=str(call.get("provider", "")),
                attempt=int(payload.get("attempt", 1)),
            ),
        )
        await repo.append_chat(
            session_id,
            role="assistant",
            kind="build",
            body=messages.build_ready(number),
            version_id=version_id,
        )
        await db.commit()
    return {"status": "succeeded", "run_id": str(run_id), "version_id": str(version_id)}


async def _fail(
    payload: dict[str, Any], envelope: FailureEnvelope, trace: dict[str, Any]
) -> dict[str, Any]:
    await _persist_failure_from_payload(payload, envelope, trace)
    return {
        "status": "failed",
        "run_id": str(payload.get("agent_run_id", "")),
        "error": {
            "code": envelope.code,
            "message": envelope.summary,
            "retryable": False,
        },
    }


async def _persist_failure_from_payload(
    payload: dict[str, Any], envelope: FailureEnvelope, trace: dict[str, Any]
) -> None:
    """Record a failed build exactly once: version row, run row, session state and chat."""
    from oryxenai.core.settings import get_settings

    sessionmaker = get_sessionmaker(get_settings())
    session_id = UUID(str(payload["portfolio_session_id"]))
    run_id = UUID(str(payload["agent_run_id"]))
    version_id = UUID(str(payload["version_id"]))
    raw_job_id = payload.get("job_id")
    job_id = UUID(str(raw_job_id)) if raw_job_id else None
    async with sessionmaker() as db:
        repo = SiteVersionRepository(db)
        session = await repo.lock_session(session_id)
        if session is None:
            return
        state = await repo.get_state(session_id)
        # Stop, the reconciler or an earlier report already settled this build.
        if not in_flight_matches(state, run_id, job_id):
            return
        failed = apply_build_failed(state, envelope)
        saved = await repo.save_state(session_id, failed, session.revision)
        if saved is None:
            return
        await repo.mark_version_failed(
            version_id,
            error=envelope.to_payload(),
            trace=trace or None,
            receipt={"validation": {"ok": False}, "browser": {"status": "not_run"}},
        )
        await repo.mark_run_failed(
            run_id,
            {"code": envelope.code, "message": envelope.summary, "retryable": envelope.retryable},
        )
        await repo.append_chat(
            session_id,
            role="system",
            kind="build",
            body=messages.build_failed(envelope, kept_previous=bool(state.active_version_id)),
            version_id=version_id,
        )
        await db.commit()


async def _job_is_ours(db: Any, payload: dict[str, Any]) -> bool:
    """False once the job was cancelled, or its lease moved to another worker."""
    raw = payload.get("job_id")
    if not raw:
        return True
    job = await JobRepository(db).get_by_id(UUID(str(raw)))
    if job is None or job.status == JobStatus.CANCELLED.value:
        return False
    lease = payload.get("lease_token")
    if lease:
        return bool(job.status == JobStatus.RUNNING.value and job.lease_token == lease)
    return True
