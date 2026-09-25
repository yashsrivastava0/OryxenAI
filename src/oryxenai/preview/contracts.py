"""Typed contracts for immutable preview artifacts and promotion receipts."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BuildManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    media_type: str
    size_bytes: int
    sha256: str
    references: list[str] = Field(default_factory=list)


class BuildManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["preview-build-manifest-v1"] = "preview-build-manifest-v1"
    candidate_identity_hash: str
    entry_paths: list[str] = Field(default_factory=list)
    entries: list[BuildManifestEntry] = Field(default_factory=list)
    total_bytes: int = 0
    build_hash: str = ""

    @model_validator(mode="after")
    def stamp_build_hash(self) -> BuildManifest:
        payload = self.model_dump(mode="json", exclude={"build_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.build_hash and self.build_hash != computed:
            raise ValueError("build_hash does not match the preview manifest")
        self.build_hash = computed
        return self


class CandidateIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_receipt_hash: str
    site_plan_hash: str
    work_graph_hash: str
    resource_ledger_hash: str = ""
    dependency_ledger_hash: str = ""
    source_checkpoint_hash: str
    source_manifest_hash: str
    scaffold_toolchain_profile_hash: str
    verification_profile_hash: str
    image_policy_hash: str = ""
    identity_hash: str = ""

    @model_validator(mode="after")
    def stamp_identity_hash(self) -> CandidateIdentity:
        payload = self.model_dump(mode="json", exclude={"identity_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.identity_hash and self.identity_hash != computed:
            raise ValueError("identity_hash does not match the candidate identity")
        self.identity_hash = computed
        return self


class CandidateArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    candidate_identity_hash: str
    build_hash: str
    key: str
    sha256: str
    size_bytes: int
    content_type: str = "application/zip"
    route_ids: list[str] = Field(default_factory=list)
    route_paths: list[str] = Field(default_factory=list)
    created_at: str
    expires_at: str


class PromotionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["preview-promotion-receipt-v1"] = "preview-promotion-receipt-v1"
    promotion_id: str
    run_id: str
    candidate_id: str
    candidate_identity_hash: str
    build_hash: str
    artifact_sha256: str
    verification_report_hash: str
    previous_pointer_etag: str = ""
    active_pointer_etag: str = ""
    promoted_at: str
    receipt_hash: str = ""

    @model_validator(mode="after")
    def stamp_receipt_hash(self) -> PromotionReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.receipt_hash and self.receipt_hash != computed:
            raise ValueError("receipt_hash does not match the promotion receipt")
        self.receipt_hash = computed
        return self


class PendingPromotion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    promotion_id: str
    candidate: CandidateArtifact
    verification_report_hash: str
    expected_revision: int
    previous_pointer_etag: str = ""
    previous_pointer_sha256: str = ""
    previous_pointer: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class PublicReadbackEntryV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    kind: Literal["root", "route", "javascript", "stylesheet", "image", "font"]
    status_code: int
    sha256: str = ""
    media_type: str = ""


class PublicReadbackReceiptV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["public-preview-readback-v1"] = "public-preview-readback-v1"
    promotion_id: str
    candidate_id: str
    build_hash: str
    public_origin: str
    entries: list[PublicReadbackEntryV1] = Field(min_length=1)
    checked_at: str
    receipt_hash: str = ""

    @model_validator(mode="after")
    def stamp_receipt_hash(self) -> PublicReadbackReceiptV1:
        if any(item.status_code < 200 or item.status_code >= 300 for item in self.entries):
            raise ValueError("public preview read-back requires successful responses")
        payload = self.model_dump(mode="json", exclude={"receipt_hash"})
        computed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if self.receipt_hash and self.receipt_hash != computed:
            raise ValueError("receipt_hash does not match public read-back evidence")
        self.receipt_hash = computed
        return self


class ActivePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = ""
    host: str
    url: str
    candidate_id: str
    candidate_identity_hash: str
    build_hash: str
    receipt_key: str
    receipt_hash: str
    pointer_etag: str
    route_ids: list[str] = Field(default_factory=list)
    route_paths: list[str] = Field(default_factory=list)
    promoted_at: str
    public_readback: PublicReadbackReceiptV1 | None = None
