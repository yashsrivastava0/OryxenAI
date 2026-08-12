from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest

from oryxenai.agents.build_preparation.packager import (
    PackageError,
    package_and_store,
    verify_bundle_bytes,
)
from oryxenai.agents.build_preparation.schemas import (
    BuildPreparationSourceRef,
    MaterializationResult,
)
from oryxenai.core.settings import Settings
from oryxenai.storage.artifacts import ArtifactStorageError, MemoryArtifactStore


def _source_ref() -> BuildPreparationSourceRef:
    return BuildPreparationSourceRef(
        content_architect_content_hash="content",
        visual_design_director_direction_hash="visual",
        input_projection_hash="projection",
    )


def _materialization(root: Path) -> MaterializationResult:
    return MaterializationResult(
        root_path=str(root),
        relative_root=str(root),
        manifest_path="resources/manifest.json",
    )


def _output_dir() -> Path:
    path = Path("output") / "test-build-preparation" / str(uuid4())
    path.mkdir(parents=True)
    return path


@pytest.mark.asyncio
async def test_package_is_verified_stored_and_restored() -> None:
    output_dir = _output_dir()
    staging = output_dir / "staging"
    staging.mkdir()
    (staging / "overview.md").write_text("# Prepared", encoding="utf-8")
    (staging / "routes").mkdir()
    (staging / "routes/home.md").write_text("Home", encoding="utf-8")
    try:
        settings = Settings()
        settings.build_preparation.fixture_output_dir = str(output_dir)
        store = MemoryArtifactStore()

        package, materialization = await package_and_store(
            staging_root=staging,
            output_dir=output_dir,
            run_id=str(uuid4()),
            portfolio_session_id=uuid4(),
            scope_hash="scope",
            source_ref=_source_ref(),
            materialization=_materialization(staging),
            settings=settings,
            artifact_store=store,
            upload_enabled=False,
            mirror_enabled=True,
        )

        assert package.archive_sha256
        assert package.artifact is not None
        assert package.artifact.provider == "memory"
        assert package.file_count >= 4
        mirror = Path(materialization.root_path)
        mirror_folder = mirror.parent.name
        assert re.fullmatch(r"\d{2}-\d{2}-\d{2}-\d{2}-[0-9a-f]{8}", mirror_folder)
        assert (mirror / "manifest.json").is_file()
        assert (mirror / "overview.md").read_text(encoding="utf-8") == "# Prepared"
        manifest = json.loads((mirror / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["pack_version"] == "phase3"
        assert manifest["source_ref"]["input_projection_hash"] == "projection"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_memory_store_rejects_immutable_conflicts() -> None:
    store = MemoryArtifactStore()
    first_hash = hashlib.sha256(b"first").hexdigest()
    second_hash = hashlib.sha256(b"second").hexdigest()
    reference = await store.put_verified(
        key="temporary/run.zip",
        data=b"first",
        sha256=first_hash,
        expires_at="2099-01-01T00:00:00+00:00",
    )
    assert reference.provider == "memory"
    with pytest.raises(ArtifactStorageError) as exc_info:
        await store.put_verified(
            key="temporary/run.zip",
            data=b"second",
            sha256=second_hash,
            expires_at="2099-01-01T00:00:00+00:00",
        )
    assert exc_info.value.code == "ARTIFACT_IMMUTABLE_CONFLICT"


def test_bundle_verification_rejects_manifest_tampering() -> None:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"files": []}))
        archive.writestr("unexpected.txt", "not indexed")
    with pytest.raises(PackageError) as exc_info:
        verify_bundle_bytes(output.getvalue(), max_bytes=1024 * 1024)
    assert exc_info.value.code == "BUILD_PACK_MANIFEST_INVALID"


def test_bundle_verification_rejects_windows_drive_paths() -> None:
    content = b"escape"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "files": [
                        {
                            "path": "C:/escape.txt",
                            "size_bytes": len(content),
                            "sha256": hashlib.sha256(content).hexdigest(),
                        }
                    ]
                }
            ),
        )
        archive.writestr("C:/escape.txt", content)
    with pytest.raises(PackageError) as exc_info:
        verify_bundle_bytes(output.getvalue(), max_bytes=1024 * 1024)
    assert exc_info.value.code == "BUILD_PACK_UNSAFE_PATH"
