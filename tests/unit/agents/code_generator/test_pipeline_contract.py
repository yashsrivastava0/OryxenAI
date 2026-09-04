from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.core.pipeline_contract import (
    PIPELINE_V3,
    PIPELINE_V4,
    PIPELINE_V5,
    is_verification_kind,
    stage_job_kind,
    stage_scope,
    uses_blueprint,
    uses_v5_namespace,
)


@pytest.mark.parametrize("stage", ["plan", "acquire", "generate"])
def test_v5_stage_names_are_isolated_from_legacy_workers(stage: str) -> None:
    assert stage_job_kind(stage, PIPELINE_V5).startswith("code_generator.v5.")
    assert stage_job_kind(stage, PIPELINE_V5) != stage_job_kind(stage, PIPELINE_V4)
    assert stage_scope(stage, PIPELINE_V5) == stage_job_kind(stage, PIPELINE_V5)


def test_legacy_versions_keep_read_compatible_queue_names() -> None:
    assert stage_job_kind("plan", PIPELINE_V3) == "code_generator.plan"
    assert stage_job_kind("verify", PIPELINE_V4) == "code_generator.verify_and_preview"
    assert is_verification_kind("code_generator.verify_and_preview")
    assert is_verification_kind("code_generator.v5.verify_and_preview")
    assert not is_verification_kind("code_generator.v5.generate")


def test_blueprint_support_is_capability_based() -> None:
    assert not uses_blueprint(PIPELINE_V3)
    assert uses_blueprint(PIPELINE_V4)
    assert uses_blueprint(PIPELINE_V5)
    assert uses_v5_namespace(PIPELINE_V5)
    assert not uses_v5_namespace(PIPELINE_V4)


def test_unknown_stage_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown Code Generator stage"):
        stage_job_kind("review", PIPELINE_V5)
