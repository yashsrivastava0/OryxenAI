"""Unit tests for the job handler registry."""

from __future__ import annotations

from oryxenai.jobs.contracts import SYSTEM_PROBE_KIND
from oryxenai.jobs.registry import get, is_registered, list_kinds


def test_is_registered_probe():
    """is_registered returns True for system.worker_probe."""
    assert is_registered("system.worker_probe") is True


def test_is_registered_nonexistent():
    """is_registered returns False for an unknown kind."""
    assert is_registered("nonexistent") is False


def test_get_probe_handler():
    """get('system.worker_probe') returns a handler with the correct kind."""
    handler = get("system.worker_probe")
    assert handler is not None
    assert handler.kind == SYSTEM_PROBE_KIND


def test_get_nonexistent():
    """get('nonexistent') returns None."""
    assert get("nonexistent") is None


def test_list_kinds():
    """list_kinds returns the registered job kinds."""
    kinds = list_kinds()
    assert "system.worker_probe" in kinds


async def test_probe_handler_execute():
    """The probe handler runs successfully with a test payload."""
    handler = get("system.worker_probe")
    assert handler is not None
    result = await handler.execute({"message": "hello"}, "test-instance")
    assert result["echo_message"] == "hello"
    assert result["worker_instance"] == "test-instance"
    assert "received_at" in result
