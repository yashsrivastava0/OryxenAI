from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from oryxenai.agents.build_preparation.schemas import (
    BuildPreparationSourceRef,
    BuildPreparationState,
    BuildPreparationStatus,
)
from oryxenai.agents.code_generator import service as code_generator_service_module
from oryxenai.agents.code_generator.service import (
    CodeGeneratorOperationError,
    CodeGeneratorService,
)
from oryxenai.agents.code_generator.session_schemas import CodeGeneratorSessionState
from oryxenai.core.settings import Settings
from oryxenai.jobs.handlers.code_generator_verification import _session_source_is_current


class _Runs:
    def __init__(self) -> None:
        self.items: dict[UUID, SimpleNamespace] = {}
        self.created: SimpleNamespace | None = None

    async def find_idempotent(self, key: str, *, scope: str = "development"):
        return next(
            (
                run
                for run in self.items.values()
                if run.idempotency_key == key and run.idempotency_scope == scope
            ),
            None,
        )

    async def get(self, run_id: UUID):
        return self.items.get(run_id)

    async def create(self, **values):
        run = SimpleNamespace(id=uuid4(), revision=0, status="created", **values)
        self.items[run.id] = run
        self.created = run
        return run

    async def compare_and_swap(self, run_id: UUID, *, expected_revision: int, values):
        run = self.items[run_id]
        if run.revision != expected_revision:
            return None
        for key, value in values.items():
            setattr(run, key, value)
        run.revision += 1
        return run

    async def append_event(self, *args, **kwargs):
        return None


class _Repository:
    def __init__(self, session_id: UUID, preparation: BuildPreparationState) -> None:
        self.session_id = session_id
        self.session = SimpleNamespace(id=session_id, revision=7, current_state={})
        self.preparation = preparation
        self.state = CodeGeneratorSessionState()
        self.runs = _Runs()

    async def get_session(self, session_id: UUID):
        return self.session if session_id == self.session_id else None

    async def get_state(self, session_id: UUID):
        assert session_id == self.session_id
        return self.state

    async def get_build_preparation_state(self, session_id: UUID):
        assert session_id == self.session_id
        return self.preparation

    async def save_state(self, session_id: UUID, state, expected_revision: int):
        assert session_id == self.session_id
        if expected_revision != self.session.revision:
            return None
        self.state = state
        self.session.revision += 1
        return self.session


class _Jobs:
    def __init__(self) -> None:
        self.job = SimpleNamespace(
            id=uuid4(),
            job_kind="code_generator.plan",
            status="queued",
            attempt=0,
            error_payload=None,
        )
        self.payload = None

    async def enqueue(self, kind: str, payload, **kwargs):
        self.payload = payload
        return self.job

    async def get(self, job_id: UUID):
        return self.job if job_id == self.job.id else None


def _ready_preparation() -> BuildPreparationState:
    return BuildPreparationState(
        status=BuildPreparationStatus.READY,
        run_id="build-preparation-run",
        scope_hash="scope-hash",
        source_ref=BuildPreparationSourceRef(
            content_architect_content_hash="content-hash",
            visual_design_director_direction_hash="visual-hash",
        ),
        content_brief_markdown="# Content brief",
        visual_brief_markdown="# Visual brief",
    )


@pytest.mark.asyncio
async def test_session_start_fails_closed_invalid_markdown_brief_pair() -> None:
    """Invalid Markdown brief pairs are rejected before a durable run exists."""
    session_id = uuid4()
    repository = _Repository(session_id, _ready_preparation())
    service = CodeGeneratorService(repository, _Jobs(), Settings())  # type: ignore[arg-type]

    with pytest.raises(CodeGeneratorOperationError) as exc_info:
        await service.start(session_id, idempotency_key="start-once")

    assert exc_info.value.code == "CODE_GENERATOR_BRIEF_INVALID"
    assert repository.runs.created is None


@pytest.mark.asyncio
async def test_session_start_still_gates_on_build_preparation_readiness() -> None:
    session_id = uuid4()
    repository = _Repository(session_id, BuildPreparationState())
    service = CodeGeneratorService(repository, _Jobs(), Settings())  # type: ignore[arg-type]

    with pytest.raises(CodeGeneratorOperationError) as exc_info:
        await service.start(session_id, idempotency_key="start-once")

    assert exc_info.value.code == "CODE_GENERATOR_BUILD_PREPARATION_NOT_READY"


@pytest.mark.asyncio
async def test_session_start_rejects_ready_briefs_when_approved_upstream_changed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = uuid4()
    repository = _Repository(session_id, _ready_preparation())
    repository.session.current_state = {
        "content_architect": {},
        "visual_design_director": {},
    }

    monkeypatch.setattr(
        code_generator_service_module.ContentArchitectState,
        "model_validate",
        lambda _value: SimpleNamespace(approved={}),
    )
    monkeypatch.setattr(
        code_generator_service_module.VisualDesignDirectorState,
        "model_validate",
        lambda _value: SimpleNamespace(approved={}),
    )

    class _Integrator:
        def __init__(self, _settings):
            pass

        def compose(self, _content, _visual):
            return SimpleNamespace(
                source_ref=SimpleNamespace(
                    visual_design_director_direction_hash="new-visual-hash",
                    input_projection_hash="new-input-hash",
                )
            )

    monkeypatch.setattr(code_generator_service_module, "BuildPreparationInputIntegrator", _Integrator)
    service = CodeGeneratorService(repository, _Jobs(), Settings())  # type: ignore[arg-type]

    with pytest.raises(code_generator_service_module.CodeGeneratorOperationError) as exc_info:
        await service.start(session_id, idempotency_key="stale-briefs")

    assert exc_info.value.code == "CODE_GENERATOR_BUILD_PREPARATION_STALE"
    assert exc_info.value.details["stale_reasons"] == ["approved_upstream_changed"]


@pytest.mark.asyncio
async def test_retry_requeues_the_existing_run_and_preserves_its_variant() -> None:
    session_id = uuid4()
    repository = _Repository(session_id, _ready_preparation())
    run = SimpleNamespace(
        id=uuid4(),
        revision=4,
        status="needs_attention",
        issues=[{"code": "PROVIDER_TIMEOUT_ERROR"}],
        terminal_failure={"code": "PROVIDER_TIMEOUT_ERROR"},
        active_preview={"preview_url": "http://preview/old"},
        coordinator_stage="plan",
        current_attempt=1,
        plan_summary={},
        source_summary={},
        plan=None,
        planner_receipt=None,
        acquire_receipt=None,
        resource_ledger=None,
        dependency_ledger=None,
        source_checkpoint=None,
        generation_projection=None,
        pending_promotion=None,
        creative_direction={"variant_receipt": {"variant_id": "variant-stable"}},
        pipeline_contract_version="code-generator-v4",
        trace_id="trace-stable",
        background_job_id=None,
        acquire_job_id=None,
        generation_job_id=None,
        verification_job_id=None,
    )
    repository.runs.items[run.id] = run
    repository.state = CodeGeneratorSessionState(
        status="needs_attention",
        current_run_id=str(run.id),
        active_preview=run.active_preview,
    )
    jobs = _Jobs()
    service = CodeGeneratorService(repository, jobs, Settings())  # type: ignore[arg-type]

    result = await service.retry(session_id, idempotency_key="same-variant-retry")

    assert run.status == "queued"
    assert repository.state.current_run_id == str(run.id)
    assert result["code_generator"]["design_variant"]["variant_id"] == "variant-stable"
    assert result["code_generator"]["active_preview"] == run.active_preview
    assert jobs.payload == {"code_generator_run_id": str(run.id)}


@pytest.mark.asyncio
async def test_get_state_projects_active_job_and_safe_retry_fields() -> None:
    session_id = uuid4()
    repository = _Repository(session_id, _ready_preparation())
    jobs = _Jobs()
    jobs.job.error_payload = {
        "code": "PROVIDER_TIMEOUT_ERROR",
        "message": "Provider timed out",
        "retryable": True,
        "provider_secret": "must-not-leak",
    }
    run = SimpleNamespace(
        id=uuid4(),
        revision=3,
        status="needs_attention",
        issues=[],
        terminal_failure=None,
        active_preview={"preview_url": "http://preview/verified"},
        coordinator_stage="plan",
        current_attempt=2,
        active_attempt_id=None,
        plan_summary={},
        source_summary={},
        plan=None,
        planner_receipt=None,
        acquire_receipt=None,
        resource_ledger=None,
        dependency_ledger=None,
        source_checkpoint=None,
        generation_projection=None,
        creative_direction={},
        pipeline_contract_version="code-generator-v4",
        trace_id="trace-projection",
        background_job_id=jobs.job.id,
        acquire_job_id=None,
        generation_job_id=None,
        verification_job_id=None,
    )
    repository.runs.items[run.id] = run
    repository.state = CodeGeneratorSessionState(
        status="needs_attention",
        current_run_id=str(run.id),
        active_preview=run.active_preview,
    )
    service = CodeGeneratorService(repository, jobs, Settings())  # type: ignore[arg-type]

    result = await service.get_state(session_id)
    projection = result["code_generator"]

    assert projection["active_job_id"] == str(jobs.job.id)
    assert projection["active_job_kind"] == "code_generator.plan"
    assert projection["retry_available"] is True
    assert result["jobs"][0]["error"] == {
        "code": "PROVIDER_TIMEOUT_ERROR",
        "message": "Provider timed out",
        "retryable": True,
    }


@pytest.mark.asyncio
async def test_session_source_is_permanently_stale_pending_markdown_brief_ingestion() -> None:
    """Any run still bound to the old artifact-based source ref is stale.

    Build Preparation no longer produces a ZIP artifact to re-verify against.
    """
    session_id = uuid4()
    repository = _Repository(session_id, _ready_preparation())
    run = SimpleNamespace(portfolio_session_id=session_id, build_preparation_source_ref={})

    assert not await _session_source_is_current(repository, run)  # type: ignore[arg-type]
