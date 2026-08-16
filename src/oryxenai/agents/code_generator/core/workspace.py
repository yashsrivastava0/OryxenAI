"""Trusted isolated workspace management for standalone source generation."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any


class WorkspaceError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def repository_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src").is_dir():
            return parent
    raise WorkspaceError(
        "REPOSITORY_ROOT_UNAVAILABLE", "The repository root could not be resolved."
    )


class GenerationWorkspace:
    """Owns a disposable generation tree and its trusted input boundary."""

    def __init__(self, root: Path, input_root: Path, checkpoint_root: Path) -> None:
        self.root = root
        self.input_dir = root / "input"
        self.ledger_dir = root / "ledger"
        self.repo_dir = root / "repo"
        self.artifacts_dir = root / "artifacts"
        self.checkpoint_root = checkpoint_root
        self.manifest_root = input_root

    @classmethod
    def open(
        cls,
        settings: Any,
        *,
        run_id: str,
        admitted_identity: str,
        scaffold_profile: str | None = None,
    ) -> GenerationWorkspace:
        config = settings.code_generator_generation
        root = _resolve_path(config.workspace_root) / run_id
        input_root = _resolve_path(settings.code_generator_development.input_root)
        checkpoint_root = _resolve_path(config.checkpoint_root) / run_id
        workspace = cls(root, input_root, checkpoint_root)
        workspace._initialize(
            settings,
            admitted_identity=admitted_identity,
            scaffold_profile=scaffold_profile or config.scaffold_profile,
        )
        return workspace

    def _initialize(self, settings: Any, *, admitted_identity: str, scaffold_profile: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        metadata_path = self.root / "ledger" / "workspace.json"
        if metadata_path.is_file():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                metadata = {}
            if (
                metadata.get("admitted_identity") != admitted_identity
                or metadata.get("scaffold_profile") != scaffold_profile
            ):
                for disposable in (
                    self.input_dir,
                    self.ledger_dir,
                    self.repo_dir,
                    self.artifacts_dir,
                ):
                    if disposable.exists():
                        shutil.rmtree(disposable)
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_root.mkdir(parents=True, exist_ok=True)

        admitted = (
            _resolve_path(settings.code_generator_development.input_root)
            / "admitted"
            / admitted_identity
        )
        if not admitted.is_dir():
            raise WorkspaceError(
                "ADMITTED_INPUT_MISSING", "The admitted input directory is unavailable."
            )
        if not self.input_dir.exists():
            shutil.copytree(admitted, self.input_dir, symlinks=False)
        self._assert_tree_safe(self.input_dir)

        scaffold_root = _resolve_path(settings.code_generator_generation.scaffold_root)
        scaffold = (scaffold_root / scaffold_profile).resolve()
        if not scaffold.is_dir() or not scaffold.is_relative_to(scaffold_root):
            raise WorkspaceError(
                "SCAFFOLD_UNAVAILABLE", "The configured generator scaffold is unavailable."
            )
        if not self.repo_dir.exists():
            shutil.copytree(
                scaffold,
                self.repo_dir,
                symlinks=False,
                ignore=shutil.ignore_patterns("node_modules", "dist"),
            )
        self._assert_tree_safe(self.repo_dir)
        self.write_json(
            self.ledger_dir / "workspace.json",
            {
                "schema_version": "code-generator-workspace-v1",
                "run_id": self.root.name,
                "admitted_identity": admitted_identity,
                "scaffold_profile": scaffold_profile,
            },
        )

    def write_json(self, path: Path, value: object) -> None:
        target = path.resolve()
        if not target.is_relative_to(self.root.resolve()):
            raise WorkspaceError("WORKSPACE_PATH_UNSAFE", "A workspace write escaped the run root.")
        target.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        partial = target.with_name(f".{target.name}.partial")
        partial.write_text(data, encoding="utf-8", newline="\n")
        os.replace(partial, target)
        if target.read_text(encoding="utf-8") != data:
            raise WorkspaceError(
                "WORKSPACE_READBACK_FAILED", "A workspace JSON write failed read-back."
            )

    def copy_pack_file(self, relative_path: str, destination: str) -> Path:
        source = (self.input_dir / relative_path).resolve()
        target = (self.repo_dir / destination).resolve()
        if not source.is_relative_to(self.input_dir.resolve()) or not source.is_file():
            raise WorkspaceError("PACK_FILE_MISSING", "A referenced pack file is unavailable.")
        if not target.is_relative_to(self.repo_dir.resolve()):
            raise WorkspaceError(
                "WORKSPACE_PATH_UNSAFE", "A resource destination escaped the repository."
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return target

    def materialize_pack_resources(self) -> list[str]:
        source_root = self.input_dir / "resources"
        if not source_root.is_dir():
            return []
        copied: list[str] = []
        for source in sorted(source_root.rglob("*")):
            if not source.is_file() or source.name in {"ledger.json", "projection.json"}:
                continue
            relative = source.relative_to(source_root).as_posix()
            destination = self.repo_dir / "public" / "resources" / "pack" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            copied.append(destination.relative_to(self.repo_dir).as_posix())
        return copied

    def materialize_acquisition_resources(
        self, ledger: dict[str, Any] | None, materials_root: Path
    ) -> list[dict[str, str]]:
        """Copy receipt-bound Phase 2 materials into this generation workspace."""

        copied: list[dict[str, str]] = []
        for receipt in (ledger or {}).get("receipts", []):
            if not isinstance(receipt, dict) or receipt.get("disposition") != "admitted":
                continue
            request_hash = str(receipt.get("request_hash", ""))
            for material in receipt.get("materialized_files", []):
                if not isinstance(material, dict):
                    continue
                local_path = str(material.get("local_path", ""))
                source = (materials_root / local_path).resolve()
                if not source.is_file():
                    raise WorkspaceError(
                        "ACQUIRED_RESOURCE_MISSING",
                        "A receipt-bound acquired resource is unavailable.",
                    )
                digest = str(material.get("sha256", ""))
                suffix = source.suffix.lower() or ".bin"
                destination_name = f"{digest}{suffix}"
                destination = (
                    self.repo_dir / "public" / "resources" / "acquired" / destination_name
                ).resolve()
                if not destination.is_relative_to(self.repo_dir.resolve()):
                    raise WorkspaceError(
                        "RESOURCE_PATH_UNSAFE", "An acquired resource destination is unsafe."
                    )
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                copied.append(
                    {
                        "request_hash": request_hash,
                        "source_path": local_path,
                        "local_path": destination.relative_to(self.repo_dir).as_posix(),
                        "sha256": digest,
                    }
                )
        return copied

    def synchronize_dependency_manifest(self, dependency_repo: Path) -> bool:
        """Apply the trusted Phase 2 manifest/lock result to this repo."""

        package = dependency_repo / "package.json"
        lock = dependency_repo / "package-lock.json"
        if not package.is_file() and not lock.is_file():
            return False
        if not package.is_file() or not lock.is_file():
            raise WorkspaceError(
                "DEPENDENCY_MANIFEST_INCOMPLETE",
                "The dependency receipt does not contain both package and lock files.",
            )
        for source, name in ((package, "package.json"), (lock, "package-lock.json")):
            data = source.read_bytes()
            target = (self.repo_dir / name).resolve()
            if not target.is_relative_to(self.repo_dir.resolve()):
                raise WorkspaceError(
                    "WORKSPACE_PATH_UNSAFE", "A dependency manifest escaped the repository."
                )
            target.write_bytes(data)
        return True

    def materialize_acquired_file(self, source: Path, relative_name: str) -> str:
        target = (self.repo_dir / "public" / "resources" / "acquired" / relative_name).resolve()
        if not target.is_relative_to(self.repo_dir.resolve()):
            raise WorkspaceError(
                "RESOURCE_PATH_UNSAFE", "An acquired resource destination is unsafe."
            )
        if not source.is_file():
            raise WorkspaceError(
                "RESOURCE_FILE_MISSING", "An acquired resource file is unavailable."
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return target.relative_to(self.repo_dir).as_posix()

    @staticmethod
    def _assert_tree_safe(root: Path) -> None:
        for path in root.rglob("*"):
            if path.is_symlink():
                raise WorkspaceError(
                    "WORKSPACE_SYMLINK", "Generation workspaces cannot contain symlinks."
                )
            if not path.resolve().is_relative_to(root.resolve()):
                raise WorkspaceError("WORKSPACE_PATH_UNSAFE", "A workspace entry escaped its root.")


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (repository_root() / path).resolve()
