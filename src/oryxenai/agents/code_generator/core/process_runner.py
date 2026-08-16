"""Trusted, bounded subprocess execution for Code Generator verification."""

from __future__ import annotations

import asyncio
import os
import shutil
import signal
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


class ProcessRunnerError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ProcessResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def combined_output(self) -> str:
        return f"{self.stdout}\n{self.stderr}".strip()


_ALLOWED_EXECUTABLES = {
    "npm",
    "npm.cmd",
    "node",
    "node.exe",
    "npx",
    "npx.cmd",
    "python",
    "python.exe",
    "playwright",
    "playwright.exe",
}


def _safe_environment(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ)
    for key in tuple(environment):
        upper = key.upper()
        if upper.endswith(("_TOKEN", "_PASSWORD", "_SECRET", "_KEY")):
            environment.pop(key, None)
    if extra:
        environment.update(extra)
    return environment


def _executable_name(value: str) -> str:
    return Path(value).name.casefold()


def _validate_command(command: list[str]) -> None:
    if not command or any(not isinstance(item, str) or not item for item in command):
        raise ProcessRunnerError(
            "COMMAND_INVALID", "A trusted command must contain non-empty arguments."
        )
    if _executable_name(command[0]) not in _ALLOWED_EXECUTABLES:
        raise ProcessRunnerError("COMMAND_NOT_ALLOWED", "The configured executable is not allowed.")


async def _terminate_process_tree(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    if sys.platform == "win32":
        try:
            killer = await asyncio.create_subprocess_exec(
                "taskkill",
                "/PID",
                str(process.pid),
                "/T",
                "/F",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await killer.communicate()
        except OSError:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            process.kill()


async def run_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: float,
    max_output_bytes: int = 64 * 1024,
    environment: Mapping[str, str] | None = None,
) -> ProcessResult:
    """Run one trusted command without a shell and clean up descendants."""

    _validate_command(command)
    executable = shutil.which(command[0])
    if executable:
        command = [executable, *command[1:]]
    if not cwd.is_dir():
        raise ProcessRunnerError(
            "COMMAND_CWD_MISSING", "The trusted command directory is unavailable."
        )
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    kwargs: dict[str, object] = {
        "cwd": str(cwd),
        "env": _safe_environment(environment),
        "stdin": asyncio.subprocess.DEVNULL,
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.PIPE,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = creationflags
    else:
        kwargs["start_new_session"] = True
    try:
        process = await asyncio.create_subprocess_exec(*command, **kwargs)  # type: ignore[arg-type]
    except OSError as exc:
        raise ProcessRunnerError(
            "COMMAND_START_FAILED", "The trusted command could not start."
        ) from exc
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(), timeout=max(0.1, timeout_seconds)
        )
        timed_out = False
    except TimeoutError:
        await _terminate_process_tree(process)
        stdout_bytes, stderr_bytes = await process.communicate()
        timed_out = True
    stdout = stdout_bytes.decode("utf-8", errors="replace")[-max_output_bytes:]
    stderr = stderr_bytes.decode("utf-8", errors="replace")[-max_output_bytes:]
    return ProcessResult(
        command=tuple(command),
        returncode=int(process.returncode or 0),
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
    )
