"""The /code-generator envelope the Studio frontend depends on.

Shared by the real API test and the fake backend the browser flows run against, so
the fake can never drift from what the server actually returns.
"""

from __future__ import annotations

ENVELOPE_KEYS = {"session_id", "session_revision", "code_generator", "versions", "chat", "jobs"}

STATE_KEYS = {
    "status",
    "theme_id",
    "source_ref",
    "active_version_id",
    "active_version_number",
    "in_flight",
    "last_error",
    "builds_started",
    "routing_policy_version",
    "routing_policy_fingerprint",
    "started_at",
    "updated_at",
}

# Keys the frontend adapter reads from each part. The real server may send more.
FRONTEND_STATE_KEYS = {
    "status",
    "active_version_id",
    "active_version_number",
    "in_flight",
    "last_error",
}
FRONTEND_IN_FLIGHT_KEYS = {
    "version_id",
    "origin",
    "stage",
    "instruction",
    "elapsed_seconds",
    "job_id",
}
FRONTEND_VERSION_KEYS = {
    "id",
    "seq",
    "version_number",
    "origin",
    "status",
    "instruction",
    "restricted",
    "created_at",
    "completed_at",
    "summary",
}
FRONTEND_CHAT_KEYS = {"id", "seq", "role", "kind", "body", "version_id", "created_at"}
FRONTEND_FAILURE_KEYS = {
    "code",
    "stage",
    "summary",
    "cause",
    "where",
    "owner",
    "retryable",
    "action",
    "issue_count",
    "reference",
    "issues",
}
GRANT_KEYS = {"url", "expires_at", "expires_in_seconds", "version_id", "version_number"}
