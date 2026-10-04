"""Serving a sealed page bundle: the one place that decides what a preview response is.

``GET /preview/g/<grant>/<path>`` returns the version's ``index.html`` (from the
database) or one of the theme's unchanged files (from the application image).
The same router, headers and MIME types run in production and in the browser
verifier; only the bundle provider differs (database vs. in memory).

The preview is untrusted content served from the application's own origin, so it
is locked down twice: the response carries a CSP ``sandbox`` (a standalone tab
becomes an opaque origin) and the Studio embeds it in a sandboxed iframe without
``allow-same-origin``. Neither the page nor its scripts-that-do-not-exist can
reach the app's storage or API.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.agents.code_generator.grants import GrantError, PreviewGrantSigner
from oryxenai.core.logging import get_logger
from oryxenai.db.models.portfolio_session import PortfolioSession
from oryxenai.db.models.site_version import PortfolioSiteVersion
from oryxenai.themes import ThemeError, get_theme, media_type_for

logger = get_logger("oryxenai.code_generator.serving")

PREVIEW_PREFIX = "/preview/g"

_CSP = (
    "default-src 'none'; style-src 'self'; font-src 'self'; img-src 'self' data:; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'self'; "
    "sandbox allow-popups allow-popups-to-escape-sandbox"
)
_SCRIPT_CSP = (
    "default-src 'none'; script-src 'self'; script-src-attr 'none'; "
    "style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'none'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'self'; "
    "sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox"
)


@dataclass(frozen=True, slots=True)
class ServedBundle:
    index_html: str
    theme_id: str
    theme_sha256: str
    index_sha256: str | None = None
    manifest: Mapping[str, object] | None = None


class BundleProvider(Protocol):
    async def load(self, session_id: UUID, version_id: UUID) -> ServedBundle | None: ...


class DbBundleProvider:
    """Loads a ready, unrestricted version of an active session from PostgreSQL."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def load(self, session_id: UUID, version_id: UUID) -> ServedBundle | None:
        async with self._sessionmaker() as db:
            row = (
                await db.execute(
                    select(
                        PortfolioSiteVersion.index_html,
                        PortfolioSiteVersion.theme_id,
                        PortfolioSiteVersion.theme_sha256,
                        PortfolioSiteVersion.index_sha256,
                        PortfolioSiteVersion.manifest,
                    )
                    .join(
                        PortfolioSession,
                        PortfolioSession.id == PortfolioSiteVersion.portfolio_session_id,
                    )
                    .where(
                        PortfolioSiteVersion.id == version_id,
                        PortfolioSiteVersion.portfolio_session_id == session_id,
                        PortfolioSiteVersion.status == "ready",
                        PortfolioSiteVersion.restricted.is_(False),
                        PortfolioSiteVersion.index_html.is_not(None),
                        PortfolioSession.status == "active",
                    )
                )
            ).first()
        if row is None or row[0] is None:
            return None
        return ServedBundle(
            index_html=str(row[0]),
            theme_id=str(row[1]),
            theme_sha256=str(row[2]),
            index_sha256=str(row[3]) if row[3] else None,
            manifest=row[4],
        )


class StaticBundleProvider:
    """In-memory provider (browser verifier, tests): one bundle per (session, version)."""

    def __init__(self, bundles: Mapping[tuple[UUID, UUID], ServedBundle]) -> None:
        self._bundles = dict(bundles)

    async def load(self, session_id: UUID, version_id: UUID) -> ServedBundle | None:
        return self._bundles.get((session_id, version_id))


def preview_headers(
    *, html: bool, etag: str | None = None, scripts: bool = False
) -> dict[str, str]:
    """Headers for every preview response (pages, theme files and error pages)."""
    headers = {
        "Content-Security-Policy": _SCRIPT_CSP if scripts else _CSP,
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "X-Robots-Tag": "noindex, nofollow",
        "Cross-Origin-Resource-Policy": "cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    }
    if html:
        headers["Cache-Control"] = "no-store"
    else:
        # A sandboxed page has an opaque origin: its font requests are CORS requests.
        headers["Access-Control-Allow-Origin"] = "*"
        headers["Cache-Control"] = "private, max-age=0, must-revalidate"
        if etag:
            headers["ETag"] = f'"{etag}"'
    return headers


def _notice(status: int, title: str, message: str) -> Response:
    body = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{title}</title></head><body><p>{message}</p></body></html>"
    )
    return Response(
        body, status_code=status, media_type="text/html", headers=preview_headers(html=True)
    )


def _unsafe_path(path: str) -> bool:
    return (
        "\\" in path
        or "\x00" in path
        or any(segment in {"..", "."} for segment in path.split("/"))
        or len(path) > 200
    )


def bundle_integrity_ok(bundle: ServedBundle, theme: object) -> bool:
    """Compare the stored page and complete theme manifest before serving."""
    from oryxenai.themes import ThemePackage

    if not isinstance(theme, ThemePackage) or theme.css_sha256 != bundle.theme_sha256:
        return False
    if (
        bundle.index_sha256
        and sha256(bundle.index_html.encode("utf-8")).hexdigest() != bundle.index_sha256
    ):
        return False
    if bundle.manifest is None:
        return not theme.allows_scripts  # older versions pinned only the stylesheet
    entries = bundle.manifest.get("files")
    if not isinstance(entries, list):
        return False
    stored = {str(row.get("path")): row for row in entries if isinstance(row, dict)}
    expected_paths = {"index.html", *theme.files}
    if set(stored) != expected_paths:
        return False
    index = stored["index.html"]
    if index.get("sha256") != sha256(bundle.index_html.encode("utf-8")).hexdigest():
        return False
    return all(
        stored[path].get("sha256") == item.sha256 and stored[path].get("bytes") == item.size
        for path, item in theme.files.items()
    )


def create_preview_router() -> APIRouter:
    """The grant-addressed preview route (mounted outside ``/api``).

    The signer and provider are read from ``request.app.state`` so production and
    the browser verifier share this exact router.
    """
    router = APIRouter(prefix="/preview", tags=["preview"], include_in_schema=False)

    @router.get("/g/{grant}/{path:path}")
    async def serve(grant: str, path: str, request: Request) -> Response:
        signer: PreviewGrantSigner = request.app.state.preview_signer
        provider: BundleProvider = request.app.state.preview_provider
        try:
            parsed = signer.verify(grant)
        except GrantError as exc:
            if exc.reason == "expired":
                return _notice(
                    410,
                    "Preview expired",
                    "This preview link has expired. Reopen the preview from OryxenAI.",
                )
            return _notice(404, "Not found", "Not found.")
        requested = path.strip("/") or "index.html"
        if _unsafe_path(requested):
            return _notice(404, "Not found", "Not found.")

        bundle = await provider.load(parsed.session_id, parsed.version_id)
        if bundle is None:
            return _notice(
                404,
                "Preview unavailable",
                "This version is no longer available. Reopen the preview from OryxenAI.",
            )
        try:
            theme = get_theme(bundle.theme_id)
        except ThemeError:
            logger.warning("preview theme is not installed theme_id=%s", bundle.theme_id)
            return _notice(
                404,
                "Preview unavailable",
                "The theme this version was built with is not installed.",
            )
        if not bundle_integrity_ok(bundle, theme):
            logger.warning(
                "preview theme hash differs from the version pin theme_id=%s", theme.theme_id
            )
            return _notice(
                404,
                "Preview unavailable",
                "The theme files changed since this version was built.",
            )

        if requested == "index.html":
            data = bundle.index_html.encode("utf-8")
            return Response(
                data,
                media_type=media_type_for("index.html"),
                headers=preview_headers(html=True, scripts=theme.allows_scripts),
            )
        entry = theme.file(requested)
        if entry is None:
            return _notice(404, "Not found", "Not found.")
        if request.headers.get("if-none-match", "").strip('"') == entry.sha256:
            return Response(
                status_code=304,
                headers=preview_headers(
                    html=False, etag=entry.sha256, scripts=theme.allows_scripts
                ),
            )
        return Response(
            entry.data,
            media_type=entry.media_type,
            headers=preview_headers(html=False, etag=entry.sha256, scripts=theme.allows_scripts),
        )

    return router
