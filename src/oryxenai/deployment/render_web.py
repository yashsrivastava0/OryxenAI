"""Run FastAPI and the durable worker inside one Render Free web service.

Render Free does not offer a free background-worker service. This launcher
runs the existing worker beside the HTTP process, after applying migrations.
It is intended only for the single-instance low-traffic pilot configuration.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from collections.abc import Sequence
from contextlib import suppress

from oryxenai.core.settings import get_settings


def _signal_children(children: Sequence[subprocess.Popen[bytes]], signum: int) -> None:
    for child in children:
        if child.poll() is None:
            with suppress(ProcessLookupError):
                child.send_signal(signum)


def _stop_children(children: Sequence[subprocess.Popen[bytes]], grace_seconds: float) -> None:
    _signal_children(children, signal.SIGTERM)
    deadline = time.monotonic() + max(1.0, grace_seconds)
    for child in children:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            child.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


def main() -> int:
    port = os.environ.get("PORT", "8000").strip()
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        raise SystemExit("PORT must be an integer between 1 and 65535.")

    settings = get_settings()
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)

    children: list[subprocess.Popen[bytes]] = []
    shutdown_signal: int | None = None

    def request_shutdown(signum: int, _frame: object) -> None:
        nonlocal shutdown_signal
        shutdown_signal = signum
        _signal_children(children, signum)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, request_shutdown)

    try:
        # Fixed executable/arguments, no shell, and no user-controlled command.
        api = subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-m",
                "uvicorn",
                "oryxenai.main:app",
                "--host",
                "0.0.0.0",  # noqa: S104 - public host must bind to Render's injected port
                "--port",
                port,
                "--timeout-graceful-shutdown",
                str(max(5, int(settings.worker.shutdown_grace))),
            ]
        )
        children.append(api)
        worker = subprocess.Popen([sys.executable, "-m", "oryxenai.jobs.worker"])
        children.append(worker)

        while True:
            if shutdown_signal is not None:
                _stop_children(children, settings.worker.shutdown_grace + 15)
                return 0

            for child in children:
                status = child.poll()
                if status is not None:
                    _stop_children(children, settings.worker.shutdown_grace + 15)
                    return status if status != 0 else 1
            time.sleep(0.25)
    except BaseException:
        _stop_children(children, settings.worker.shutdown_grace + 15)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
