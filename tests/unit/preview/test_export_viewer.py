from __future__ import annotations

import importlib.util
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType

import httpx
import pytest


def _load_viewer_module() -> ModuleType:
    script = Path(__file__).parents[3] / "scripts" / "preview-codegen-export.py"
    spec = importlib.util.spec_from_file_location("preview_codegen_export", script)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load viewer script: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def export_server(tmp_path: Path):
    viewer = _load_viewer_module()
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        "<!doctype html><html><head>"
        '<script type="module" src="./assets/app.js"></script>'
        '<link rel="stylesheet" href="./assets/app.css">'
        "</head><body><main><h1>Export</h1></main></body></html>",
        encoding="utf-8",
    )
    (dist / "assets" / "app.js").write_text("console.log('fresh')", encoding="utf-8")
    (dist / "assets" / "app.css").write_text("main { color: red; }", encoding="utf-8")
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        lambda *args, **kwargs: viewer.ExportHandler(*args, directory=str(dist), **kwargs),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, dist
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_export_viewer_serves_nested_spa_routes_and_root_assets(export_server) -> None:
    server, _dist = export_server
    base = f"http://127.0.0.1:{server.server_address[1]}"
    with httpx.Client(base_url=base) as client:
        root = client.get("/")
        nested = client.get("/work/project")
        asset = client.get("/assets/app.js")
        missing = client.get("/assets/missing.js")

    assert root.status_code == 200
    assert nested.status_code == 200
    assert 'src="/assets/app.js"' in nested.text
    assert 'href="/assets/app.css"' in nested.text
    assert asset.status_code == 200
    assert asset.text == "console.log('fresh')"
    assert missing.status_code == 404
    assert "<html" not in missing.text.lower()


def test_export_viewer_ignores_conditional_cache_headers(export_server) -> None:
    server, dist = export_server
    base = f"http://127.0.0.1:{server.server_address[1]}"
    with httpx.Client(base_url=base) as client:
        first = client.get("/", headers={"If-Modified-Since": "Wed, 01 Jan 2020 00:00:00 GMT"})
        (dist / "index.html").write_text(
            "<!doctype html><html><body><main><h1>Switched export</h1></main></body></html>",
            encoding="utf-8",
        )
        second = client.get("/", headers={"If-None-Match": '"stale-export"'})
        head = client.head("/work/project")

    assert first.status_code == 200
    assert second.status_code == 200
    assert "Switched export" in second.text
    assert second.headers["cache-control"] == "no-store, max-age=0"
    assert head.status_code == 200
    assert head.content == b""


def test_export_viewer_preserves_external_and_data_urls() -> None:
    viewer = _load_viewer_module()
    html = (
        b'<script src="https://cdn.example/app.js"></script>'
        b'<img src="data:image/svg+xml;base64,abc">'
        b'<link href="#local">'
    )
    assert viewer._rewrite_export_html_urls(html) == html
