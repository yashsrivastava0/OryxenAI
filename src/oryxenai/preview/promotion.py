"""Crash-safe candidate storage and active-preview promotion."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

import httpx
from pydantic import ValidationError

from oryxenai.agents.code_generator.core.development_schemas import (
    ActivePreview,
    BuildManifest,
    BuildManifestEntry,
    CandidateArtifact,
    CandidateIdentity,
    PendingPromotion,
    PromotionReceipt,
    PublicReadbackEntryV1,
    PublicReadbackReceiptV1,
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


PublicReadback = Callable[
    [str, str, CandidateArtifact, BuildManifest, str],
    Awaitable[PublicReadbackReceiptV1],
]
_PREVIEW_HOST_RE = re.compile(r"^[a-z2-7][a-z2-7-]{15,63}$")


class PreviewPromoter:
    def __init__(
        self,
        storage: PreviewStorage,
        *,
        preview_base_url: str = "http://127.0.0.1:4174/preview",
        require_readback: bool = False,
        public_readback: PublicReadback | None = None,
    ) -> None:
        self.storage = storage
        self.preview_base_url = preview_base_url.rstrip("/")
        self.require_readback = require_readback
        self.public_readback = public_readback

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
                key = f"{prefix}/dist/{entry.path}"
                await self.storage.put_immutable(
                    key=key,
                    data=data,
                    content_type=entry.media_type,
                )
                stored = await self.storage.get(key)
                if (
                    stored is None
                    or stored[0].sha256 != entry.sha256
                    or stored[0].size_bytes != entry.size_bytes
                    or stored[1] != data
                ):
                    raise PromotionError(
                        "CANDIDATE_STORAGE_READBACK_FAILED",
                        "A candidate build object failed storage read-back verification.",
                    )
            except PreviewStorageError as exc:
                raise PromotionError(exc.code, exc.message) from exc
        report_data = _canonical(verification_report)
        report_hash = hashlib.sha256(report_data).hexdigest()
        try:
            report_key = f"preview/verification/{candidate_id}/{report_hash}.json"
            await self.storage.put_immutable(
                key=report_key,
                data=report_data,
                content_type="application/json",
            )
            stored_report = await self.storage.get(report_key)
            if (
                stored_report is None
                or stored_report[0].sha256 != report_hash
                or stored_report[0].size_bytes != len(report_data)
                or stored_report[1] != report_data
            ):
                raise PromotionError(
                    "CANDIDATE_STORAGE_READBACK_FAILED",
                    "The verification report failed storage read-back verification.",
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
        current = await self.storage.get(f"preview/hosts/{host}/active.json")
        previous_pointer: dict[str, Any] = {}
        previous_pointer_sha256 = ""
        if current is not None:
            try:
                decoded = json.loads(current[1].decode("utf-8"))
                if isinstance(decoded, dict):
                    previous_pointer = decoded
                    previous_pointer_sha256 = current[0].sha256
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise PromotionError(
                    "PROMOTION_POINTER_INVALID",
                    "The existing active preview pointer is invalid.",
                ) from None
        return PendingPromotion(
            promotion_id=f"promotion-{hashlib.sha256(f'{run_id}:{artifact.build_hash}:{expected_revision}'.encode()).hexdigest()[:24]}",
            candidate=artifact,
            verification_report_hash=verification_report_hash,
            expected_revision=expected_revision,
            previous_pointer_etag=current[0].etag if current else "",
            previous_pointer_sha256=previous_pointer_sha256,
            previous_pointer=previous_pointer,
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
        candidate_prefix = str(candidate_pointer.get("candidate_prefix", ""))
        candidate_parts = candidate_prefix.split("/")
        if len(candidate_parts) < 4 or pending.candidate.candidate_id != candidate_parts[2]:
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
            manifest = BuildManifest.model_validate(candidate_pointer["manifest"])
            pointer = {
                "schema_version": "code-generator-active-preview-v1",
                "host": host,
                "candidate_prefix": candidate_prefix,
                "manifest": candidate_pointer["manifest"],
                "receipt_key": receipt_key,
                "receipt_hash": receipt_object.sha256,
                "candidate_id": pending.candidate.candidate_id,
                "candidate_identity_hash": pending.candidate.candidate_identity_hash,
                "build_hash": pending.candidate.build_hash,
                "route_ids": pending.candidate.route_ids,
                "route_paths": pending.candidate.route_paths,
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
            public_readback: PublicReadbackReceiptV1 | None = None
            if self.require_readback:
                try:
                    reader = self.public_readback or self._default_public_readback
                    public_readback = await reader(
                        self.preview_base_url,
                        host,
                        pending.candidate,
                        manifest,
                        pending.promotion_id,
                    )
                except Exception as exc:
                    await self._restore_previous_pointer(
                        pointer_key=pointer_key,
                        pointer_object=pointer_object,
                        pending=pending,
                    )
                    if isinstance(exc, PromotionError):
                        raise
                    raise PromotionError(
                        "PREVIEW_PUBLIC_READBACK_FAILED",
                        "The promoted preview did not pass public URL read-back verification.",
                    ) from exc
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
                route_paths=pending.candidate.route_paths,
                promoted_at=receipt.promoted_at,
                public_readback=public_readback,
            )
        except PreviewStorageError as exc:
            raise PromotionError(exc.code, exc.message) from exc

    async def _restore_previous_pointer(
        self,
        *,
        pointer_key: str,
        pointer_object: Any,
        pending: PendingPromotion,
    ) -> None:
        """Undo a failed public promotion only if this attempt still owns it."""

        current = await self.storage.head(pointer_key)
        if current is None or current.etag != pointer_object.etag:
            # A newer promotion won the race.  Never delete or overwrite it.
            return
        if pending.previous_pointer:
            await self.storage.put_conditional(
                key=pointer_key,
                data=_canonical(pending.previous_pointer),
                content_type="application/json",
                expected_etag=pointer_object.etag,
            )
        elif not pending.previous_pointer_etag:
            await self.storage.delete(pointer_key)

    async def _default_public_readback(
        self,
        base_url: str,
        host: str,
        candidate: CandidateArtifact,
        manifest: BuildManifest,
        promotion_id: str,
    ) -> PublicReadbackReceiptV1:
        parsed_base = urlsplit(base_url)
        if (
            parsed_base.scheme not in {"http", "https"}
            or not parsed_base.netloc
            or parsed_base.username is not None
            or parsed_base.password is not None
            or parsed_base.query
            or parsed_base.fragment
            or not _PREVIEW_HOST_RE.fullmatch(host)
        ):
            raise PromotionError(
                "PREVIEW_PUBLIC_READBACK_FAILED",
                "The configured public preview URL is not a safe HTTP(S) origin.",
            )
        root_url = f"{base_url}/{host}/"
        checks: list[tuple[str, str, BuildManifestEntry | None]] = [
            # The gateway injects the mount metadata into index.html for the
            # runtime base URL, so the public root is intentionally checked
            # for reachability and evidence, not byte identity with the
            # immutable artifact. Static assets below remain hash-bound.
            (root_url, "root", None)
        ]
        for route_path in candidate.route_paths:
            normalized = str(route_path or "/").strip()
            if not normalized.startswith("/"):
                normalized = f"/{normalized}"
            encoded_route = quote(normalized.lstrip("/"), safe="/:@-._~")
            url = f"{root_url}{encoded_route}" if normalized != "/" else root_url
            checks.append((url, "route", None))
        for entry in manifest.entries:
            if entry.path == "index.html":
                continue
            url = f"{root_url}{quote(entry.path, safe='/:@-._~')}"
            checks.append((url, _public_readback_kind(entry.path), entry))
        seen: set[str] = set()
        evidence: list[PublicReadbackEntryV1] = []
        try:
            async with httpx.AsyncClient(follow_redirects=False, timeout=8.0) as client:
                for url, kind, expected in checks:
                    if url in seen:
                        continue
                    seen.add(url)
                    response = await client.get(url)
                    if response.status_code < 200 or response.status_code >= 300:
                        raise PromotionError(
                            "PREVIEW_PUBLIC_READBACK_FAILED",
                            f"Public preview read-back returned HTTP {response.status_code}.",
                        )
                    body_hash = hashlib.sha256(response.content).hexdigest()
                    if expected is not None and body_hash != expected.sha256:
                        raise PromotionError(
                            "PREVIEW_PUBLIC_READBACK_FAILED",
                            "A public preview asset differed from the verified build.",
                        )
                    evidence.append(
                        PublicReadbackEntryV1(
                            url=url,
                            kind=kind,  # type: ignore[arg-type]
                            status_code=response.status_code,
                            sha256=body_hash,
                            media_type=response.headers.get("content-type", "").split(";", 1)[0],
                        )
                    )
        except httpx.HTTPError as exc:
            raise PromotionError(
                "PREVIEW_PUBLIC_READBACK_FAILED",
                "The public preview gateway could not be reached for read-back.",
            ) from exc
        return PublicReadbackReceiptV1(
            promotion_id=promotion_id,
            candidate_id=candidate.candidate_id,
            build_hash=candidate.build_hash,
            public_origin=f"{parsed_base.scheme}://{parsed_base.netloc}",
            entries=evidence,
            checked_at=_now(),
        )


def _public_readback_kind(path: str) -> str:
    suffix = Path(path).suffix.casefold()
    if suffix in {".js", ".mjs"}:
        return "javascript"
    if suffix == ".css":
        return "stylesheet"
    if suffix in {".woff", ".woff2", ".ttf", ".otf"}:
        return "font"
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"}:
        return "image"
    return "route"


def pending_manifest_entries(manifest: dict[str, Any]) -> list[BuildManifestEntry]:
    """Parse the pointer manifest through the same typed build contract."""

    try:
        return BuildManifest.model_validate(manifest).entries
    except ValidationError as exc:
        raise PromotionError(
            "PROMOTION_MANIFEST_INVALID", "The promotion manifest is invalid."
        ) from exc
