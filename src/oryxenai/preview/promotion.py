"""Crash-safe candidate storage and active-preview promotion."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from oryxenai.agents.code_generator.core.development_schemas import (
    ActivePreview,
    BuildManifest,
    BuildManifestEntry,
    CandidateArtifact,
    CandidateIdentity,
    PendingPromotion,
    PromotionReceipt,
)
from oryxenai.storage.preview import PreviewStorage, PreviewStorageError


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


class PromotionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class PreviewPromoter:
    def __init__(
        self,
        storage: PreviewStorage,
        *,
        preview_base_url: str = "http://127.0.0.1:4174/preview",
        require_readback: bool = False,
    ) -> None:
        self.storage = storage
        self.preview_base_url = preview_base_url.rstrip("/")
        self.require_readback = require_readback

    async def store_candidate(
        self,
        *,
        candidate_id: str,
        host: str,
        identity: CandidateIdentity,
        manifest: BuildManifest,
        dist_dir: Path,
        verification_report: dict[str, Any],
        expires_at: str | None = None,
    ) -> tuple[CandidateArtifact, str, dict[str, Any]]:
        if not dist_dir.is_dir():
            raise PromotionError(
                "CANDIDATE_DIST_MISSING", "The verified dist directory is unavailable."
            )
        build_hash = manifest.build_hash
        prefix = f"preview/candidates/{candidate_id}/{build_hash}"
        for entry in manifest.entries:
            path = dist_dir / entry.path
            if not path.is_file():
                raise PromotionError(
                    "CANDIDATE_FILE_MISSING", "A verified build file is unavailable."
                )
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != entry.sha256:
                raise PromotionError(
                    "CANDIDATE_FILE_CHANGED", "A verified build file changed before storage."
                )
            try:
                await self.storage.put_immutable(
                    key=f"{prefix}/dist/{entry.path}",
                    data=data,
                    content_type=entry.media_type,
                )
            except PreviewStorageError as exc:
                raise PromotionError(exc.code, exc.message) from exc
        report_data = _canonical(verification_report)
        report_hash = hashlib.sha256(report_data).hexdigest()
        try:
            await self.storage.put_immutable(
                key=f"preview/verification/{candidate_id}/{report_hash}.json",
                data=report_data,
                content_type="application/json",
            )
        except PreviewStorageError as exc:
            raise PromotionError(exc.code, exc.message) from exc
        expires = expires_at or (datetime.now(UTC) + timedelta(days=3)).isoformat()
        artifact = CandidateArtifact(
            candidate_id=candidate_id,
            candidate_identity_hash=identity.identity_hash,
            build_hash=build_hash,
            key=prefix,
            sha256=hashlib.sha256(
                _canonical(
                    {"manifest": manifest.model_dump(mode="json"), "report_hash": report_hash}
                )
            ).hexdigest(),
            size_bytes=manifest.total_bytes,
            route_ids=[],
            created_at=_now(),
            expires_at=expires,
        )
        pointer_manifest = manifest.model_dump(mode="json")
        return (
            artifact,
            report_hash,
            {
                "candidate_prefix": prefix,
                "manifest": pointer_manifest,
                "verification_report_hash": report_hash,
                "host": host,
            },
        )

    async def create_pending(
        self,
        *,
        run_id: str,
        host: str,
        artifact: CandidateArtifact,
        verification_report_hash: str,
        expected_revision: int,
    ) -> PendingPromotion:
        current = await self.storage.head(f"preview/hosts/{host}/active.json")
        return PendingPromotion(
            promotion_id=f"promotion-{hashlib.sha256(f'{run_id}:{artifact.build_hash}:{expected_revision}'.encode()).hexdigest()[:24]}",
            candidate=artifact,
            verification_report_hash=verification_report_hash,
            expected_revision=expected_revision,
            previous_pointer_etag=current.etag if current else "",
            created_at=_now(),
        )

    async def promote(
        self,
        *,
        run_id: str,
        host: str,
        pending: PendingPromotion,
        candidate_pointer: dict[str, Any],
        verification_report_hash: str,
    ) -> ActivePreview:
        if (
            pending.candidate.candidate_id
            != candidate_pointer.get("candidate_prefix", "").split("/")[2]
        ):
            raise PromotionError(
                "PROMOTION_CANDIDATE_MISMATCH",
                "The pending candidate does not match the stored candidate.",
            )
        receipt = PromotionReceipt(
            promotion_id=pending.promotion_id,
            run_id=run_id,
            candidate_id=pending.candidate.candidate_id,
            candidate_identity_hash=pending.candidate.candidate_identity_hash,
            build_hash=pending.candidate.build_hash,
            artifact_sha256=pending.candidate.sha256,
            verification_report_hash=verification_report_hash,
            previous_pointer_etag=pending.previous_pointer_etag,
            promoted_at=_now(),
        )
        receipt_key = f"preview/receipts/{receipt.promotion_id}.json"
        receipt_data = _canonical(receipt.model_dump(mode="json"))
        try:
            existing_receipt = await self.storage.get(receipt_key)
            if existing_receipt is not None:
                try:
                    existing_receipt_model = PromotionReceipt.model_validate(
                        json.loads(existing_receipt[1].decode("utf-8"))
                    )
                except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
                    raise PromotionError(
                        "PROMOTION_RECEIPT_CONFLICT",
                        "The promotion receipt key contains an invalid receipt.",
                    ) from exc
                expected_identity = receipt.model_dump(
                    mode="json", exclude={"promoted_at", "receipt_hash"}
                )
                stored_identity = existing_receipt_model.model_dump(
                    mode="json", exclude={"promoted_at", "receipt_hash"}
                )
                if stored_identity != expected_identity:
                    raise PromotionError(
                        "PROMOTION_RECEIPT_CONFLICT",
                        "The promotion receipt key contains different promotion facts.",
                    )
                receipt = existing_receipt_model
                receipt_data = existing_receipt[1]
                receipt_object = existing_receipt[0]
            else:
                receipt_object = await self.storage.put_conditional(
                    key=receipt_key,
                    data=receipt_data,
                    content_type="application/json",
                    expected_etag=None,
                )
            stored_receipt = await self.storage.get(receipt_key)
            if (
                stored_receipt is None
                or stored_receipt[0].sha256 != hashlib.sha256(receipt_data).hexdigest()
            ):
                raise PromotionError(
                    "PROMOTION_RECEIPT_READBACK_FAILED",
                    "The promotion receipt failed read-back verification.",
                )
            index_entry = next(
                (
                    item
                    for item in pending_manifest_entries(candidate_pointer["manifest"])
                    if item.path == "index.html"
                ),
                None,
            )
            if index_entry is None:
                raise PromotionError(
                    "PREVIEW_READBACK_FAILED", "The promoted preview manifest has no index.html."
                )
            stored_index = await self.storage.get(
                f"{candidate_pointer['candidate_prefix']}/dist/index.html"
            )
            if stored_index is not None and stored_index[0].sha256 != index_entry.sha256:
                raise PromotionError(
                    "PREVIEW_READBACK_FAILED",
                    "The promoted preview index failed storage read-back verification.",
                )
            if self.require_readback and stored_index is None:
                raise PromotionError(
                    "PREVIEW_READBACK_FAILED",
                    "The promoted preview index failed storage read-back verification.",
                )
            pointer = {
                "schema_version": "code-generator-active-preview-v1",
                "host": host,
                "candidate_prefix": candidate_pointer["candidate_prefix"],
                "manifest": candidate_pointer["manifest"],
                "receipt_key": receipt_key,
                "receipt_hash": receipt_object.sha256,
                "candidate_id": pending.candidate.candidate_id,
                "candidate_identity_hash": pending.candidate.candidate_identity_hash,
                "build_hash": pending.candidate.build_hash,
                "promoted_at": receipt.promoted_at,
            }
            pointer_data = _canonical(pointer)
            pointer_key = f"preview/hosts/{host}/active.json"
            existing_pointer = await self.storage.get(pointer_key)
            if existing_pointer is not None:
                try:
                    existing_payload = json.loads(existing_pointer[1].decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise PromotionError(
                        "PROMOTION_POINTER_INVALID", "The active preview pointer is invalid."
                    ) from exc
                if existing_payload.get("receipt_key") == receipt_key:
                    pointer_object = existing_pointer[0]
                else:
                    pointer_object = await self.storage.put_conditional(
                        key=pointer_key,
                        data=pointer_data,
                        content_type="application/json",
                        expected_etag=pending.previous_pointer_etag or None,
                    )
            else:
                pointer_object = await self.storage.put_conditional(
                    key=pointer_key,
                    data=pointer_data,
                    content_type="application/json",
                    expected_etag=pending.previous_pointer_etag or None,
                )
            return ActivePreview(
                host=host,
                url=f"{self.preview_base_url}/{host}/",
                candidate_id=pending.candidate.candidate_id,
                candidate_identity_hash=pending.candidate.candidate_identity_hash,
                build_hash=pending.candidate.build_hash,
                receipt_key=receipt_key,
                receipt_hash=receipt_object.sha256,
                pointer_etag=pointer_object.etag,
                route_ids=pending.candidate.route_ids,
                promoted_at=receipt.promoted_at,
            )
        except PreviewStorageError as exc:
            raise PromotionError(exc.code, exc.message) from exc


def pending_manifest_entries(manifest: dict[str, Any]) -> list[BuildManifestEntry]:
    """Parse the pointer manifest through the same typed build contract."""

    try:
        return BuildManifest.model_validate(manifest).entries
    except ValidationError as exc:
        raise PromotionError(
            "PROMOTION_MANIFEST_INVALID", "The promotion manifest is invalid."
        ) from exc
