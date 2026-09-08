"""Safe access to the complete persisted output of an agent run.

Agent runs keep the authoritative, decoded agent response in
``AgentRun.output_payload``.  The normal stage state is intentionally a
presentation projection and cannot be used to reconstruct a complete output:
doing so drops fields that a downstream consumer may need.  This module is a
small, provider-neutral boundary for exposing that persisted response to an
authorized product client without leaking transport state or credentials.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
from typing import Any
from uuid import UUID

# These are persistence/transport fields, not agent-owned output.  The
# explicit allowlist is deliberately small: unknown and future agent fields
# must survive unchanged.
_TRANSPORT_KEYS = frozenset(
    {
        "input_payload",
        "state_before",
        "state_after",
        "model_metadata",
        "error_payload",
        "job",
        "jobs",
        "job_id",
        "session_id",
        "request_id",
        "authorization",
        "request_headers",
        "debug_mirror_path",  # server-local path, useful only to operators
    }
)

# A provider bug must not turn an accidentally persisted credential into a
# copyable browser artifact.  These names are security fields, not ordinary
# agent prose, and are removed recursively.
_CREDENTIAL_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "client_secret",
        "secret_key",
        "authorization",
        "bearer_token",
        "password",
    }
)


def _clean(value: Any, *, top_level: bool = False) -> Any:
    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            normalized = key.casefold()
            if (top_level and normalized in _TRANSPORT_KEYS) or normalized in _CREDENTIAL_KEYS:
                continue
            cleaned[key] = _clean(raw_value)
        return cleaned
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if isinstance(value, tuple):
        return [_clean(item) for item in value]
    return deepcopy(value)


def public_agent_output(payload: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Return an exact agent-owned JSON projection, or ``None``.

    No field allowlist is applied.  The only omissions are explicitly known
    platform transport/security fields above.  The persisted payload is
    already JSONB, so the returned value is JSON-serializable by construction.
    """

    if not isinstance(payload, Mapping):
        return None
    cleaned = _clean(payload, top_level=True)
    return cleaned if isinstance(cleaned, dict) else None


RunLoader = Callable[[UUID], Awaitable[Any | None]]


async def public_output_for_run(
    loader: RunLoader | None, run_id: str | None
) -> dict[str, Any] | None:
    """Load one successful run and expose only its safe agent output."""

    if not run_id or not callable(loader):
        return None
    try:
        run = await loader(UUID(str(run_id)))
    except (TypeError, ValueError):
        return None
    if run is None or getattr(run, "status", "") != "succeeded":
        return None
    payload = getattr(run, "output_payload", None)
    return public_agent_output(payload if isinstance(payload, Mapping) else None)


async def public_discovery_outputs(
    loader: RunLoader | None,
    *,
    questions_run_id: str | None,
    brief_run_id: str | None,
) -> dict[str, dict[str, Any] | None] | None:
    """Return Discovery's complete output for both model operations.

    Discovery intentionally has two distinct operation envelopes.  Keeping
    both under stable operation names lets a caller inspect the question
    generation response and the final brief response without exposing the raw
    intake or job envelope.
    """

    questions = await public_output_for_run(loader, questions_run_id)
    brief = await public_output_for_run(loader, brief_run_id)
    if questions is None and brief is None:
        return None
    return {
        "understand_and_question": questions,
        "build_or_revise_brief": brief,
    }
