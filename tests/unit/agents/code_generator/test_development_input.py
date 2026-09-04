from __future__ import annotations

from pathlib import Path

import pytest

from oryxenai.agents.code_generator.core.brief_ingestion import (
    CONTENT_FILENAME,
    VISUAL_FILENAME,
)
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


def test_fixture_markdown_pair_is_admitted_and_compiled(tmp_path) -> None:
    """Legacy privacy-safe fixtures are converted to the current brief contract."""

    adapter = _adapter(tmp_path)
    reference = adapter.from_fixture("privacy-safe-v3")

    receipt, projections = adapter.admit(reference)

    assert receipt.source_version == "build-preparation-brief-v1"
    assert receipt.schema_version == "code-generator-brief-envelope-v1"
    assert receipt.route_ids == ["home"]
    assert projections["site/contract.json"]["navigation_contract"]["closed"] is True
    assert (
        projections["execution/contract.json"]["policy"]["runtime_network_fetch_allowed"] is False
    )


def test_build_preparation_markdown_uploads_are_wrapped_and_admitted(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    output = Path("output/build-preparation/01-31-04-09-94ae4a9c")
    reference = adapter.from_brief_uploads(
        content_filename=CONTENT_FILENAME,
        content_data=(output / CONTENT_FILENAME).read_bytes(),
        visual_filename=VISUAL_FILENAME,
        visual_data=(output / VISUAL_FILENAME).read_bytes(),
    )
    receipt, _projections = adapter.admit(reference)

    assert reference.mode == "build_preparation_briefs"
    assert receipt.content_brief_sha256
    assert receipt.visual_brief_sha256
    assert receipt.source_sha256 == reference.source_sha256
    admitted_copy = (
        Path(adapter._config.input_root)
        / "admitted"
        / receipt.admitted_identity
        / "brief-envelope.json"
    )
    # The workspace consumes the identity-addressed admission tree even though
    # the immutable source itself remains content-addressed under inputs/.
    assert admitted_copy.is_file()
    assert admitted_copy.read_bytes() == adapter.read(reference)


def test_upload_mime_and_filename_are_rejected_before_storage(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    valid = adapter.read(adapter.from_fixture("privacy-safe-v3"))
    with pytest.raises(DevelopmentInputError, match="application/json"):
        adapter.from_upload(filename="briefs.json", mime_type="text/plain", data=valid)
    with pytest.raises(DevelopmentInputError, match=r"safe \.json"):
        adapter.from_upload(filename="../briefs.json", mime_type="application/json", data=valid)


def test_upload_size_limit_is_enforced_before_storage(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    adapter._config.max_upload_bytes = 1
    with pytest.raises(DevelopmentInputError, match="size limit"):
        adapter.from_upload(filename="briefs.json", mime_type="application/json", data=b"{}")


def test_json_envelope_upload_rejects_malformed_payload(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    with pytest.raises(DevelopmentInputError) as caught:
        adapter.from_upload(filename="briefs.json", mime_type="application/json", data=b"not-json")
    assert caught.value.code == "BRIEF_ENVELOPE_INVALID"


def test_markdown_upload_names_and_encoding_are_closed(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    with pytest.raises(DevelopmentInputError, match="named"):
        adapter.from_brief_uploads(
            content_filename="content.md",
            content_data=b"# content",
            visual_filename=VISUAL_FILENAME,
            visual_data=b"# visual",
        )
    with pytest.raises(DevelopmentInputError, match="UTF-8"):
        adapter.from_brief_uploads(
            content_filename=CONTENT_FILENAME,
            content_data=b"\xff",
            visual_filename=VISUAL_FILENAME,
            visual_data=b"# visual",
        )
