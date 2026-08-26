from __future__ import annotations

from asyncpg.exceptions import InvalidPasswordError

from oryxenai.api.errors import _build_envelope, _database_failure
from oryxenai.core.logging import redact_sensitive_text


def test_sensitive_assignments_and_configured_values_are_redacted(monkeypatch) -> None:
    monkeypatch.setenv("TEST_PASSWORD", "unit-test-password")

    result = redact_sensitive_text("POSTGRES_PASSWORD=unit-test-password and unit-test-password")

    assert "unit-test-password" not in result
    assert "[REDACTED]" in result


def test_error_envelope_redacts_nested_detail_strings(monkeypatch) -> None:
    monkeypatch.setenv("TEST_API_KEY", "unit-test-api-key")

    result = _build_envelope(
        "INTERNAL_ERROR",
        "request failed with unit-test-api-key",
        {"nested": ["TEST_API_KEY=unit-test-api-key"]},
    )

    serialized = str(result)
    assert "unit-test-api-key" not in serialized
    assert result["error"]["details"]["nested"] == ["TEST_API_KEY=[REDACTED]"]


def test_invalid_database_password_has_safe_actionable_classification() -> None:
    failure = _database_failure(
        InvalidPasswordError('password authentication failed for user "oryxen"')
    )

    assert failure is not None
    assert failure[0] == "DATABASE_CREDENTIALS_INVALID"
    assert "POSTGRES_PASSWORD" in failure[1]
    assert "oryxen" not in failure[1]
