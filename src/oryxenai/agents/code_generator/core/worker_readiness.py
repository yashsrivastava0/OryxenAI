"""Durable, configuration-bound readiness proof for Code Generator workers."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.core.process_runner import resolve_npm_executable
from oryxenai.agents.code_generator.core.workspace import repository_root
from oryxenai.jobs.heartbeat import HeartbeatRepository

_REQUIRED_PROOF_CHECKS = (
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
    "preview_storage_readback",
    "preview_gateway_readback",
)


def verification_is_enabled(settings: Any) -> bool:
    """Read the one effective Code Generator verification admission flag."""

    verification = getattr(settings, "code_generator_verification", None)
    return bool(getattr(verification, "enabled", True))


def _json_config(value: Any) -> Any:
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return {str(key): _json_config(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_json_config(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _scaffold_identity(settings: Any) -> str:
    generation = getattr(settings, "code_generator_generation", None)
    configured_root = Path(str(getattr(generation, "scaffold_root", "")))
    if not configured_root.is_absolute():
        configured_root = repository_root() / configured_root
    scaffold = (configured_root / str(getattr(generation, "scaffold_profile", ""))).resolve()
    digest = hashlib.sha256()
    for name in (
        "package.json",
        "package-lock.json",
        "vite.config.ts",
        "tsconfig.app.json",
        "tsconfig.node.json",
    ):
        path = (scaffold / name).resolve()
        digest.update(name.encode("utf-8"))
        if not path.is_relative_to(scaffold) or not path.is_file():
            digest.update(b"<missing-or-unsafe>")
            continue
        try:
            digest.update(path.read_bytes())
        except OSError:
            digest.update(b"<unreadable>")
    return digest.hexdigest()


def capability_toolchain_identity_hash(config_identity_sha256: str, facts: dict[str, Any]) -> str:
    serialized = json.dumps(
        {"config_identity_sha256": config_identity_sha256, "facts": facts},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def capability_config_identity(settings: Any) -> dict[str, Any]:
    """Return only non-secret inputs that determine Code Generator capability.

    Model profiles are projected onto routing/schema identity fields. Actual
    API key values are deliberately neither read nor included.
    """

    development = getattr(settings, "code_generator_development", None)
    generation = getattr(settings, "code_generator_generation", None)
    dependencies = getattr(settings, "code_generator_dependencies", None)
    verification = getattr(settings, "code_generator_verification", None)
    acquisition = getattr(settings, "code_generator_acquisition", None)
    profile_names = list(
        dict.fromkeys(
            str(getattr(section, field, "") or "")
            for section, field in (
                (development, "director_profile"),
                (development, "planner_profile"),
                (acquisition, "resource_scout_profile"),
                (generation, "route_profile"),
                (generation, "compose_profile"),
                (generation, "integration_profile"),
                (generation, "repair_profile"),
            )
            if getattr(section, field, "")
        )
    )
    profiles: dict[str, dict[str, Any]] = {}
    models = getattr(settings, "models", None)
    get_profile = getattr(models, "get_profile", None)
    if callable(get_profile):
        for name in profile_names:
            profile = get_profile(name)
            if profile is None:
                profiles[name] = {"missing": True}
                continue
            capabilities = getattr(profile, "capabilities", None)
            profiles[name] = {
                key: getattr(profile, key, None)
                for key in (
                    "provider",
                    "model",
                    "api_key_env",
                    "base_url_env",
                    "max_output_tokens",
                    "reasoning_effort",
                    "timeout_seconds",
                )
            }
            profiles[name]["capabilities"] = _json_config(capabilities)

    payload = {
        "release_id": str(getattr(development, "worker_release_id", "") or ""),
        "pipeline_contract_version": str(
            getattr(development, "pipeline_contract_version", "") or ""
        ),
        "development": _json_config(development),
        "generation": _json_config(generation),
        "dependencies": _json_config(dependencies),
        "verification": _json_config(verification),
        "profiles": profiles,
        "toolchain": {
            "scaffold_hash": _scaffold_identity(settings),
            "node_executable": shutil.which("node") or "",
            "npm_executable": resolve_npm_executable(settings),
        },
    }
    return payload


def capability_config_identity_hash(settings: Any) -> str:
    serialized = json.dumps(
        capability_config_identity(settings),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def capability_proof_blocker(
    proof: Any,
    *,
    settings: Any,
    worker_instance_id: str,
    now: datetime | None = None,
) -> str:
    """Validate a worker's cached proof against its current runtime identity."""

    if not verification_is_enabled(settings):
        return "code_generator_verification_disabled"
    if not isinstance(proof, dict):
        return "code_generator_worker_capability_proof_missing"
    if proof.get("schema_version") != "code-generator-worker-capability-v1":
        return "code_generator_worker_capability_proof_invalid"
    if str(proof.get("worker_instance_id", "")) != worker_instance_id:
        return "code_generator_worker_capability_identity_mismatch"
    development = settings.code_generator_development
    if str(proof.get("release_id", "")) != str(development.worker_release_id):
        return "code_generator_worker_contract_mismatch"
    if str(proof.get("pipeline_contract_version", "")) != str(
        development.pipeline_contract_version
    ):
        return "code_generator_worker_contract_mismatch"
    if str(proof.get("config_identity_sha256", "")) != capability_config_identity_hash(settings):
        return "code_generator_worker_capability_identity_mismatch"
    facts = proof.get("toolchain_facts")
    if not isinstance(facts, dict) or str(
        proof.get("toolchain_identity_sha256", "")
    ) != capability_toolchain_identity_hash(str(proof.get("config_identity_sha256", "")), facts):
        return "code_generator_worker_capability_identity_mismatch"
    try:
        expires_at = datetime.fromisoformat(str(proof.get("expires_at", "")))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return "code_generator_worker_capability_proof_invalid"
    current_time = now or datetime.now(UTC)
    if expires_at <= current_time:
        return "code_generator_worker_capability_proof_expired"
    if not bool(proof.get("ready")):
        return "code_generator_worker_toolchain_unavailable"
    checks = proof.get("checks")
    if not isinstance(checks, dict) or not all(
        bool(checks.get(key)) for key in _REQUIRED_PROOF_CHECKS
    ):
        return "code_generator_worker_toolchain_unavailable"
    return ""


async def worker_contract_readiness(repository: Any, settings: Any) -> dict[str, Any]:
    """Return whether every fresh worker can claim the active Code Generator lane.

    A worker must carry a complete, unexpired proof from its own process. A
    legacy executable-presence heartbeat is intentionally insufficient.
    Repositories used by isolated pure unit tests do not expose a database
    session; they retain the historical optimistic result while still
    respecting the verification-disabled policy.
    """

    session = getattr(repository, "_session", None)
    expected_version = str(
        getattr(settings.code_generator_development, "pipeline_contract_version", "") or ""
    )
    expected_release = str(
        getattr(settings.code_generator_development, "worker_release_id", "") or ""
    )
    enabled = verification_is_enabled(settings)
    base = {
        "checked": False,
        "ready": enabled,
        "expected_pipeline_contract_version": expected_version,
        "expected_worker_release_id": expected_release,
        "active_workers": [],
        "blocker": "" if enabled else "code_generator_verification_disabled",
    }
    if not enabled or session is None:
        return base

    try:
        rows = await HeartbeatRepository(session).get_recent(limit=25)
    except Exception:
        return {
            **base,
            "checked": True,
            "ready": False,
            "blocker": "code_generator_worker_heartbeat_unavailable",
        }

    try:
        stale_after = max(
            float(
                getattr(
                    getattr(settings, "diagnostics", None),
                    "heartbeat_staleness",
                    60.0,
                )
            ),
            float(getattr(getattr(settings, "worker", None), "heartbeat_interval", 30.0)) * 2,
        )
    except (TypeError, ValueError):
        stale_after = 60.0

    now = datetime.now(UTC)
    active_workers: list[dict[str, Any]] = []
    for row in rows:
        last_seen = getattr(row, "last_seen_at", None)
        if getattr(row, "stopped_at", None) is not None or last_seen is None:
            continue
        age = max(0.0, (now - last_seen).total_seconds())
        if age > stale_after:
            continue
        metadata = getattr(row, "service_metadata", {})
        metadata = metadata if isinstance(metadata, dict) else {}
        proof = metadata.get("code_generator_capability_proof")
        proof = proof if isinstance(proof, dict) else {}
        worker_id = str(getattr(row, "instance_id", ""))
        proof_blocker = capability_proof_blocker(
            proof,
            settings=settings,
            worker_instance_id=worker_id,
            now=now,
        )
        checks = proof.get("checks", {})
        checks = checks if isinstance(checks, dict) else {}
        active_workers.append(
            {
                "instance_id": worker_id,
                "release_id": str(metadata.get("release_id", "")),
                "pipeline_contract_version": str(metadata.get("pipeline_contract_version", "")),
                "code_generator_capability": not bool(proof_blocker),
                "capability_proof_expires_at": str(proof.get("expires_at", "")),
                "capability_proof_config_identity_matches": not proof_blocker.endswith(
                    "identity_mismatch"
                ),
                "code_generator_toolchain": {
                    "node": bool(checks.get("node", False)),
                    "npm": bool(checks.get("npm", False)),
                    "browser": bool(checks.get("browser", False)),
                    "install": bool(checks.get("install", False)),
                    "typecheck": bool(checks.get("typecheck", False)),
                    "build": bool(checks.get("build", False)),
                    "storage": bool(checks.get("preview_storage_readback", False)),
                    "gateway": bool(checks.get("preview_gateway_readback", False)),
                },
                "capability_blocker": proof_blocker,
                "age_seconds": round(age, 1),
            }
        )

    compatible = [
        worker
        for worker in active_workers
        if worker["release_id"] == expected_release
        and worker["pipeline_contract_version"] == expected_version
    ]
    capability_ready = [worker for worker in compatible if worker["code_generator_capability"]]
    blocker = ""
    if not active_workers:
        blocker = "code_generator_worker_unavailable"
    elif not compatible:
        blocker = "code_generator_worker_contract_mismatch"
    elif not capability_ready:
        blockers = {str(worker["capability_blocker"]) for worker in compatible}
        blocker = (
            next(iter(blockers))
            if len(blockers) == 1
            else "code_generator_worker_toolchain_unavailable"
        )
    elif len(compatible) != len(active_workers):
        blocker = "code_generator_worker_contract_mismatch"
    elif len(capability_ready) != len(active_workers):
        blocker = "code_generator_worker_toolchain_unavailable"

    return {
        "checked": True,
        "ready": bool(active_workers)
        and len(capability_ready) == len(active_workers)
        and not blocker,
        "expected_pipeline_contract_version": expected_version,
        "expected_worker_release_id": expected_release,
        "active_workers": active_workers,
        "blocker": blocker,
    }


__all__ = [
    "capability_config_identity",
    "capability_config_identity_hash",
    "capability_proof_blocker",
    "capability_toolchain_identity_hash",
    "verification_is_enabled",
    "worker_contract_readiness",
]
