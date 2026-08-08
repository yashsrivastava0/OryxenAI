"""Unit tests for Content Architect service helpers (pure functions only)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from oryxenai.agents.content_architect.schemas import (
    ContentArchitectSourceRef,
    ContentArchitectState,
)
from oryxenai.agents.content_architect.service import (
    ContentArchitectOperationError,
    ContentArchitectService,
    _content_hash,
    _elapsed_seconds,
)
from oryxenai.agents.discovery.schemas import DiscoveryApproval, DiscoveryState


def _service() -> ContentArchitectService:
    return ContentArchitectService.__new__(ContentArchitectService)


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


class TestContentHash:
    def test_deterministic_for_same_content(self):
        packs = [{"route_id": "home", "blocks": []}]
        manifest = {"nav": []}
        assert _content_hash(packs, manifest) == _content_hash(packs, manifest)

    def test_differs_for_different_content(self):
        assert _content_hash([{"a": 1}], {}) != _content_hash([{"a": 2}], {})


class TestIdempotencyKey:
    def test_stable_for_same_input(self):
        service = _service()
        key1 = service._idempotency_key("s1", "build", {"a": 1}, {})
        key2 = service._idempotency_key("s1", "build", {"a": 1}, {})
        assert key1 == key2

    def test_differs_for_different_intake(self):
        service = _service()
        key1 = service._idempotency_key("s1", "build", {"a": 1}, {})
        key2 = service._idempotency_key("s1", "build", {"a": 2}, {})
        assert key1 != key2

    def test_differs_for_different_preferences(self):
        service = _service()
        key1 = service._idempotency_key("s1", "build", {"a": 1}, {"goal": "x"})
        key2 = service._idempotency_key("s1", "build", {"a": 1}, {"goal": "y"})
        assert key1 != key2

    def test_differs_for_different_prior_output(self):
        service = _service()
        key1 = service._idempotency_key("s1", "build", {"a": 1}, {}, prior_output={})
        key2 = service._idempotency_key(
            "s1", "build", {"a": 1}, {}, prior_output={"route_plan": [1]}
        )
        assert key1 != key2

    def test_differs_for_different_source_ref(self):
        service = _service()
        key1 = service._idempotency_key(
            "s1", "build", {"a": 1}, {}, source_ref={"discovery_brief_hash": "h1"}
        )
        key2 = service._idempotency_key(
            "s1", "build", {"a": 1}, {}, source_ref={"discovery_brief_hash": "h2"}
        )
        assert key1 != key2

    def test_differs_for_different_revision_request(self):
        service = _service()
        key1 = service._idempotency_key("s1", "build", {"a": 1}, {}, revision_request="")
        key2 = service._idempotency_key(
            "s1", "build", {"a": 1}, {}, revision_request="lead with QueueGuard"
        )
        assert key1 != key2


class TestCheckDiscoveryNotStale:
    def test_passes_when_hash_matches(self):
        service = _service()
        state = ContentArchitectState(
            source_ref=ContentArchitectSourceRef(discovery_brief_hash="hash1")
        )
        discovery = DiscoveryState()
        discovery.brief.approved = DiscoveryApproval(brief_hash="hash1")
        service._check_discovery_not_stale(discovery, state)  # no raise

    def test_raises_when_hash_differs(self):
        service = _service()
        state = ContentArchitectState(
            source_ref=ContentArchitectSourceRef(discovery_brief_hash="hash1")
        )
        discovery = DiscoveryState()
        discovery.brief.approved = DiscoveryApproval(brief_hash="hash2")
        with pytest.raises(ContentArchitectOperationError) as exc_info:
            service._check_discovery_not_stale(discovery, state)
        assert exc_info.value.code == "CONTENT_ARCHITECT_STALE_SOURCE"

    def test_raises_when_discovery_never_approved(self):
        service = _service()
        state = ContentArchitectState(
            source_ref=ContentArchitectSourceRef(discovery_brief_hash="hash1")
        )
        discovery = DiscoveryState()
        with pytest.raises(ContentArchitectOperationError) as exc_info:
            service._check_discovery_not_stale(discovery, state)
        assert exc_info.value.code == "CONTENT_ARCHITECT_STALE_SOURCE"
