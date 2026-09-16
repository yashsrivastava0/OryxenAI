"""Unit test for the test_engine fixture's non-test-database guard.

tests/conftest.py's `test_engine` fixture drops and recreates every table
against whatever database `get_settings()` resolves to. If the test overlay
(OryxenAI_CONFIG_OVERLAY=config/app.test.toml) is not active for any reason,
`get_settings()` can silently fall back to config/app.toml's default
database — the real local `oryxenai` application database — and this
fixture would then destroy its tables.

This test proves the fixture's defensive guard fires *before* any
drop_all/create_all call, whenever the resolved database is not
"oryxenai_test" — without ever pointing the fixture at a second real
database to prove it (that would recreate the exact risk being guarded
against). It does this by monkeypatching `get_settings` to return a fake
settings object and driving the fixture's underlying async generator
function directly.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import tests.conftest as conftest_module


class _FakeDatabaseConfig:
    def __init__(self, database: str) -> None:
        self.database = database


class _FakeSettings:
    def __init__(self, database: str) -> None:
        self.database = _FakeDatabaseConfig(database)


def _unwrapped_test_engine():
    """Return the plain async generator function behind the pytest_asyncio
    fixture wrapper, so it can be driven directly without full fixture
    injection (and without needing a reachable PostgreSQL server)."""
    return conftest_module.test_engine.__wrapped__


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_database_name",
    ["oryxenai", "some_other_db", ""],
)
async def test_test_engine_refuses_non_test_database(monkeypatch, bad_database_name):
    """The fixture must raise before drop_all/create_all when the resolved
    database is not the dedicated test database, regardless of why
    (overlay unset, overlay wrong, or anything else that changes what
    get_settings() resolves to)."""
    fake_settings = _FakeSettings(database=bad_database_name)
    # get_settings is imported locally inside the fixture from
    # oryxenai.core.settings at call time, so patch it at the source.
    monkeypatch.setattr(
        "oryxenai.core.settings.get_settings",
        lambda: fake_settings,
    )

    # Guard against accidentally exercising real engine/connection logic:
    # get_engine must never be reached once the guard fires.
    called = SimpleNamespace(get_engine=False)

    def _fail_if_called(*_args, **_kwargs):
        called.get_engine = True
        raise AssertionError("get_engine must not be called once the guard fires")

    monkeypatch.setattr("oryxenai.db.session.get_engine", _fail_if_called)

    agen = _unwrapped_test_engine()()
    with pytest.raises(RuntimeError, match="test_engine fixture refused to run"):
        await agen.__anext__()

    assert called.get_engine is False


@pytest.mark.asyncio
async def test_test_engine_guard_error_message_names_resolved_database(monkeypatch):
    """The raised error must be actionable: it should name the bad database
    it actually resolved, not just fail silently or with a bare
    AssertionError."""
    fake_settings = _FakeSettings(database="oryxenai")
    monkeypatch.setattr(
        "oryxenai.core.settings.get_settings",
        lambda: fake_settings,
    )

    agen = _unwrapped_test_engine()()
    with pytest.raises(RuntimeError) as exc_info:
        await agen.__anext__()

    message = str(exc_info.value)
    assert "oryxenai" in message
    assert "oryxenai_test" in message
    assert "OryxenAI_CONFIG_OVERLAY" in message
