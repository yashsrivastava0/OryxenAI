"""Pure stage-attempt fencing contracts used by the durable coordinator."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StageAttemptStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class StageAttemptToken(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: UUID
    run_id: UUID
    stage: str
    attempt_no: int = Field(ge=1)
    job_id: UUID | None = None
    expected_run_revision: int = Field(ge=0)
    input_fingerprint: str
    trace_id: str = ""


class StageFinalization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: StageAttemptStatus
    run_id: UUID
    stage: str
    attempt_id: UUID
    input_fingerprint: str
    safe_error: dict[str, Any] | None = None
    artifact_references: list[dict[str, Any]] = Field(default_factory=list)


def fingerprint_input(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stage_idempotency_key(
    run_id: UUID | str, stage: str, input_fingerprint: str, attempt_no: int = 1
) -> str:
    return f"code-generator:{run_id}:{stage}:{attempt_no}:{input_fingerprint}"


def owns_attempt(
    attempt: StageAttemptToken | dict[str, Any],
    *,
    run_id: UUID,
    stage: str,
    job_id: UUID | None,
    expected_run_revision: int,
    input_fingerprint: str,
) -> bool:
    token = (
        attempt
        if isinstance(attempt, StageAttemptToken)
        else StageAttemptToken.model_validate(attempt)
    )
    return (
        token.run_id == run_id
        and token.stage == stage
        and (job_id is None or token.job_id == job_id)
        and token.expected_run_revision == expected_run_revision
        and token.input_fingerprint == input_fingerprint
    )


class StageCoordinator:
    """Deterministic stage sequencing and finalization decisions.

    Database writes are delegated to ``CodeGeneratorDevelopmentRepository``;
    this object owns the rules so handlers and integration tests share one
    implementation.
    """

    _NEXT: ClassVar[dict[str, tuple[str, str]]] = {
        "plan": ("acquire", "code_generator.acquire"),
        "planned": ("acquire", "code_generator.acquire"),
        "acquire": ("generate", "code_generator.generate"),
        "acquired": ("generate", "code_generator.generate"),
        "generate": ("verify", "code_generator.verify_and_preview"),
        "source_ready": ("verify", "code_generator.verify_and_preview"),
    }

    @classmethod
    def next_stage(cls, completed_stage: str) -> tuple[str, str] | None:
        return cls._NEXT.get(completed_stage)

    @staticmethod
    def finalization_is_valid(
        token: StageAttemptToken | dict[str, Any],
        finalization: StageFinalization,
        *,
        job_id: UUID | None,
        expected_run_revision: int,
    ) -> bool:
        return owns_attempt(
            token,
            run_id=finalization.run_id,
            stage=finalization.stage,
            job_id=job_id,
            expected_run_revision=expected_run_revision,
            input_fingerprint=finalization.input_fingerprint,
        ) and finalization.attempt_id == (
            token.attempt_id
            if isinstance(token, StageAttemptToken)
            else UUID(str(token["attempt_id"]))
        )

    @classmethod
    def payload_for_attempt(
        cls, token: StageAttemptToken, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        result = dict(payload or {})
        result.update(
            {
                "stage_attempt_id": str(token.attempt_id),
                "stage": token.stage,
                "stage_attempt_no": token.attempt_no,
                "expected_run_revision": token.expected_run_revision,
                "input_fingerprint": token.input_fingerprint,
                "trace_id": token.trace_id,
            }
        )
        return result
