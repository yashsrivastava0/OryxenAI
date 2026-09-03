from __future__ import annotations

import io
import json
import zipfile

import pytest

from oryxenai.agents.code_generator.core.development_input import (
    DevelopmentInputAdapter,
    DevelopmentInputError,
    _blocking_execution_gaps,
)
from oryxenai.core.settings import Settings


def _adapter(tmp_path) -> DevelopmentInputAdapter:
    settings = Settings()
    settings.code_generator_development.input_root = str(tmp_path / "inputs")
    return DevelopmentInputAdapter(settings)


def test_optional_execution_gaps_are_admissible_but_required_gaps_block() -> None:
    optional = {
        "slots": [{"resource_slot_id": "slot-optional", "required": False}],
        "execution_gaps": [{"slot_id": "slot-optional"}],
    }
    required = {
        "slots": [{"resource_slot_id": "slot-required", "required": True}],
        "execution_gaps": [{"slot_id": "slot-required"}],
    }

    assert _blocking_execution_gaps(optional) == []
    assert _blocking_execution_gaps(required) == required["execution_gaps"]


def test_admit_fails_closed_pending_markdown_brief_ingestion(tmp_path) -> None:
    """Build Preparation now hands off two Markdown briefs, not a versioned

    JSON/ZIP pack. Code Generator ingestion of that new contract is tracked
    as explicit follow-up work (see DECISIONS.md) -- admit() must fail
    closed with one clear diagnostic rather than validating a contract that
    no longer exists on the Build Preparation side.
    """
    adapter = _adapter(tmp_path)
    fixture = adapter.from_fixture("privacy-safe-v3")

    with pytest.raises(DevelopmentInputError) as caught:
        adapter.admit(fixture)

    assert caught.value.code == "PACK_INGESTION_NOT_MIGRATED"


def test_zip_traversal_is_rejected_before_storage(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("../escape.txt", "no")
    with pytest.raises(DevelopmentInputError, match="unsafe entry path"):
        adapter.from_upload(
            filename="unsafe.zip", mime_type="application/zip", data=output.getvalue()
        )


def test_upload_mime_and_filename_are_rejected_before_storage(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    with pytest.raises(DevelopmentInputError, match="application/zip"):
        adapter.from_upload(filename="pack.zip", mime_type="text/plain", data=b"PK")
    with pytest.raises(DevelopmentInputError, match=r"safe \.zip"):
        adapter.from_upload(filename="../pack.zip", mime_type="application/zip", data=b"PK")


def test_upload_size_limit_is_enforced_before_storage(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    adapter._config.max_upload_bytes = 1
    with pytest.raises(DevelopmentInputError, match="size limit"):
        adapter.from_upload(filename="pack.zip", mime_type="application/zip", data=b"PKxx")


def test_v1_pack_still_admits_the_zip_itself_but_fails_at_content_ingestion(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"pack_version": "phase3", "files": []}))
    reference = adapter.from_upload(
        filename="diagnostic.zip", mime_type="application/zip", data=output.getvalue()
    )
    with pytest.raises(DevelopmentInputError) as caught:
        adapter.admit(reference)
    assert caught.value.code == "PACK_INGESTION_NOT_MIGRATED"
