"""Unit tests for Visual Design Director service helpers (pure functions only)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from oryxenai.agents.content_architect.schemas import (
    ContentArchitectApproval,
    ContentArchitectState,
    RoutePlanEntry,
)
from oryxenai.agents.visual_design_director.schemas import (
    VisualDesignDirectorSourceRef,
    VisualDesignDirectorState,
)
from oryxenai.agents.visual_design_director.service import (
    VisualDesignDirectorOperationError,
    VisualDesignDirectorService,
    _elapsed_seconds,
    _visual_direction_hash,
    compute_content_architect_visual_input_hash,
    compute_route_publication_hash,
)


def _service() -> VisualDesignDirectorService:
    return VisualDesignDirectorService.__new__(VisualDesignDirectorService)


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


class TestVisualDirectionHash:
    def test_deterministic_for_same_content(self):
        pages = [{"route_id": "home"}]
        language = {"creative_thesis": "x"}
        shared = {"card_treatment": "flat"}
        assets: list[dict[str, object]] = []
        assert _visual_direction_hash(pages, language, shared, assets) == _visual_direction_hash(
            pages, language, shared, assets
        )

    def test_differs_for_different_content(self):
        assert _visual_direction_hash([{"a": 1}], {}, {}, []) != _visual_direction_hash(
            [{"a": 2}], {}, {}, []
        )

    def test_includes_compiler_relevant_direction_fields(self):
        base = _visual_direction_hash(
            [],
            {},
            {},
            [],
            navigation_direction={"placement": "top"},
            motion_system={"global_character": "quiet"},
            resource_candidates=[{"resource_id": "hero"}],
        )
        changed = _visual_direction_hash(
            [],
            {},
            {},
            [],
            navigation_direction={"placement": "rail"},
            motion_system={"global_character": "quiet"},
            resource_candidates=[{"resource_id": "hero"}],
        )
        assert base != changed


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
        key1 = service._idempotency_key("s1", "build", {"a": 1}, {"visual_tone": "x"})
        key2 = service._idempotency_key("s1", "build", {"a": 1}, {"visual_tone": "y"})
        assert key1 != key2

    def test_differs_for_different_prior_output(self):
        service = _service()
        key1 = service._idempotency_key("s1", "build", {"a": 1}, {}, prior_output={})
        key2 = service._idempotency_key("s1", "build", {"a": 1}, {}, prior_output={"pages": [1]})
        assert key1 != key2

    def test_differs_for_different_source_ref(self):
        service = _service()
        key1 = service._idempotency_key(
            "s1", "build", {"a": 1}, {}, source_ref={"content_architect_content_hash": "h1"}
        )
        key2 = service._idempotency_key(
            "s1", "build", {"a": 1}, {}, source_ref={"content_architect_content_hash": "h2"}
        )
        assert key1 != key2

    def test_differs_for_different_revision_request(self):
        service = _service()
        key1 = service._idempotency_key("s1", "build", {"a": 1}, {}, revision_request="")
        key2 = service._idempotency_key(
            "s1", "build", {"a": 1}, {}, revision_request="use a lighter palette"
        )
        assert key1 != key2


def _route_plan_dump(*, publication_status: str = "approved") -> list[dict[str, object]]:
    return [
        RoutePlanEntry(
            route_id="home", path="/", purpose="p", publication_status=publication_status
        ).model_dump(mode="json")
    ]


class TestComputeRoutePublicationHash:
    def test_deterministic_for_same_input(self):
        plan = _route_plan_dump()
        assert compute_route_publication_hash(plan) == compute_route_publication_hash(plan)

    def test_differs_when_publication_status_differs(self):
        approved = compute_route_publication_hash(_route_plan_dump(publication_status="approved"))
        pending = compute_route_publication_hash(_route_plan_dump(publication_status="pending"))
        assert approved != pending


class TestComputeContentArchitectVisualInputHash:
    def test_changes_when_visual_input_changes(self):
        content = ContentArchitectState(
            approved=ContentArchitectApproval(content_hash="hash1"),
            site_story_strategy={"presentation_mode": "single_page"},
        )
        changed = content.model_copy(deep=True)
        changed.media_status = {"project_images": "approved"}
        assert compute_content_architect_visual_input_hash(content) != (
            compute_content_architect_visual_input_hash(changed)
        )


class TestCheckContentArchitectNotStale:
    def test_passes_when_hash_and_route_publication_match(self):
        service = _service()
        route_plan_dump = _route_plan_dump()
        state = VisualDesignDirectorState(
            source_ref=VisualDesignDirectorSourceRef(
                content_architect_content_hash="hash1",
                route_publication_hash=compute_route_publication_hash(route_plan_dump),
            )
        )
        content_architect = ContentArchitectState(
            approved=ContentArchitectApproval(content_hash="hash1"),
            route_plan=[RoutePlanEntry(**route_plan_dump[0])],
        )
        service._check_content_architect_not_stale(content_architect, state)  # no raise

    def test_raises_when_hash_differs(self):
        service = _service()
        route_plan_dump = _route_plan_dump()
        state = VisualDesignDirectorState(
            source_ref=VisualDesignDirectorSourceRef(
                content_architect_content_hash="hash1",
                route_publication_hash=compute_route_publication_hash(route_plan_dump),
            )
        )
        content_architect = ContentArchitectState(
            approved=ContentArchitectApproval(content_hash="hash2"),
            route_plan=[RoutePlanEntry(**route_plan_dump[0])],
        )
        with pytest.raises(VisualDesignDirectorOperationError) as exc_info:
            service._check_content_architect_not_stale(content_architect, state)
        assert exc_info.value.code == "VISUAL_DESIGN_DIRECTOR_STALE_SOURCE"

    def test_raises_when_route_publication_status_changes_with_same_content_hash(self):
        """A route flipping pending -> approved with no other content change
        must still be caught, even though Content Architect's own
        content_hash never changes for a publication_status-only edit."""
        service = _service()
        state = VisualDesignDirectorState(
            source_ref=VisualDesignDirectorSourceRef(
                content_architect_content_hash="hash1",
                route_publication_hash=compute_route_publication_hash(
                    _route_plan_dump(publication_status="pending")
                ),
            )
        )
        content_architect = ContentArchitectState(
            approved=ContentArchitectApproval(content_hash="hash1"),
            route_plan=[RoutePlanEntry(**_route_plan_dump(publication_status="approved")[0])],
        )
        with pytest.raises(VisualDesignDirectorOperationError) as exc_info:
            service._check_content_architect_not_stale(content_architect, state)
        assert exc_info.value.code == "VISUAL_DESIGN_DIRECTOR_STALE_SOURCE"

    def test_raises_when_content_architect_never_approved(self):
        service = _service()
        state = VisualDesignDirectorState(
            source_ref=VisualDesignDirectorSourceRef(content_architect_content_hash="hash1")
        )
        content_architect = ContentArchitectState()
        with pytest.raises(VisualDesignDirectorOperationError) as exc_info:
            service._check_content_architect_not_stale(content_architect, state)
        assert exc_info.value.code == "VISUAL_DESIGN_DIRECTOR_STALE_SOURCE"
