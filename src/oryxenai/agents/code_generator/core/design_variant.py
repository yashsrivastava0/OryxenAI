"""Persistent same-variant retry and new-variant regeneration semantics."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from oryxenai.agents.code_generator.core.development_schemas import DesignVariantReceiptV1


def create_design_variant_receipt(
    *,
    input_hash: str,
    ordinal: int,
    idempotency_key: str,
    creation_reason: str,
    prior_fingerprint_hashes: list[str],
    created_at: str | None = None,
) -> DesignVariantReceiptV1:
    seed_hash = hashlib.sha256(
        f"{input_hash}:{ordinal}:{idempotency_key}:{creation_reason}".encode()
    ).hexdigest()
    return DesignVariantReceiptV1(
        variant_id=f"variant-{seed_hash[:24]}",
        ordinal=ordinal,
        input_hash=input_hash,
        seed_hash=seed_hash,
        prior_design_fingerprints=prior_fingerprint_hashes[-3:],
        creation_reason=creation_reason,  # type: ignore[arg-type]
        created_at=created_at or datetime.now(UTC).isoformat(),
    )


__all__ = ["create_design_variant_receipt"]
