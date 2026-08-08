"""Explicit provider capability model.

Capabilities represent what a provider endpoint supports. They are
declared, never silently assumed. The OpenCode Go adapter consults this
model before sending parameters such as ``store`` or thinking-mode keys,
so an unsupported parameter is never relied on.

The defaults in ``DEFAULT_OPENCODE_GO`` describe the observed shape of
the configured OpenCode Go endpoint and are confirmed/refuted by the
opt-in live capability smoke test (``tests/live/``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelCapabilities(BaseModel):
    """Declared capability set for a provider/model endpoint."""

    model_config = ConfigDict(extra="forbid")

    json_object_mode: bool
    json_schema_mode: bool
    thinking_mode: bool
    reasoning_content: bool
    temperature_control: bool
    usage_metadata: bool
    response_id: bool
    context_cache_metadata: bool
    supports_store_parameter: bool
    uses_max_completion_tokens: bool


DEFAULT_OPENCODE_GO = ModelCapabilities(
    json_object_mode=True,
    json_schema_mode=False,
    thinking_mode=True,
    reasoning_content=True,
    temperature_control=True,
    usage_metadata=True,
    response_id=True,
    context_cache_metadata=False,
    supports_store_parameter=True,
    uses_max_completion_tokens=False,
)
