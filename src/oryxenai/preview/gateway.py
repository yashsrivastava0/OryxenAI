"""Isolated gateway serving only the active generated portfolio artifact."""

from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import posixpath
import re
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from oryxenai.storage.preview import PreviewStorage, PreviewStorageError

_HOST_RE = re.compile(r"^[a-z2-7][a-z2-7-]{15,63}$")
_CAPABILITY_RE = re.compile(r"^[A-Za-z0-9_-]{24,160}$")
_IDENTITY_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._-]{1,160}$")
_HTML_ASSET_ATTRIBUTE_RE = re.compile(
    r"(?P<prefix><(?:script|link|img|source|video|audio|track)\b[^>]*?\s"
    r"(?:src|href)\s*=\s*)(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)
_HTML_SRCSET_ATTRIBUTE_RE = re.compile(
    r"(?P<prefix><(?:img|source|video)\b[^>]*?\ssrcset\s*=\s*)"
    r"(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)
_ASSET_SUFFIXES = {
    ".js",
    ".mjs",
    ".css",
    ".json",
    ".map",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".txt",
    ".xml",
}
_PREVIEW_BRIDGE_PATH = "__oryxenai/preview-bridge.js"
_PREVIEW_BRIDGE_JS = b"""(() => {
  const VERSION = "preview-bridge-v1";
  if (window.parent === window || window.__ORYXENAI_PREVIEW_BRIDGE__) return;
  window.__ORYXENAI_PREVIEW_BRIDGE__ = true;
  let parentOrigin = "";
  const route = () => window.location.pathname;
  const announce = (type) => {
    if (!parentOrigin) return;
    window.parent.postMessage(
      { type, version: VERSION, path: route(), route: route(), title: document.title },
      parentOrigin,
    );
  };
  window.addEventListener("message", (event) => {
    if (event.source !== window.parent || !event.data || event.data.type !== "preview:init" || event.data.version !== VERSION) return;
    parentOrigin = event.origin;
    announce("preview:ready");
  });
  window.addEventListener("popstate", () => announce("preview:route"));
})();
"""


def _safe_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip("/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or ".." in path.parts
        or any(ord(char) < 32 for char in normalized)
    ):
        raise ValueError("unsafe preview path")
    return path.as_posix()


def _normalize_embed_origins(
    origins: list[str] | tuple[str, ...] | None,
    parent_origin: str,
) -> tuple[str, ...]:
    values = list(origins) if origins else [parent_origin]
    result: list[str] = []
    for value in values:
        origin = str(value or "").strip().rstrip("/")
        if not origin:
            continue
        if origin == "*":
            raise ValueError("wildcard preview embed origins are not allowed")
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("preview embed origins must be exact HTTP(S) origins")
        if origin not in result:
            result.append(origin)
    if not result:
        raise ValueError("at least one exact preview embed origin is required")
    return tuple(result)


def _headers(*, embed_origins: tuple[str, ...], asset: bool) -> dict[str, str]:
    return {
        "Content-Security-Policy": (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
            "font-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; "
            "form-action 'none'; worker-src 'none'; manifest-src 'none'; "
            f"frame-ancestors {' '.join(embed_origins)}"
        ),
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
        "Cross-Origin-Resource-Policy": "cross-origin",
        "X-Robots-Tag": "noindex, nofollow, noarchive",
        "Cache-Control": "public, max-age=31536000, immutable" if asset else "no-store",
    }


def _inject_preview_base(data: bytes, base_path: str) -> bytes:
    """Add runtime mount metadata and the deterministic browser bridge.

    The stored artifact remains immutable; both additions are response-only
    gateway behavior. The bridge is external rather than inline so the
    artifact keeps the strict ``script-src 'self'`` policy.
    """

    if not base_path or b"<head" not in data.lower():
        return data
    marker = f'<meta name="oryxenai-preview-base" content="{base_path}">'.encode()
    bridge_src = f"{base_path.rstrip('/')}/{_PREVIEW_BRIDGE_PATH}".encode()
    bridge_marker = b'<script src="' + bridge_src + b'" defer></script>'
    injection = (b"" if marker in data else marker) + (
        b"" if bridge_marker in data else bridge_marker
    )
    if not injection:
        return data
    lowered = data.lower()
    head_index = lowered.find(b"<head")
    close_index = data.find(b">", head_index)
    if close_index < 0:
        return data
    return data[: close_index + 1] + injection + data[close_index + 1 :]


def _preview_bridge_response(*, method: str, embed_origins: tuple[str, ...]) -> Response:
    return Response(
        content=b"" if method == "HEAD" else _PREVIEW_BRIDGE_JS,
        media_type="text/javascript",
        headers=_headers(embed_origins=embed_origins, asset=True),
    )


def _preview_asset_url(value: str, mount_path: str) -> str:
    """Resolve one local HTML asset reference against the preview mount.

    Vite emits relative entrypoint references.  A route request such as
    ``/preview/<host>/about`` would otherwise resolve ``./assets/app.js``
    under ``/about/assets`` in the browser.  Only local asset references are
    rewritten; external/data URLs and fragments retain their original value.
    """

    from urllib.parse import urlsplit, urlunsplit

    stripped = value.strip()
    if not stripped or stripped.startswith(("#", "//", "data:", "blob:", "javascript:")):
        return value
    parsed = urlsplit(stripped)
    if parsed.scheme or parsed.netloc:
        return value
    path = parsed.path.replace("\\", "/")
    if not path:
        return value
    while path.startswith("./"):
        path = path[2:]
    if path.startswith("../"):
        # The artifact manifest rejects traversal; leave malformed input
        # untouched so the existing closure/404 checks report it precisely.
        return value
    path = posixpath.normpath(path.lstrip("/"))
    if path in {"", "."} or path == ".." or path.startswith("../"):
        return value
    mount = "/" + mount_path.strip("/") + "/" if mount_path.strip("/") else "/"
    rewritten = f"{mount.rstrip('/')}/{path}" if mount != "/" else f"/{path}"
    return urlunsplit(("", "", rewritten, parsed.query, parsed.fragment))


def _rewrite_preview_html_urls(data: bytes, mount_path: str) -> bytes:
    """Rewrite local script/style/media URLs in served HTML only.

    Stored immutable artifact bytes and their manifest hashes are never
    changed.  The gateway transforms the response copy so nested SPA route
    requests consistently fetch assets from the artifact root.
    """

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data

    def replace_attribute(match: re.Match[str]) -> str:
        return (
            f"{match.group('prefix')}{match.group('quote')}"
            f"{_preview_asset_url(match.group('value'), mount_path)}"
            f"{match.group('quote')}"
        )

    def replace_srcset(match: re.Match[str]) -> str:
        rewritten = ", ".join(
            (
                f"{_preview_asset_url(parts[0], mount_path)}"
                + (f" {parts[1]}" if len(parts) > 1 else "")
            )
            for candidate in match.group("value").split(",")
            for parts in [candidate.strip().split(None, 1)]
            if parts and parts[0]
        )
        return f"{match.group('prefix')}{match.group('quote')}{rewritten}{match.group('quote')}"

    text = _HTML_ASSET_ATTRIBUTE_RE.sub(replace_attribute, text)
    text = _HTML_SRCSET_ATTRIBUTE_RE.sub(replace_srcset, text)
    return text.encode("utf-8")


class PreviewGateway:
    def __init__(
        self,
        storage: PreviewStorage,
        *,
        parent_origin: str = "http://127.0.0.1:8000",
        embed_origins: list[str] | tuple[str, ...] | None = None,
        route_prefix: str = "/preview",
    ) -> None:
        self.storage = storage
        self.embed_origins = _normalize_embed_origins(embed_origins, parent_origin)
        self.route_prefix = "/" + route_prefix.strip("/") if route_prefix.strip("/") else ""

    async def serve(self, request: Request) -> Response:
        if request.method not in {"GET", "HEAD"}:
            return Response("Method not allowed", status_code=405, headers={"Allow": "GET, HEAD"})
        host = str(request.path_params.get("host", ""))
        if not _HOST_RE.fullmatch(host):
            return JSONResponse({"status": "unavailable"}, status_code=404)
        raw_path = str(request.path_params.get("path", ""))
        try:
            requested = _safe_path(raw_path) if raw_path else "index.html"
        except ValueError:
            return Response("Not found", status_code=404)
        pointer_key = f"preview/hosts/{host}/active.json"
        try:
            pointer_object = await self.storage.get(pointer_key)
        except PreviewStorageError:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        if pointer_object is None:
            return JSONResponse({"status": "unavailable"}, status_code=404)
        try:
            pointer = json.loads(pointer_object[1].decode("utf-8"))
            receipt_key = str(pointer["receipt_key"])
            candidate_prefix = str(pointer["candidate_prefix"])
            entries = {
                str(item["path"]): item
                for item in pointer["manifest"]["entries"]
                if isinstance(item, dict)
            }
            receipt_object = await self.storage.get(receipt_key)
            if (
                receipt_object is None
                or str(pointer.get("receipt_hash", "")) != receipt_object[0].sha256
            ):
                raise ValueError("active receipt mismatch")
            receipt = json.loads(receipt_object[1].decode("utf-8"))
            if pointer.get("run_id") is not None and str(receipt.get("run_id", "")) != str(
                pointer.get("run_id", "")
            ):
                raise ValueError("active run mismatch")
            if (
                str(receipt.get("build_hash", "")) != str(pointer.get("build_hash", ""))
                or str(receipt.get("candidate_id", "")) != str(pointer.get("candidate_id", ""))
                or str(receipt.get("candidate_identity_hash", ""))
                != str(pointer.get("candidate_identity_hash", ""))
            ):
                raise ValueError("active build mismatch")
        except (
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            PreviewStorageError,
        ):
            return JSONResponse({"status": "unavailable"}, status_code=503)
        if requested == _PREVIEW_BRIDGE_PATH:
            return _preview_bridge_response(method=request.method, embed_origins=self.embed_origins)
        asset = requested in entries
        if not asset:
            if (
                requested != "index.html"
                and PurePosixPath(requested).suffix.casefold() in _ASSET_SUFFIXES
            ):
                return Response(
                    "Not found",
                    status_code=404,
                    headers=_headers(embed_origins=self.embed_origins, asset=True),
                )
            requested = "index.html"
        entry = entries.get(requested)
        if entry is None:
            return Response("Not found", status_code=404)
        try:
            stored = await self.storage.get(f"{candidate_prefix}/dist/{requested}")
        except PreviewStorageError:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        if stored is None or stored[0].sha256 != str(entry.get("sha256", "")):
            return JSONResponse({"status": "unavailable"}, status_code=503)
        # index.html is an active pointer response, never an immutable asset.
        headers = _headers(
            embed_origins=self.embed_origins,
            asset=requested != "index.html",
        )
        body = stored[1]
        if requested == "index.html":
            body = _rewrite_preview_html_urls(body, f"{self.route_prefix}/{host}/")
            body = _inject_preview_base(body, f"{self.route_prefix}/{host}/")
        return Response(
            content=b"" if request.method == "HEAD" else body,
            media_type=str(entry.get("media_type", stored[0].content_type)),
            headers=headers,
        )

    async def serve_candidate(self, request: Request) -> Response:
        """Serve one buildable candidate through an opaque capability URL."""

        if request.method not in {"GET", "HEAD"}:
            return Response("Method not allowed", status_code=405, headers={"Allow": "GET, HEAD"})
        token = str(request.path_params.get("token", ""))
        candidate_id = str(request.path_params.get("candidate_id", ""))
        build_hash = str(request.path_params.get("build_hash", ""))
        if (
            not _CAPABILITY_RE.fullmatch(token)
            or not _IDENTITY_SEGMENT_RE.fullmatch(candidate_id)
            or not re.fullmatch(r"[a-f0-9]{32,128}", build_hash)
        ):
            return Response("Not found", status_code=404)
        raw_path = str(request.path_params.get("path", ""))
        try:
            requested = _safe_path(raw_path) if raw_path else "index.html"
        except ValueError:
            return Response("Not found", status_code=404)
        prefix = f"preview/candidates/{candidate_id}/{build_hash}"
        try:
            stored_manifest = await self.storage.get(f"{prefix}/manifest.json")
        except PreviewStorageError:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        if stored_manifest is None:
            return Response("Not found", status_code=404)
        try:
            payload = json.loads(stored_manifest[1].decode("utf-8"))
            if (
                payload.get("candidate_id") != candidate_id
                or payload.get("build_hash") != build_hash
            ):
                return Response("Not found", status_code=404)
            if not hmac.compare_digest(
                str(payload.get("token_sha256", "")),
                hashlib.sha256(token.encode("utf-8")).hexdigest(),
            ):
                return Response("Not found", status_code=404)
            expires_at = datetime.fromisoformat(str(payload["expires_at"]).replace("Z", "+00:00"))
            if expires_at <= datetime.now(UTC):
                return Response("Not found", status_code=404)
            manifest = payload["manifest"]
            entries = {
                str(item["path"]): item for item in manifest["entries"] if isinstance(item, dict)
            }
        except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return JSONResponse({"status": "unavailable"}, status_code=503)
        if requested == _PREVIEW_BRIDGE_PATH:
            return _preview_bridge_response(method=request.method, embed_origins=self.embed_origins)
        if requested not in entries:
            if (
                requested != "index.html"
                and PurePosixPath(requested).suffix.casefold() in _ASSET_SUFFIXES
            ):
                return Response("Not found", status_code=404)
            requested = "index.html"
        entry = entries.get(requested)
        if entry is None:
            return Response("Not found", status_code=404)
        try:
            stored = await self.storage.get(f"{prefix}/dist/{requested}")
        except PreviewStorageError:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        if stored is None or stored[0].sha256 != str(entry.get("sha256", "")):
            return JSONResponse({"status": "unavailable"}, status_code=503)
        body = stored[1]
        if requested == "index.html":
            mount = self._candidate_mount(token, candidate_id, build_hash)
            body = _rewrite_preview_html_urls(body, mount)
            body = _inject_preview_base(body, mount)
        return Response(
            content=b"" if request.method == "HEAD" else body,
            media_type=str(entry.get("media_type", stored[0].content_type)),
            headers=_headers(
                embed_origins=self.embed_origins,
                asset=requested != "index.html",
            ),
        )

    def _candidate_mount(self, token: str, candidate_id: str, build_hash: str) -> str:
        return f"{self.route_prefix}/candidate/{token}/{candidate_id}/{build_hash}/"


def create_preview_app(
    storage: PreviewStorage,
    *,
    parent_origin: str = "http://127.0.0.1:8000",
    embed_origins: list[str] | tuple[str, ...] | None = None,
    route_prefix: str = "/preview",
) -> Starlette:
    gateway = PreviewGateway(
        storage,
        parent_origin=parent_origin,
        embed_origins=embed_origins,
        route_prefix=route_prefix,
    )

    async def preview(request: Request) -> Response:
        return await gateway.serve(request)

    async def candidate(request: Request) -> Response:
        return await gateway.serve_candidate(request)

    async def health_live(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "preview-gateway"})

    async def health_ready(_request: Request) -> JSONResponse:
        try:
            # A harmless missing-object HEAD proves that the configured
            # backend is reachable without mutating shared preview state.
            await gateway.storage.head("preview/health/readiness")
        except PreviewStorageError:
            return JSONResponse(
                {
                    "status": "unavailable",
                    "service": "preview-gateway",
                    "storage": "unreadable",
                },
                status_code=503,
            )
        return JSONResponse(
            {"status": "ready", "service": "preview-gateway", "storage": "readable"}
        )

    return Starlette(
        routes=[
            Route("/health/live", health_live, methods=["GET"]),
            Route("/health/ready", health_ready, methods=["GET"]),
            Route(
                f"{route_prefix}/candidate/{{token}}/{{candidate_id}}/{{build_hash}}/{{path:path}}",
                candidate,
                methods=["GET", "HEAD"],
            ),
            Route(f"{route_prefix}/{{host}}/{{path:path}}", preview, methods=["GET", "HEAD"]),
        ]
    )


class CandidateGateway:
    """Protected local gateway used only while a candidate is being verified."""

    def __init__(
        self,
        dist_dir: Path,
        *,
        token: str,
        parent_origin: str = "http://127.0.0.1:8000",
        embed_origins: list[str] | tuple[str, ...] | None = None,
        mount_prefix: str = "/",
    ) -> None:
        self.dist_dir = dist_dir.resolve()
        self.token = token
        self.embed_origins = _normalize_embed_origins(embed_origins, parent_origin)
        self.mount_prefix = "/" + mount_prefix.strip("/") + "/" if mount_prefix.strip("/") else "/"

    async def serve(self, request: Request) -> Response:
        if request.method not in {"GET", "HEAD"}:
            return Response("Method not allowed", status_code=405, headers={"Allow": "GET, HEAD"})
        if request.headers.get("x-preview-verify-token", "") != self.token:
            return Response(
                "Not found",
                status_code=404,
                headers={"X-OryxenAI-Candidate-404": "token"},
            )
        raw_path = str(request.path_params.get("path", ""))
        if self.mount_prefix != "/":
            prefix = self.mount_prefix.strip("/")
            if raw_path == prefix:
                raw_path = ""
            elif raw_path.startswith(prefix + "/"):
                raw_path = raw_path[len(prefix) + 1 :]
            else:
                return Response(
                    "Not found",
                    status_code=404,
                    headers={"X-OryxenAI-Candidate-404": "mount"},
                )
        try:
            relative = _safe_path(raw_path) if raw_path else "index.html"
        except ValueError:
            return Response(
                "Not found",
                status_code=404,
                headers={"X-OryxenAI-Candidate-404": "path"},
            )
        if relative == _PREVIEW_BRIDGE_PATH:
            return _preview_bridge_response(method=request.method, embed_origins=self.embed_origins)
        target = (self.dist_dir / relative).resolve()
        if not target.is_relative_to(self.dist_dir) or not target.is_file():
            if PurePosixPath(relative).suffix.casefold() in _ASSET_SUFFIXES:
                return Response(
                    "Not found",
                    status_code=404,
                    headers={"X-OryxenAI-Candidate-404": "artifact"},
                )
            target = self.dist_dir / "index.html"
        if not target.is_file():
            return Response(
                "Not found",
                status_code=404,
                headers={"X-OryxenAI-Candidate-404": "artifact"},
            )
        data = target.read_bytes()
        if target == self.dist_dir / "index.html":
            data = _rewrite_preview_html_urls(data, self.mount_prefix)
            data = _inject_preview_base(data, self.mount_prefix)
        return Response(
            content=b"" if request.method == "HEAD" else data,
            media_type=mimetypes.guess_type(target.name)[0] or "application/octet-stream",
            headers=_headers(
                embed_origins=self.embed_origins,
                asset=target.relative_to(self.dist_dir).as_posix() != "index.html",
            ),
        )


def create_candidate_app(
    dist_dir: Path,
    *,
    token: str,
    parent_origin: str = "http://127.0.0.1:8000",
    embed_origins: list[str] | tuple[str, ...] | None = None,
    mount_prefix: str = "/",
) -> Starlette:
    gateway = CandidateGateway(
        dist_dir,
        token=token,
        parent_origin=parent_origin,
        embed_origins=embed_origins,
        mount_prefix=mount_prefix,
    )

    async def candidate(request: Request) -> Response:
        return await gateway.serve(request)

    return Starlette(routes=[Route("/{path:path}", candidate, methods=["GET", "HEAD"])])


def main() -> None:
    import uvicorn

    from oryxenai.core.settings import get_settings
    from oryxenai.storage.preview import create_preview_storage

    settings = get_settings()
    storage = create_preview_storage(settings)
    auth_config = settings.auth
    gateway_config = settings.preview_gateway
    parent_origin = str(auth_config.primary_origin)
    configured_origins = list(getattr(auth_config, "allowed_origins", []) or [])
    uvicorn.run(
        create_preview_app(
            storage,
            parent_origin=parent_origin,
            embed_origins=[*configured_origins, parent_origin],
            route_prefix=str(gateway_config.route_prefix),
        ),
        host=str(gateway_config.host),
        port=int(gateway_config.port),
        log_level="info",
    )


if __name__ == "__main__":
    main()
