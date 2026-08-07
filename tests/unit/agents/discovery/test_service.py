"""Unit tests for Discovery service helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from oryxenai.agents.discovery.service import DiscoveryService, _brief_hash, _elapsed_seconds


class TestElapsedSeconds:
    def test_none_started_at(self):
        assert _elapsed_seconds(None) is None

    def test_invalid_timestamp(self):
        assert _elapsed_seconds("not-a-date") is None

    def test_past_timestamp_returns_positive(self):
        started = (datetime.now(UTC) - timedelta(seconds=65)).isoformat()
        elapsed = _elapsed_seconds(started)
        assert elapsed is not None
        assert 60 <= elapsed <= 70

    def test_future_timestamp_clamped(self):
        started = (datetime.now(UTC) + timedelta(seconds=10)).isoformat()
        assert _elapsed_seconds(started) == 0.0


class TestBriefHash:
    def test_deterministic_for_same_markdown(self):
        markdown = "# Portfolio Discovery Brief\n\nContent."
        assert _brief_hash(markdown) == _brief_hash(markdown)

    def test_differs_for_different_markdown(self):
        assert _brief_hash("brief one") != _brief_hash("brief two")


class TestIdempotencyKey:
    def test_stable_for_same_input(self):
        service = DiscoveryService.__new__(DiscoveryService)
        key1 = service._idempotency_key("s1", "understand_and_question", {"message": "x"}, {})
        key2 = service._idempotency_key("s1", "understand_and_question", {"message": "x"}, {})
        assert key1 == key2

    def test_differs_for_different_input(self):
        service = DiscoveryService.__new__(DiscoveryService)
        key1 = service._idempotency_key("s1", "understand_and_question", {"message": "x"}, {})
        key2 = service._idempotency_key("s1", "understand_and_question", {"message": "y"}, {})
        assert key1 != key2

    def test_differs_for_different_operation(self):
        service = DiscoveryService.__new__(DiscoveryService)
        key1 = service._idempotency_key("s1", "understand_and_question", {"message": "x"}, {})
        key2 = service._idempotency_key("s1", "build_or_revise_brief", {"message": "x"}, {})
        assert key1 != key2

    def test_differs_for_different_memory(self):
        service = DiscoveryService.__new__(DiscoveryService)
        key1 = service._idempotency_key(
            "s1", "understand_and_question", {"message": "x"}, {}, memory={"intent_summary": "a"}
        )
        key2 = service._idempotency_key(
            "s1", "understand_and_question", {"message": "x"}, {}, memory={"intent_summary": "b"}
        )
        assert key1 != key2

    def test_same_memory_same_key(self):
        service = DiscoveryService.__new__(DiscoveryService)
        key1 = service._idempotency_key(
            "s1", "understand_and_question", {"message": "x"}, {}, memory={"intent_summary": "a"}
        )
        key2 = service._idempotency_key(
            "s1", "understand_and_question", {"message": "x"}, {}, memory={"intent_summary": "a"}
        )
        assert key1 == key2

    def test_differs_for_existing_brief(self):
        service = DiscoveryService.__new__(DiscoveryService)
        key1 = service._idempotency_key(
            "s1", "build_or_revise_brief", {"message": "x"}, {}, existing_brief=""
        )
        key2 = service._idempotency_key(
            "s1", "build_or_revise_brief", {"message": "x"}, {}, existing_brief="# old brief"
        )
        assert key1 != key2
