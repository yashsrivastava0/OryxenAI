from __future__ import annotations

import sys

import pytest

from oryxenai.agents.code_generator.process_runner import ProcessRunnerError, run_command


@pytest.mark.asyncio
async def test_process_runner_uses_no_shell_and_captures_output(tmp_path) -> None:
    result = await run_command(
        [sys.executable, "-c", "print('safe')"],
        cwd=tmp_path,
        timeout_seconds=5,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "safe"


@pytest.mark.asyncio
async def test_process_runner_rejects_untrusted_executable(tmp_path) -> None:
    with pytest.raises(ProcessRunnerError, match="not allowed"):
        await run_command(["cmd", "/c", "echo unsafe"], cwd=tmp_path, timeout_seconds=5)
