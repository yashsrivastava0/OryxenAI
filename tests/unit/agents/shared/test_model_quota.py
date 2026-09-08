from __future__ import annotations

from oryxenai.agents.shared.model_quota import (
    CapacityRegistry,
    CapacitySnapshot,
    _bounded_metadata,
    _extract_capacity_limits,
    _extract_external_identifier,
    _extract_key_identifier,
    _extract_usage_totals,
)


def test_quota_parsing_uses_explicit_provider_observations_only() -> None:
    payloads = [
        {
            "limits": {
                "requests_per_minute": 10,
                "tokens_per_minute": "2000",
                "requests_per_day": 100,
            },
            "usage": {"requests": 3, "input_tokens": 450},
        }
    ]

    assert _extract_capacity_limits(payloads) == {
        "request_limit": 10,
        "input_token_limit": 2000,
        "daily_request_limit": 100,
    }
    assert _extract_usage_totals(payloads) == {"requests": 3, "input_tokens": 450}


def test_experiential_key_limit_lookup_ignores_generic_event_ids() -> None:
    payloads = [{"id": "event-123", "request_id": "request-456"}]
    assert _extract_external_identifier(payloads) == "event-123"
    assert _extract_key_identifier(payloads) == ""
    assert _extract_key_identifier([{"key_id": "key-789"}]) == "key-789"


def test_observation_metadata_redacts_credentials_and_bounds_text() -> None:
    value = _bounded_metadata(
        {"api_key": "secret", "nested": {"authorization": "Bearer secret"}, "text": "x" * 3000}
    )
    assert value == {"nested": {}, "text": "x" * 2000}


def test_capacity_registry_does_not_select_a_cooldown_source() -> None:
    registry = CapacityRegistry()
    registry.observe(CapacitySnapshot(provider="gemini", source_id="GEMINI_1", cooldown_until=10**12))
    registry.observe(CapacitySnapshot(provider="gemini", source_id="GEMINI_2"))
    assert registry.order_profiles([("one", "GEMINI_1"), ("two", "GEMINI_2")]) == ["two"]


def test_capacity_observation_does_not_drop_inflight_reservations() -> None:
    registry = CapacityRegistry(0.8)
    registry.observe(
        CapacitySnapshot(
            provider="gemini",
            source_id="GEMINI_1",
            request_limit=10,
            input_token_limit=1000,
        )
    )
    registry.reserve("GEMINI_1", input_tokens=200)
    registry.observe(
        CapacitySnapshot(
            provider="gemini",
            source_id="GEMINI_1",
            request_limit=10,
            observed_requests=1,
            input_token_limit=1000,
        )
    )
    snapshot = registry.snapshot("GEMINI_1")
    assert snapshot is not None
    assert snapshot.reserved_requests == 1
    assert snapshot.reserved_input_tokens == 200
