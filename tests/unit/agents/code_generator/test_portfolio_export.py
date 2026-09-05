"""Failed runs must still export whatever source tree exists for inspection,
not only runs that reach a promoted READY state -- the user explicitly asked
for this (2026-09-05): "store the output even if it is a failed run"."""

from __future__ import annotations

from pathlib import Path

import oryxenai.agents.code_generator.core.portfolio_export as portfolio_export
import oryxenai.jobs.handlers.code_generator_verification as code_generator_verification
from oryxenai.agents.code_generator.core.portfolio_export import export_failed_run
from oryxenai.core.settings import get_settings


def _settings_with_roots(tmp_path: Path):
    settings = get_settings()
    settings.code_generator_generation.workspace_root = str(tmp_path / "workspace")
    settings.code_generator_verification.export_root = str(tmp_path / "export")
    return settings


def test_export_failed_run_returns_none_when_nothing_was_generated_yet(tmp_path: Path) -> None:
    settings = _settings_with_roots(tmp_path)

    result = export_failed_run(
        settings=settings,
        run_id="00000000-0000-0000-0000-000000000000",
        reason="PLANNER_OUTPUT_INVALID",
    )

    assert result is None


def test_export_failed_run_exports_the_existing_source_tree(tmp_path: Path) -> None:
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

    result = export_failed_run(
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
    assert (result / "generation-report.md").is_file()


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

    def fake_export_failed_run(**kwargs):
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

    def fake_export_failed_run(**kwargs):
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
