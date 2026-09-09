"""Failed runs must still export whatever source tree exists for inspection,
not only runs that reach a promoted READY state -- the user explicitly asked
for this (2026-09-05): "store the output even if it is a failed run"."""

from __future__ import annotations

from pathlib import Path

import oryxenai.agents.code_generator.core.portfolio_export as portfolio_export
import oryxenai.jobs.handlers.code_generator_verification as code_generator_verification
from oryxenai.agents.code_generator.core.portfolio_export import (
    _generation_report,
    _source_references_resource_slot,
    build_export_receipt,
    export_failed_run,
)
from oryxenai.core.settings import get_settings


def _settings_with_roots(tmp_path: Path):
    settings = get_settings()
    settings.code_generator_generation.workspace_root = str(tmp_path / "workspace")
    settings.code_generator_verification.export_root = str(tmp_path / "export")
    return settings


def test_generation_report_reads_receipt_fields_and_image_evidence() -> None:
    report = _generation_report(
        {
            "run_id": "run-1",
            "quality_review": {"accepted": True},
            "verification": {
                "gate_results": [
                    {"gate_id": "source_contract", "status": "passed", "diagnostics": []},
                    {
                        "gate_id": "dom_runtime",
                        "status": "passed",
                        "diagnostics": [{"code": "RUNTIME_REGION_GAP", "severity": "advisory"}],
                    },
                ],
                "advisories": [],
            },
            "build_attempt": {"status": "success", "build_hash": "build-1"},
            "image_evidence": {
                "planned_count": 1,
                "materialized_count": 1,
                "rendered_count": 1,
                "failed_count": 0,
                "entries": [
                    {
                        "resource_slot_id": "slot-hero",
                        "route_id": "home",
                        "section_id": "hero",
                        "materialized": True,
                        "rendered": True,
                        "disposition": "admitted",
                    }
                ],
            },
            "routes": [],
            "call_ledger": {},
        }
    )

    assert "Quality review: `accepted`" in report
    assert "Verification: `passed`" in report
    assert "Build attempt: `success`" in report
    assert "Planned: `1`; materialized: `1`; rendered: `1`; failed: `0`" in report
    assert "Advisory observations: `1`" in report


def test_generation_report_preserves_terminal_stage_and_pipeline_issue() -> None:
    report = _generation_report(
        {
            "run_id": "run-failed",
            "issues": [{"code": "SOURCE_REPAIR_EXHAUSTED", "message": "repair limit"}],
            "terminal_failure": {
                "terminal_code": "GENERATION_FAILED",
                "phase": "generation",
                "safe_user_summary": "The generated source did not pass validation.",
            },
        }
    )

    assert "Failing stage: `generation`" in report
    assert "Recorded pipeline issues: `1`" in report
    assert "Primary failure: `GENERATION_FAILED`" in report
    assert "The generated source did not pass validation." in report


def test_image_evidence_recognizes_literal_jsx_resource_bindings() -> None:
    assert _source_references_resource_slot('<LocalImage resourceId="slot-hero" />', "slot-hero")
    assert _source_references_resource_slot("<LocalImage resourceId={`slot-hero`} />", "slot-hero")
    assert not _source_references_resource_slot(
        '<LocalImage resourceId="slot-other" />', "slot-hero"
    )


async def test_export_failed_run_writes_metadata_only_receipt_when_nothing_was_generated_yet(
    tmp_path: Path,
) -> None:
    settings = _settings_with_roots(tmp_path)

    result = await export_failed_run(
        settings=settings,
        run_id="00000000-0000-0000-0000-000000000000",
        reason="PLANNER_OUTPUT_INVALID",
    )

    assert result is not None
    assert (result / "source").is_dir()
    assert not (result / "dist").exists()
    portfolio = (result / "portfolio.json").read_text(encoding="utf-8")
    assert '"source_status": "not_created"' in portfolio
    assert '"status": "not_run"' in portfolio
    report = (result / "generation-report.md").read_text(encoding="utf-8")
    assert "SOURCE_NOT_CREATED" in report
    assert "Build attempt: `not_run`" in report


async def test_export_failed_run_exports_the_existing_source_tree(
    tmp_path: Path, monkeypatch
) -> None:
    """The build attempt is exercised separately below; here it's stubbed
    out to keep this test a fast, hermetic unit test with no real npm/vite
    subprocess."""
    settings = _settings_with_roots(tmp_path)
    run_id = "11111111-1111-1111-1111-111111111111"
    repo_dir = tmp_path / "workspace" / run_id / "repo"
    (repo_dir / "src").mkdir(parents=True)
    (repo_dir / "src" / "App.tsx").write_text(
        "export default function App() { return null; }\n", encoding="utf-8"
    )
    screenshots_dir = tmp_path / "workspace" / run_id / "verification-screenshots"
    screenshots_dir.mkdir(parents=True)
    (screenshots_dir / "direct_home.png").write_bytes(b"not a real png, just bytes")

    async def fake_build_attempt(**_kwargs):
        return {"status": "skipped", "diagnostics": []}

    monkeypatch.setattr(portfolio_export, "_attempt_best_effort_build", fake_build_attempt)

    result = await export_failed_run(
        settings=settings,
        run_id=run_id,
        reason="DOM_RUNTIME_FAILED",
        issues=[{"code": "RUNTIME_TOUCH_TARGET_TOO_SMALL", "message": "too small"}],
    )

    assert result is not None
    assert result.is_dir()
    assert (result / "source" / "src" / "App.tsx").is_file()
    assert (result / "screenshots" / "direct_home.png").is_file()
    portfolio = (result / "portfolio.json").read_text(encoding="utf-8")
    assert '"export_reason": "DOM_RUNTIME_FAILED"' in portfolio
    assert '"status": "needs_attention"' in portfolio
    assert "RUNTIME_TOUCH_TARGET_TOO_SMALL" in portfolio
    assert '"status": "skipped"' in portfolio
    report = (result / "generation-report.md").read_text(encoding="utf-8")
    assert "Build attempt: `skipped`" in report


async def test_export_failed_run_ships_a_real_dist_when_the_source_builds(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression test for the auto-build-on-export fix: a needs_attention
    export whose source is actually buildable must ship a real dist/ and an
    honest 'success' build status, not force the reader to build it by hand."""
    settings = _settings_with_roots(tmp_path)
    run_id = "44444444-4444-4444-4444-444444444444"
    repo_dir = tmp_path / "workspace" / run_id / "repo"
    repo_dir.mkdir(parents=True)

    class _FakeManifest:
        pass

    async def fake_run_clean_build(repo_dir_arg: Path, **_kwargs):
        assert repo_dir_arg == repo_dir
        dist_dir = repo_dir_arg / "dist"
        dist_dir.mkdir(parents=True)
        (dist_dir / "index.html").write_text("<html></html>", encoding="utf-8")
        return _FakeManifest(), []

    monkeypatch.setattr(portfolio_export, "run_clean_build", fake_run_clean_build)

    result = await export_failed_run(
        settings=settings,
        run_id=run_id,
        reason="QUALITY_REVIEW_REJECTED_AFTER_REPAIR",
    )

    assert result is not None
    assert (result / "dist" / "index.html").is_file()
    portfolio = (result / "portfolio.json").read_text(encoding="utf-8")
    assert '"status": "success"' in portfolio
    report = (result / "generation-report.md").read_text(encoding="utf-8")
    assert "Build attempt: `success`" in report


def test_build_export_receipt_shapes_a_discoverable_receipt(tmp_path: Path) -> None:
    """A needs_attention run's export previously existed only on disk, with
    nothing in the run's own state pointing at it -- the frontend's Output
    tab showed a blank folder/dist even though a real export existed. This
    receipt is what the run-state API now surfaces so the UI (and a
    candidate-preview route) can find it, mirroring the exact shape the
    promoted-export success path already writes."""
    exported = tmp_path / "export" / "16-43-07-09-2026-0ffd6cec"
    (exported / "dist").mkdir(parents=True)
    (exported / "source").mkdir(parents=True)

    receipt = build_export_receipt(exported)

    assert receipt["status"] == "exported"
    assert receipt["folder"] == "16-43-07-09-2026-0ffd6cec"
    assert receipt["dist_path"] == "dist"
    assert receipt["source_path"] == "source"
    assert receipt["relative_path"].endswith("16-43-07-09-2026-0ffd6cec")


def test_build_export_receipt_reports_no_dist_when_the_build_failed(tmp_path: Path) -> None:
    exported = tmp_path / "export" / "run-with-no-build"
    (exported / "source").mkdir(parents=True)

    receipt = build_export_receipt(exported)

    assert receipt["dist_path"] == ""


async def test_export_failed_run_stays_source_only_when_the_build_fails(
    tmp_path: Path, monkeypatch
) -> None:
    """A build failure during the best-effort export attempt must never
    break the export -- it stays source-only, same as before this change,
    with the failure recorded instead of silently dropped."""
    settings = _settings_with_roots(tmp_path)
    run_id = "55555555-5555-5555-5555-555555555555"
    repo_dir = tmp_path / "workspace" / run_id / "repo"
    repo_dir.mkdir(parents=True)

    from oryxenai.agents.code_generator.core.build_runner import diagnostic as make_diagnostic

    async def fake_run_clean_build(repo_dir_arg: Path, **_kwargs):
        return None, [make_diagnostic("INSTALL_FAILED", "no package.json", phase="install")]

    monkeypatch.setattr(portfolio_export, "run_clean_build", fake_run_clean_build)

    result = await export_failed_run(
        settings=settings,
        run_id=run_id,
        reason="TOOLCHAIN_INSTALL_FAILED",
    )

    assert result is not None
    assert not (result / "dist").exists()
    portfolio = (result / "portfolio.json").read_text(encoding="utf-8")
    assert '"status": "failed"' in portfolio
    assert "INSTALL_FAILED" in portfolio
    report = (result / "generation-report.md").read_text(encoding="utf-8")
    assert "Build attempt: `failed`" in report


async def test_verification_handler_exports_on_needs_attention(monkeypatch) -> None:
    """Regression test for the 2026-09-05 fix: CodeGeneratorVerificationHandler
    .execute() must attempt a best-effort export whenever the real
    verification result is needs_attention/failed, not only on success."""
    calls: list[dict[str, object]] = []

    async def fake_execute(payload, **_kwargs):
        return {
            "status": "needs_attention",
            "run_id": "22222222-2222-2222-2222-222222222222",
            "code": "DOM_RUNTIME_FAILED",
        }

    async def fake_export_failed_run(**kwargs):
        calls.append(kwargs)
        return None

    monkeypatch.setattr(code_generator_verification, "_execute", fake_execute)
    monkeypatch.setattr(portfolio_export, "export_failed_run", fake_export_failed_run)

    handler = code_generator_verification.CodeGeneratorVerificationHandler()
    result = await handler.execute(
        {"development_run_id": "22222222-2222-2222-2222-222222222222"}, "test-worker"
    )

    assert result["status"] == "needs_attention"
    assert len(calls) == 1
    assert calls[0]["run_id"] == "22222222-2222-2222-2222-222222222222"
    assert calls[0]["reason"] == "DOM_RUNTIME_FAILED"


async def test_verification_handler_does_not_export_on_success(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    async def fake_execute(payload, **_kwargs):
        return {"status": "succeeded", "run_id": "33333333-3333-3333-3333-333333333333"}

    async def fake_export_failed_run(**kwargs):
        calls.append(kwargs)
        return None

    monkeypatch.setattr(code_generator_verification, "_execute", fake_execute)
    monkeypatch.setattr(portfolio_export, "export_failed_run", fake_export_failed_run)

    handler = code_generator_verification.CodeGeneratorVerificationHandler()
    result = await handler.execute(
        {"development_run_id": "33333333-3333-3333-3333-333333333333"}, "test-worker"
    )

    assert result["status"] == "succeeded"
    assert calls == []
