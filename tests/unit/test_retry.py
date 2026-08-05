"""Unit tests for retry scheduling logic."""

from __future__ import annotations

from oryxenai.jobs.contracts import JobError, permanent, retryable
from oryxenai.jobs.retry import delay_for_attempt, should_retry


def test_delay_attempt_1_no_jitter():
    """delay_for_attempt(attempt=1, jitter=False) returns exactly base_delay."""
    result = delay_for_attempt(attempt=1, base_delay=1.0, max_delay=10.0, jitter=False)
    assert result == 1.0


def test_delay_attempt_2_no_jitter():
    """delay_for_attempt(attempt=2, jitter=False) returns exactly base_delay * 2."""
    result = delay_for_attempt(attempt=2, base_delay=1.0, max_delay=10.0, jitter=False)
    assert result == 2.0


def test_delay_attempt_5_capped():
    """delay_for_attempt(attempt=5, jitter=False) is capped at max_delay."""
    result = delay_for_attempt(attempt=5, base_delay=1.0, max_delay=10.0, jitter=False)
    assert result == 10.0


def test_delay_attempt_1_with_jitter():
    """delay_for_attempt with jitter returns value in expected range."""
    result = delay_for_attempt(attempt=1, base_delay=1.0, max_delay=10.0, jitter=True)
    assert 0.75 <= result <= 1.25


def test_should_retry_retryable_below_max():
    """should_retry returns True for retryable error with attempt < max."""
    err: JobError | None = retryable("ERR", "msg")
    assert should_retry(err, attempt=1, max_attempts=3) is True


def test_should_retry_permanent_error():
    """should_retry returns False for a permanent error."""
    err: JobError | None = permanent("ERR", "msg")
    assert should_retry(err, attempt=1, max_attempts=3) is False


def test_should_retry_attempt_exceeds_max():
    """should_retry returns False when attempt >= max_attempts."""
    err: JobError | None = retryable("ERR", "msg")
    assert should_retry(err, attempt=3, max_attempts=3) is False


def test_should_retry_none_error():
    """should_retry returns False for None error."""
    assert should_retry(None, attempt=1, max_attempts=3) is False
