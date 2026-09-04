"""Code Generator pipeline/version compatibility helpers.

The durable queue is shared by long-lived API and worker processes.  A stage
job therefore needs an explicit namespace when the executable contract
changes; otherwise an older worker can claim a newer job and fail it as an
unknown/invalid operation.  The helpers in this module keep that policy in
one place while retaining read compatibility for v3/v4 rows already stored in
the database.
"""

from __future__ import annotations

from typing import Final

PIPELINE_V3: Final = "code-generator-v3"
PIPELINE_V4: Final = "code-generator-v4"
PIPELINE_V5: Final = "code-generator-v5"

BLUEPRINT_PIPELINES: Final = frozenset({PIPELINE_V4, PIPELINE_V5})

_STAGE_SUFFIXES: Final = {
    "plan": "plan",
    "acquire": "acquire",
    "generate": "generate",
    "verify": "verify_and_preview",
}


def uses_blueprint(version: str | None) -> bool:
    """Return whether a pipeline uses the structured ExperienceBlueprint."""

    return str(version or "").strip() in BLUEPRINT_PIPELINES


def uses_v5_namespace(version: str | None) -> bool:
    """Return whether stage jobs must use the v5 queue namespace."""

    return str(version or "").strip() == PIPELINE_V5


def stage_job_kind(stage: str, version: str | None) -> str:
    """Resolve a durable stage job kind for a pipeline version.

    v3/v4 names remain stable for existing queued and historical work.  v5 is
    deliberately namespaced so a pre-v5 worker cannot execute a new contract.
    """

    try:
        suffix = _STAGE_SUFFIXES[stage]
    except KeyError:
        raise ValueError(f"unknown Code Generator stage: {stage}") from None
    if uses_v5_namespace(version):
        return f"code_generator.v5.{suffix}"
    return f"code_generator.{suffix}"


def stage_scope(stage: str, version: str | None) -> str:
    """Use the job kind as the idempotency scope for that executable stage."""

    return stage_job_kind(stage, version)


def is_verification_kind(kind: str) -> bool:
    return kind in {
        stage_job_kind("verify", PIPELINE_V3),
        stage_job_kind("verify", PIPELINE_V4),
        stage_job_kind("verify", PIPELINE_V5),
    }


__all__ = [
    "BLUEPRINT_PIPELINES",
    "PIPELINE_V3",
    "PIPELINE_V4",
    "PIPELINE_V5",
    "is_verification_kind",
    "stage_job_kind",
    "stage_scope",
    "uses_blueprint",
    "uses_v5_namespace",
]
