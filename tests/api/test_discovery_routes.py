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
        "/api/v1/sessions/{session_id}/discovery/stop",
    }
    assert expected.issubset(paths)
    assert "get" in paths["/api/v1/sessions/{session_id}/discovery"]
    assert "post" in paths["/api/v1/sessions/{session_id}/discovery/start"]
    assert "put" in paths["/api/v1/sessions/{session_id}/discovery/answers"]
    assert "post" in paths["/api/v1/sessions/{session_id}/discovery/revise"]
    assert "post" in paths["/api/v1/sessions/{session_id}/discovery/approve"]
    assert "post" in paths["/api/v1/sessions/{session_id}/discovery/stop"]


def test_model_profile_endpoint_is_config_driven_and_safe() -> None:
    paths = create_app().openapi()["paths"]
    assert "post" in paths["/api/v1/sessions/{session_id}/content-architect/stop"]
    assert "/api/v1/model-profiles" in paths
    schema = paths["/api/v1/model-profiles"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert schema["type"] == "array"
    assert "api_key_env" not in str(schema).lower()
    assert "base_url" not in str(schema).lower()
    assert "/api/v1/pipeline/model-profiles" in paths
    assert "/api/v1/pipeline/model-profiles/preflight" in paths


def test_removed_endpoints_are_gone() -> None:
    paths = create_app().openapi()["paths"]
    for removed in (
        "/api/v1/sessions/{session_id}/discovery/input",
        "/api/v1/sessions/{session_id}/discovery/questions",
        "/api/v1/sessions/{session_id}/discovery/brief",
    ):
        assert removed not in paths


def test_legacy_static_pipeline_shell_is_not_tracked() -> None:
    root = Path(__file__).resolve().parents[2]
    assert not (root / "src" / "oryxenai" / "web" / "static" / "app.js").exists()
    assert not (root / "src" / "oryxenai" / "web" / "static" / "app.css").exists()
    assert not (root / "src" / "oryxenai" / "web" / "templates" / "index.html").exists()


def test_product_frontend_is_the_checked_in_preact_source() -> None:
    source = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "main.tsx").read_text(
        encoding="utf-8"
    )
    assert "export function boot" in source
    assert "export function stop" in source
    assert "export function restart" in source
