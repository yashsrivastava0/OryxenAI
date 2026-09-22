from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from oryxenai.agents.code_generator.core import worker_readiness
from oryxenai.core.settings import Settings
from oryxenai.jobs import worker as worker_module
from oryxenai.jobs.worker import Worker


class _HeartbeatRepository:
    def __init__(self, rows):
        self.rows = rows

    async def get_recent(self, *, limit: int):
        assert limit == 25
        return self.rows


def _proof(settings: Settings, worker_id: str, *, ready: bool = True, checks=None, expires=None):
    required = {
        "scaffold": True,
        "node": True,
        "npm": True,
        "workspace_writable": True,
        "checkpoint_writable": True,
        "artifact_writable": True,
        "cache_writable": True,
        "preview_writable": True,
        "install": True,
        "typecheck": True,
        "build": True,
        "browser": True,
        "preview_storage_readback": True,
        "preview_gateway_readback": True,
    }
    if checks:
        required.update(checks)
    return _proof_toolchain_identity(
        {
            "schema_version": "code-generator-worker-capability-v1",
            "worker_instance_id": worker_id,
            "release_id": settings.code_generator_development.worker_release_id,
            "pipeline_contract_version": settings.code_generator_development.pipeline_contract_version,
            "config_identity_sha256": worker_readiness.capability_config_identity_hash(settings),
            "toolchain_facts": {"node_version": "v22.0.0", "npm_version": "10.0.0"},
            "checked_at": datetime.now(UTC).isoformat(),
            "expires_at": (expires or datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            "ready": ready,
            "checks": required,
        }
    )


def _proof_toolchain_identity(proof):
    proof["toolchain_identity_sha256"] = worker_readiness.capability_toolchain_identity_hash(
        proof["config_identity_sha256"], proof["toolchain_facts"]
    )
    return proof


def _row(settings: Settings, *, worker_id: str = "worker-1", proof=None, **metadata):
    return SimpleNamespace(
        instance_id=worker_id,
        last_seen_at=datetime.now(UTC),
        stopped_at=None,
        service_metadata={
            "release_id": settings.code_generator_development.worker_release_id,
            "pipeline_contract_version": settings.code_generator_development.pipeline_contract_version,
            "code_generator_capability_proof": proof or _proof(settings, worker_id),
            **metadata,
        },
    )


def _mock_rows(monkeypatch, rows):
    monkeypatch.setattr(
        worker_readiness,
        "HeartbeatRepository",
        lambda _session: _HeartbeatRepository(rows),
    )


@pytest.mark.asyncio
async def test_worker_readiness_requires_full_local_capability_proof(monkeypatch) -> None:
    settings = Settings()
    row = _row(
        settings,
        proof=_proof(settings, "worker-1", checks={"browser": False}),
        code_generator_capability=True,
        code_generator_toolchain={"node": True, "npm": True, "browser": True},
    )
    _mock_rows(monkeypatch, [row])

    result = await worker_readiness.worker_contract_readiness(
        SimpleNamespace(_session=object()), settings
    )

    assert result["ready"] is False
    assert result["blocker"] == "code_generator_worker_toolchain_unavailable"
    assert result["active_workers"][0]["code_generator_toolchain"]["browser"] is False


@pytest.mark.asyncio
async def test_worker_readiness_accepts_only_fresh_matching_worker(monkeypatch) -> None:
    settings = Settings()
    _mock_rows(monkeypatch, [_row(settings)])

    result = await worker_readiness.worker_contract_readiness(
        SimpleNamespace(_session=object()), settings
    )

    assert result["ready"] is True
    assert result["blocker"] == ""


@pytest.mark.asyncio
async def test_worker_readiness_rejects_expired_or_configuration_stale_proofs(monkeypatch) -> None:
    settings = Settings()
    expired = _row(
        settings,
        proof=_proof(settings, "worker-1", expires=datetime.now(UTC) - timedelta(seconds=1)),
    )
    _mock_rows(monkeypatch, [expired])
    expired_result = await worker_readiness.worker_contract_readiness(
        SimpleNamespace(_session=object()), settings
    )
    assert expired_result["blocker"] == "code_generator_worker_capability_proof_expired"

    settings.code_generator_verification.browser_timeout_ms += 1
    _mock_rows(monkeypatch, [_row(Settings())])
    changed_result = await worker_readiness.worker_contract_readiness(
        SimpleNamespace(_session=object()), settings
    )
    assert changed_result["blocker"] == "code_generator_worker_capability_identity_mismatch"


@pytest.mark.asyncio
async def test_worker_readiness_blocks_disabled_policy_and_mixed_releases(monkeypatch) -> None:
    settings = Settings()
    settings.code_generator_verification.enabled = False
    disabled = await worker_readiness.worker_contract_readiness(SimpleNamespace(), settings)
    assert disabled["ready"] is False
    assert disabled["blocker"] == "code_generator_verification_disabled"

    settings.code_generator_verification.enabled = True
    stale_release = _row(settings, release_id="older-release")
    _mock_rows(monkeypatch, [_row(settings), stale_release])
    mixed = await worker_readiness.worker_contract_readiness(
        SimpleNamespace(_session=object()), settings
    )
    assert mixed["ready"] is False
    assert mixed["blocker"] == "code_generator_worker_contract_mismatch"


def test_worker_capability_identity_binds_scaffold_contents(tmp_path) -> None:
    settings = Settings()
    scaffold = tmp_path / "scaffolds" / "identity-test"
    scaffold.mkdir(parents=True)
    settings.code_generator_generation.scaffold_root = str(scaffold.parent)
    settings.code_generator_generation.scaffold_profile = scaffold.name
    (scaffold / "package.json").write_text('{"name":"before"}', encoding="utf-8")

    before = worker_readiness.capability_config_identity_hash(settings)
    (scaffold / "package.json").write_text('{"name":"after"}', encoding="utf-8")

    assert worker_readiness.capability_config_identity_hash(settings) != before


@pytest.mark.asyncio
async def test_worker_caches_model_free_capability_until_identity_changes(monkeypatch) -> None:
    settings = Settings()
    settings.code_generator_verification.enabled = True
    worker = Worker(settings)
    calls = 0

    async def fake_preflight(_settings, *, require_brief_dependency_paths):
        nonlocal calls
        assert require_brief_dependency_paths is False
        calls += 1
        checked_at = datetime.now(UTC)
        return {
            "ready": True,
            "checked_at": checked_at.isoformat(),
            "expires_at": (checked_at + timedelta(minutes=5)).isoformat(),
            "facts": {"node_version": "v22", "npm_version": "10"},
            "checks": {
                "scaffold": True,
                "node": True,
                "npm": True,
                "workspace_writable": True,
                "checkpoint_writable": True,
                "artifact_writable": True,
                "cache_writable": True,
                "preview_writable": True,
                "install": True,
                "typecheck": True,
                "build": True,
                "browser": True,
                "preview_storage_readback": True,
                "preview_gateway_readback": True,
            },
        }

    monkeypatch.setattr(worker_module, "run_toolchain_preflight", fake_preflight)

    await worker._refresh_code_generator_capability(force=True)
    await worker._refresh_code_generator_capability()
    assert calls == 1
    assert (
        worker_readiness.capability_proof_blocker(
            worker._code_generator_capability_proof,
            settings=settings,
            worker_instance_id=worker._instance_id,
        )
        == ""
    )

    settings.code_generator_verification.browser_timeout_ms += 1
    await worker._refresh_code_generator_capability()
    assert calls == 2
