from __future__ import annotations

from pathlib import Path

import pytest

from oryxenai.agents.code_generator.core.check_runner import _unbalanced
from oryxenai.agents.code_generator.core.development_schemas import (
    GenerationChanges,
    GenerationProjection,
    GenerationWorkUnitProjection,
    SourceFileChange,
    WorkUnit,
)
from oryxenai.agents.code_generator.core.generation_orchestrator import (
    _build_pending_proposal,
    _complete_generation_attempt,
    _pending_files_from_ledger,
    _reserve_generation_attempt,
    _write_pending_proposal,
)
from oryxenai.agents.code_generator.core.parallel_scheduler import execute_waves
from oryxenai.agents.code_generator.core.source_validation import (
    validate_generation_changes_incrementally,
)
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace


def test_incremental_source_validation_keeps_safe_siblings() -> None:
    changes = GenerationChanges(
        files=[
            SourceFileChange(
                path="src/routes/home/sections/Hero.tsx",
                operation="create",
                complete_utf8_content="export const Hero = () => null;",
            ),
            SourceFileChange(
                path="src/routes/home/sections/Hero.css",
                operation="create",
                complete_utf8_content="#hero { max-width: fiftych; }",
            ),
        ]
    )

    valid, errors = validate_generation_changes_incrementally(
        changes,
        owned_paths=["src/routes/home/sections/**"],
        repo_dir=Path("."),
        max_file_bytes=10_000,
        max_response_bytes=20_000,
        allowed_packages=set(),
        public_text=set(),
    )

    assert [item.path for item in valid] == ["src/routes/home/sections/Hero.tsx"]
    assert [item.code for item in errors] == ["SOURCE_CSS_INVALID_LENGTH"]


def test_pending_proposal_retains_inventory_and_integrity_checked_bodies(tmp_path) -> None:
    workspace = GenerationWorkspace(
        tmp_path / "workspace", tmp_path / "input", tmp_path / "checkpoints"
    )
    workspace.root.mkdir()
    workspace.ledger_dir.mkdir()
    workspace.repo_dir.mkdir()
    (workspace.repo_dir / "src").mkdir()
    (workspace.repo_dir / "src" / "existing.ts").write_text(
        "export const existing = true;\n", encoding="utf-8"
    )
    unit = WorkUnit(
        unit_id="route-home-batch-1",
        kind="route_batch",
        owns_paths=["src/new.ts", "src/existing.ts"],
    )
    files = {"src/new.ts": "export const newValue = true;\n"}

    proposal = _build_pending_proposal(
        workspace=workspace,
        unit=unit,
        owned_paths=unit.owns_paths,
        base_checkpoint_hash="checkpoint-1",
        base_repo=workspace.repo_dir,
        files=files,
        attempt_id="attempt-1",
        restricted_evidence={"src/bad.css": "#hero { max-width: fiftych; }\n"},
    )
    stored = _write_pending_proposal(
        workspace,
        proposal,
        files,
        restricted_evidence={"src/bad.css": "#hero { max-width: fiftych; }\n"},
    )
    projection = GenerationWorkUnitProjection(
        unit_id=unit.unit_id,
        kind=unit.kind,
        status="model_requested",
        owned_paths=list(unit.owns_paths),
        pending_proposal=stored,
    )

    assert stored.expected_paths == ["src/existing.ts", "src/new.ts"]
    assert stored.present_paths == ["src/existing.ts", "src/new.ts"]
    assert stored.missing_paths == ["src/existing.ts"]
    assert stored.restricted_evidence_paths == ["src/bad.css"]
    assert _pending_files_from_ledger(workspace, unit, projection) == files


def test_attempt_ledger_is_idempotent_and_records_failure() -> None:
    projection = GenerationProjection(
        generation_id="generation-1",
        input_receipt_hash="input-1",
        site_plan_hash="plan-1",
        phase="generating_routes",
    )

    attempt_id = _reserve_generation_attempt(
        projection,
        operation="route_batch",
        unit_id="route-home-batch-1",
        phase="generating_routes",
        request_round=1,
        repair_round=0,
        context_hash="context-1",
    )
    assert (
        _reserve_generation_attempt(
            projection,
            operation="route_batch",
            unit_id="route-home-batch-1",
            phase="generating_routes",
            request_round=1,
            repair_round=0,
            context_hash="context-1",
        )
        == attempt_id
    )
    _complete_generation_attempt(
        projection,
        attempt_id,
        status="failed",
        error_code="PROVIDER_TIMEOUT",
        error_message="provider timed out",
    )

    assert len(projection.attempt_records) == 1
    assert projection.attempt_records[0].status == "failed"
    assert projection.attempt_records[0].error_code == "PROVIDER_TIMEOUT"
    assert projection.attempt_records[0].completed_at


@pytest.mark.asyncio
async def test_serial_scheduler_does_not_start_siblings_after_failure() -> None:
    started: list[str] = []

    async def execute(unit: WorkUnit) -> object:
        started.append(unit.unit_id)
        if unit.unit_id == "first":
            raise RuntimeError("first failed")
        return unit.unit_id

    with pytest.raises(RuntimeError, match="first failed"):
        await execute_waves(
            [
                WorkUnit(unit_id="first", kind="route_batch"),
                WorkUnit(unit_id="second", kind="route_batch"),
            ],
            execute,
            max_concurrency=1,
        )

    assert started == ["first"]


def test_structural_delimiter_check_ignores_comments() -> None:
    assert not _unbalanced("// a model's comment contains { and [\nconst value = {}; ")
    assert not _unbalanced(
        "/* a comment contains an apostrophe's delimiters: { [ */\nconst value = []; "
    )
    assert not _unbalanced('const normalized = path.replace(/^public\\//, "");')
    assert _unbalanced("const value = {")
