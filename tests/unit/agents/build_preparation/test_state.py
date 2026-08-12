from __future__ import annotations

import pytest

from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    BuildPreparationSourceRef,
    BuildPreparationState,
    BuildPreparationStatus,
    HandoffIssue,
    HandoffQualityReport,
    MaterializationResult,
    PackageResult,
    Stage1QueryPlan,
    Stage2SelectionPlan,
)
from oryxenai.agents.build_preparation.state import (
    InvalidTransitionError,
    apply_build_running,
    apply_needs_attention,
    apply_phase3_result,
    apply_result,
    apply_start,
    reset_for_regeneration,
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
    state = apply_result(
        state, scope_hash="scope", routes=[], resource_needs=[], warnings=[], events=[]
    )
    assert state.status is BuildPreparationStatus.READY
    reset = reset_for_regeneration(state)
    assert reset.status is BuildPreparationStatus.NOT_STARTED
    assert reset.model_profile == "build_preparation"
    assert reset.attempt == 2


def test_ready_state_cannot_be_overwritten_by_failure() -> None:
    ready = BuildPreparationState(status=BuildPreparationStatus.READY)
    with pytest.raises(InvalidTransitionError):
        apply_needs_attention(ready, {"code": "error"})


def test_phase3_result_persists_verified_package_metadata() -> None:
    running = apply_start(
        BuildPreparationState(),
        source_ref=BuildPreparationSourceRef(input_projection_hash="projection"),
        model_profile="build_preparation",
        max_attempts=3,
    )
    ready = apply_phase3_result(
        running,
        scope_hash="scope",
        routes=[],
        resource_needs=[],
        query_plan=Stage1QueryPlan(),
        fetched_candidates=[],
        selection_plan=Stage2SelectionPlan(),
        build_context=BuildContextDraft(overview_markdown="# Overview"),
        materialization=MaterializationResult(root_path="", relative_root=""),
        package=PackageResult(
            archive_sha256="a" * 64,
            archive_size_bytes=42,
            file_count=3,
            expires_at="2099-01-01T00:00:00+00:00",
        ),
        warnings=[],
        events=[],
        model_calls=3,
        provider_calls=1,
    )
    assert ready.status is BuildPreparationStatus.READY
    assert ready.current_stage == "phase_3"
    assert ready.package is not None
    assert ready.package.archive_size_bytes == 42


def test_phase3_result_retains_package_when_handoff_is_blocked() -> None:
    running = apply_start(
        BuildPreparationState(),
        source_ref=BuildPreparationSourceRef(input_projection_hash="projection"),
        model_profile="build_preparation",
        max_attempts=3,
    )
    blocked = apply_phase3_result(
        running,
        scope_hash="scope",
        routes=[],
        resource_needs=[],
        query_plan=Stage1QueryPlan(),
        fetched_candidates=[],
        selection_plan=Stage2SelectionPlan(),
        build_context=BuildContextDraft(overview_markdown="# Overview"),
        materialization=MaterializationResult(root_path="", relative_root=""),
        package=PackageResult(
            archive_sha256="a" * 64,
            archive_size_bytes=42,
            file_count=3,
            expires_at="2099-01-01T00:00:00+00:00",
        ),
        warnings=[],
        events=[],
        model_calls=3,
        provider_calls=1,
        handoff_report=HandoffQualityReport(
            handoff_eligible=False,
            status="needs_attention",
            issues=[
                HandoffIssue(
                    code="REQUIRED_RESOURCE_UNRESOLVED",
                    need_id="editorial-hero-image",
                    message="The required editorial image has no eligible selection.",
                )
            ],
        ),
    )

    assert blocked.status is BuildPreparationStatus.NEEDS_ATTENTION
    assert blocked.package is not None
    assert blocked.handoff_report is not None
    assert blocked.latest_error is not None
    assert blocked.latest_error["code"] == "BUILD_PREPARATION_HANDOFF_BLOCKED"
