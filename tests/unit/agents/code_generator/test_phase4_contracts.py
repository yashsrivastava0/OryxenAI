from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

from oryxenai.agents.code_generator.core import fs_safe
from oryxenai.agents.code_generator.core.artifact_manifest import build_manifest, candidate_zip
from oryxenai.agents.code_generator.core.development_schemas import (
    CandidateIdentity,
    Diagnostic,
    VerificationProfile,
)
from oryxenai.agents.code_generator.core.final_repair import _deterministic_marker_repair
from oryxenai.agents.code_generator.core.portfolio_export import export_portfolio
from oryxenai.agents.code_generator.core.repair_policy import RepairBudget
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace


def test_candidate_identity_is_canonical_and_stable() -> None:
    values = {
        "input_receipt_hash": "input",
        "site_plan_hash": "plan",
        "work_graph_hash": "graph",
        "source_checkpoint_hash": "checkpoint",
        "source_manifest_hash": "manifest",
        "scaffold_toolchain_profile_hash": "toolchain",
        "verification_profile_hash": "verification",
    }
    first = CandidateIdentity.model_validate(values)
    second = CandidateIdentity.model_validate({**values, "identity_hash": first.identity_hash})
    assert first.identity_hash == second.identity_hash


def test_clean_artifact_manifest_rejects_missing_references(tmp_path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text('<script src="/assets/app.js"></script>', encoding="utf-8")
    try:
        build_manifest(dist, candidate_identity_hash="identity", max_total_bytes=10000)
    except ValueError as exc:
        assert "missing" in str(exc).casefold()
    else:
        raise AssertionError("missing build references must block the artifact")


def test_artifact_zip_excludes_unlisted_files(tmp_path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<main>ok</main>", encoding="utf-8")
    manifest = build_manifest(dist, candidate_identity_hash="identity", max_total_bytes=10000)
    archive = candidate_zip(dist, manifest)
    assert b"index.html" in archive
    assert b"node_modules" not in archive


def test_repair_budget_detects_recurrence() -> None:
    diagnostic = Diagnostic(
        diagnostic_id="d1",
        group="type_build_artifact",
        code="TYPECHECK_FAILED",
        phase="typecheck",
        normalized_message="bad type",
        fingerprint="same",
    )
    budget = RepairBudget(max_total=2, max_per_unit=2)
    assert budget.consume([diagnostic]) == "bounded-correction"
    assert budget.consume([diagnostic]) == "bounded-simplification"
    assert not budget.can_attempt([diagnostic])


def test_verification_profile_hash_is_receipt_bound() -> None:
    profile = VerificationProfile(profile_id="test")
    assert profile.profile_hash


def test_portfolio_export_contains_source_dist_and_metadata(tmp_path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "dist").mkdir()
    (repo / "node_modules").mkdir()
    (repo / "src" / "main.tsx").write_text("export {};", encoding="utf-8")
    (repo / "dist" / "index.html").write_text("<main>ok</main>", encoding="utf-8")
    (repo / "node_modules" / "ignored.txt").write_text("ignored", encoding="utf-8")
    settings = SimpleNamespace(
        code_generator_verification=SimpleNamespace(export_root=str(tmp_path / "exports"))
    )

    exported = export_portfolio(
        settings=settings,
        run_id="run-1",
        repo_dir=repo,
        metadata={
            "preview_url": "http://127.0.0.1:4174/preview/run-1/",
            "candidate_id": "candidate-1",
            "candidate_identity_hash": "identity-1",
            "pack_reference": "pack-1",
        },
    )

    assert (exported / "source" / "src" / "main.tsx").is_file()
    assert (exported / "dist" / "index.html").is_file()
    assert not (exported / "source" / "node_modules").exists()
    assert re.fullmatch(r"\d{2}-\d{2}-\d{2}-\d{2}-\d{4}-[a-z0-9]+", exported.name)
    metadata = (exported / "portfolio.json").read_text(encoding="utf-8")
    assert '"candidate_identity_hash": "identity-1"' in metadata
    assert '"pack_reference": "pack-1"' in metadata
    assert '"export_folder": "' + exported.name + '"' in metadata


def test_fs_safe_directory_rename_retries_transient_permission_errors(
    tmp_path, monkeypatch
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    real_replace = fs_safe.os.replace
    attempts = 0

    def flaky_replace(left: Path, right: Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError("transient lock")
        real_replace(left, right)

    monkeypatch.setattr(fs_safe.os, "replace", flaky_replace)
    monkeypatch.setattr(fs_safe, "_sleep_before_retry", lambda _attempt: None)

    fs_safe.rename_dir_with_retry(source, target)

    assert attempts == 3
    assert target.is_dir()


def test_marker_repair_fallback_inserts_only_missing_route_markers(tmp_path) -> None:
    repo = tmp_path / "repo"
    route = repo / "src" / "routes" / "home-route" / "index.tsx"
    route.parent.mkdir(parents=True)
    route.write_text("return (<main><section>Home</section></main>);", encoding="utf-8")
    diagnostic = Diagnostic(
        diagnostic_id="marker-missing",
        group="source_contract",
        code="SOURCE_ACCEPTANCE_MARKER_MISSING",
        phase="source_contract",
        route_id="home",
        normalized_message="marker missing",
        fingerprint="marker-missing",
    )
    plan = SimpleNamespace(
        acceptance_coverage=[
            SimpleNamespace(route_id="home", source_marker="marker:criterion:home:3")
        ]
    )

    changes = _deterministic_marker_repair(
        diagnostics=[diagnostic],
        plan=plan,
        projections={
            "site/contract.json": {
                "routes": [{"route_id": "home", "storage_key": "routes/home-route"}]
            }
        },
        repo_dir=repo,
    )

    assert changes is not None
    assert len(changes.files) == 1
    assert "marker:criterion:home:3" in changes.files[0].complete_utf8_content
    assert changes.files[0].path == "src/routes/home-route/index.tsx"


def test_workspace_reasserts_trusted_shell_from_scaffold(tmp_path) -> None:
    source_shell = Path("src/oryxenai/agents/code_generator/scaffolds/react-vite-v1").resolve()
    repo = tmp_path / "run" / "repo"
    repo.mkdir(parents=True)
    target = repo / "src" / "app" / "AppRouter.tsx"
    target.parent.mkdir(parents=True)
    target.write_text("export function AppRouter() { return null; }", encoding="utf-8")
    workspace = GenerationWorkspace(tmp_path / "run", tmp_path / "input", tmp_path / "checkpoint")

    workspace.scaffold_dir = source_shell
    workspace.reassert_trusted_shell()

    assert target.read_text(encoding="utf-8") == (
        source_shell / "src" / "app" / "AppRouter.tsx"
    ).read_text(encoding="utf-8")
