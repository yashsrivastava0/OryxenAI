from __future__ import annotations

from types import SimpleNamespace

import pytest

from oryxenai.agents.code_generator.core import check_runner
from oryxenai.agents.code_generator.core.process_runner import ProcessResult


@pytest.mark.asyncio
async def test_configured_typecheck_timeout_has_distinct_diagnostic(tmp_path, monkeypatch) -> None:
    async def timed_out_command(*_args, **_kwargs) -> ProcessResult:
        return ProcessResult(
            command=("npm", "run", "typecheck"),
            returncode=-9,
            stdout="",
            stderr="",
            timed_out=True,
        )

    monkeypatch.setattr(check_runner, "run_command", timed_out_command)
    settings = SimpleNamespace(
        code_generator_generation=SimpleNamespace(
            typecheck_command=["npm", "run", "typecheck"],
            typecheck_timeout_seconds=1,
        )
    )

    diagnostics = await check_runner._run_configured_typecheck(
        tmp_path, work_unit_id="unit:test", settings=settings
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "TYPECHECK_TIMEOUT"


@pytest.mark.asyncio
async def test_configured_typecheck_can_defer_whole_site_source_audit(
    tmp_path, monkeypatch
) -> None:
    calls: list[tuple[str, ...]] = []

    async def successful_command(command, *_args, **_kwargs) -> ProcessResult:
        calls.append(tuple(command))
        return ProcessResult(command=tuple(command), returncode=0, stdout="", stderr="")

    monkeypatch.setattr(check_runner, "run_command", successful_command)
    settings = SimpleNamespace(
        code_generator_generation=SimpleNamespace(
            source_audit_command=["npm", "run", "source:audit"],
            typecheck_command=["npm", "run", "typecheck"],
            typecheck_timeout_seconds=1,
        )
    )

    diagnostics = await check_runner._run_configured_typecheck(
        tmp_path,
        work_unit_id="unit:foundation",
        settings=settings,
        include_source_audit=False,
    )

    assert diagnostics == []
    assert calls == [("npm", "run", "typecheck")]
