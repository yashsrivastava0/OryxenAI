from __future__ import annotations

import pytest

from oryxenai.agents.build_preparation.schemas import (
    BuildPreparationSourceRef,
    BuildPreparationState,
    BuildPreparationStatus,
)
from oryxenai.agents.build_preparation.state import (
    InvalidTransitionError,
    apply_build_running,
    apply_needs_attention,
    apply_result,
    apply_start,
    reset_for_regeneration,
)


def _apply_result(state: BuildPreparationState) -> BuildPreparationState:
    return apply_result(
        state,
        scope_hash="scope",
        routes=[],
        resource_needs=[],
        resource_index=[],
        component_index=[],
        content_brief_markdown="# Content brief",
        visual_brief_markdown="# Visual brief",
        content_brief_hash="a" * 64,
        visual_brief_hash="b" * 64,
        target_contract="react-vite-v1",
        recommended_dependencies=[],
        debug_mirror_path="",
        warnings=[],
        events=[],
        model_calls=1,
        provider_calls=2,
    )


def test_state_machine_start_result_and_regeneration() -> None:
    state = apply_start(
        BuildPreparationState(),
        source_ref=BuildPreparationSourceRef(input_projection_hash="projection"),
        model_profile="build_preparation",
        max_attempts=3,
    )
    assert state.status is BuildPreparationStatus.RUNNING
    state = apply_build_running(state, "run", "job", 1, 3)
    state = _apply_result(state)
    assert state.status is BuildPreparationStatus.READY
    assert state.content_brief_markdown == "# Content brief"
    assert state.visual_brief_markdown == "# Visual brief"
    reset = reset_for_regeneration(state)
    assert reset.status is BuildPreparationStatus.NOT_STARTED
    assert reset.model_profile == "build_preparation"
    assert reset.attempt == 2


def test_ready_state_cannot_be_overwritten_by_failure() -> None:
    ready = BuildPreparationState(status=BuildPreparationStatus.READY)
    with pytest.raises(InvalidTransitionError):
        apply_needs_attention(ready, {"code": "error"})


def test_result_persists_both_briefs_and_hashes() -> None:
    running = apply_start(
        BuildPreparationState(),
        source_ref=BuildPreparationSourceRef(input_projection_hash="projection"),
        model_profile="build_preparation",
        max_attempts=3,
    )
    ready = _apply_result(running)
    assert ready.status is BuildPreparationStatus.READY
    assert ready.current_stage == "compose_visual_brief"
    assert ready.content_brief_hash == "a" * 64
    assert ready.visual_brief_hash == "b" * 64
    assert ready.latest_error is None


def test_needs_attention_records_error_and_allows_restart() -> None:
    running = apply_start(
        BuildPreparationState(),
        source_ref=BuildPreparationSourceRef(input_projection_hash="projection"),
        model_profile="build_preparation",
        max_attempts=3,
    )
    blocked = apply_needs_attention(
        running, {"code": "BUILD_PREPARATION_MODEL_OUTPUT_INVALID", "message": "bad output"}
    )
    assert blocked.status is BuildPreparationStatus.NEEDS_ATTENTION
    assert blocked.latest_error is not None
    assert blocked.latest_error["code"] == "BUILD_PREPARATION_MODEL_OUTPUT_INVALID"
    restarted = apply_start(
        blocked,
        source_ref=BuildPreparationSourceRef(input_projection_hash="projection"),
        model_profile="build_preparation",
        max_attempts=3,
    )
    assert restarted.status is BuildPreparationStatus.RUNNING
    assert restarted.latest_error is None
