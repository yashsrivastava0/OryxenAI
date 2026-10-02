"""Shared browser fixture: a Vite fixture server plus one headless Chromium page."""

from __future__ import annotations

import shutil
import subprocess
import time
from collections.abc import Iterator

import pytest
from tests.browser.helpers import BASE_URL, FRONTEND_ROOT, sync_playwright


@pytest.fixture(scope="module")
def browser_page() -> Iterator[object]:
    node_executable = shutil.which("node")
    if node_executable is None:
        pytest.skip("Node.js is required for the browser remediation fixture")
    # The executable is resolved from PATH and the script/config are checked-in
    # repository files owned by this test fixture.
    server = subprocess.Popen(  # noqa: S603
        [
            node_executable,
            "node_modules/vite/bin/vite.js",
            "--config",
            "vite.browser-test.config.ts",
        ],
        cwd=FRONTEND_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        with sync_playwright() as playwright_instance:
            try:
                browser = playwright_instance.chromium.launch(headless=True)
            except Exception:
                # Developer machines often have Chrome but not Playwright's bundled build.
                browser = playwright_instance.chromium.launch(headless=True, channel="chrome")
            page = browser.new_page()
            for _ in range(50):
                try:
                    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=500)
                    break
                except Exception:
                    time.sleep(0.1)
            else:
                pytest.fail("Vite browser fixture did not become ready")
            yield page
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=5)
