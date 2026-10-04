"""Code Generator background job handler.

Registered job kind:
  - code_generator.build

One handler runs a whole build. A first build is generate -> validate -> seal ->
promote. A chat change first asks the interpreter what the message means: a reply
(question, refusal, clarification, no-op) ends there with no new version; a valid
content edit continues through the same generate -> validate -> seal -> promote line
on the edited content. The handler never retries and never repairs: any failure is
persisted as one exact what / where / why envelope on the version row and the
session state, and the handler returns a ``failed`` result so the job row ends
terminal. The page the user already has is only ever replaced inside the single
promote transaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from oryxenai.agents.code_generator import messages
from oryxenai.agents.code_generator.changes import (
    content_sha256,
    decide_change,
    leaf_strings,
)
from oryxenai.agents.code_generator.diagnostics import (
    failure_from_provider_error,
    failure_unexpected,
    reference_for,
)
from oryxenai.agents.code_generator.pipeline import BuildOutcome, build_page
from oryxenai.agents.code_generator.schemas import (
    ChangePlanEnvelope,
    CodeGeneratorFailure,
    FailureEnvelope,
    FailureStage,
)
from oryxenai.agents.code_generator.state import (
    apply_build_failed,
    apply_build_succeeded,
    apply_reply_only,
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


@dataclass(slots=True)
class _ChangeContext:
    """What a chat-driven build needs at promote time."""

    is_change: bool = False
    reply: str = ""
    removed: frozenset[str] = field(default_factory=frozenset)


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
    from oryxenai.agents.code_generator.verify_browser import build_verifier
    from oryxenai.core.settings import get_settings

    return build_verifier(get_settings().code_generator.verification)


def _cancelled(job_id: UUID | None) -> dict[str, Any]:
    return {"status": "cancelled", "job_id": str(job_id or "")}


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

    # ── 1. claim: confirm this job still owns the in-flight build ──
    async with sessionmaker() as db:
        if not await _job_is_ours(db, payload):
            return _cancelled(job_id)
        await WorkerAuthorizationFence(db).validate_payload(payload)
        repo = SiteVersionRepository(db)
        run = await repo.get_run(run_id)
        session = await repo.lock_session(session_id)
        if run is None or session is None:
            raise ValueError("Code Generator run or session was not found")
        state = await repo.get_state(session_id)
        if not in_flight_matches(state, run_id, job_id):
            return _cancelled(job_id)
        await repo.mark_run_started(run_id)
        input_payload: dict[str, Any] = dict(run.input_payload)
        page_content: dict[str, Any] = dict(input_payload.get("page_content") or {})
        operation = str(input_payload.get("operation", "build"))
        existing = await repo.get_version(version_id, session_id=session_id, light=True)
        if existing is not None and existing.status in _TERMINAL_VERSION_STATUSES:
            return _cancelled(job_id)
        if operation == "build":
            # A chat change creates its version only once the interpreter decided to build.
            if existing is None:
                await repo.create_version(
                    version_id=version_id,
                    session_id=session_id,
                    origin=str(input_payload.get("origin", "initial")),
                    status="generating",
                    instruction="",
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
    trace["operation"] = operation

    async def on_stage(stage: str) -> None:
        async with sessionmaker() as stage_db:
            if not await _job_is_ours(stage_db, payload):
                raise _BuildStopped
            await SiteVersionRepository(stage_db).set_version_status(version_id, stage)
            await stage_db.commit()

    # ── 2. (change only) interpret, then build: generate -> validate -> seal (-> verify) ──
    stage_name: FailureStage = "generate"
    change = _ChangeContext()
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
        content_to_build = page_content
        if operation == "change":
            stage_name = "interpret"
            interpreted = await agent.interpret_change(
                page_content,
                str(input_payload.get("instruction", "")),
                list(input_payload.get("history") or []),
                context,
            )
            trace.setdefault("calls", []).append(interpreted.call.to_dict())
            trace["plan"] = interpreted.plan.model_dump(mode="json")
            decision = decide_change(
                page_content,
                interpreted.plan,
                theme_id=theme_id,
                allow_illustrative_work=bool(input_payload.get("allow_illustrative_work", False)),
            )
            if decision.kind == "reply":
                return await _finish_reply(sessionmaker, payload, decision.reply, interpreted.plan)
            assert decision.new_content is not None
            content_to_build = decision.new_content
            change = _ChangeContext(True, decision.reply, decision.removed)
            if not await _create_change_version(
                sessionmaker, payload, input_payload, content_to_build, interpreted.plan
            ):
                return _cancelled(job_id)
            stage_name = "generate"
        outcome = await build_page(
            page_content=content_to_build,
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
        return _cancelled(job_id)
    except CodeGeneratorFailure as exc:
        return await _fail(payload, exc.envelope, trace)
    except ProviderError as exc:
        envelope = failure_from_provider_error(exc, stage=stage_name, reference=reference)
        return await _fail(payload, envelope, trace)
    except Exception as exc:
        logger.warning("code_generator build failed with %s", type(exc).__name__)
        return await _fail(
            payload, failure_unexpected(exc, stage=stage_name, reference=reference), trace
        )

    # ── 3. promote: one transaction swaps the live page ──
    try:
        return await _promote(sessionmaker, payload, outcome, trace, change)
    except Exception as exc:
        logger.warning("code_generator promote failed with %s", type(exc).__name__)
        return await _fail(
            payload, failure_unexpected(exc, stage="promote", reference=reference), trace
        )


async def _create_change_version(
    sessionmaker: Any,
    payload: dict[str, Any],
    input_payload: dict[str, Any],
    content: dict[str, Any],
    plan: ChangePlanEnvelope,
) -> bool:
    """Insert the version row for a change that will be built. False if the build was stopped."""
    session_id = UUID(str(payload["portfolio_session_id"]))
    run_id = UUID(str(payload["agent_run_id"]))
    version_id = UUID(str(payload["version_id"]))
    raw_job_id = payload.get("job_id")
    job_id = UUID(str(raw_job_id)) if raw_job_id else None
    base_id = input_payload.get("base_version_id")
    async with sessionmaker() as db:
        repo = SiteVersionRepository(db)
        if await repo.lock_session(session_id) is None:
            return False
        if not await _job_is_ours(db, payload):
            return False
        state = await repo.get_state(session_id)
        if not in_flight_matches(state, run_id, job_id):
            return False
        await repo.create_version(
            version_id=version_id,
            session_id=session_id,
            origin="change",
            status="generating",
            instruction=str(input_payload.get("instruction", "")),
            content_snapshot=content,
            content_sha256=content_sha256(content),
            theme_id=str(input_payload.get("theme_id", DEFAULT_THEME_ID)),
            run_id=run_id,
            job_id=job_id,
            parent_version_id=UUID(str(base_id)) if base_id else None,
            change_plan=plan.model_dump(mode="json"),
        )
        await db.commit()
    return True


async def _finish_reply(
    sessionmaker: Any, payload: dict[str, Any], reply: str, plan: ChangePlanEnvelope
) -> dict[str, Any]:
    """The message needed no new page: post the reply and return to ready."""
    session_id = UUID(str(payload["portfolio_session_id"]))
    run_id = UUID(str(payload["agent_run_id"]))
    raw_job_id = payload.get("job_id")
    job_id = UUID(str(raw_job_id)) if raw_job_id else None
    async with sessionmaker() as db:
        repo = SiteVersionRepository(db)
        session = await repo.lock_session(session_id)
        if session is None or not await _job_is_ours(db, payload):
            return _cancelled(job_id)
        state = await repo.get_state(session_id)
        if not in_flight_matches(state, run_id, job_id):
            return _cancelled(job_id)
        next_state = apply_reply_only(state)
        if await repo.save_state(session_id, next_state, session.revision) is None:
            raise ValueError("Code Generator state changed while the job was running")
        await repo.mark_run_succeeded(
            run_id,
            {"outcome": "reply", "intent": plan.intent.value},
            {"code_generator": next_state.model_dump(mode="json")},
            prompt_version="code_generator.interpret_change.v1",
        )
        await repo.append_chat(session_id, role="assistant", kind="message", body=reply)
        await db.commit()
    return {"status": "succeeded", "run_id": str(run_id), "outcome": "reply"}


async def _promote(
    sessionmaker: Any,
    payload: dict[str, Any],
    outcome: BuildOutcome,
    trace: dict[str, Any],
    change: _ChangeContext,
) -> dict[str, Any]:
    from oryxenai.core.settings import get_settings

    session_id = UUID(str(payload["portfolio_session_id"]))
    run_id = UUID(str(payload["agent_run_id"]))
    version_id = UUID(str(payload["version_id"]))
    raw_job_id = payload.get("job_id")
    job_id = UUID(str(raw_job_id)) if raw_job_id else None
    keep = get_settings().code_generator.max_versions_per_session
    async with sessionmaker() as db:
        repo = SiteVersionRepository(db)
        session = await repo.lock_session(session_id)
        if session is None:
            return _cancelled(job_id)
        if not await _job_is_ours(db, payload):
            return _cancelled(job_id)
        await WorkerAuthorizationFence(db).validate_payload(payload)
        state = await repo.get_state(session_id)
        if not in_flight_matches(state, run_id, job_id):
            return _cancelled(job_id)
        version = await repo.get_version(version_id, session_id=session_id)
        if version is None or version.status in _TERMINAL_VERSION_STATUSES:
            return _cancelled(job_id)

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
        if await repo.save_state(session_id, next_state, session.revision) is None:
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
        if change.is_change:
            await repo.append_chat(
                session_id,
                role="assistant",
                kind="message",
                body=change.reply,
                version_id=version_id,
            )
            if change.removed:
                await _restrict_older_versions(repo, session_id, version_id, change.removed)
        else:
            await repo.append_chat(
                session_id,
                role="assistant",
                kind="build",
                body=messages.build_ready(number),
                version_id=version_id,
            )
        await repo.prune_versions(session_id, keep=keep, active_id=version_id)
        await db.commit()
    return {"status": "succeeded", "run_id": str(run_id), "version_id": str(version_id)}


async def _restrict_older_versions(
    repo: SiteVersionRepository, session_id: UUID, keep_id: UUID, removed: frozenset[str]
) -> None:
    """The person asked to hide information: no older page that shows it stays reachable."""
    doomed = [
        identifier
        for identifier, content in await repo.ready_versions_with_content(
            session_id, exclude=keep_id
        )
        if removed & leaf_strings(content)
    ]
    if doomed:
        await repo.restrict_versions(session_id, doomed)
        await repo.append_chat(
            session_id,
            role="system",
            kind="notice",
            body=messages.versions_restricted(len(doomed)),
        )


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
        origin = state.in_flight.origin if state.in_flight is not None else "initial"
        failed = apply_build_failed(state, envelope)
        if await repo.save_state(session_id, failed, session.revision) is None:
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
            body=messages.build_failed(
                envelope, kept_previous=bool(state.active_version_id), origin=origin
            ),
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
