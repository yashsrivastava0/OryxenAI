"""Direct product and explicitly development-only web shells."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from oryxenai.auth.web import auth_csp

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_AUTH_STATIC_DIR = Path(__file__).resolve().parents[1] / "auth" / "static"

templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def _asset_version(filename: str) -> str:
    """Return a cheap dev-friendly cache key for a checked-in static asset."""
    try:
        return str((_STATIC_DIR / filename).stat().st_mtime_ns)
    except OSError:
        return "0"


def _auth_asset_version(filename: str) -> str:
    try:
        return str((_AUTH_STATIC_DIR / filename).stat().st_mtime_ns)
    except OSError:
        return "0"


def _resolve_product_entry() -> dict[str, Any] | None:
    """Resolve the built Preact bundle's hashed entry script and CSS.

    Reads the Vite manifest produced by ``frontend/`` (see
    docs/Frontend/05-implementation-blueprint-and-acceptance-matrix.md §16).
    Returns None when the bundle has not been built yet — the caller falls
    back to the legacy pipeline UI rather than serving a broken page.
    """
    manifest_path = _STATIC_DIR / "product" / ".vite" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    entry = manifest.get("src/main.tsx")
    if not isinstance(entry, dict) or "file" not in entry:
        return None
    return {
        "script": f"/static/product/{entry['file']}",
        "styles": [f"/static/product/{css}" for css in entry.get("css", [])],
    }


def _shell_context(settings: Any, *, pipeline_mode: str | None = None) -> dict[str, object]:
    # No model profiles, identity, session state, or provider credentials are
    # rendered into a public HTML shell.  The authenticated bootstrap may
    # request safe profile metadata only after an administrator check.
    effective_pipeline_mode = pipeline_mode or settings.auth.pipeline_mode
    return {
        "app_name": settings.app.name,
        "dev_ui": settings.is_dev_ui_enabled,
        "model_profiles": [],
        "auth_config": settings.auth_public_config,
        "pipeline_mode": effective_pipeline_mode,
        "tokens_css_version": _auth_asset_version("tokens.css"),
        "motion_css_version": _auth_asset_version("motion.css"),
        "living_draft_mark_css_version": _auth_asset_version("living-draft-mark.css"),
        "auth_css_version": _auth_asset_version("auth.css"),
        "auth_client_version": _auth_asset_version("auth-client.js"),
        "auth_runtime_version": _asset_version("auth-runtime.mjs"),
        "app_auth_bootstrap_version": _asset_version("app-auth-bootstrap.mjs"),
        "pipeline_bootstrap_version": _asset_version("pipeline-bootstrap.mjs"),
        "dev_auth_bootstrap_version": _asset_version("dev-auth-bootstrap.mjs"),
    }


def _development_auth_config(settings: Any) -> dict[str, object]:
    """Expose the isolated harness mode without changing product auth config."""
    config = dict(settings.auth_public_config)
    config["pipelineMode"] = settings.auth.development_harness_mode
    return config


def _set_shell_headers(response: Response, settings: Any) -> Response:
    response.headers["Content-Security-Policy"] = auth_csp(settings.supabase_url)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


def create_web_router(settings_override: Any | None = None) -> APIRouter:
    """Return the Preact product shell plus optional diagnostic routes."""
    router = APIRouter()
    dev_enabled = bool(getattr(settings_override, "is_dev_ui_enabled", False))
    fixture_enabled = bool(
        getattr(getattr(settings_override, "build_preparation", None), "fixture_enabled", False)
    )
    code_generator_dev_enabled = bool(
        getattr(getattr(settings_override, "code_generator_development", None), "enabled", False)
    )

    @router.get("/app", response_class=HTMLResponse)
    async def product_app(request: Request) -> Any:
        settings = request.app.state.settings
        if not settings.is_product_preact_shell_enabled:
            response = Response(
                "The product frontend is disabled.",
                status_code=503,
                media_type="text/plain",
            )
        else:
            product_entry = _resolve_product_entry()
            if product_entry is None:
                response = Response(
                    "The product frontend bundle is unavailable. Build the frontend before starting the app.",
                    status_code=503,
                    media_type="text/plain",
                )
            else:
                response = templates.TemplateResponse(
                    request=request,
                    name="product_shell.html",
                    context={**_shell_context(settings), "product_entry": product_entry},
                )
        return _set_shell_headers(response, settings)

    if dev_enabled and fixture_enabled:

        @router.get("/dev/build-preparation-fixture", response_class=HTMLResponse)
        @router.get("/build-preparation-fixture", response_class=HTMLResponse)
        async def build_preparation_fixture(request: Request) -> Any:
            settings = request.app.state.settings
            response = templates.TemplateResponse(
                request=request,
                name="build_preparation_fixture.html",
                context={
                    "app_name": settings.app.name,
                    "auth_config": _development_auth_config(settings),
                    "auth_client_version": _auth_asset_version("auth-client.js"),
                    "dev_auth_bootstrap_version": _asset_version("dev-auth-bootstrap.mjs"),
                    "fixture_enabled": True,
                },
            )
            return _set_shell_headers(response, settings)

        @router.get("/dev/build-preparation-fixture/progress", response_class=HTMLResponse)
        @router.get("/build-preparation-fixture/progress", response_class=HTMLResponse)
        async def build_preparation_fixture_progress(request: Request) -> Any:
            settings = request.app.state.settings
            response = templates.TemplateResponse(
                request=request,
                name="build_preparation_progress.html",
                context={
                    "app_name": settings.app.name,
                    "auth_config": _development_auth_config(settings),
                    "auth_client_version": _auth_asset_version("auth-client.js"),
                    "dev_auth_bootstrap_version": _asset_version("dev-auth-bootstrap.mjs"),
                    "fixture_enabled": True,
                },
            )
            return _set_shell_headers(response, settings)

    if dev_enabled and code_generator_dev_enabled:

        @router.get("/dev/code-generator-development", response_class=HTMLResponse)
        @router.get("/code-generator-development", response_class=HTMLResponse)
        async def code_generator_development(request: Request) -> Any:
            settings = request.app.state.settings
            response = templates.TemplateResponse(
                request=request,
                name="code_generator_development.html",
                context={
                    "app_name": settings.app.name,
                    "auth_config": _development_auth_config(settings),
                    "pipeline_mode": settings.auth.development_harness_mode,
                    "auth_client_version": _auth_asset_version("auth-client.js"),
                    "dev_auth_bootstrap_version": _asset_version("dev-auth-bootstrap.mjs"),
                    "detached_bootstrap_version": _asset_version(
                        "code-generator-development-detached-bootstrap.mjs"
                    ),
                    "css_version": _asset_version("code-generator-development.css"),
                    "js_version": _asset_version("code-generator-development.js"),
                },
            )
            return _set_shell_headers(response, settings)

        @router.get("/dev/code-generator-development/candidate-preview/{folder}")
        @router.get("/dev/code-generator-development/candidate-preview/{folder}/{path:path}")
        async def code_generator_candidate_preview(
            request: Request, folder: str, path: str = ""
        ) -> Any:
            """Serve a needs_attention/failed run's own already-built `dist/`
            straight from its export folder, unauthenticated -- this whole
            harness has no auth boundary in detached dev mode already. This
            is deliberately NOT the promoted `PreviewGateway`: it carries no
            verification claim. Every response is labeled as an unverified
            candidate so it can never be mistaken for a passed run."""
            from oryxenai.agents.code_generator.core.workspace import repository_root
            from oryxenai.preview.gateway import _headers, _inject_preview_base, _safe_path

            settings = request.app.state.settings
            config = settings.code_generator_verification
            export_root = Path(str(getattr(config, "export_root", "output/code-gen-output")))
            if not export_root.is_absolute():
                export_root = repository_root() / export_root
            try:
                safe_folder = _safe_path(folder)
            except ValueError:
                return Response("Not found", status_code=404)
            if "/" in safe_folder:
                return Response("Not found", status_code=404)
            dist_dir = (export_root / safe_folder / "dist").resolve()
            try:
                dist_dir.relative_to(export_root.resolve())
            except ValueError:
                return Response("Not found", status_code=404)
            if not dist_dir.is_dir():
                return Response("Not found", status_code=404)
            try:
                relative = _safe_path(path) if path else "index.html"
            except ValueError:
                return Response("Not found", status_code=404)
            target = (dist_dir / relative).resolve()
            if not target.is_relative_to(dist_dir) or not target.is_file():
                target = dist_dir / "index.html"
            if not target.is_file():
                return Response("Not found", status_code=404)
            data = target.read_bytes()
            is_index = target.relative_to(dist_dir).as_posix() == "index.html"
            mount_prefix = f"/dev/code-generator-development/candidate-preview/{safe_folder}/"
            if is_index:
                data = _inject_preview_base(data, mount_prefix)
            return Response(
                content=b"" if request.method == "HEAD" else data,
                media_type=mimetypes.guess_type(target.name)[0] or "application/octet-stream",
                headers=_headers(embed_origins=("'self'",), asset=not is_index),
            )

    router.mount("/static", app=StaticFiles(directory=str(_STATIC_DIR)), name="static")
    return router
