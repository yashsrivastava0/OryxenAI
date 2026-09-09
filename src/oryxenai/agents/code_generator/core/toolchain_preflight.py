"""Disposable, model-free Code Generator toolchain preflight."""

from __future__ import annotations

import contextlib
import hashlib
import json
import platform
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.core import fs_safe
from oryxenai.agents.code_generator.core.build_runner import run_clean_build
from oryxenai.agents.code_generator.core.process_runner import (
    ProcessRunnerError,
    resolve_npm_executable,
    run_command,
)
from oryxenai.agents.code_generator.core.workspace import repository_root

_PREFLIGHT_TTL_SECONDS = 15 * 60
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


def _cache_key(settings: Any) -> str:
    config = settings.code_generator_generation
    dependencies = settings.code_generator_dependencies
    verification = settings.code_generator_verification
    scaffold_root = _resolve(str(config.scaffold_root))
    scaffold = (scaffold_root / str(config.scaffold_profile)).resolve()
    payload = {
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
        "scaffold_profile": str(config.scaffold_profile),
        "npm": resolve_npm_executable(settings),
        "npm_cache_root": str(getattr(dependencies, "npm_cache_root", "") or ""),
        "browser": str(getattr(verification, "browser_name", "chromium")),
        "browser_executable": str(getattr(verification, "browser_executable", "") or ""),
        "preview_health_url": str(getattr(verification, "preview_health_url", "") or ""),
        "preview_host": str(getattr(verification, "preview_host", "") or ""),
        "preview_port": int(getattr(verification, "preview_port", 0) or 0),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def cache_toolchain_preflight(settings: Any, result: dict[str, Any]) -> dict[str, Any]:
    """Publish one safe receipt for later readiness/create requests."""

    key = _cache_key(settings)
    stored = dict(result)
    stored.setdefault("checked_at", datetime.now(UTC).isoformat())
    stored["cache_key"] = key
    _PREFLIGHT_CACHE[key] = stored
    return stored


def toolchain_preflight_status(settings: Any) -> dict[str, Any]:
    """Read the latest proof for the current scaffold/toolchain identity."""

    key = _cache_key(settings)
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
        age = (datetime.now(UTC) - datetime.fromisoformat(checked_at)).total_seconds()
    except (TypeError, ValueError):
        age = _PREFLIGHT_TTL_SECONDS + 1
    if age > _PREFLIGHT_TTL_SECONDS:
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


async def run_toolchain_preflight(settings: Any) -> dict[str, Any]:
    """Prove install, TypeScript, Vite, browser, and gateway readiness.

    The function creates a disposable copy of the configured scaffold and
    invokes the same clean-build path used by production verification. It does
    not load a brief, call a model, or mutate a generation run.
    """

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
        "brief_dependency_paths": False,
    }
    diagnostics: list[dict[str, Any]] = []
    workspace_root = _resolve(str(config.workspace_root))
    try:
        from oryxenai.agents.code_generator.core.development_input import DevelopmentInputAdapter

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

    try:
        workspace_root.mkdir(parents=True, exist_ok=True)
        probe = workspace_root / ".preflight-write"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks["workspace_writable"] = True
    except OSError:
        diagnostics.append(
            {
                "code": "WORKSPACE_NOT_WRITABLE",
                "message": "The generation workspace is not writable.",
            }
        )

    cache_value = str(getattr(settings.code_generator_dependencies, "npm_cache_root", "") or "")
    cache_root = _resolve(cache_value) if cache_value else workspace_root / ".npm-cache"
    try:
        cache_root.mkdir(parents=True, exist_ok=True)
        probe = cache_root / ".preflight-write"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks["cache_writable"] = True
    except OSError:
        diagnostics.append(
            {
                "code": "NPM_CACHE_NOT_WRITABLE",
                "message": "The configured npm cache is not writable.",
            }
        )

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

    ready = all(
        bool(checks[key])
        for key in (
            "scaffold",
            "node",
            "npm",
            "workspace_writable",
            "cache_writable",
            "install",
            "typecheck",
            "build",
            "browser",
            "preview_gateway",
            "brief_dependency_paths",
        )
    )
    result = {
        "schema_version": "code-generator-toolchain-preflight-v1",
        "checked_at": datetime.now(UTC).isoformat(),
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "model_calls": 0,
        "checks": checks,
        "facts": facts,
        "diagnostics": diagnostics[:24],
    }
    return cache_toolchain_preflight(settings, result)


__all__ = [
    "cache_toolchain_preflight",
    "clear_toolchain_preflight_cache",
    "run_toolchain_preflight",
    "toolchain_preflight_status",
]
