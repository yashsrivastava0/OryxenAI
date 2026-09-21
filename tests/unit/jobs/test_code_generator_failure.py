from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from oryxenai.agents.code_generator.core.development_schemas import DevelopmentRunStatus
from oryxenai.jobs.handlers import code_generator_failure as failure_module


class _Session:
    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def commit(self) -> None:
        return None


class _Repository:
    def __init__(self, run: SimpleNamespace) -> None:
        self.run = run
        self.event = None

    async def get(self, run_id):
        return self.run if run_id == self.run.id else None

    async def compare_and_swap(self, run_id, *, expected_revision, values):
        if run_id != self.run.id or expected_revision != self.run.revision:
            return None
        for key, value in values.items():
            setattr(self.run, key, value)
        self.run.revision += 1
        return self.run

    async def append_event(self, *args, **kwargs):
        self.event = (args, kwargs)


@pytest.mark.asyncio
async def test_terminal_failure_converges_run_to_needs_attention(monkeypatch) -> None:
    run = SimpleNamespace(
        id=uuid4(),
        revision=4,
        status=DevelopmentRunStatus.PLANNING.value,
        terminal_failure=None,
        generation_projection=None,
    )
    repository = _Repository(run)
    session = _Session()
    monkeypatch.setattr(failure_module, "get_settings", lambda: object())
    monkeypatch.setattr(failure_module, "get_sessionmaker", lambda settings: lambda: session)
    monkeypatch.setattr(
        failure_module,
        "CodeGeneratorDevelopmentRepository",
        lambda db: repository,
    )

    await failure_module.reconcile_terminal_failure(
        {
            "development_run_id": str(run.id),
            "job_kind": "code_generator.v5.plan",
        },
        {
            "code": "HANDLER_ERROR",
            "message": "The background job handler failed.",
            "retryable": False,
            "will_retry": False,
        },
    )

    assert run.status == DevelopmentRunStatus.NEEDS_ATTENTION.value
    assert run.terminal_failure["terminal_code"] == "HANDLER_ERROR"
    assert (
        run.terminal_failure["safe_user_summary"] == "Code Generator could not complete this stage."
    )
    assert run.issues[0]["code"] == "HANDLER_ERROR"
    assert repository.event[1]["event_type"] == "needs_attention"


@pytest.mark.asyncio
async def test_retryable_failure_does_not_surface_attention(monkeypatch) -> None:
    called = False

    def sessionmaker(settings):
        nonlocal called
        called = True
        return lambda: _Session()

    monkeypatch.setattr(failure_module, "get_settings", lambda: object())
    monkeypatch.setattr(failure_module, "get_sessionmaker", sessionmaker)

    await failure_module.reconcile_terminal_failure(
        {"development_run_id": str(uuid4()), "job_kind": "code_generator.v5.plan"},
        {"code": "JOB_TIMEOUT", "message": "timeout", "retryable": True, "will_retry": True},
    )

    assert called is False
