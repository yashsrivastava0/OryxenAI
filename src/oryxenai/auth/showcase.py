"""Fixed fictional demo assets, never backed by owner sessions or model calls."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, Response

from oryxenai.agents.code_generator.serving import preview_headers
from oryxenai.themes import media_type_for

SHOWCASE_ROOT = Path(__file__).resolve().parent / "showcase"


@lru_cache(maxsize=1)
def showcase_manifest() -> dict[str, Any]:
    """The committed preparation output is also the public file allowlist."""
    value: dict[str, Any] = json.loads((SHOWCASE_ROOT / "manifest.json").read_text())
    return value


def create_showcase_router() -> APIRouter:
    router = APIRouter()

    @router.get("/showcase-samples/{sample_id}/{asset_path:path}")
    async def sample_asset(request: Request, sample_id: str, asset_path: str) -> Response:
        entry = next((s for s in showcase_manifest()["samples"] if s["id"] == sample_id), None)
        relative = asset_path or "index.html"
        if entry is None or relative not in entry["files"]:
            return Response(status_code=404, headers=preview_headers(html=True))
        root = (SHOWCASE_ROOT / sample_id).resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            return Response(status_code=404, headers=preview_headers(html=True))
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry["files"][relative]:
            return Response(status_code=503, headers=preview_headers(html=True))
        html = relative.endswith(".html")
        headers = preview_headers(html=html, etag=digest, scripts=True)
        if not html and request.headers.get("if-none-match") == headers.get("ETag"):
            return Response(status_code=304, headers=headers)
        extra_types = {".webp": "image/webp", ".mjs": "text/javascript"}
        media_type = extra_types.get(path.suffix, media_type_for(relative))
        return Response(data, media_type=media_type, headers=headers)

    return router
