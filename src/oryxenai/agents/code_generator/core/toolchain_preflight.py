"""Disposable, model-free Code Generator toolchain preflight."""

from __future__ import annotations

import contextlib
import hashlib
import json
import platform
import secrets
import shutil
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.core import fs_safe
from oryxenai.agents.code_generator.core.build_runner import run_clean_build
from oryxenai.agents.code_generator.core.process_runner import (
    ProcessRunnerError,
    resolve_npm_executable,
    run_command,
)
from oryxenai.agents.code_generator.core.worker_readiness import (
    capability_config_identity_hash,
    capability_toolchain_identity_hash,
    verification_is_enabled,
)
from oryxenai.agents.code_generator.core.workspace import repository_root

_PREFLIGHT_CACHE: dict[str, dict[str, Any]] = {}


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (repository_root() / path).resolve()


def _hash_files(root: Path, names: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for name in names:
        path = (root / name).resolve()
        if not path.is_file() or not path.is_relative_to(root.resolve()):
            digest.update(f"missing:{name}".encode())
            continue
        digest.update(name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _hash_dependency_pins(settings: Any, scaffold: Path) -> str:
    package_json: dict[str, Any] = {}
    try:
        raw = json.loads((scaffold / "package.json").read_text(encoding="utf-8"))
        package_json = raw if isinstance(raw, dict) else {}
    except (OSError, UnicodeDecodeError, ValueError):
        pass
    configured = getattr(settings.code_generator_dependencies, "supported_packages", {}) or {}
    payload = {
        "scaffold_dependencies": package_json.get("dependencies", {}),
        "scaffold_dev_dependencies": package_json.get("devDependencies", {}),
        "supported_packages": configured,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _proof_ttl(settings: Any) -> int:
    verification = settings.code_generator_verification
    return max(30, int(getattr(verification, "capability_proof_ttl_seconds", 900) or 900))


def _cache_key(settings: Any, *, require_brief_dependency_paths: bool = True) -> str:
    payload = {
        "config_identity_sha256": capability_config_identity_hash(settings),
        "scaffold_hash": _hash_files(
            _resolve(str(settings.code_generator_generation.scaffold_root))
            / str(settings.code_generator_generation.scaffold_profile),
            (
                "package.json",
                "package-lock.json",
                "vite.config.ts",
                "tsconfig.app.json",
                "tsconfig.node.json",
            ),
        ),
        "require_brief_dependency_paths": require_brief_dependency_paths,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def cache_toolchain_preflight(settings: Any, result: dict[str, Any]) -> dict[str, Any]:
    """Publish one safe receipt for later readiness/create requests."""

    require_briefs = bool(result.get("requires_brief_dependency_paths", True))
    key = _cache_key(settings, require_brief_dependency_paths=require_briefs)
    stored = dict(result)
    checked_at = str(stored.setdefault("checked_at", datetime.now(UTC).isoformat()))
    try:
        expires_at = datetime.fromisoformat(checked_at) + timedelta(seconds=_proof_ttl(settings))
    except (TypeError, ValueError):
        expires_at = datetime.now(UTC)
    stored.setdefault("expires_at", expires_at.isoformat())
    stored["config_identity_sha256"] = capability_config_identity_hash(settings)
    stored["cache_key"] = key
    _PREFLIGHT_CACHE[key] = stored
    return stored


def toolchain_preflight_status(
    settings: Any, *, require_brief_dependency_paths: bool = True
) -> dict[str, Any]:
    """Read the latest proof for the current scaffold/toolchain identity."""

    key = _cache_key(settings, require_brief_dependency_paths=require_brief_dependency_paths)
    result = _PREFLIGHT_CACHE.get(key)
    if result is None:
        return {
            "schema_version": "code-generator-toolchain-preflight-v1",
            "status": "not_run",
            "ready": False,
            "model_calls": 0,
            "checks": {},
            "facts": {},
            "diagnostics": [],
        }
    checked_at = str(result.get("checked_at", ""))
    try:
        expires_at = datetime.fromisoformat(str(result.get("expires_at", "")))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        try:
            expires_at = datetime.fromisoformat(checked_at) + timedelta(
                seconds=_proof_ttl(settings)
            )
        except (TypeError, ValueError):
            expires_at = datetime.min.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        _PREFLIGHT_CACHE.pop(key, None)
        return {
            "schema_version": "code-generator-toolchain-preflight-v1",
            "status": "expired",
            "ready": False,
            "model_calls": 0,
            "checks": {},
            "facts": {},
            "diagnostics": [],
        }
    return dict(result)


def clear_toolchain_preflight_cache() -> None:
    _PREFLIGHT_CACHE.clear()


async def _version(executable: str, *, cwd: Path, timeout: float) -> str:
    try:
        result = await run_command(
            [executable, "--version"],
            cwd=cwd,
            timeout_seconds=timeout,
            max_output_bytes=512,
        )
    except ProcessRunnerError:
        return ""
    if result.timed_out or result.returncode != 0:
        return ""
    return " ".join(result.combined_output.split())[:120]


async def _browser_smoke(settings: Any) -> dict[str, Any]:
    verification = settings.code_generator_verification
    try:
        from playwright.async_api import async_playwright
    except Exception:
        return {"ready": False, "code": "BROWSER_IMPORT_FAILED"}
    browser = None
    try:
        async with async_playwright() as playwright:
            browser_type = getattr(
                playwright, str(getattr(verification, "browser_name", "chromium"))
            )
            launch: dict[str, Any] = {
                "headless": bool(getattr(verification, "browser_headless", True)),
                "timeout": int(getattr(verification, "browser_timeout_ms", 15000)),
            }
            executable = str(getattr(verification, "browser_executable", "") or "").strip()
            if executable:
                launch["executable_path"] = executable
            browser = await browser_type.launch(**launch)
            page = await browser.new_page(viewport={"width": 390, "height": 844})
            await page.set_content(
                "<main><h1>OryxenAI preflight</h1><button type='button'>ready</button></main>",
                wait_until="load",
            )
            await page.locator("main h1").wait_for(state="visible")
            return {"ready": True, "page_probe": "visible_dom"}
    except Exception as exc:
        return {"ready": False, "code": "BROWSER_LAUNCH_FAILED", "error": str(exc)[:300]}
    finally:
        if browser is not None:
            with contextlib.suppress(Exception):
                await browser.close()


def _write_probe(path: Path) -> bool:
    probe = path / f".codegen-capability-{secrets.token_hex(12)}"
    try:
        path.mkdir(parents=True, exist_ok=True)
        marker = secrets.token_hex(16)
        probe.write_text(marker, encoding="utf-8")
        matched = probe.read_text(encoding="utf-8") == marker
        probe.unlink()
        return matched
    except OSError:
        with contextlib.suppress(OSError):
            probe.unlink()
        return False


async def _preview_delivery_smoke(settings: Any) -> dict[str, bool]:
    """Prove configured storage readback and gateway serving without a run."""

    from urllib.parse import quote

    import httpx

    from oryxenai.preview.promotion import preview_urls
    from oryxenai.storage.preview import PreviewStorageError, create_preview_storage

    verification = settings.code_generator_verification
    storage = create_preview_storage(settings)
    base_url = preview_urls(verification)[1]
    marker = f"oryxenai-capability-proof-{secrets.token_hex(16)}"
    body = (
        f"<!doctype html><html><head><title>preflight</title></head><body>{marker}</body></html>"
    ).encode()
    digest = hashlib.sha256(body).hexdigest()
    import base64

    host = base64.b32encode(secrets.token_bytes(20)).decode("ascii").lower().rstrip("=")
    candidate_id = secrets.token_hex(16)
    build_hash = digest
    prefix = f"preview/capability-proof/{candidate_id}/{build_hash}"
    index_key = f"{prefix}/dist/index.html"
    receipt_key = f"preview/capability-proof/{candidate_id}/receipt.json"
    pointer_key = f"preview/hosts/{host}/active.json"
    receipt = {
        "run_id": "worker-capability-proof",
        "candidate_id": candidate_id,
        "candidate_identity_hash": digest,
        "build_hash": build_hash,
    }
    receipt_data = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    pointer = {
        "run_id": receipt["run_id"],
        "candidate_id": candidate_id,
        "candidate_identity_hash": digest,
        "build_hash": build_hash,
        "candidate_prefix": prefix,
        "manifest": {
            "entries": [
                {
                    "path": "index.html",
                    "sha256": digest,
                    "size_bytes": len(body),
                    "media_type": "text/html",
                }
            ]
        },
        "receipt_key": receipt_key,
        "receipt_hash": hashlib.sha256(receipt_data).hexdigest(),
    }
    pointer_data = (json.dumps(pointer, sort_keys=True, separators=(",", ":")) + "\n").encode()
    storage_ok = False
    gateway_ok = False
    pointer_written = False
    try:
        await storage.put_immutable(key=index_key, data=body, content_type="text/html")
        await storage.put_immutable(
            key=receipt_key, data=receipt_data, content_type="application/json"
        )
        stored = await storage.get(index_key)
        stored_receipt = await storage.get(receipt_key)
        storage_ok = bool(
            stored is not None
            and stored[0].sha256 == digest
            and stored[1] == body
            and stored_receipt is not None
            and stored_receipt[1] == receipt_data
        )
        if not storage_ok:
            return {"storage": False, "gateway": False}
        await storage.put_conditional(
            key=pointer_key,
            data=pointer_data,
            content_type="application/json",
            expected_etag=None,
        )
        pointer_written = True
        timeout = max(
            1.0,
            min(float(getattr(verification, "runtime_timeout_ms", 15000)) / 1000, 15.0),
        )
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.get(f"{base_url.rstrip('/')}/{quote(host, safe='')}/")
        gateway_ok = response.status_code == 200 and marker.encode() in response.content
    except (PreviewStorageError, httpx.HTTPError, OSError, ValueError):
        gateway_ok = False
    finally:
        cleanup_ok = True
        for key in ((pointer_key,) if pointer_written else ()) + (receipt_key, index_key):
            try:
                await storage.delete(key)
            except Exception:
                cleanup_ok = False
        if not cleanup_ok:
            storage_ok = False
            gateway_ok = False
    return {"storage": storage_ok, "gateway": gateway_ok}


async def run_toolchain_preflight(
    settings: Any, *, require_brief_dependency_paths: bool = True
) -> dict[str, Any]:
    """Prove install, TypeScript, Vite, browser, and gateway readiness.

    The function creates a disposable copy of the configured scaffold and
    invokes the same clean-build path used by production verification. It does
    not load a brief, call a model, or mutate a generation run.
    """

    if not verification_is_enabled(settings):
        return cache_toolchain_preflight(
            settings,
            {
                "schema_version": "code-generator-toolchain-preflight-v1",
                "checked_at": datetime.now(UTC).isoformat(),
                "status": "blocked",
                "ready": False,
                "requires_brief_dependency_paths": require_brief_dependency_paths,
                "model_calls": 0,
                "checks": {"verification_enabled": False},
                "facts": {},
                "diagnostics": [
                    {
                        "code": "CODE_GENERATOR_VERIFICATION_DISABLED",
                        "message": "Code Generator verification is disabled by configuration.",
                    }
                ],
            },
        )

    config = settings.code_generator_generation
    scaffold_root = _resolve(str(config.scaffold_root))
    scaffold = (scaffold_root / str(config.scaffold_profile)).resolve()
    npm = resolve_npm_executable(settings)
    facts: dict[str, Any] = {
        "platform": platform.system().casefold(),
        "architecture": platform.machine().casefold(),
        "scaffold_profile": str(config.scaffold_profile),
        "scaffold_hash": _hash_files(
            scaffold,
            (
                "package.json",
                "package-lock.json",
                "vite.config.ts",
                "tsconfig.app.json",
                "tsconfig.node.json",
            ),
        ),
        "dependency_pins_hash": _hash_dependency_pins(settings, scaffold),
        "npm_configured": bool(npm),
        "workspace_root": str(_resolve(str(config.workspace_root)).relative_to(repository_root()))
        if _resolve(str(config.workspace_root)).is_relative_to(repository_root())
        else "external",
    }
    checks: dict[str, Any] = {
        "scaffold": scaffold.is_dir(),
        "node": False,
        "npm": bool(npm),
        "workspace_writable": False,
        "cache_writable": False,
        "install": False,
        "typecheck": False,
        "build": False,
        "browser": False,
        "preview_gateway": False,
        "checkpoint_writable": False,
        "artifact_writable": False,
        "preview_writable": False,
        "preview_storage_readback": False,
        "preview_gateway_readback": False,
        "brief_dependency_paths": not require_brief_dependency_paths,
    }
    diagnostics: list[dict[str, Any]] = []
    workspace_root = _resolve(str(config.workspace_root))
    if require_brief_dependency_paths:
        try:
            from oryxenai.agents.code_generator.core.development_input import (
                DevelopmentInputAdapter,
            )

            pack_infos = DevelopmentInputAdapter(settings).list_build_preparation_packs()
            facts["build_preparation_packs"] = [
                {
                    "pack_dir": Path(str(item.get("pack_dir", ""))).name,
                    "eligible": bool(item.get("eligible")),
                    "content_brief_sha256": str(item.get("content_brief_sha256", "")),
                    "visual_brief_sha256": str(item.get("visual_brief_sha256", "")),
                    "contract_hash": str(item.get("contract_hash", "")),
                    "route_count": int(item.get("route_count", 0) or 0),
                    "section_count": int(item.get("section_count", 0) or 0),
                    "resource_coverage": int(item.get("resource_coverage", 0) or 0),
                    "component_coverage": int(item.get("component_coverage", 0) or 0),
                }
                for item in pack_infos
                if isinstance(item, dict)
            ]
            checks["brief_dependency_paths"] = any(
                bool(item.get("eligible")) for item in pack_infos if isinstance(item, dict)
            )
            if not checks["brief_dependency_paths"]:
                diagnostics.append(
                    {
                        "code": "BUILD_PREPARATION_PACKS_UNAVAILABLE",
                        "message": "No eligible Build Preparation brief pair is available.",
                    }
                )
        except Exception:
            diagnostics.append(
                {
                    "code": "BUILD_PREPARATION_PREFLIGHT_FAILED",
                    "message": "Build Preparation brief dependency paths could not be checked.",
                }
            )
    if not scaffold.is_dir():
        diagnostics.append(
            {"code": "SCAFFOLD_UNAVAILABLE", "message": "The configured scaffold is unavailable."}
        )
    if not npm:
        diagnostics.append(
            {
                "code": "TOOLCHAIN_NPM_UNAVAILABLE",
                "message": "The configured npm executable is unavailable.",
            }
        )

    checks["workspace_writable"] = _write_probe(workspace_root)
    if not checks["workspace_writable"]:
        diagnostics.append(
            {
                "code": "WORKSPACE_NOT_WRITABLE",
                "message": "The generation workspace is not writable.",
            }
        )

    cache_value = str(getattr(settings.code_generator_dependencies, "npm_cache_root", "") or "")
    cache_root = _resolve(cache_value) if cache_value else workspace_root / ".npm-cache"
    checks["cache_writable"] = _write_probe(cache_root)
    checks["checkpoint_writable"] = _write_probe(_resolve(str(config.checkpoint_root)))
    checks["artifact_writable"] = _write_probe(_resolve(str(config.artifact_root)))
    checks["preview_writable"] = _write_probe(
        _resolve(str(settings.code_generator_verification.preview_root))
    )
    if not checks["cache_writable"]:
        diagnostics.append(
            {
                "code": "NPM_CACHE_NOT_WRITABLE",
                "message": "The configured npm cache is not writable.",
            }
        )
    for check, code, message in (
        (
            "checkpoint_writable",
            "CHECKPOINT_NOT_WRITABLE",
            "The configured Code Generator checkpoint store is not writable.",
        ),
        (
            "artifact_writable",
            "ARTIFACT_STORE_NOT_WRITABLE",
            "The configured Code Generator artifact store is not writable.",
        ),
        (
            "preview_writable",
            "PREVIEW_ROOT_NOT_WRITABLE",
            "The configured local preview workspace is not writable.",
        ),
    ):
        if not checks[check]:
            diagnostics.append({"code": code, "message": message})

    node = shutil.which("node") or ""
    if npm and node and scaffold.is_dir() and checks["workspace_writable"]:
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix="codegen-preflight-", dir=str(workspace_root)))
            repo = temp_dir / "repo"
            # Do not copy checked-in disposables into the proof workspace.
            # The clean-build gate removes them before install anyway, and
            # skipping them keeps the preflight a proof of the configured
            # install rather than a large filesystem copy.
            shutil.copytree(
                scaffold,
                repo,
                symlinks=False,
                ignore=shutil.ignore_patterns("node_modules", "dist"),
            )
            node_version = await _version(node, cwd=repo, timeout=10.0)
            npm_version = await _version(npm, cwd=repo, timeout=10.0)
            checks["node"] = bool(node_version)
            facts.update({"node_version": node_version, "npm_version": npm_version})
            manifest, build_diagnostics = await run_clean_build(
                repo,
                settings=settings,
                candidate_identity_hash=hashlib.sha256(b"codegen-toolchain-preflight").hexdigest(),
            )
            checks["install"] = not any(item.phase == "install" for item in build_diagnostics)
            checks["typecheck"] = not any(item.phase == "typecheck" for item in build_diagnostics)
            checks["build"] = manifest is not None
            diagnostics.extend(item.model_dump(mode="json") for item in build_diagnostics)
            facts["lock_hash"] = (
                hashlib.sha256((repo / "package-lock.json").read_bytes()).hexdigest()
                if (repo / "package-lock.json").is_file()
                else ""
            )
        except Exception:
            diagnostics.append(
                {
                    "code": "TOOLCHAIN_PREFLIGHT_FAILED",
                    "message": "The disposable install/typecheck/build proof failed.",
                }
            )
        finally:
            if "temp_dir" in locals():
                fs_safe.remove_tree(temp_dir, required=False)
    elif not node:
        diagnostics.append(
            {
                "code": "TOOLCHAIN_NODE_UNAVAILABLE",
                "message": "The configured Node executable is unavailable.",
            }
        )

    browser = await _browser_smoke(settings)
    checks["browser"] = bool(browser.get("ready"))
    if not checks["browser"]:
        diagnostics.append(
            {
                "code": str(browser.get("code", "BROWSER_UNAVAILABLE")),
                "message": "The configured browser could not launch.",
            }
        )

    try:
        from oryxenai.agents.code_generator.core.development_service import _probe_preview_gateway

        gateway_ready, gateway_blocker = await _probe_preview_gateway(
            settings.code_generator_verification
        )
        checks["preview_gateway"] = gateway_ready
        if gateway_blocker:
            diagnostics.append(
                {"code": gateway_blocker, "message": "The preview gateway is not reachable."}
            )
    except Exception:
        diagnostics.append(
            {
                "code": "PREVIEW_GATEWAY_PROBE_FAILED",
                "message": "The preview gateway probe failed.",
            }
        )

    try:
        delivery = await _preview_delivery_smoke(settings)
        checks["preview_storage_readback"] = delivery["storage"]
        checks["preview_gateway_readback"] = delivery["gateway"]
        if not checks["preview_storage_readback"]:
            diagnostics.append(
                {
                    "code": "PREVIEW_STORAGE_READBACK_FAILED",
                    "message": "Temporary preview bytes could not be written and read back safely.",
                }
            )
        if not checks["preview_gateway_readback"]:
            diagnostics.append(
                {
                    "code": "PREVIEW_GATEWAY_READBACK_FAILED",
                    "message": "The configured preview gateway could not serve temporary stored bytes.",
                }
            )
    except Exception:
        diagnostics.append(
            {
                "code": "PREVIEW_DELIVERY_PROBE_FAILED",
                "message": "Preview storage and gateway delivery could not be proven.",
            }
        )

    ready = all(
        bool(checks[key])
        for key in (
            "scaffold",
            "node",
            "npm",
            "workspace_writable",
            "checkpoint_writable",
            "artifact_writable",
            "cache_writable",
            "preview_writable",
            "install",
            "typecheck",
            "build",
            "browser",
            "preview_gateway",
            "preview_storage_readback",
            "preview_gateway_readback",
            "brief_dependency_paths",
        )
    )
    result = {
        "schema_version": "code-generator-toolchain-preflight-v1",
        "checked_at": datetime.now(UTC).isoformat(),
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "requires_brief_dependency_paths": require_brief_dependency_paths,
        "model_calls": 0,
        "checks": checks,
        "facts": facts,
        "diagnostics": diagnostics[:24],
    }
    result["config_identity_sha256"] = capability_config_identity_hash(settings)
    result["toolchain_identity_sha256"] = capability_toolchain_identity_hash(
        str(result["config_identity_sha256"]), facts
    )
    return cache_toolchain_preflight(settings, result)


__all__ = [
    "cache_toolchain_preflight",
    "clear_toolchain_preflight_cache",
    "run_toolchain_preflight",
    "toolchain_preflight_status",
]
