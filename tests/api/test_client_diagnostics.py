"""API tests for the local browser test-trace handoff."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import httpx
from httpx import ASGITransport

from oryxenai.core.settings import Settings
from oryxenai.main import create_app


async def test_client_trace_stores_only_allowlisted_metadata():
    settings = Settings()
    settings.client_diagnostics.enabled = True
    trace_id = uuid4()
    diagnostic_root = Path(".workspace") / f"client-diagnostics-test-{trace_id.hex}"
    settings.client_diagnostics.output_root = str(diagnostic_root)
    app = create_app(settings)

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/client-diagnostics/events",
                json={
                    "client_run_id": str(trace_id),
                    "events": [
                        {
                            "kind": "api_response",
                            "route": "/api/v1/sessions/example/discovery",
                            "method": "GET",
                            "status": 200,
                            "duration_ms": 18,
                            "input_characters": 11441,
                            # Unknown body-like fields are intentionally ignored.
                            "resume": "must never be persisted",
                        }
                    ],
                },
            )

        assert response.status_code == 202
        assert response.json() == {"client_run_id": str(trace_id), "accepted": 1, "stored": True}
        trace_file = diagnostic_root / str(trace_id) / "events.jsonl"
        record = json.loads(trace_file.read_text(encoding="utf-8").splitlines()[0])
        assert record["client_run_id"] == str(trace_id)
        assert record["route"] == "/api/v1/sessions/example/discovery"
        assert record["input_characters"] == 11441
        assert "resume" not in record
    finally:
        trace_file = diagnostic_root / str(trace_id) / "events.jsonl"
        if trace_file.exists():
            trace_file.unlink()
        if trace_file.parent.exists():
            trace_file.parent.rmdir()
        if diagnostic_root.exists():
            diagnostic_root.rmdir()


async def test_client_trace_route_is_not_mounted_when_disabled():
    settings = Settings()
    settings.client_diagnostics.enabled = False
    app = create_app(settings)
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/api/v1/client-diagnostics/events" not in paths
