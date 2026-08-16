"""Trusted dependency resolution for Code Generator acquisition."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import (
    DependencyLedger,
    DependencyReceipt,
    DependencyReceiptBasis,
    DependencyRequest,
    ResourceReceipt,
)


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class DependencyPolicyError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class DependencyManager:
    """Own package/lock mutation and disposable installation."""

    def __init__(self, resource_receipts: Iterable[ResourceReceipt] = ()) -> None:
        self._resource_receipts = {receipt.request_hash: receipt for receipt in resource_receipts}

    async def resolve(
        self,
        request: DependencyRequest,
        *,
        repo_dir: Path,
        prior_manifest: dict[str, Any],
        prior_lock: dict[str, Any],
        settings: Any,
    ) -> DependencyReceipt:
        if not re.fullmatch(r"(?:@[a-z0-9._-]+/)?[a-z0-9._-]+", request.package_name.casefold()):
            raise DependencyPolicyError(
                "DEPENDENCY_NAME_UNSAFE", "The dependency name is not a safe package identifier."
            )
        if self._resource_receipts and not any(
            _canonical_hash(receipt.model_dump(mode="json"))
            == request.requesting_resource_receipt_hash
            or receipt.request_hash == request.requesting_resource_receipt_hash
            for receipt in self._resource_receipts.values()
        ):
            raise DependencyPolicyError(
                "DEPENDENCY_RESOURCE_RECEIPT_UNKNOWN",
                "The dependency request is not bound to an admitted resource receipt.",
            )
        config = settings.code_generator_dependencies
        package_meta = dict(getattr(config, "supported_packages", {}).get(request.package_name, {}))
        prior_manifest_hash = _canonical_hash(prior_manifest)
        prior_lock_hash = _canonical_hash(prior_lock)
        basis = DependencyReceiptBasis(
            toolchain_profile="react-vite-v1",
            scaffold_manifest_hash="",
            prior_manifest_hash=prior_manifest_hash,
            prior_lock_hash=prior_lock_hash,
            resource_receipt_hash=request.requesting_resource_receipt_hash,
        )
        if not package_meta:
            return DependencyReceipt(
                based_on=basis,
                decision="rejected_fallback",
                package_name=request.package_name,
                licence_result="not_configured",
                vulnerability_policy_result="not_evaluated",
                install_script_result="not_run",
                manifest_hash=prior_manifest_hash,
                lock_hash=prior_lock_hash,
                fallback={"strategy": request.fallback_component_strategy},
            )
        if bool(package_meta.get("install_scripts", False)) and not bool(
            getattr(config, "allow_install_scripts", False)
        ):
            return DependencyReceipt(
                based_on=basis,
                decision="rejected_fallback",
                package_name=request.package_name,
                resolved_version=str(package_meta.get("version_pin", "")),
                licence_result=str(package_meta.get("licence", "")),
                vulnerability_policy_result="policy_blocked",
                install_script_result="blocked_per_policy",
                manifest_hash=prior_manifest_hash,
                lock_hash=prior_lock_hash,
                fallback={"strategy": request.fallback_component_strategy},
            )
        configured_version = str(package_meta.get("version_pin", "")).strip()
        existing_version = str(prior_manifest.get("dependencies", {}).get(request.package_name, ""))
        if existing_version == configured_version and configured_version:
            return DependencyReceipt(
                based_on=basis,
                decision="existing",
                package_name=request.package_name,
                resolved_version=configured_version,
                transitive_summary=_transitive_summary(package_meta),
                licence_result=str(package_meta.get("licence", "")),
                vulnerability_policy_result="allowed_by_config",
                install_script_result="not_run",
                manifest_hash=prior_manifest_hash,
                lock_hash=prior_lock_hash,
            )
        repo_dir = repo_dir.resolve()
        repo_dir.mkdir(parents=True, exist_ok=True)
        manifest = json.loads(json.dumps(prior_manifest))
        dependencies = dict(manifest.get("dependencies", {}))
        dependencies[request.package_name] = configured_version
        manifest["dependencies"] = dict(sorted(dependencies.items()))
        manifest.setdefault("name", "oryxenai-code-generator-workspace")
        manifest.setdefault("private", True)
        manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        manifest_hash = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()
        previous_lock = repo_dir / "package-lock.json"
        previous_lock_hash = (
            hashlib.sha256(previous_lock.read_bytes()).hexdigest()
            if previous_lock.is_file()
            else _canonical_hash(prior_lock)
        )
        node_modules = repo_dir / "node_modules"
        (repo_dir / "package.json").write_text(manifest_text, encoding="utf-8")
        await self._create_lock(repo_dir, settings)
        lock_file = repo_dir / "package-lock.json"
        lock_hash = hashlib.sha256(lock_file.read_bytes()).hexdigest()
        if previous_lock_hash != lock_hash:
            shutil.rmtree(node_modules, ignore_errors=True)
        await self._install(repo_dir, settings)
        return DependencyReceipt(
            based_on=basis,
            decision="admitted",
            package_name=request.package_name,
            resolved_version=configured_version,
            transitive_summary=_transitive_summary(package_meta),
            licence_result=str(package_meta.get("licence", "")),
            vulnerability_policy_result="allowed_by_config",
            install_script_result="blocked_per_policy"
            if not bool(getattr(config, "allow_install_scripts", False))
            else "allowed_by_config",
            manifest_hash=manifest_hash,
            lock_hash=lock_hash,
            cache_receipt={"mode": "offline" if not config.allow_network_install else "configured"},
        )

    async def _create_lock(self, repo_dir: Path, settings: Any) -> None:
        """Ask npm to produce the lockfile; application code never synthesizes one."""

        executable = _npm_executable(settings)
        command = [
            executable,
            "install",
            "--package-lock-only",
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
            "--prefix",
            str(repo_dir),
        ]
        if not bool(settings.code_generator_dependencies.allow_network_install):
            command.insert(2, "--offline")
        await _run_npm(command, repo_dir, settings, stage="lockfile")
        lock_file = repo_dir / "package-lock.json"
        if not lock_file.is_file():
            raise DependencyPolicyError(
                "DEPENDENCY_LOCKFILE_MISSING",
                "The package manager completed without producing a lockfile.",
            )
        try:
            lock = json.loads(lock_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DependencyPolicyError(
                "DEPENDENCY_LOCKFILE_INVALID",
                "The package manager produced an unreadable lockfile.",
            ) from exc
        if not isinstance(lock, dict) or not isinstance(lock.get("packages"), dict):
            raise DependencyPolicyError(
                "DEPENDENCY_LOCKFILE_INVALID",
                "The package manager produced an invalid lockfile shape.",
            )

    async def _install(self, repo_dir: Path, settings: Any) -> None:
        config = settings.code_generator_dependencies
        executable = _npm_executable(settings)
        command = [executable, "ci", "--ignore-scripts", "--prefix", str(repo_dir)]
        if not bool(getattr(config, "allow_network_install", False)):
            command.insert(2, "--offline")
        await _run_npm(command, repo_dir, settings, stage="install")
        if not (repo_dir / "node_modules").is_dir():
            raise DependencyPolicyError(
                "DEPENDENCY_INSTALL_FAILED", "The package manager did not create node_modules."
            )


def _npm_executable(settings: Any) -> str:
    executable = str(getattr(settings.code_generator_dependencies, "npm_executable", "") or "")
    if not executable:
        raise DependencyPolicyError(
            "DEPENDENCY_INSTALL_UNAVAILABLE",
            "No package-manager executable is configured for dependency acquisition.",
        )
    return executable


async def _run_npm(command: list[str], repo_dir: Path, settings: Any, *, stage: str) -> None:
    config = settings.code_generator_dependencies
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.upper().endswith("_TOKEN") or key.upper().endswith("_PASSWORD"):
            environment.pop(key, None)
    cache_root = str(getattr(config, "npm_cache_root", "") or "")
    if cache_root:
        environment["npm_config_cache"] = cache_root
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            command,
            cwd=repo_dir,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DependencyPolicyError(
            "DEPENDENCY_INSTALL_FAILED", f"The package-manager {stage} command could not start."
        ) from exc
    if result.returncode != 0:
        raise DependencyPolicyError(
            "DEPENDENCY_INSTALL_FAILED", f"The package-manager {stage} command failed safely."
        )


def _transitive_summary(metadata: dict[str, Any]) -> dict[str, str]:
    values = metadata.get("transitive", [])
    if isinstance(values, dict):
        return {str(key): str(value) for key, value in values.items()}
    return {str(index): str(value) for index, value in enumerate(values) if str(value)}


def build_dependency_ledger(receipts: list[DependencyReceipt]) -> DependencyLedger:
    payload = [receipt.model_dump(mode="json") for receipt in receipts]
    return DependencyLedger(
        receipts=receipts,
        dependency_ledger_hash=_canonical_hash({"receipts": payload}),
    )
