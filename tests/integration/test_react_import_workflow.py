"""The Codex skill's actual importer against our remote MCP transport."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
from pathlib import Path
from uuid import UUID

import pytest
import uvicorn

from oryxenai.db.models.react_handoff import ReactHandoff
from oryxenai.db.models.site_version import PortfolioSiteVersion
from oryxenai.delivery.contracts import sha256
from oryxenai.delivery.mcp import create_mcp
from oryxenai.jobs.handlers.react_delivery import prepare
from oryxenai.jobs.repository import JobRepository
from oryxenai.themes import get_theme
from tests.integration.test_react_handoffs import db_session as db_session
from tests.integration.test_react_handoffs import fixture, start

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
ROOT = Path(__file__).resolve().parents[2]


async def run(*args, cwd, env=None):
    process = await asyncio.create_subprocess_exec(
        *args, cwd=cwd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    stdout, _ = await asyncio.wait_for(process.communicate(), timeout=120)
    assert process.returncode == 0, stdout.decode(errors="replace")[-6000:]
    return stdout.decode(errors="replace")


async def test_mcp_imported_projects_install_typecheck_and_build_for_every_theme(
    test_engine, db_session, tmp_path
):
    from oryxenai.delivery.project import SUPPORTED_THEMES

    node = shutil.which("node")
    assert node, "Install Node.js for React delivery acceptance checks."
    runtime, access, initial_source = await fixture(db_session, test_engine)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(64)
    port = listener.getsockname()[1]
    endpoint = f"http://127.0.0.1:{port}/mcp"
    app, _ = create_mcp(runtime)
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="on"))
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        async with asyncio.timeout(10):
            while not server.started:
                await asyncio.sleep(0.02)
        for index, theme_id in enumerate(sorted(SUPPORTED_THEMES), start=2):
            theme = get_theme(theme_id)
            source = PortfolioSiteVersion(
                portfolio_session_id=access.session.id,
                seq=index,
                status="ready",
                content_snapshot=initial_source.content_snapshot,
                theme_id=theme_id,
                theme_sha256=theme.css_sha256,
                index_html="fixture",
                index_sha256=sha256(b"fixture"),
            )
            db_session.add(source)
            await db_session.commit()
            handoff, payload = await start(db_session, runtime, access, source)
            await prepare(runtime, payload)
            await JobRepository(db_session).mark_succeeded(UUID(payload["job_id"]), {})
            await db_session.commit()
            async with runtime.sessionmaker() as db:
                status = runtime.status(await db.get(ReactHandoff, UUID(handoff["id"])))
            directory = tmp_path / theme_id.replace("/", "-")
            # Exercise the skill's real --build path without registry traffic
            # or dependency lifecycle hooks in standard acceptance tests.
            environment = {
                **os.environ,
                "ORYXENAI_SHARE_LINK": status["share_link"],
                "npm_config_offline": "true",
                "npm_config_ignore_scripts": "true",
            }
            output = await run(
                node,
                str(ROOT / "plugins/oryxenai-react-handoff/scripts/import-project.mjs"),
                "--endpoint",
                endpoint,
                "--destination",
                str(directory),
                "--build",
                cwd=ROOT,
                env=environment,
            )
            imported = json.loads(output.strip().splitlines()[-1])
            assert imported["handoff_id"] == handoff["id"] and imported["build"] == "passed"
            assert imported["timings"]["transfer_seconds"] >= 0
            assert imported["timings"]["install_typecheck_build_seconds"] > 0
            assert (directory / "dist/index.html").exists()
            assert (directory / "public/theme" / theme.stylesheet.path).exists()
            assert (directory / "project-manifest.json").exists()
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, timeout=10)
