"""Construction of the immutable Phase 4 candidate identity."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import (
    CandidateIdentity,
    DependencyLedger,
    SitePlan,
    SourceCheckpoint,
    VerificationProfile,
)


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def build_candidate_identity(
    *,
    run: Any,
    plan: SitePlan,
    checkpoint: SourceCheckpoint,
    source_manifest_hash: str,
    profile: VerificationProfile,
) -> CandidateIdentity:
    resource_ledger = dict(run.resource_ledger or {})
    dependency_ledger = DependencyLedger.model_validate(run.dependency_ledger or {"receipts": []})
    input_receipt = dict(run.input_receipt or {})
    plan_hash = str((run.planner_receipt or {}).get("plan_hash", ""))
    return CandidateIdentity(
        input_receipt_hash=str(input_receipt.get("admitted_identity", "")),
        site_plan_hash=plan_hash or _hash(plan.model_dump(mode="json")),
        work_graph_hash=_hash(plan.work_graph.model_dump(mode="json")),
        resource_ledger_hash=str(resource_ledger.get("ledger_hash", "")),
        dependency_ledger_hash=str(dependency_ledger.dependency_ledger_hash),
        source_checkpoint_hash=checkpoint.checkpoint_hash,
        source_manifest_hash=source_manifest_hash or checkpoint.source_manifest_hash,
        scaffold_toolchain_profile_hash=_hash(
            {
                "scaffold_profile": "react-vite-v1",
                "source_manifest_hash": source_manifest_hash or checkpoint.source_manifest_hash,
            }
        ),
        verification_profile_hash=profile.profile_hash,
    )
