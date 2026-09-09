"""Serve one exported Code Generator ``dist`` directory on loopback.

This viewer deliberately does not use ``SimpleHTTPRequestHandler``'s
conditional-cache path.  Each invocation is tied to one explicit export and
returns fresh HTML, while missing asset extensions remain real 404s instead of
being mistaken for SPA routes.
"""

from __future__ import annotations

import argparse
import mimetypes
import posixpath
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit

_ASSET_SUFFIXES = {
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".map",
    ".mjs",
    ".otf",
    ".png",
    ".svg",
    ".ttf",
    ".txt",
    ".webp",
    ".woff",
    ".woff2",
    ".xml",
}
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


def _export_asset_url(value: str) -> str:
    """Resolve a local Vite asset URL from any SPA route to export root."""

    stripped = value.strip()
    if not stripped or stripped.startswith(("#", "//", "data:", "blob:", "javascript:")):
        return value
    parsed = urlsplit(stripped)
    if parsed.scheme or parsed.netloc:
        return value
    path = parsed.path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    if path.startswith("../"):
        return value
    path = posixpath.normpath(path.lstrip("/"))
    if path in {"", ".", ".."} or path.startswith("../"):
        return value
    return urlunsplit(("", "", f"/{path}", parsed.query, parsed.fragment))


def _rewrite_export_html_urls(data: bytes) -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data

    def replace_attribute(match: re.Match[str]) -> str:
        return (
            f"{match.group('prefix')}{match.group('quote')}"
            f"{_export_asset_url(match.group('value'))}{match.group('quote')}"
        )

    def replace_srcset(match: re.Match[str]) -> str:
        candidates: list[str] = []
        for candidate in match.group("value").split(","):
            parts = candidate.strip().split(None, 1)
            if parts and parts[0]:
                candidates.append(
                    f"{_export_asset_url(parts[0])}"
                    + (f" {parts[1]}" if len(parts) > 1 else "")
                )
        rewritten = ", ".join(candidates)
        return f"{match.group('prefix')}{match.group('quote')}{rewritten}{match.group('quote')}"

    text = _HTML_ASSET_ATTRIBUTE_RE.sub(replace_attribute, text)
    text = _HTML_SRCSET_ATTRIBUTE_RE.sub(replace_srcset, text)
    return text.encode("utf-8")


class ExportHandler(SimpleHTTPRequestHandler):
    """Fresh, cache-resistant static/SPA handler for one immutable export."""

    server_version = "OryxenAIExportPreview/1"

    def __init__(self, *args: Any, directory: str, **kwargs: Any) -> None:
        self.export_root = Path(directory).resolve()
        super().__init__(*args, directory=str(self.export_root), **kwargs)

    def _requested_target(self) -> tuple[Path | None, bool]:
        raw_path = unquote(urlsplit(self.path).path or "/")
        relative = raw_path.lstrip("/")
        candidate = PurePosixPath(relative)
        if any(part in {"", ".", ".."} for part in candidate.parts if part != "."):
            return None, False
        target = (self.export_root / Path(*candidate.parts)).resolve()
        if target.is_file() and target.is_relative_to(self.export_root):
            return target, target.name == "index.html" and target.parent == self.export_root
        if candidate.suffix.casefold() in _ASSET_SUFFIXES:
            return None, False
        index = self.export_root / "index.html"
        return (index if index.is_file() else None), True

    def _send_file(self, target: Path) -> None:
        try:
            data = target.read_bytes()
        except OSError:
            self._send_not_found()
            return
        if target == self.export_root / "index.html":
            data = _rewrite_export_html_urls(data)
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        if self.command == "GET":
            self.wfile.write(data)

    def _send_not_found(self) -> None:
        data = b"Not found\n"
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.end_headers()
        if self.command == "GET":
            self.wfile.write(data)

    def do_GET(self) -> None:
        self._serve()

    def do_HEAD(self) -> None:
        self._serve()

    def _serve(self) -> None:
        target, _is_spa_route = self._requested_target()
        if target is None:
            self._send_not_found()
            return
        self._send_file(target)

    def log_message(self, format: str, *args: Any) -> None:
        super().log_message(format, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", type=Path, help="The exported portfolio dist directory")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    root = args.dist_dir.resolve()
    if not root.is_dir() or not (root / "index.html").is_file():
        parser.error(f"dist_dir must contain index.html: {root}")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), lambda *a, **kw: ExportHandler(*a, directory=str(root), **kw))
    print(f"Serving exported portfolio from: {root}")
    print(f"Local URL: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
