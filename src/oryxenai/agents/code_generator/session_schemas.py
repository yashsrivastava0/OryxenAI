"""Session-facing state contracts for the production Code Generator stage."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from oryxenai.storage.artifacts import ArtifactReference


class CodeGeneratorSessionStatus(StrEnum):
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    PLANNING = "planning"
    ACQUIRING = "acquiring"
    GENERATING = "generating"
    VERIFYING = "verifying"
    READY = "ready"
    NEEDS_ATTENTION = "needs_attention"


class CodeGeneratorSourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    build_preparation_run_id: str
    build_preparation_scope_hash: str
    build_preparation_source_ref: dict[str, Any]
    archive_sha256: str
    artifact: ArtifactReference
    bound_session_revision: int


class CodeGeneratorSessionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CodeGeneratorSessionStatus = CodeGeneratorSessionStatus.NOT_STARTED
    current_run_id: str = ""
    model_profile: str = ""
    source_ref: CodeGeneratorSourceRef | None = None
    active_preview: dict[str, Any] | None = None
    latest_error: dict[str, Any] | None = None
    stale: bool = False
    stale_reasons: list[str] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None


class ProviderPreflightEnvelope(BaseModel):
    """Fixed no-context strict response used only to prove provider reachability."""

    model_config = ConfigDict(extra="forbid")

    ok: bool = True
    protocol: str = "code-generator-preflight-v1"
