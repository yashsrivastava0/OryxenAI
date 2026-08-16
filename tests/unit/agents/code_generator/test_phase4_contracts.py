from __future__ import annotations

from oryxenai.agents.code_generator.artifact_manifest import build_manifest, candidate_zip
from oryxenai.agents.code_generator.development_schemas import (
    CandidateIdentity,
    Diagnostic,
    VerificationProfile,
)
from oryxenai.agents.code_generator.repair_policy import RepairBudget


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
