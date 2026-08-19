from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from oryxenai.agents.code_generator.core.error_policy import (
    FailureClass,
    classify_failure,
    safe_issue_for,
)
from oryxenai.agents.code_generator.core.stage_attempt import (
    StageAttemptStatus,
    StageAttemptToken,
    StageCoordinator,
    StageFinalization,
    fingerprint_input,
    owns_attempt,
    stage_idempotency_key,
)
from oryxenai.storage.code_generator_artifacts import (
    LocalFsCodeGeneratorArtifactRepository,
    deterministic_bundle,
)


def test_failure_policy_distinguishes_retry_input_and_repair() -> None:
    assert (
        classify_failure(type("Error", (), {"code": "PROVIDER_TIMEOUT_ERROR"})()).category
        is FailureClass.RETRYABLE_INFRASTRUCTURE
    )
    assert (
        classify_failure(type("Error", (), {"code": "PACK_SCHEMA_INVALID"})()).category
        is FailureClass.PERMANENT_INPUT_POLICY
    )
    assert (
        classify_failure(type("Error", (), {"code": "DOM_DUPLICATE_ID"})()).category
        is FailureClass.REPAIRABLE_GENERATED_SOURCE
    )
    issue = safe_issue_for(type("Error", (), {"code": "PROVIDER_AUTH_ERROR", "message": "auth"})())
    assert issue.next_action
    assert issue.code == "PROVIDER_AUTH_ERROR"


def test_stage_fence_rejects_late_or_wrong_worker_completion() -> None:
    run_id = uuid4()
    job_id = uuid4()
    attempt_id = uuid4()
    token = StageAttemptToken(
        attempt_id=attempt_id,
        run_id=run_id,
        stage="generate",
        attempt_no=1,
        job_id=job_id,
        expected_run_revision=7,
        input_fingerprint=fingerprint_input({"checkpoint": "a"}),
    )
    finalization = StageFinalization(
        status=StageAttemptStatus.SUCCEEDED,
        run_id=run_id,
        stage="generate",
        attempt_id=attempt_id,
        input_fingerprint=token.input_fingerprint,
    )
    assert StageCoordinator.finalization_is_valid(
        token, finalization, job_id=job_id, expected_run_revision=7
    )
    assert not StageCoordinator.finalization_is_valid(
        token, finalization, job_id=uuid4(), expected_run_revision=7
    )
    assert owns_attempt(
        token,
        run_id=run_id,
        stage="generate",
        job_id=job_id,
        expected_run_revision=7,
        input_fingerprint=token.input_fingerprint,
    )
    assert stage_idempotency_key(run_id, "generate", token.input_fingerprint).startswith(
        "code-generator:"
    )


def test_stage_coordinator_has_no_implicit_supervisor_transition() -> None:
    assert StageCoordinator.next_stage("plan") == ("acquire", "code_generator.acquire")
    assert StageCoordinator.next_stage("verify") is None


def test_deterministic_artifact_bundle_is_stable() -> None:
    first, manifest = deterministic_bundle({"src/a.ts": b"a", "public/b.png": b"b"})
    second, same_manifest = deterministic_bundle({"public/b.png": b"b", "src/a.ts": b"a"})
    assert first == second
    assert manifest == same_manifest
    assert [item["path"] for item in manifest["files"]] == ["public/b.png", "src/a.ts"]


@pytest.mark.asyncio
async def test_local_artifact_repository_is_content_addressed_and_verifies_reads(tmp_path) -> None:
    repository = LocalFsCodeGeneratorArtifactRepository(tmp_path / "artifacts")
    expires_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    reference = await repository.put(
        artifact_kind="accepted-source",
        data=b"source",
        expires_at=expires_at,
        manifest={"files": ["src/main.tsx"]},
    )
    assert reference.key == f"accepted-source/{reference.sha256[:2]}/{reference.sha256}"
    assert await repository.head(reference) == reference
    assert await repository.get(reference) == b"source"
    (
        tmp_path / "artifacts" / "accepted-source" / reference.sha256[:2] / reference.sha256
    ).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash or size"):
        await repository.get(reference)
