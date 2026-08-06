"""Total attempt and retry budget for a logical Discovery operation.

One logical Discovery operation (Call A or Call B) may consume at most
``total_model_calls_max`` model requests, counting:

- the initial completed response, and
- one completed-response recovery attempt (used for empty/whitespace,
  truncated, malformed JSON, or semantically invalid output — the
  semantic repair *is* the recovery attempt when used for semantic
  invalidity).

Transport retries (connection failure, timeout, rate limit, retryable
5xx) are handled separately by the provider SDK and are bounded by the
profile's ``max_retries``. A worker retry must not blindly restart an
already completed provider response; the worker-level ``max_attempts``
only re-runs the whole logical operation from the persisted input.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AttemptBudget(BaseModel):
    """Bounded attempt policy for model-backed Discovery operations."""

    model_config = ConfigDict(extra="forbid")

    transport_retry: int = Field(default=1, ge=0)
    completed_response_recovery: int = Field(default=1, ge=0, le=1)
    semantic_repair: int = Field(default=1, ge=0, le=1)
    worker_max_attempts: int = Field(default=3, ge=1)

    @property
    def total_model_calls_max(self) -> int:
        """Maximum model requests per logical operation.

        1 initial + up to 1 recovery/repair = at most 2 model calls per
        logical operation (transport retries are SDK-internal).
        """
        return 1 + self.completed_response_recovery

    def remaining(self, model_calls_used: int) -> int:
        return max(0, self.total_model_calls_max - model_calls_used)


def default_budget() -> AttemptBudget:
    return AttemptBudget()
