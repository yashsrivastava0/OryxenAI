from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from oryxenai.agents.build_preparation.schemas import (
    BuildPreparationSourceRef,
    BuildPreparationState,
    BuildPreparationStatus,
    HandoffQualityReport,
    PackageResult,
)
from oryxenai.agents.code_generator import service as service_module
from oryxenai.agents.code_generator.service import (
    CodeGeneratorOperationError,
    CodeGeneratorService,
)
from oryxenai.agents.code_generator.session_schemas import CodeGeneratorSessionState
from oryxenai.core.settings import Settings
from oryxenai.jobs.handlers.code_generator_verification import _session_source_is_current
from oryxenai.storage.artifacts import ArtifactReference


class _ArtifactStore:
    def __init__(self, reference: ArtifactReference) -> None:
        self.reference = reference

    async def head(self, reference: ArtifactReference) -> ArtifactReference | None:
        assert reference == self.reference
        return self.reference


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
        run = SimpleNamespace(
            id=uuid4(),
            revision=0,
            status="created",
            issues=[],
            terminal_failure=None,
            active_preview=None,
            coordinator_stage="plan",
            current_attempt=0,
            plan_summary={},
            source_summary={},
            background_job_id=None,
            acquire_job_id=None,
            generation_job_id=None,
            verification_job_id=None,
            **values,
        )
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
        assert kind == "code_generator.plan"
        self.payload = payload
        return self.job

    async def get(self, job_id: UUID):
        return self.job if job_id == self.job.id else None


def _preparation(reference: ArtifactReference) -> BuildPreparationState:
    return BuildPreparationState(
        status=BuildPreparationStatus.READY,
        run_id="build-preparation-run",
        scope_hash="scope-hash",
        source_ref=BuildPreparationSourceRef(
            content_architect_content_hash="content-hash",
            visual_design_director_direction_hash="visual-hash",
        ),
        package=PackageResult(
            archive_sha256=reference.sha256,
            archive_size_bytes=reference.size_bytes,
            file_count=12,
            expires_at=reference.expires_at,
            artifact=reference,
        ),
        handoff_report=HandoffQualityReport(
            handoff_eligible=True,
            upstream_approval_verified=True,
            status="ready_for_handoff",
        ),
    )


@pytest.mark.asyncio
async def test_session_start_binds_exact_artifact_and_queues_production_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expiry = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    reference = ArtifactReference(
        provider="memory",
        key="temporary/pack.zip",
        sha256="a" * 64,
        size_bytes=128,
        expires_at=expiry,
        etag="etag",
    )
    session_id = uuid4()
    repository = _Repository(session_id, _preparation(reference))
    jobs = _Jobs()
    settings = Settings()
    checked_profiles: list[str] = []

    async def provider_preflight(profile: str):
        checked_profiles.append(profile)
        return {"ok": True}

    monkeypatch.setattr(service_module, "resolve_api_key", lambda profile: "configured")
    monkeypatch.setattr(service_module.shutil, "which", lambda executable: executable)
    monkeypatch.setattr(service_module, "browser_ready", lambda config: True)
    service = CodeGeneratorService(
        repository,  # type: ignore[arg-type]
        jobs,  # type: ignore[arg-type]
        settings,
        artifact_store=_ArtifactStore(reference),  # type: ignore[arg-type]
        provider_preflight=provider_preflight,
    )

    result = await service.start(session_id, idempotency_key="start-once")

    assert result["code_generator"]["status"] == "queued"
    assert jobs.payload == {"code_generator_run_id": str(repository.runs.created.id)}
    assert repository.runs.created.run_mode == "session"
    assert repository.runs.created.portfolio_session_id == session_id
    assert repository.runs.created.artifact_reference["sha256"] == reference.sha256
    assert repository.state.source_ref is not None
    assert repository.state.source_ref.archive_sha256 == reference.sha256
    assert checked_profiles


@pytest.mark.asyncio
async def test_session_start_rejects_request_time_profile_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = ArtifactReference(
        provider="memory",
        key="temporary/pack.zip",
        sha256="b" * 64,
        size_bytes=64,
        expires_at=(datetime.now(UTC) + timedelta(days=2)).isoformat(),
    )
    session_id = uuid4()
    settings = Settings()
    monkeypatch.setattr(service_module, "resolve_api_key", lambda profile: "configured")
    monkeypatch.setattr(service_module.shutil, "which", lambda executable: executable)
    monkeypatch.setattr(service_module, "browser_ready", lambda config: True)
    service = CodeGeneratorService(
        _Repository(session_id, _preparation(reference)),  # type: ignore[arg-type]
        _Jobs(),  # type: ignore[arg-type]
        settings,
        artifact_store=_ArtifactStore(reference),  # type: ignore[arg-type]
        provider_preflight=lambda profile: pytest.fail("preflight must not run"),  # type: ignore[arg-type]
    )

    with pytest.raises(CodeGeneratorOperationError) as exc_info:
        await service.start(
            session_id,
            idempotency_key="override",
            model_profile="unconfigured-request-profile",
        )

    assert exc_info.value.code == "CODE_GENERATOR_PROFILE_OVERRIDE_UNSUPPORTED"


@pytest.mark.asyncio
async def test_preview_promotion_rejects_a_changed_build_preparation_source() -> None:
    reference = ArtifactReference(
        provider="memory",
        key="temporary/pack.zip",
        sha256="c" * 64,
        size_bytes=64,
        expires_at=(datetime.now(UTC) + timedelta(days=2)).isoformat(),
    )
    session_id = uuid4()
    repository = _Repository(session_id, _preparation(reference))
    run = SimpleNamespace(
        portfolio_session_id=session_id,
        build_preparation_source_ref={
            "build_preparation_run_id": "build-preparation-run",
            "build_preparation_scope_hash": "scope-hash",
            "archive_sha256": reference.sha256,
            "artifact": reference.model_dump(mode="json"),
        },
    )

    assert await _session_source_is_current(repository, run)  # type: ignore[arg-type]
    repository.preparation.scope_hash = "changed-scope"
    assert not await _session_source_is_current(repository, run)  # type: ignore[arg-type]
