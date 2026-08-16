"""Bounded model-assisted correction for final verification diagnostics."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from oryxenai.agents.code_generator.core.check_runner import prepare_toolchain, run_source_checks
from oryxenai.agents.code_generator.core.checkpoint_store import CheckpointStore
from oryxenai.agents.code_generator.core.development_schemas import (
    CandidateIdentity,
    Diagnostic,
    GenerationResult,
    RepairReceipt,
    SitePlan,
    SourceCheckpoint,
)
from oryxenai.agents.code_generator.core.diagnostics import build_bundle
from oryxenai.agents.code_generator.core.generation_prompt_builder import build_instructions
from oryxenai.agents.code_generator.core.source_validation import validate_generation_changes
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace


class FinalRepairError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class FinalRepairer:
    def __init__(self, model_factory: Callable[[str], Any] | None = None) -> None:
        self._model_factory = model_factory

    async def repair(
        self,
        *,
        settings: Any,
        workspace: GenerationWorkspace,
        checkpoint_store: CheckpointStore,
        checkpoint: SourceCheckpoint,
        identity: CandidateIdentity,
        plan: SitePlan,
        projections: dict[str, dict[str, Any]],
        diagnostics: list[Diagnostic],
        allowed_paths: list[str],
        public_text: set[str],
        allowed_packages: set[str],
        strategy: str,
        round_number: int,
    ) -> tuple[SourceCheckpoint, RepairReceipt]:
        bundle = build_bundle(
            checkpoint_hash=checkpoint.checkpoint_hash,
            diagnostics=diagnostics,
            allowed_paths=allowed_paths,
            plan_slice=plan.model_dump(mode="json"),
            source_root=workspace.repo_dir,
            required_checks=["source.paths", "source.policy", "source.typecheck"],
            resource_bindings=list(
                (projections.get("resources/ledger.json") or {}).get("active_bindings", [])
            ),
            dependency_signatures=list(
                (projections.get("dependencies/ledger.json") or {}).get("receipts", [])
            ),
        )
        context = {
            "role_profile": str(settings.code_generator_generation.repair_profile),
            "operation": "repair",
            "candidate_identity": identity.model_dump(mode="json"),
            "plan": plan.model_dump(mode="json"),
            "diagnostic_bundle": bundle.model_dump(mode="json"),
            "strategy": strategy,
            "round": round_number,
            "owned_paths": allowed_paths,
            "input_hashes": [identity.identity_hash, checkpoint.checkpoint_hash],
            "output_ceiling": int(settings.code_generator_generation.max_response_bytes),
        }
        system, instructions, context_receipt = build_instructions("repair", context)
        key = hashlib.sha256(
            f"{identity.identity_hash}:{checkpoint.checkpoint_hash}:{round_number}:{context_receipt.context_hash}".encode()
        ).hexdigest()
        result_path = workspace.ledger_dir / "repairs" / f"{key}.json"
        if result_path.is_file():
            result = GenerationResult.model_validate(
                json.loads(result_path.read_text(encoding="utf-8"))
            )
        else:
            client = self._client(settings, str(settings.code_generator_generation.repair_profile))
            if client is None:
                raise FinalRepairError(
                    "REPAIR_PROFILE_UNAVAILABLE", "The configured repair profile is unavailable."
                )
            raw = await client.generate_structured(
                operation="code_generator.repair",
                instructions=instructions,
                input_payload={**context, "context_receipt_hash": context_receipt.context_hash},
                output_model=GenerationResult,
                system_prompt=system,
                model_profile=str(settings.code_generator_generation.repair_profile),
                strict_schema=True,
            )
            parsed = getattr(raw, "parsed_output", raw)
            result = GenerationResult.model_validate(parsed)
            if result.based_on_context_receipt not in {
                context_receipt.context_hash,
                context_receipt.receipt_id,
            }:
                raise FinalRepairError(
                    "REPAIR_CONTEXT_MISMATCH",
                    "The repair result is not bound to the current diagnostic context.",
                )
            workspace.write_json(result_path, result.model_dump(mode="json"))
        if result.mode != "changes" or result.changes is None:
            raise FinalRepairError(
                "REPAIR_NO_SOURCE_CHANGE",
                "The repair operation did not return a bounded source correction.",
            )
        candidate = workspace.root / f"repair-{round_number}"
        if candidate.exists():
            shutil.rmtree(candidate)
        shutil.copytree(
            workspace.repo_dir,
            candidate,
            symlinks=False,
            ignore=shutil.ignore_patterns("node_modules", "dist"),
        )
        normalized = validate_generation_changes(
            result.changes,
            owned_paths=allowed_paths,
            repo_dir=candidate,
            max_file_bytes=int(settings.code_generator_generation.max_file_bytes),
            max_response_bytes=int(settings.code_generator_generation.max_response_bytes),
            allowed_packages=allowed_packages,
            public_text=public_text,
        )
        for change in normalized:
            target = (candidate / change.path).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(change.complete_utf8_content, encoding="utf-8", newline="\n")
        old = workspace.root / f"repair-{round_number}-old"
        if old.exists():
            shutil.rmtree(old)
        os.replace(workspace.repo_dir, old)
        os.replace(candidate, workspace.repo_dir)
        shutil.rmtree(old, ignore_errors=True)
        toolchain_issue = await prepare_toolchain(workspace.repo_dir, settings=settings)
        if toolchain_issue is not None:
            raise FinalRepairError("REPAIR_TOOLCHAIN_FAILED", toolchain_issue.normalized_message)
        cheap_diagnostics = await run_source_checks(
            workspace.repo_dir,
            allowed_packages=allowed_packages,
            public_text=public_text,
            max_source_bytes=int(settings.code_generator_generation.max_source_bytes),
            work_unit_id="final-repair",
            settings=settings,
        )
        if cheap_diagnostics:
            raise FinalRepairError(
                "REPAIR_SOURCE_CHECK_FAILED", cheap_diagnostics[0].normalized_message
            )
        corrected = checkpoint_store.accept(
            work_unit_id=f"final-repair-{round_number}",
            parent_hash=checkpoint.checkpoint_hash,
        )
        receipt = RepairReceipt(
            generation_id=identity.identity_hash,
            diagnostic_fingerprints=sorted({item.fingerprint for item in diagnostics}),
            strategy_summary=strategy,
            based_on_checkpoint=checkpoint.checkpoint_hash,
            context_receipt=context_receipt.context_hash,
            allowed_paths=allowed_paths,
            changed_file_hashes={
                change.path: hashlib.sha256(
                    change.complete_utf8_content.encode("utf-8")
                ).hexdigest()
                for change in normalized
            },
            corrected_checkpoint=corrected.checkpoint_hash,
            checks_rerun=["source.paths", "source.policy", "source.typecheck"],
            accepted_at=datetime.now(UTC).isoformat(),
        )
        return corrected, receipt

    def _client(self, settings: Any, profile: str) -> Any | None:
        if self._model_factory is not None:
            return self._model_factory(profile)
        from oryxenai.agents.shared.model_client import build_provider_client

        return build_provider_client(profile, settings.models)


def repair_allowed_paths(diagnostics: list[Diagnostic], plan: SitePlan) -> list[str]:
    del plan
    file_paths = {
        item.file for item in diagnostics if item.file and not item.file.startswith("public/")
    }
    if file_paths:
        return sorted(file_paths)
    route_ids = {item.route_id for item in diagnostics if item.route_id}
    if route_ids:
        route_paths: list[str] = []
        for route_id in sorted(route_ids):
            route_paths.append(f"src/routes/{route_id}/**")
        return route_paths
    return ["src/design/**", "src/components/shared/**"]
