"""Durable Code Generator flow: start -> worker handler -> live page, and every way it can fail."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import func, select, update

from oryxenai.agents.code_generator.agent import CodeGeneratorAgent
from oryxenai.agents.code_generator.dev.mock_client import ReferenceModelClient
from oryxenai.agents.code_generator.grants import PreviewGrantSigner
from oryxenai.agents.code_generator.service import (
    CodeGeneratorOperationError,
    CodeGeneratorService,
)
from oryxenai.agents.code_generator.serving import DbBundleProvider
from oryxenai.agents.content_architect.schemas import (
    ContentArchitectApproval,
    ContentArchitectState,
    ContentArchitectStatus,
    PortfolioPageContent,
)
from oryxenai.agents.shared.providers.errors import ProviderTimeoutError
from oryxenai.core.settings import get_settings
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.models.site_version import PortfolioChatMessage, PortfolioSiteVersion
from oryxenai.db.repositories.content_architect import ContentArchitectRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.db.repositories.site_versions import SiteVersionRepository
from oryxenai.db.session import get_sessionmaker
from oryxenai.jobs.handlers.code_generator import CodeGeneratorBuildHandler
from oryxenai.jobs.repository import JobRepository
from oryxenai.jobs.service import JobService
from tests.unit.agents.code_generator.helpers import sample_content

pytestmark = pytest.mark.integration

_SIGNER = PreviewGrantSigner("0123456789abcdef0123456789abcdef")


def _use_client(
    monkeypatch: pytest.MonkeyPatch, client: ReferenceModelClient
) -> ReferenceModelClient:
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.code_generator._build_code_generator_agent",
        lambda **kwargs: CodeGeneratorAgent(
            client, theme_id=kwargs.get("theme_id", "editorial-forest/v1")
        ),
    )
    return client


def _service(db: Any) -> CodeGeneratorService:
    return CodeGeneratorService(SiteVersionRepository(db), JobService(db), _SIGNER)


async def _new_session(
    db: Any, *, approved: bool = True, content: dict[str, Any] | None = None
) -> UUID:
    session = await PortfolioSessionRepository(db).create("Code generator test")
    session_id = session.id
    if approved:
        await _approve_content(db, session_id, content)
    await db.commit()
    return session_id


async def _approve_content(
    db: Any, session_id: UUID, content: dict[str, Any] | None = None
) -> None:
    state = ContentArchitectState(
        status=ContentArchitectStatus.APPROVED,
        page_content=PortfolioPageContent.model_validate(
            content or sample_content("01_strong_profile")
        ),
        approved=ContentArchitectApproval(
            approved_at="2026-10-02T00:00:00+00:00", content_hash="hash-1"
        ),
    )
    repo = ContentArchitectRepository(db)
    session = await repo.get_session(session_id)
    assert session is not None
    await repo.save_content_architect_state(session_id, state, session.revision)


async def _job_payload(db: Any, state: dict[str, Any], *, claim: bool = True) -> dict[str, Any]:
    """The payload a worker hands the handler (claimed through the real queue)."""
    job_id = UUID(state["code_generator"]["in_flight"]["job_id"])
    if not claim:
        job = await JobService(db).get(job_id)
        assert job is not None
        return {**job.payload, "job_id": str(job_id), "attempt": 1, "max_attempts": 1}
    claimed = await JobRepository(db).claim_batch(
        "test-worker", 60.0, 5, allowed_job_kinds=["code_generator.build"]
    )
    await db.commit()
    job = next(item for item in claimed if item.id == job_id)
    return {
        **job.payload,
        "attempt": job.attempt,
        "max_attempts": job.max_attempts,
        "job_id": str(job.id),
        "job_kind": job.job_kind,
        "worker_instance": "test-worker",
        "lease_token": job.lease_token,
    }


async def _start_and_run(db: Any, session_id: UUID) -> tuple[dict[str, Any], dict[str, Any]]:
    service = _service(db)
    started = await service.start(session_id)
    await db.commit()
    payload = await _job_payload(db, started)
    result = await CodeGeneratorBuildHandler().execute(payload, "test-worker")
    db.expire_all()
    return started, result


@pytest.mark.asyncio
async def test_start_requires_approved_content(db_session) -> None:
    session_id = await _new_session(db_session, approved=False)
    with pytest.raises(CodeGeneratorOperationError) as caught:
        await _service(db_session).start(session_id)
    assert caught.value.code == "CODE_GENERATOR_CONTENT_NOT_APPROVED"
    assert caught.value.status_code == 409


@pytest.mark.asyncio
async def test_unbuildable_content_is_refused_before_any_job_or_model_call(db_session) -> None:
    content = sample_content("01_strong_profile")
    content["hero"]["intro"] = "x" * 5000
    session_id = await _new_session(db_session, content=content)
    with pytest.raises(CodeGeneratorOperationError) as caught:
        await _service(db_session).start(session_id)
    assert caught.value.code == "CODE_GENERATOR_CONTENT_NOT_BUILDABLE"
    assert caught.value.status_code == 422
    failure = caught.value.details["failure"]
    assert failure["code"] == "CONTENT_NOT_BUILDABLE" and failure["owner"] == "content"
    assert failure["where"][0]["ref"] == "hero.intro"
    jobs = await db_session.scalar(select(func.count()).select_from(BackgroundJob))
    runs = await db_session.scalar(select(func.count()).select_from(AgentRun))
    assert (jobs, runs) == (0, 0)


@pytest.mark.asyncio
async def test_state_before_any_start_is_not_started_and_never_an_error(db_session) -> None:
    session_id = await _new_session(db_session)
    state = await _service(db_session).get_state(session_id)
    assert state["code_generator"]["status"] == "not_started"
    assert state["versions"] == [] and state["chat"] == [] and state["jobs"] == []


@pytest.mark.asyncio
async def test_happy_path_builds_promotes_and_serves_the_page(db_session, monkeypatch) -> None:
    client = _use_client(monkeypatch, ReferenceModelClient())
    session_id = await _new_session(db_session)
    service = _service(db_session)

    started = await service.start(session_id)
    await db_session.commit()
    flight = started["code_generator"]["in_flight"]
    assert started["code_generator"]["status"] == "build_running"
    assert flight["stage"] == "queued" and flight["origin"] == "initial"
    job = await JobService(db_session).get(UUID(flight["job_id"]))
    assert job is not None
    assert (job.job_kind, job.max_attempts, job.status) == ("code_generator.build", 1, "queued")
    assert job.execution_lane  # shares the model-generation lane

    payload = await _job_payload(db_session, started)
    result = await CodeGeneratorBuildHandler().execute(payload, "test-worker")
    assert result["status"] == "succeeded"
    db_session.expire_all()

    state = await service.get_state(session_id)
    generator = state["code_generator"]
    assert generator["status"] == "ready"
    assert generator["in_flight"] is None and generator["last_error"] is None
    assert generator["active_version_number"] == 1
    assert generator["source_ref"]["content_hash"] == "hash-1"
    [version] = state["versions"]
    assert (version["status"], version["version_number"], version["origin"]) == (
        "ready",
        1,
        "initial",
    )
    assert version["id"] == generator["active_version_id"] == flight["version_id"]
    assert version["summary"]["model"] == "reference-renderer"
    assert version["summary"]["browser"] == "not_run"
    assert [(row["role"], row["kind"]) for row in state["chat"]] == [
        ("assistant", "build"),
        ("assistant", "build"),
    ]
    assert "version 1" in state["chat"][-1]["body"]

    detail = await service.get_version(session_id, UUID(version["id"]), include_html=True)
    assert detail["index_html"].startswith("<!doctype html>")
    assert detail["receipt"]["validation"]["ok"] is True
    assert detail["receipt"]["index_sha256"] == detail["index_sha256"]
    assert detail["trace"]["calls"][0]["operation"] == "generate_page"
    assert len(client.requests) == 1

    # The live page is reachable through a grant and the production provider.
    grant = await service.mint_preview(session_id)
    assert grant["url"].startswith("/preview/g/") and grant["url"].endswith("/index.html")
    token = grant["url"].split("/")[3]
    parsed = _SIGNER.verify(token)
    bundle = await DbBundleProvider(get_sessionmaker(get_settings())).load(
        parsed.session_id, parsed.version_id
    )
    assert bundle is not None and bundle.index_html == detail["index_html"]

    run = await db_session.get(AgentRun, UUID(started["code_generator"]["in_flight"]["run_id"]))
    assert run is not None and run.status == "succeeded"
    assert "page_content" not in (run.output_payload or {})


@pytest.mark.asyncio
async def test_starting_twice_returns_the_same_build(db_session, monkeypatch) -> None:
    _use_client(monkeypatch, ReferenceModelClient())
    session_id = await _new_session(db_session)
    service = _service(db_session)
    first = await service.start(session_id)
    await db_session.commit()
    second = await service.start(session_id)
    await db_session.commit()
    assert (
        first["code_generator"]["in_flight"]["job_id"]
        == second["code_generator"]["in_flight"]["job_id"]
    )
    assert await db_session.scalar(select(func.count()).select_from(BackgroundJob)) == 1
    assert await db_session.scalar(select(func.count()).select_from(AgentRun)) == 1
    assert await db_session.scalar(select(func.count()).select_from(PortfolioChatMessage)) == 1


@pytest.mark.asyncio
async def test_a_ready_site_is_not_rebuilt_by_another_start(db_session, monkeypatch) -> None:
    _use_client(monkeypatch, ReferenceModelClient())
    session_id = await _new_session(db_session)
    await _start_and_run(db_session, session_id)
    again = await _service(db_session).start(session_id)
    await db_session.commit()
    assert again["code_generator"]["status"] == "ready"
    assert await db_session.scalar(select(func.count()).select_from(BackgroundJob)) == 1


@pytest.mark.asyncio
async def test_invalid_page_fails_with_exact_diagnostics_and_keeps_the_rejected_body(
    db_session, monkeypatch
) -> None:
    name = sample_content("01_strong_profile")["hero"]["name"]
    _use_client(
        monkeypatch, ReferenceModelClient(mutate=lambda body: body.replace(name, name + " Jr.", 1))
    )
    session_id = await _new_session(db_session)
    started, result = await _start_and_run(db_session, session_id)

    assert result["status"] == "failed" and result["error"]["code"] == "PAGE_COPY_MISMATCH"
    state = await _service(db_session).get_state(session_id)
    generator = state["code_generator"]
    assert generator["status"] == "needs_attention" and generator["in_flight"] is None
    error = generator["last_error"]
    assert (error["code"], error["stage"], error["owner"]) == (
        "PAGE_COPY_MISMATCH",
        "validate",
        "model_output",
    )
    assert error["where"][0]["ref"].startswith("hero") and error["reference"].startswith("cg-")
    assert error["issues"] and error["expected"] and error["found"]

    [version] = state["versions"]
    assert version["status"] == "failed" and version["version_number"] is None
    assert version["error"]["code"] == "PAGE_COPY_MISMATCH"
    detail = await _service(db_session).get_version(
        session_id, UUID(version["id"]), include_html=True
    )
    assert name + " Jr." in detail["trace"]["rejected_body_html"]
    assert detail["index_html"] is None
    assert (
        "rejected_body_html"
        not in (await _service(db_session).get_version(session_id, UUID(version["id"])))["trace"]
    )
    assert "couldn't finish" in state["chat"][-1]["body"]

    with pytest.raises(CodeGeneratorOperationError) as caught:
        await _service(db_session).mint_preview(session_id)
    assert caught.value.code == "CODE_GENERATOR_NO_PREVIEW"
    run = await db_session.get(AgentRun, UUID(started["code_generator"]["in_flight"]["run_id"]))
    assert run is not None and run.status == "failed"


@pytest.mark.asyncio
async def test_a_provider_timeout_is_reported_exactly_without_any_automatic_retry(
    db_session, monkeypatch
) -> None:
    client = _use_client(monkeypatch, ReferenceModelClient(error=ProviderTimeoutError("slow")))
    session_id = await _new_session(db_session)
    _started, result = await _start_and_run(db_session, session_id)
    assert result["status"] == "failed"
    state = await _service(db_session).get_state(session_id)
    error = state["code_generator"]["last_error"]
    assert (error["code"], error["stage"]) == ("PROVIDER_TIMEOUT_ERROR", "generate")
    assert len(client.requests) == 1
    [job] = (await db_session.execute(select(BackgroundJob))).scalars().all()
    assert job.max_attempts == 1  # one shot: a failure is never retried by the queue


@pytest.mark.asyncio
async def test_retry_after_a_failure_is_a_fresh_user_started_build(db_session, monkeypatch) -> None:
    client = _use_client(monkeypatch, ReferenceModelClient(error=ProviderTimeoutError("slow")))
    session_id = await _new_session(db_session)
    await _start_and_run(db_session, session_id)

    client.error = None  # the model recovers; the user presses "Try again"
    started, result = await _start_and_run(db_session, session_id)
    assert result["status"] == "succeeded"
    assert started["code_generator"]["in_flight"]["origin"] == "retry"
    state = await _service(db_session).get_state(session_id)
    assert state["code_generator"]["status"] == "ready"
    assert state["code_generator"]["builds_started"] == 2
    assert state["code_generator"]["last_error"] is None
    statuses = {item["status"]: item for item in state["versions"]}
    assert set(statuses) == {"failed", "ready"}
    # Only a verified page gets a user-facing number, so the failure leaves no gap.
    assert statuses["ready"]["version_number"] == 1 and statuses["failed"]["version_number"] is None


@pytest.mark.asyncio
async def test_stop_cancels_the_job_and_the_late_worker_changes_nothing(
    db_session, monkeypatch
) -> None:
    client = _use_client(monkeypatch, ReferenceModelClient())
    session_id = await _new_session(db_session)
    service = _service(db_session)
    started = await service.start(session_id)
    await db_session.commit()
    payload = await _job_payload(db_session, started, claim=False)

    stopped = await service.stop(session_id)
    await db_session.commit()
    assert stopped["code_generator"]["status"] == "needs_attention"
    assert stopped["code_generator"]["last_error"]["code"] == "JOB_CANCELLED"
    job = await JobService(db_session).get(UUID(payload["job_id"]))
    assert job is not None and job.status == "cancelled"

    result = await CodeGeneratorBuildHandler().execute(payload, "test-worker")
    assert result["status"] == "cancelled"
    db_session.expire_all()
    assert client.requests == []  # no model call after the stop
    assert await db_session.scalar(select(func.count()).select_from(PortfolioSiteVersion)) == 0
    state = await service.get_state(session_id)
    assert state["code_generator"]["active_version_id"] == ""
    assert "stopped" in state["chat"][-1]["body"]


@pytest.mark.asyncio
async def test_a_stop_during_the_build_prevents_promotion(db_session, monkeypatch) -> None:
    """The model call returns after the user pressed Stop: the page must not go live."""
    session_id = await _new_session(db_session)
    started = await _service(db_session).start(session_id)
    await db_session.commit()
    payload = await _job_payload(db_session, started)

    class _StoppingClient(ReferenceModelClient):
        async def generate_structured(self, **kwargs: Any) -> Any:
            async with get_sessionmaker(get_settings())() as other:
                await _service(other).stop(session_id)
                await other.commit()
            return await super().generate_structured(**kwargs)

    _use_client(monkeypatch, _StoppingClient())
    result = await CodeGeneratorBuildHandler().execute(payload, "test-worker")
    assert result["status"] == "cancelled"
    db_session.expire_all()
    state = await _service(db_session).get_state(session_id)
    assert state["code_generator"]["status"] == "needs_attention"
    assert state["code_generator"]["active_version_id"] == ""
    assert all(item["status"] != "ready" for item in state["versions"])


@pytest.mark.asyncio
async def test_a_lost_job_is_reconciled_into_an_exact_worker_lost_failure(db_session) -> None:
    session_id = await _new_session(db_session)
    service = _service(db_session)
    started = await service.start(session_id)
    await db_session.commit()
    job_id = UUID(started["code_generator"]["in_flight"]["job_id"])
    # The worker died and stale recovery gave up on the single-attempt job.
    await db_session.execute(
        update(BackgroundJob).where(BackgroundJob.id == job_id).values(status="failed")
    )
    await db_session.commit()

    state = await service.get_state(session_id)
    await db_session.commit()
    generator = state["code_generator"]
    assert generator["status"] == "needs_attention" and generator["in_flight"] is None
    assert generator["last_error"]["code"] == "WORKER_LOST"
    assert generator["last_error"]["retryable"] is True
    assert "interrupted" in state["chat"][-1]["body"]
    # Reading again changes nothing; the user can simply start again.
    again = await service.get_state(session_id)
    assert again["code_generator"]["last_error"]["code"] == "WORKER_LOST"
    assert len(again["chat"]) == len(state["chat"])


@pytest.mark.asyncio
async def test_a_queued_build_is_not_mistaken_for_a_lost_one(db_session) -> None:
    session_id = await _new_session(db_session)
    service = _service(db_session)
    await service.start(session_id)
    await db_session.commit()
    state = await service.get_state(session_id)
    assert state["code_generator"]["status"] == "build_running"
    assert state["code_generator"]["in_flight"]["stage"] == "queued"
    assert state["jobs"][0]["status"] == "queued"


@pytest.mark.asyncio
async def test_timeout_hook_records_job_timeout_once_and_is_idempotent(
    db_session, monkeypatch
) -> None:
    _use_client(monkeypatch, ReferenceModelClient())
    session_id = await _new_session(db_session)
    service = _service(db_session)
    started = await service.start(session_id)
    await db_session.commit()
    payload = await _job_payload(db_session, started)

    handler = CodeGeneratorBuildHandler()
    await handler.on_timeout(payload, {"code": "JOB_TIMEOUT", "message": "x"})
    db_session.expire_all()
    state = await service.get_state(session_id)
    assert state["code_generator"]["status"] == "needs_attention"
    assert state["code_generator"]["last_error"]["code"] == "JOB_TIMEOUT"
    chat_count = len(state["chat"])

    await handler.on_terminal_failure(payload, {"code": "JOB_TIMEOUT", "message": "x"})
    db_session.expire_all()
    again = await service.get_state(session_id)
    assert again["code_generator"]["last_error"]["code"] == "JOB_TIMEOUT"
    assert len(again["chat"]) == chat_count


@pytest.mark.asyncio
async def test_a_failed_attempt_never_replaces_the_live_page(db_session, monkeypatch) -> None:
    client = _use_client(monkeypatch, ReferenceModelClient())
    session_id = await _new_session(db_session)
    await _start_and_run(db_session, session_id)
    state = await _service(db_session).get_state(session_id)
    live = state["code_generator"]["active_version_id"]

    # Simulate a later (chat-driven) build that fails: the control plane keeps the live page.
    client.error = ProviderTimeoutError("slow")
    repo = SiteVersionRepository(db_session)
    session = await repo.lock_session(session_id)
    assert session is not None
    from oryxenai.agents.code_generator.diagnostics import failure_unexpected
    from oryxenai.agents.code_generator.state import (
        InFlightBuild,
        apply_build_failed,
        apply_build_started,
    )

    current = await repo.get_state(session_id)
    running = apply_build_started(
        current,
        in_flight=InFlightBuild(run_id="r", job_id="j", version_id="v", origin="change"),
        source_ref=current.source_ref,
        theme_id=current.theme_id,
    )
    failed = apply_build_failed(running, failure_unexpected(RuntimeError("x"), stage="generate"))
    assert failed.status.value == "ready" and failed.active_version_id == live
    assert failed.last_error is not None and failed.in_flight is None


@pytest.mark.asyncio
async def test_deleting_a_session_removes_its_versions_and_chat(db_session, monkeypatch) -> None:
    _use_client(monkeypatch, ReferenceModelClient())
    session_id = await _new_session(db_session)
    await _start_and_run(db_session, session_id)
    assert await db_session.scalar(select(func.count()).select_from(PortfolioSiteVersion)) == 1
    from sqlalchemy import delete

    # Same order as the real deletion path: jobs and runs first, then the session.
    await db_session.execute(delete(BackgroundJob))
    await db_session.execute(delete(AgentRun))
    await db_session.execute(delete(PortfolioSession).where(PortfolioSession.id == session_id))
    await db_session.commit()
    assert await db_session.scalar(select(func.count()).select_from(PortfolioSiteVersion)) == 0
    assert await db_session.scalar(select(func.count()).select_from(PortfolioChatMessage)) == 0


@pytest.mark.asyncio
async def test_admin_pipeline_reset_clears_generated_pages(db_session, monkeypatch) -> None:
    from oryxenai.runtime.pipeline_reset import PipelineResetService

    _use_client(monkeypatch, ReferenceModelClient())
    session_id = await _new_session(db_session)
    await _start_and_run(db_session, session_id)
    service = PipelineResetService(
        db_session, settings=get_settings(), auth_admin_provider=None, archive_storage=None
    )
    from uuid import uuid4

    async def _noop(self: Any, _session_id: UUID) -> None:
        return None

    monkeypatch.setattr("oryxenai.auth.admin.service.AdminService._cleanup_external", _noop)
    await service.reset_admin_pipeline(session_id, uuid4())
    await db_session.commit()
    assert await db_session.scalar(select(func.count()).select_from(PortfolioSiteVersion)) == 0
    assert await db_session.scalar(select(func.count()).select_from(PortfolioChatMessage)) == 0
    session = await db_session.get(PortfolioSession, session_id)
    assert session is not None and session.current_state == {}


@pytest.mark.asyncio
async def test_versions_and_numbers_are_scoped_to_their_session(db_session, monkeypatch) -> None:
    _use_client(monkeypatch, ReferenceModelClient())
    first = await _new_session(db_session)
    second = await _new_session(db_session)
    await _start_and_run(db_session, first)
    await _start_and_run(db_session, second)
    one = await _service(db_session).get_state(first)
    two = await _service(db_session).get_state(second)
    assert one["versions"][0]["version_number"] == two["versions"][0]["version_number"] == 1
    assert one["versions"][0]["id"] != two["versions"][0]["id"]
    with pytest.raises(CodeGeneratorOperationError) as caught:
        await _service(db_session).get_version(first, UUID(two["versions"][0]["id"]))
    assert caught.value.status_code == 404
    with pytest.raises(CodeGeneratorOperationError):
        await _service(db_session).mint_preview(first, UUID(two["versions"][0]["id"]))


@pytest.mark.asyncio
async def test_content_snapshot_is_frozen_with_the_version(db_session, monkeypatch) -> None:
    _use_client(monkeypatch, ReferenceModelClient())
    session_id = await _new_session(db_session)
    await _start_and_run(db_session, session_id)
    [row] = (await db_session.execute(select(PortfolioSiteVersion))).scalars().all()
    expected = PortfolioPageContent.model_validate(sample_content("01_strong_profile")).model_dump(
        mode="json"
    )
    assert row.content_snapshot == expected
    assert len(row.content_sha256) == 64
    assert (row.theme_id, len(row.theme_sha256)) == ("editorial-forest/v1", 64)


@pytest.mark.asyncio
async def test_browser_verification_is_recorded_in_the_receipt(db_session, monkeypatch) -> None:
    from oryxenai.agents.code_generator.verify_browser import BrowserVerifier
    from oryxenai.core.settings import CodeGeneratorVerificationConfig

    _use_client(monkeypatch, ReferenceModelClient())
    for options in ({}, {"browser_channel": "chrome"}):
        config = CodeGeneratorVerificationConfig(
            browser="best_effort", viewports=[390, 1280], page_timeout_seconds=25.0, **options
        )
        monkeypatch.setattr(
            "oryxenai.jobs.handlers.code_generator._build_verifier",
            lambda cfg=config: BrowserVerifier(cfg),
        )
        session_id = await _new_session(db_session)
        _started, result = await _start_and_run(db_session, session_id)
        assert result["status"] == "succeeded"
        state = await _service(db_session).get_state(session_id)
        status = state["versions"][0]["summary"]["browser"]
        if status != "unavailable":
            break
    else:
        pytest.skip("no headless browser can be started on this machine")
    assert status == "passed"
    detail = await _service(db_session).get_version(
        session_id, UUID(state["versions"][0]["id"]), include_html=True
    )
    assert detail["receipt"]["browser"]["status"] == "passed"
    assert detail["receipt"]["browser"]["viewports"] == [390, 1280]
    assert detail["trace"]["verification"]["status"] == "passed"
    assert "verify" in detail["trace"]["timings_ms"]


@pytest.mark.asyncio
async def test_a_browser_finding_blocks_publication_with_the_exact_location(
    db_session, monkeypatch
) -> None:
    from oryxenai.agents.code_generator.pipeline import VerificationResult
    from oryxenai.themes.issues import Issue

    class _Failing:
        async def verify(self, bundle, theme):
            issue = Issue(
                "REQUEST_FAILED",
                "error",
                "A page resource did not load (HTTP 404).",
                found="/assets/gone.png: HTTP 404",
                origin="request:/assets/gone.png",
            )
            return VerificationResult("failed", [issue], {"viewports": [390]})

    _use_client(monkeypatch, ReferenceModelClient())
    monkeypatch.setattr("oryxenai.jobs.handlers.code_generator._build_verifier", lambda: _Failing())
    session_id = await _new_session(db_session)
    _started, result = await _start_and_run(db_session, session_id)
    assert result["status"] == "failed" and result["error"]["code"] == "PAGE_BROWSER_CHECK_FAILED"
    state = await _service(db_session).get_state(session_id)
    error = state["code_generator"]["last_error"]
    assert (error["stage"], error["owner"]) == ("verify", "browser")
    assert error["where"][0] == {
        "kind": "request",
        "ref": "/assets/gone.png",
        "detail": "A page resource did not load (HTTP 404).",
    }
    assert state["code_generator"]["status"] == "needs_attention"
    assert state["code_generator"]["active_version_id"] == ""


@pytest.mark.asyncio
async def test_a_session_with_state_from_the_retired_generator_can_still_build(
    db_session, monkeypatch
) -> None:
    """Existing sessions carry the old generator's state (status 'queued' and its own fields)."""
    from tests.unit.agents.code_generator.test_admission_bundle_diagnostics import LEGACY_STATE

    _use_client(monkeypatch, ReferenceModelClient())
    session_id = await _new_session(db_session)
    session = await db_session.get(PortfolioSession, session_id)
    assert session is not None
    session.current_state = {**session.current_state, "code_generator": dict(LEGACY_STATE)}
    await db_session.commit()

    service = _service(db_session)
    before = await service.get_state(session_id)  # must not raise
    assert before["code_generator"]["status"] == "not_started"
    _started, result = await _start_and_run(db_session, session_id)
    assert result["status"] == "succeeded"
    after = await service.get_state(session_id)
    assert after["code_generator"]["status"] == "ready"
    assert "trace_id" not in after["code_generator"]  # the old fields were replaced, not merged
