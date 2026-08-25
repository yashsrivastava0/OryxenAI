"""Validated, source-bound checkpoints for bounded Build Preparation retries."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CHECKPOINT_SCHEMA_VERSION: Literal["build-preparation-checkpoint-v1"] = (
    "build-preparation-checkpoint-v1"
)
CheckpointStage = Literal["stage_0", "stage_1", "stage_2", "stage_3", "stage_4"]

_STAGE_ORDER: dict[str, int] = {
    "stage_0": 0,
    "stage_1": 1,
    "stage_2": 2,
    "stage_3": 3,
    "stage_4": 4,
}


class BuildPreparationCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["build-preparation-checkpoint-v1"] = CHECKPOINT_SCHEMA_VERSION
    run_id: str
    approved_source_hash: str
    profile_fingerprint: str
    candidate_set_hash: str = ""
    completed_stage: CheckpointStage
    data: dict[str, Any] = Field(default_factory=dict)
    model_calls: int = 0
    model_call_receipts: list[dict[str, Any]] = Field(default_factory=list)

    def includes(self, stage: str) -> bool:
        return _STAGE_ORDER.get(self.completed_stage, -1) >= _STAGE_ORDER.get(stage, 99)

    def compatible_with(
        self,
        *,
        run_id: str,
        approved_source_hash: str,
        profile_fingerprint: str,
    ) -> bool:
        return (
            self.run_id == run_id
            and self.approved_source_hash == approved_source_hash
            and self.profile_fingerprint == profile_fingerprint
        )


def source_binding_hash(source_ref: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(source_ref, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def candidate_set_hash(candidates: list[Any]) -> str:
    """Hash candidate identity/metadata without source files or artifact bytes."""

    material: list[dict[str, Any]] = []
    for candidate in candidates:
        raw = (
            candidate.model_dump(mode="json")
            if hasattr(candidate, "model_dump")
            else dict(candidate)
        )
        raw.pop("source_files", None)
        material.append(raw)
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
