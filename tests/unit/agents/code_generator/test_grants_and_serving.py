"""Preview grants and the grant-addressed serving route."""

from __future__ import annotations

import logging
import time
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport

from oryxenai.agents.code_generator.bundle import build_bundle
from oryxenai.agents.code_generator.dev.reference_renderer import render_body
from oryxenai.agents.code_generator.grants import GrantError, PreviewGrantSigner
from oryxenai.agents.code_generator.serving import (
    ServedBundle,
    StaticBundleProvider,
    create_preview_router,
)
from oryxenai.core.logging import _PreviewGrantFilter, redact_sensitive_text
from oryxenai.themes import get_theme
from tests.unit.agents.code_generator.helpers import sample_content

THEME = get_theme()
SESSION = uuid4()
VERSION = uuid4()


def _signer() -> PreviewGrantSigner:
    return PreviewGrantSigner("0123456789abcdef0123456789abcdef")


# ── grants ───────────────────────────────────────────────────────────────────


def test_a_minted_grant_verifies_and_carries_its_scope() -> None:
    signer = _signer()
    token, expires_at = signer.mint(SESSION, VERSION, 60)
    grant = signer.verify(token)
    assert (grant.session_id, grant.version_id, grant.expires_at) == (SESSION, VERSION, expires_at)


def test_grants_are_url_safe_and_do_not_contain_slashes() -> None:
    token, _ = _signer().mint(SESSION, VERSION, 60)
    assert "/" not in token and "?" not in token and "#" not in token and " " not in token


def test_an_expired_grant_is_reported_as_expired() -> None:
    signer = _signer()
    token, expires_at = signer.mint(SESSION, VERSION, 60)
    with pytest.raises(GrantError) as caught:
        signer.verify(token, now=expires_at + 1)
    assert caught.value.reason == "expired"


def test_a_tampered_or_foreign_grant_is_rejected() -> None:
    signer = _signer()
    token, _ = signer.mint(SESSION, VERSION, 60)
    head, body, signature = token.split(".")
    forged_body = body[:-2] + ("AA" if not body.endswith("AA") else "BB")
    for bad in (f"{head}.{forged_body}.{signature}", f"{head}.{body}.{signature[:-3]}abc"):
        with pytest.raises(GrantError) as caught:
            signer.verify(bad)
        assert caught.value.reason in {"invalid_signature", "malformed"}
    other = PreviewGrantSigner("another-secret-another-secret-0000")
    with pytest.raises(GrantError):
        other.verify(token)


@pytest.mark.parametrize(
    "token", ["", "x", "v1.a", "v1.a.b.c", "v2.a.b", "....", "v1..".ljust(40, "x")]
)
def test_malformed_grants_are_rejected(token: str) -> None:
    with pytest.raises(GrantError):
        _signer().verify(token)


def test_a_short_secret_is_refused() -> None:
    with pytest.raises(ValueError, match="at least 16 bytes"):
        PreviewGrantSigner("short")


def test_random_signers_do_not_accept_each_others_grants() -> None:
    token, _ = PreviewGrantSigner.random().mint(SESSION, VERSION, 60)
    with pytest.raises(GrantError):
        PreviewGrantSigner.random().verify(token)


# ── serving ──────────────────────────────────────────────────────────────────


def _bundle() -> ServedBundle:
    content = sample_content("01_strong_profile")
    derived = THEME.contract.derive(content)
    sealed = build_bundle(content, derived, render_body(content, derived), "en", THEME)
    return ServedBundle(sealed.index_html, THEME.theme_id, THEME.css_sha256)


def _client(
    bundle: ServedBundle | None = None, signer: PreviewGrantSigner | None = None
) -> tuple[httpx.AsyncClient, PreviewGrantSigner]:
    app = FastAPI()
    app.state.preview_signer = signer or _signer()
    served = bundle or _bundle()
    app.state.preview_provider = StaticBundleProvider({(SESSION, VERSION): served})
    app.include_router(create_preview_router())
    client = httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    return client, app.state.preview_signer


def _url(signer: PreviewGrantSigner, path: str = "index.html", **kwargs: UUID) -> str:
    token, _ = signer.mint(kwargs.get("session", SESSION), kwargs.get("version", VERSION), 300)
    return f"/preview/g/{token}/{path}"


async def test_index_html_is_served_with_the_locked_down_headers() -> None:
    client, signer = _client()
    response = await client.get(_url(signer))
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.text == _bundle().index_html
    csp = response.headers["content-security-policy"]
    for directive in (
        "default-src 'none'",
        "style-src 'self'",
        "font-src 'self'",
        "img-src 'self' data:",
        "base-uri 'none'",
        "form-action 'none'",
        "frame-ancestors 'self'",
        "sandbox allow-popups allow-popups-to-escape-sandbox",
    ):
        assert directive in csp
    assert "script-src" not in csp and "allow-scripts" not in csp and "allow-same-origin" not in csp
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert "noindex" in response.headers["x-robots-tag"]
    assert "access-control-allow-origin" not in response.headers


async def test_the_bare_grant_path_serves_the_index() -> None:
    client, signer = _client()
    token, _ = signer.mint(SESSION, VERSION, 300)
    assert (await client.get(f"/preview/g/{token}/")).status_code == 200


async def test_theme_files_are_served_unchanged_with_cors_and_validators() -> None:
    client, signer = _client()
    css = await client.get(_url(signer, "styles.css"))
    assert css.status_code == 200
    assert css.content == THEME.stylesheet.data
    assert css.headers["content-type"] == "text/css; charset=utf-8"
    assert css.headers["access-control-allow-origin"] == "*"
    assert css.headers["etag"] == f'"{THEME.css_sha256}"'
    assert css.headers["cache-control"].startswith("private")
    assert "content-security-policy" in css.headers
    again = await client.get(
        _url(signer, "styles.css"), headers={"If-None-Match": css.headers["etag"]}
    )
    assert again.status_code == 304

    font_path = next(path for path in THEME.files if path.endswith(".woff2"))
    font = await client.get(_url(signer, font_path))
    assert font.status_code == 200
    assert font.headers["content-type"] == "font/woff2"
    assert font.headers["access-control-allow-origin"] == "*"
    assert font.content == THEME.file(font_path).data  # type: ignore[union-attr]

    svg = await client.get(_url(signer, "assets/hero-visual.svg"))
    assert svg.status_code == 200 and svg.headers["content-type"] == "image/svg+xml"


async def test_every_theme_file_referenced_by_the_page_resolves() -> None:
    client, signer = _client()
    html = (await client.get(_url(signer))).text
    assert 'href="./styles.css"' in html
    for path in ("styles.css", "assets/hero-visual.svg"):
        assert (await client.get(_url(signer, path))).status_code == 200


async def test_unknown_files_and_path_tricks_are_not_found() -> None:
    client, signer = _client()
    for path in (
        "missing.js",
        "index.html/extra",
        "assets/../manifest.json",
        "%2e%2e/secret",
        "a%5Cb",
    ):
        assert (await client.get(_url(signer, path))).status_code == 404, path
    # The manifest and contract are theme internals, not bundle files.
    assert (await client.get(_url(signer, "manifest.json"))).status_code == 404


async def test_an_expired_grant_returns_a_small_gone_page_under_the_same_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, signer = _client()
    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() - 3600)
    token, _ = signer.mint(SESSION, VERSION, 60)
    monkeypatch.setattr(time, "time", real_time)
    response = await client.get(f"/preview/g/{token}/index.html")
    assert response.status_code == 410
    assert "expired" in response.text.lower()
    assert "sandbox" in response.headers["content-security-policy"]


async def test_forged_and_foreign_grants_get_a_plain_not_found() -> None:
    client, _signer_in_use = _client()
    other = PreviewGrantSigner("another-secret-another-secret-0000")
    assert (await client.get(_url(other))).status_code == 404
    assert (await client.get("/preview/g/garbage/index.html")).status_code == 404


async def test_a_grant_for_a_version_that_is_gone_is_unavailable() -> None:
    client, signer = _client()
    response = await client.get(_url(signer, version=uuid4()))
    assert response.status_code == 404
    assert "no longer available" in response.text


async def test_a_theme_whose_files_changed_is_refused_instead_of_served() -> None:
    drifted = ServedBundle(_bundle().index_html, THEME.theme_id, "0" * 64)
    client, signer = _client(bundle=drifted)
    response = await client.get(_url(signer))
    assert response.status_code == 404
    assert "changed" in response.text


async def test_an_uninstalled_theme_is_refused() -> None:
    gone = ServedBundle(_bundle().index_html, "no-such-theme/v9", THEME.css_sha256)
    client, signer = _client(bundle=gone)
    assert (await client.get(_url(signer))).status_code == 404


# ── grants never reach logs ──────────────────────────────────────────────────


async def test_preview_grants_are_redacted_from_log_text() -> None:
    token, _ = _signer().mint(SESSION, VERSION, 60)
    text = redact_sensitive_text(f"GET /preview/g/{token}/index.html -> 200 (3.0ms)")
    assert token not in text
    assert "/preview/g/[REDACTED]/index.html" in text


async def test_the_access_log_filter_redacts_the_path_argument() -> None:
    token, _ = _signer().mint(SESSION, VERSION, 60)
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:1", "GET", f"/preview/g/{token}/styles.css?x=1", "1.1", 200),
        None,
    )
    assert _PreviewGrantFilter().filter(record) is True
    assert token not in record.getMessage()
    assert "/preview/g/[REDACTED]/styles.css" in record.getMessage()
