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
    if not isinstance(stages, list) and (
        isinstance(result.get("telemetry"), dict) or isinstance(result.get("cache"), dict)
    ):
        # Discovery and the single-call Build Preparation operation expose a
        # flat receipt; normalize them to the same aggregate shape as the
        # adaptive multi-call agents.
        stages = [result]
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
    cost_telemetry: dict[str, Any] = {}
    cost_unit = ""
    for item in safe_stages:
        telemetry = item.get("telemetry")
        if isinstance(telemetry, dict):
            for key in (
                "input_characters",
                "output_characters",
                "charged_input_characters",
                "charged_output_characters",
                "estimated_cost",
            ):
                value = telemetry.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    cost_telemetry[key] = cost_telemetry.get(key, 0) + value
            if not cost_unit and telemetry.get("cost_unit"):
                cost_unit = str(telemetry["cost_unit"])
    if cost_telemetry:
        if cost_unit:
            cost_telemetry["cost_unit"] = cost_unit
        result["cost_telemetry"] = cost_telemetry

    cache_summary: dict[str, Any] = {
        "cache_hits": 0,
        "cache_misses": 0,
        "cache_stored": 0,
        "wait_timeouts": 0,
        "avoided_input_characters": 0,
        "avoided_output_characters": 0,
        "avoided_cost": 0.0,
        "stage_count": len(safe_stages),
    }
    for item in safe_stages:
        cache = item.get("cache")
        if not isinstance(cache, dict) or not cache.get("enabled", False):
            continue
        if cache.get("cache_hit") is True:
            cache_summary["cache_hits"] += 1
            for key in ("avoided_input_characters", "avoided_output_characters"):
                value = cache.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    cache_summary[key] += value
            avoided_cost = cache.get("avoided_cost")
            if isinstance(avoided_cost, (int, float)) and not isinstance(avoided_cost, bool):
                cache_summary["avoided_cost"] += avoided_cost
        else:
            cache_summary["cache_misses"] += 1
        if cache.get("stored") is True:
            cache_summary["cache_stored"] += 1
        if cache.get("wait_timeout") is True:
            cache_summary["wait_timeouts"] += 1
        if not cache_summary.get("cost_unit") and cache.get("cost_unit"):
            cache_summary["cost_unit"] = str(cache["cost_unit"])
    if int(cache_summary["cache_hits"]) or int(cache_summary["cache_misses"]):
        cache_summary["saved_calls"] = int(cache_summary["cache_hits"])
        result["cache_summary"] = cache_summary
    finish_reasons = [
        str(item.get("finish_reason", "") or "")
        for item in safe_stages
        if item.get("finish_reason")
    ]
    result["finish_reason"] = finish_reasons[-1] if finish_reasons else ""
    return result


def frontend_cache_receipt(
    model_metadata: Any,
    *,
    run_id: str = "",
) -> dict[str, Any]:
    """Return the minimal truthful cache receipt safe for the product UI."""

    if not isinstance(model_metadata, dict):
        return {}
    summary = model_metadata.get("cache_summary")
    if not isinstance(summary, dict):
        return {}
    hits = summary.get("cache_hits", 0)
    if not isinstance(hits, int) or hits <= 0:
        return {}
    receipt: dict[str, Any] = {
        "cache_hit": True,
        "cached_stage_count": hits,
        "stage_count": int(summary.get("stage_count", hits) or hits),
        "saved_calls": int(summary.get("saved_calls", hits) or hits),
    }
    if run_id:
        receipt["run_id"] = run_id
    return receipt
