"""Safe, provider-neutral durable model-run receipts."""

from __future__ import annotations

from typing import Any

_EXCLUDED_KEYS = frozenset(
    {
        "chain_of_thought",
        "content",
        "raw_input",
        "raw_output",
        "raw_provider_body",
        "raw_response",
        "reasoning",
        "reasoning_content",
        "response_body",
    }
)


def _safe_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _safe_metadata(item)
            for key, item in value.items()
            if str(key).casefold() not in _EXCLUDED_KEYS
        }
    if isinstance(value, list):
        return [_safe_metadata(item) for item in value]
    return value


def durable_model_metadata(
    metadata: dict[str, Any],
    *,
    profile_id: str,
    attempt: int,
) -> dict[str, Any]:
    """Stamp a run and aggregate bounded stage receipts without raw content."""

    sanitized = _safe_metadata(metadata)
    result: dict[str, Any] = sanitized if isinstance(sanitized, dict) else {}
    result["profile_id"] = profile_id
    result["attempt"] = attempt
    stages = result.get("stages")
    if not isinstance(stages, list):
        stages = result.get("model_call_receipts")
    if not isinstance(stages, list):
        return result

    safe_stages = [dict(item) for item in stages if isinstance(item, dict)]
    result["stages"] = safe_stages
    result["latency_ms"] = sum(float(item.get("latency_ms", 0.0) or 0.0) for item in safe_stages)
    usage: dict[str, int | float] = {}
    for item in safe_stages:
        raw_usage = item.get("usage")
        if not isinstance(raw_usage, dict):
            continue
        for key, value in raw_usage.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage[str(key)] = usage.get(str(key), 0) + value
    result["usage"] = usage
    finish_reasons = [
        str(item.get("finish_reason", "") or "")
        for item in safe_stages
        if item.get("finish_reason")
    ]
    result["finish_reason"] = finish_reasons[-1] if finish_reasons else ""
    return result
