"""Isolated gateway serving only the active generated portfolio artifact."""

from __future__ import annotations

import json
import mimetypes
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from oryxenai.storage.preview import PreviewStorage, PreviewStorageError

_HOST_RE = re.compile(r"^[a-z2-7][a-z2-7-]{15,63}$")
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
    """Add the runtime mount prefix without changing the immutable artifact."""

    if not base_path or b"<head" not in data.lower():
        return data
    marker = f'<meta name="oryxenai-preview-base" content="{base_path}">'.encode()
    lowered = data.lower()
    head_index = lowered.find(b"<head")
    close_index = data.find(b">", head_index)
    if close_index < 0:
        return data
    return data[: close_index + 1] + marker + data[close_index + 1 :]


class PreviewGateway:
    def __init__(
        self,
        storage: PreviewStorage,
        *,
        parent_origin: str = "http://127.0.0.1:8000",
        embed_origins: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self.storage = storage
        self.embed_origins = _normalize_embed_origins(embed_origins, parent_origin)

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
            body = _inject_preview_base(body, f"/preview/{host}/")
        return Response(
            content=b"" if request.method == "HEAD" else body,
            media_type=str(entry.get("media_type", stored[0].content_type)),
            headers=headers,
        )


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
    )

    async def preview(request: Request) -> Response:
        return await gateway.serve(request)

    async def health_live(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "preview-gateway"})

    async def health_ready(_request: Request) -> JSONResponse:
        return JSONResponse(
            {"status": "ready", "service": "preview-gateway", "storage": "configured"}
        )

    return Starlette(
        routes=[
            Route("/health/live", health_live, methods=["GET"]),
            Route("/health/ready", health_ready, methods=["GET"]),
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
        if relative == "index.html":
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
    parent_origin = str(settings.code_generator_verification.preview_parent_origin)
    configured_origins = list(
        getattr(settings.code_generator_verification, "preview_embed_origins", []) or []
    )
    uvicorn.run(
        create_preview_app(
            storage,
            parent_origin=parent_origin,
            embed_origins=[*configured_origins, parent_origin],
            route_prefix=str(settings.code_generator_verification.preview_route_prefix),
        ),
        host=str(settings.code_generator_verification.preview_host),
        port=int(settings.code_generator_verification.preview_port),
        log_level="info",
    )


if __name__ == "__main__":
    main()
