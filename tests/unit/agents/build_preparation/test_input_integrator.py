from __future__ import annotations

import hashlib
from types import SimpleNamespace
from uuid import uuid4

import pytest

from oryxenai.agents.build_preparation.input_integrator import (
    BuildPreparationInputIntegrator,
)
from oryxenai.agents.build_preparation.schemas import (
    BuildPreparationState,
    BuildPreparationStatus,
    PackageResult,
)
from oryxenai.agents.build_preparation.service import BuildPreparationService
from oryxenai.agents.build_preparation.validators import (
    BuildPreparationValidationError,
    validate_content_visual_identity_consistency,
)
from oryxenai.agents.content_architect.schemas import (
    ContentArchitectApproval,
    ContentArchitectState,
    ContentArchitectStatus,
)
from oryxenai.agents.visual_design_director.schemas import (
    VisualDesignDirectorApproval,
    VisualDesignDirectorState,
    VisualDesignDirectorStatus,
)
from oryxenai.core.settings import Settings
from oryxenai.jobs.service import JobService
from oryxenai.storage.artifacts import MemoryArtifactStore


def _content() -> dict[str, object]:
    return {
        "approved": {"content_hash": "content-hash"},
        "route_plan": [{"route_id": "home", "path": "/", "publication_status": "approved"}],
        "page_content_packs": [
            {
                "route_id": "home",
                "internal_notes": {"private": "remove me"},
                "sections": [{"section_id": "hero", "content": {"heading": "Public"}}],
            }
        ],
        "claim_grounding": [
            {"claim_id": "public", "publication_status": "approved"},
            {"claim_id": "private", "publication_status": "draft"},
        ],
    }


def _visual() -> dict[str, object]:
    return {
        "approved": {"visual_direction_hash": "visual-hash"},
        "pages": [{"route_id": "home", "path": "/", "scenes": []}],
        "asset_briefs": [],
        "resource_candidates": [],
        "visual_language": {"style": "editorial"},
    }


def test_integrator_returns_redacted_two_input_snapshot() -> None:
    inputs = BuildPreparationInputIntegrator(Settings()).compose(
        _content(),
        _visual(),
        content_architect_session_revision=4,
        visual_design_director_session_revision=5,
    )

    assert inputs.content_architect["approved"] == {"content_hash": "content-hash"}
    assert inputs.content_architect["page_content_packs"][0]["internal_notes"] == {}
    assert inputs.content_architect["claim_grounding"] == [
        {"claim_id": "public", "publication_status": "approved"}
    ]
    assert inputs.visual_design_director["approved"] == {"visual_direction_hash": "visual-hash"}
    assert inputs.source_ref.content_architect_content_hash == "content-hash"
    assert inputs.source_ref.visual_design_director_direction_hash == "visual-hash"
    assert inputs.source_ref.content_architect_session_revision == 4
    assert inputs.source_ref.visual_design_director_session_revision == 5
    assert inputs.source_ref.input_projection_hash


def test_integrator_source_ref_changes_when_either_upstream_changes() -> None:
    integrator = BuildPreparationInputIntegrator(Settings())
    original = integrator.compose(_content(), _visual()).source_ref

    changed_content = _content()
    changed_content["route_plan"] = [
        {"route_id": "about", "path": "/about", "publication_status": "approved"}
    ]
    changed_visual = _visual()
    changed_visual["approved"] = {"visual_direction_hash": "different-visual-hash"}

    assert integrator.compose(changed_content, _visual()).source_ref.input_projection_hash != (
        original.input_projection_hash
    )
    assert integrator.compose(
        _content(), changed_visual
    ).source_ref.visual_design_director_direction_hash != (
        original.visual_design_director_direction_hash
    )


def test_integrator_rejects_repeated_visual_identity_mismatch() -> None:
    content = _content()
    content["claim_grounding"] = [
        {
            "claim_id": "role",
            "publication_status": "approved",
            "statement": "Arjun Mehta is a Senior UI/UX Designer.",
        }
    ]
    visual = _visual()
    visual["must_preserve"] = ["Aarav Mehta"]
    visual["visual_language"] = {
        "anti_patterns": ["Do not present Aarav as the owner of team outcomes."],
    }

    with pytest.raises(BuildPreparationValidationError) as caught:
        BuildPreparationInputIntegrator(Settings()).compose(content, visual)

    assert caught.value.code == "PACK_VISUAL_IDENTITY_MISMATCH"
    assert caught.value.details == {
        "approved_name": "Arjun Mehta",
        "mismatched_names": "Aarav Mehta",
    }


def test_identity_validator_accepts_compiled_canonical_projection() -> None:
    validate_content_visual_identity_consistency(
        {"facts": [{"fact_id": "role", "statement": "Arjun Mehta is a designer."}]},
        {
            "global": {
                "must_preserve": ["Arjun Mehta"],
                "visual_language": {"style": "technical editorial"},
            }
        },
    )


class _DownloadRepository:
    def __init__(self, state: BuildPreparationState) -> None:
        self.state = state
        self.session_id = uuid4()

    async def get_session(self, session_id):
        return SimpleNamespace(id=session_id, revision=3)

    async def get_state(self, session_id):
        return self.state

    async def get_content_architect_snapshot(self, session_id):
        return ContentArchitectState(
            status=ContentArchitectStatus.APPROVED,
            approved=ContentArchitectApproval(content_hash="content-hash"),
        )

    async def get_visual_design_director_snapshot(self, session_id):
        return VisualDesignDirectorState(
            status=VisualDesignDirectorStatus.APPROVED,
            approved=VisualDesignDirectorApproval(visual_direction_hash="visual-hash"),
        )


async def _download_service():
    data = b"PK\x03\x04verified-build-pack"
    store = MemoryArtifactStore()
    reference = await store.put_verified(
        key="temporary/session/build.zip",
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        expires_at="2099-01-01T00:00:00+00:00",
    )
    source_ref = (
        BuildPreparationInputIntegrator(Settings())
        .compose(
            ContentArchitectState(
                status=ContentArchitectStatus.APPROVED,
                approved=ContentArchitectApproval(content_hash="content-hash"),
            ),
            VisualDesignDirectorState(
                status=VisualDesignDirectorStatus.APPROVED,
                approved=VisualDesignDirectorApproval(visual_direction_hash="visual-hash"),
            ),
        )
        .source_ref
    )
    state = BuildPreparationState(
        status=BuildPreparationStatus.READY,
        source_ref=source_ref,
        package=PackageResult(
            archive_sha256=reference.sha256,
            archive_size_bytes=reference.size_bytes,
            file_count=1,
            expires_at=reference.expires_at,
            artifact=reference,
        ),
    )
    repository = _DownloadRepository(state)
    service = BuildPreparationService(
        repository,
        JobService(None),
        artifact_store=store,
    )
    return service, data


async def test_session_artifact_download_reads_verified_package_bytes() -> None:
    service, expected = await _download_service()

    data, content_type = await service.download_artifact(service._repository.session_id)

    assert data == expected
    assert content_type == "application/zip"
