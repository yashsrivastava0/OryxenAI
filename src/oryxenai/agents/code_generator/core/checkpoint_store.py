"""Immutable source checkpoint storage for Phase 3."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.core import fs_safe
from oryxenai.agents.code_generator.core.development_schemas import SourceCheckpoint
from oryxenai.agents.code_generator.core.source_manifest import build_source_manifest, digest
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace


class CheckpointError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class CheckpointStore:
    def __init__(self, workspace: GenerationWorkspace, *, generation_id: str) -> None:
        self.workspace = workspace
        self.generation_id = generation_id

    def accept(self, *, work_unit_id: str, parent_hash: str = "") -> SourceCheckpoint:
        manifest = build_source_manifest(self.workspace.repo_dir)
        source_manifest_hash = digest(manifest)
        checkpoint_hash = hashlib.sha256(
            json.dumps(
                {
                    "parent": parent_hash,
                    "work_unit_id": work_unit_id,
                    "manifest": source_manifest_hash,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        target = self.workspace.checkpoint_root / checkpoint_hash
        if target.exists():
            if not (target / "source-manifest.json").is_file():
                raise CheckpointError("CHECKPOINT_INVALID", "An existing checkpoint is incomplete.")
        else:
            partial = target.with_name(f".{target.name}.partial")
            fs_safe.remove_tree(partial, required=False)
            partial.mkdir(parents=True, exist_ok=True)
            self._copy_source_tree(self.workspace.repo_dir, partial / "repo")
            fs_safe.write_text_atomic(
                partial / "source-manifest.json",
                json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            )
            try:
                fs_safe.rename_dir_with_retry(partial, target)
            except fs_safe.FsSafeError as exc:
                fs_safe.remove_tree(partial, required=False)
                raise CheckpointError(
                    "CHECKPOINT_SWAP_FAILED",
                    "The checkpoint could not be finalized under filesystem locks; "
                    "the run stays resumable from the last accepted checkpoint.",
                ) from exc
        total_bytes = sum(int(item["size"]) for item in manifest)
        relative_checkpoint = target.relative_to(
            self.workspace.checkpoint_root.parent.parent
        ).as_posix()
        manifest_relative = self._write_api_manifest(
            checkpoint_hash,
            manifest,
            source_manifest_hash,
            work_unit_id,
        )
        return SourceCheckpoint(
            checkpoint_id=f"checkpoint-{checkpoint_hash[:20]}",
            parent_checkpoint_hash=parent_hash,
            checkpoint_hash=checkpoint_hash,
            stored_relative_path=relative_checkpoint,
            manifest_path=manifest_relative,
            source_manifest_hash=source_manifest_hash,
            file_count=len(manifest),
            total_bytes=total_bytes,
            work_unit_id=work_unit_id,
            accepted_at=datetime.now(UTC).isoformat(),
        )

    def restore(self, checkpoint: SourceCheckpoint) -> None:
        source = self.workspace.checkpoint_root / checkpoint.checkpoint_hash / "repo"
        if not source.is_dir():
            raise CheckpointError(
                "CHECKPOINT_MISSING", "The accepted source checkpoint is unavailable."
            )
        if self.workspace.repo_dir.exists():
            fs_safe.remove_tree(self.workspace.repo_dir)
        self._copy_source_tree(source, self.workspace.repo_dir)

    def _write_api_manifest(
        self,
        checkpoint_hash: str,
        manifest: list[dict[str, Any]],
        source_manifest_hash: str,
        work_unit_id: str,
    ) -> str:
        relative = Path("generation-manifests") / self.generation_id / f"{checkpoint_hash}.json"
        target = (self.workspace.manifest_root / relative).resolve()
        if not target.is_relative_to(self.workspace.manifest_root.resolve()):
            raise CheckpointError("MANIFEST_PATH_UNSAFE", "The source manifest path is unsafe.")
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "code-generator-source-manifest-v1",
            "checkpoint_hash": checkpoint_hash,
            "source_manifest_hash": source_manifest_hash,
            "work_unit_id": work_unit_id,
            "files": manifest,
        }
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        fs_safe.write_text_atomic(target, data)
        return relative.as_posix()

    @staticmethod
    def _copy_source_tree(source: Path, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        for path in sorted(source.rglob("*")):
            if any(part in {"node_modules", "dist"} for part in path.parts):
                continue
            relative = path.relative_to(source)
            destination = target / relative
            if path.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            elif path.is_file():
                fs_safe.copy_file_with_retry(path, destination)
