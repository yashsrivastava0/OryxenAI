"""Atomic trusted application of model-owned source changes."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from oryxenai.agents.code_generator.core.development_schemas import GenerationChanges
from oryxenai.agents.code_generator.core.source_validation import validate_generation_changes


class SourceAssembler:
    def apply(
        self,
        repo_dir: Path,
        changes: GenerationChanges,
        *,
        owned_paths: list[str],
        max_file_bytes: int,
        max_response_bytes: int,
        allowed_packages: set[str],
        public_text: set[str],
    ) -> list[str]:
        normalized = validate_generation_changes(
            changes,
            owned_paths=owned_paths,
            repo_dir=repo_dir,
            max_file_bytes=max_file_bytes,
            max_response_bytes=max_response_bytes,
            allowed_packages=allowed_packages,
            public_text=public_text,
        )
        candidate = repo_dir.with_name(f".{repo_dir.name}.candidate")
        old = repo_dir.with_name(f".{repo_dir.name}.previous")
        if candidate.exists():
            shutil.rmtree(candidate)
        if old.exists():
            shutil.rmtree(old)
        shutil.copytree(
            repo_dir,
            candidate,
            symlinks=False,
            ignore=shutil.ignore_patterns("node_modules", "dist"),
        )
        for change in normalized:
            target = (candidate / change.path).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(change.complete_utf8_content, encoding="utf-8", newline="\n")
        os.replace(repo_dir, old)
        os.replace(candidate, repo_dir)
        shutil.rmtree(old, ignore_errors=True)
        return [change.path for change in normalized]
