from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from oryxenai.agents.code_generator.core.development_schemas import (
    AdmittedInputReference,
    GenerationProjection,
    QualityFindingV2,
    SafeIssue,
    SourceDiagnostic,
)
from oryxenai.agents.code_generator.core.development_service import _projection
from oryxenai.agents.code_generator.core.finding_policy import effective_finding_severity
from oryxenai.agents.code_generator.core.terminal_failure import (
    build_terminal_failure_report,
    normalize_terminal_failure,
)


def test_subjective_model_finding_ids_do_not_become_functional_blockers() -> None:
    for code in (
        "blueprint-distinctive-move-missing",
        "composition-missing-section-rail",
        "typography-role-coverage",
        "MISSING_VISUAL_BALANCE",
    ):
        finding = QualityFindingV2(
            finding_id=f"finding-{code}",
            severity="blocking",
            owner_work_unit_id="route-home",
            code=code,
            file="src/routes/home/index.tsx",
            line=1,
            marker="data-section",
            evidence="The composition is missing visual balance.",
            requested_outcome="Improve the visual composition if desired.",
        )
        assert effective_finding_severity(finding) == "advisory"


def test_explicit_functional_finding_still_blocks() -> None:
    finding = QualityFindingV2(
        finding_id="finding-hidden",
        severity="advisory",
        owner_work_unit_id="route-home",
        code="interaction-hidden-approved-content",
        file="src/routes/home/index.tsx",
        line=1,
        marker="data-section",
        evidence="Approved content is hidden behind an interaction.",
        requested_outcome="Keep the approved content visible.",
    )
    assert effective_finding_severity(finding) == "blocking"


def _generation_projection() -> GenerationProjection:
    return GenerationProjection(
        generation_id="generation-1",
        input_receipt_hash="input-hash",
        site_plan_hash="plan-hash",
        resource_ledger_hash="resource-hash",
        dependency_ledger_hash="dependency-hash",
        phase="integrating",
        repair_fingerprint_counts={"fingerprint": 2},
        diagnostics=[
            SourceDiagnostic(
                diagnostic_id="source-diagnostic-1",
                group="source_contract",
                code="SOURCE_CONTRACT_INVALID",
                phase="generation",
                normalized_message="The source contract needs correction.",
                fingerprint="source-fingerprint",
            )
        ],
    )


def test_terminal_failure_report_is_strict_and_safe() -> None:
    report = build_terminal_failure_report(
        run_id="run-1",
        issue=SafeIssue(
            code="INTEGRATION_REVIEW_UNRESOLVED",
            message="The bounded quality review did not converge.",
            next_action="Review the findings and start a corrected run.",
        ),
        projection=_generation_projection(),
    )

    assert report.terminal_code == "INTEGRATION_REVIEW_UNRESOLVED"
    assert report.generation_id == "generation-1"
    assert report.input_plan_source_build_hashes["site_plan"] == "plan-hash"
    assert report.fingerprint_occurrences == {"fingerprint": 2}
    assert {item.code for item in report.diagnostics} == {
        "INTEGRATION_REVIEW_UNRESOLVED",
        "SOURCE_CONTRACT_INVALID",
    }


def test_legacy_terminal_failure_is_normalized_for_readback() -> None:
    payload = normalize_terminal_failure(
        {
            "stage": "generation",
            "code": "INTEGRATION_REVIEW_UNRESOLVED",
            "message": "The bounded quality review did not converge.",
            "first_issue": {"code": "INTEGRATION_REVIEW_UNRESOLVED"},
        },
        run_id="run-1",
        projection=_generation_projection(),
    )

    assert payload is not None
    assert payload["terminal_code"] == "INTEGRATION_REVIEW_UNRESOLVED"
    assert "stage" not in payload
    assert "code" not in payload


def test_development_projection_reads_a_legacy_terminal_failure() -> None:
    run_id = uuid4()
    now = datetime.now(UTC)
    run = SimpleNamespace(
        id=run_id,
        status="needs_attention",
        revision=1,
        current_attempt=1,
        run_mode="development",
        portfolio_session_id=None,
        auto_advance=True,
        coordinator_stage="integrating",
        pipeline_contract_version="code-generator-v5-quality-v3",
        trace_id="trace-1",
        active_attempt_id=None,
        selected_pack_receipt=None,
        build_preparation_source_ref=None,
        artifact_reference=None,
        artifact_receipt=None,
        preflight_receipt=None,
        creative_direction=None,
        integration_review=None,
        background_job_id=None,
        input_reference=AdmittedInputReference(
            mode="fixture",
            source_id="fixture-1",
            original_filename="fixture.json",
            source_sha256="source-hash",
            stored_relative_path="fixtures/fixture.json",
            size_bytes=1,
        ).model_dump(mode="json"),
        input_receipt=None,
        context_receipt=None,
        planner_receipt=None,
        plan_summary={},
        acquire_receipt=None,
        resource_ledger=None,
        dependency_ledger=None,
        acquire_summary={},
        plan_delta_count=0,
        generation_job_id=None,
        generation_projection=_generation_projection().model_dump(mode="json"),
        source_checkpoint=None,
        source_summary={},
        verification_job_id=None,
        verification_projection=None,
        candidate_artifact=None,
        pending_promotion=None,
        active_preview=None,
        export_receipt=None,
        terminal_failure={
            "stage": "generation",
            "code": "INTEGRATION_REVIEW_UNRESOLVED",
            "message": "The bounded quality review did not converge.",
        },
        issues=[],
        created_at=now,
        updated_at=now,
    )

    projection = _projection(run)  # type: ignore[arg-type]

    assert projection.status == "needs_attention"
    assert projection.terminal_failure is not None
    assert projection.terminal_failure.terminal_code == "INTEGRATION_REVIEW_UNRESOLVED"
