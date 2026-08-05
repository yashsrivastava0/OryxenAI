"""Contract checks for the Discovery HTTP surface and frontend harness."""

from __future__ import annotations

from pathlib import Path

from oryxenai.main import create_app


def test_all_discovery_endpoints_are_registered() -> None:
    paths = create_app().openapi()["paths"]
    expected = {
        "/api/v1/sessions/{session_id}/discovery",
        "/api/v1/sessions/{session_id}/discovery/input",
        "/api/v1/sessions/{session_id}/discovery/questions",
        "/api/v1/sessions/{session_id}/discovery/answers",
        "/api/v1/sessions/{session_id}/discovery/brief",
        "/api/v1/sessions/{session_id}/discovery/approve",
    }
    assert expected.issubset(paths)
    assert "get" in paths["/api/v1/sessions/{session_id}/discovery"]
    assert "put" in paths["/api/v1/sessions/{session_id}/discovery/input"]
    assert "post" in paths["/api/v1/sessions/{session_id}/discovery/questions"]
    assert "patch" in paths["/api/v1/sessions/{session_id}/discovery/brief"]


def test_frontend_uses_safe_dom_rendering_and_approval_endpoint() -> None:
    javascript = (
        Path(__file__).resolve().parents[2] / "src" / "oryxenai" / "web" / "static" / "app.js"
    ).read_text(encoding="utf-8")
    assert "innerHTML" not in javascript
    assert "/discovery/approve" in javascript
    assert "sessionStorage" in javascript
    assert "discovery/answers" in javascript
