"""Unit tests for worker-related settings."""

from __future__ import annotations

from oryxenai.core.settings import Settings, reset_settings


def test_settings_worker_config():
    """Settings loads worker config from default config/app.toml."""
    reset_settings()
    s = Settings()
    assert s.worker.polling_interval == 2.0
    assert s.worker.heartbeat_interval == 30.0
    assert s.worker.claim_batch_size == 5
    assert s.worker.concurrency == 2
    assert s.worker.shutdown_grace == 10.0


def test_settings_worker_job_config():
    """Settings loads worker_job config (handler_timeout, lease_duration)."""
    reset_settings()
    s = Settings()
    assert s.worker_job.handler_timeout == 300.0
    assert s.worker_job.lease_duration == 120.0


def test_settings_worker_retry_config():
    """Settings loads worker_retry config (max_attempts, base_delay, max_delay)."""
    reset_settings()
    s = Settings()
    assert s.worker_retry.max_attempts == 3
    assert s.worker_retry.base_delay == 1.0
    assert s.worker_retry.max_delay == 60.0
    assert s.worker_retry.jitter is True


def test_settings_pool_config():
    """Settings loads pool config (pool_size, max_overflow)."""
    reset_settings()
    s = Settings()
    assert s.pool.pool_size == 5
    assert s.pool.max_overflow == 10


def test_settings_api_config():
    """Settings loads api config (max_input_bytes)."""
    reset_settings()
    s = Settings()
    assert s.api.max_input_bytes == 262144


def test_settings_diagnostics_config():
    """Settings loads diagnostics config (heartbeat_staleness)."""
    reset_settings()
    s = Settings()
    assert s.diagnostics.heartbeat_staleness == 60.0


def test_db_host_port_overrides():
    """db_host_override and db_port_override apply correctly in database_url."""
    reset_settings()
    s = Settings()
    url_default = s.database_url

    s.db_host_override = "override-host"
    s.db_port_override = 9999
    url_override = s.database_url

    assert url_default != url_override
    assert "override-host" in url_override
    assert "9999" in url_override
