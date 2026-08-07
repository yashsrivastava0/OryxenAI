"""Contract checks for the Discovery HTTP surface and frontend chat harness."""

from __future__ import annotations

from pathlib import Path

from oryxenai.main import create_app


def test_all_discovery_endpoints_are_registered() -> None:
    paths = create_app().openapi()["paths"]
    expected = {
        "/api/v1/sessions/{session_id}/discovery",
        "/api/v1/sessions/{session_id}/discovery/start",
        "/api/v1/sessions/{session_id}/discovery/answers",
        "/api/v1/sessions/{session_id}/discovery/revise",
        "/api/v1/sessions/{session_id}/discovery/approve",
    }
    assert expected.issubset(paths)
    assert "get" in paths["/api/v1/sessions/{session_id}/discovery"]
    assert "post" in paths["/api/v1/sessions/{session_id}/discovery/start"]
    assert "put" in paths["/api/v1/sessions/{session_id}/discovery/answers"]
    assert "post" in paths["/api/v1/sessions/{session_id}/discovery/revise"]
    assert "post" in paths["/api/v1/sessions/{session_id}/discovery/approve"]


def test_removed_endpoints_are_gone() -> None:
    paths = create_app().openapi()["paths"]
    for removed in (
        "/api/v1/sessions/{session_id}/discovery/input",
        "/api/v1/sessions/{session_id}/discovery/questions",
        "/api/v1/sessions/{session_id}/discovery/brief",
    ):
        assert removed not in paths


def test_frontend_uses_safe_dom_rendering_and_chat_endpoints() -> None:
    javascript = (
        Path(__file__).resolve().parents[2] / "src" / "oryxenai" / "web" / "static" / "app.js"
    ).read_text(encoding="utf-8")
    assert "innerHTML" not in javascript
    assert "demo-mode" not in javascript
    assert "demoMode" not in javascript
    assert "/discovery/start" in javascript
    assert "/discovery/answers" in javascript
    assert "/discovery/revise" in javascript
    assert "/discovery/approve" in javascript
    assert "sessionStorage" in javascript
    assert "textContent" in javascript


def test_frontend_has_chat_page_elements() -> None:
    template = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "oryxenai"
        / "web"
        / "templates"
        / "index.html"
    ).read_text(encoding="utf-8")
    for element in ("chat-messages", "composer", "btn-send", "btn-attach", "advanced"):
        assert element in template
    assert "demo-mode" not in template
    assert "mode-bar" not in template
