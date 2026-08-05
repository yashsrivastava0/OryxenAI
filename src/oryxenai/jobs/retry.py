"""Retry scheduling — delay calculation and retry decisions."""

from __future__ import annotations

import random

from oryxenai.jobs.contracts import JobError


def delay_for_attempt(
    attempt: int,
    base_delay: float,
    max_delay: float,
    jitter: bool = True,
) -> float:
    """Exponential backoff with optional jitter."""
    delay: float = min(base_delay * (2 ** (attempt - 1)), max_delay)
    if jitter:
        r: float = random.random()  # noqa: S311
        delay *= 0.75 + (r * 0.5)
    return delay


def should_retry(
    error: JobError | None,
    attempt: int,
    max_attempts: int,
) -> bool:
    """Decide whether a failed job should be retried."""
    if error is None:
        return False
    if not error.retryable:
        return False
    return attempt < max_attempts
