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
