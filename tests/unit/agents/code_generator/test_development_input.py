from __future__ import annotations

import copy
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


def test_fixture_and_upload_share_admitted_identity(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    fixture = adapter.from_fixture("privacy-safe-v3")
    fixture_receipt, _ = adapter.admit(fixture)
    upload = adapter.from_upload(
        filename="same-pack.zip", mime_type="application/zip", data=adapter.read(fixture)
    )
    upload_receipt, _ = adapter.admit(upload)
    assert fixture_receipt.admitted_identity == upload_receipt.admitted_identity
    assert fixture_receipt.route_ids == ["home"]


def test_rich_privacy_safe_fixture_admits_advanced_section_contract(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    reference = adapter.from_fixture("privacy-safe-v3-rich")
    receipt, projections = adapter.admit(reference)
    sections = projections["site/contract.json"]["public_content"][0]["sections"]
    assert receipt.route_ids == ["home"]
    assert [section["section_id"] for section in sections] == [
        "hero",
        "principles",
        "selected-work",
        "process",
        "contact",
    ]


def test_compiled_projection_rejects_visual_identity_mismatch(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    reference = adapter.from_fixture("privacy-safe-v3")
    _, admitted = adapter.admit(reference)
    projections = copy.deepcopy(admitted)
    projections["site/contract.json"]["facts"] = [
        {"fact_id": "owner", "statement": "Arjun Mehta is a designer."}
    ]
    projections["design/visual-direction.json"]["global"] = {
        "must_preserve": ["Aarav Mehta"],
        "visual_language": {"anti_patterns": ["Avoid presenting Aarav as the owner of outcomes."]},
    }
    with zipfile.ZipFile(io.BytesIO(adapter.read(reference))) as archive:
        package_paths = set(archive.namelist())
        route_resource_maps = {
            str(route["route_id"]): json.loads(
                archive.read(str(route["files"]["resources"])).decode("utf-8")
            )
            for route in projections["site/contract.json"]["routes"]
        }

    with pytest.raises(DevelopmentInputError) as caught:
        adapter._validate_projections(
            projections,
            package_paths=package_paths,
            route_resource_maps=route_resource_maps,
        )

    assert caught.value.code == "PACK_VISUAL_IDENTITY_MISMATCH"


def test_v1_pack_is_rejected_without_adaptation(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"pack_version": "phase3", "files": []}))
    reference = adapter.from_upload(
        filename="diagnostic.zip", mime_type="application/zip", data=output.getvalue()
    )
    with pytest.raises(DevelopmentInputError, match="Only Build Preparation pack v3"):
        adapter.admit(reference)


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


def test_missing_required_projection_is_rejected_after_zip_validation(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "manifest.json", json.dumps({"pack_version": "build-preparation-pack-v3", "files": []})
        )
    reference = adapter.from_upload(
        filename="incomplete.zip", mime_type="application/zip", data=output.getvalue()
    )
    with pytest.raises(DevelopmentInputError, match="projection"):
        adapter.admit(reference)
