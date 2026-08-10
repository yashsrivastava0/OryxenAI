"""Development-only Build Preparation fixture runner.

This module intentionally does not touch portfolio sessions or AgentRuns.  It
adapts the checked-in Visual Design output into the same deterministic
Blueprint/resource/context/bundle pipeline so that the pre-code stage can be
debugged independently from the upstream agents.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from oryxenai.agents.content_architect.schemas import ContentArchitectState
from oryxenai.agents.visual_design_director.schemas import VisualDesignDirectorState
from oryxenai.build_preparation.bundle import create_bundle
from oryxenai.build_preparation.compiler import compile_blueprint, compile_context
from oryxenai.build_preparation.fingerprints import projection_hash
from oryxenai.build_preparation.resources import catalogue_hash, resolve_local_requirements
from oryxenai.build_preparation.schemas import ArtifactObjectRef, ResourceManifest, SourceRef
from oryxenai.build_preparation.service import load_target_contract, target_contract_hash
from oryxenai.build_preparation.storage import (
    ArtifactStore,
    ArtifactStoreError,
    StoredArtifact,
    build_r2_store,
    memory_artifact_store,
)
from oryxenai.core.settings import Settings

_REPO_ROOT = Path(__file__).resolve().parents[3]
_RUNTIME_FIELDS = {"elapsed_seconds"}


class FixturePreparationError(ValueError):
    """Safe error raised by the development-only fixture path."""

    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def fixture_path(settings: Settings) -> Path:
    configured = Path(settings.build_preparation.fixture_input_path)
    candidate = configured if configured.is_absolute() else _REPO_ROOT / configured
    resolved = candidate.resolve()
    try:
        resolved.relative_to(_REPO_ROOT)
    except ValueError as exc:
        raise FixturePreparationError(
            "FIXTURE_PATH_INVALID", "The configured fixture path must remain inside the repository."
        ) from exc
    if not resolved.is_file():
        raise FixturePreparationError(
            "FIXTURE_INPUT_MISSING",
            "The configured Visual Design fixture file was not found.",
            details={"path": str(configured)},
        )
    return resolved


def load_fixture(
    settings: Settings,
    *,
    raw_override: dict[str, Any] | None = None,
) -> tuple[VisualDesignDirectorState, dict[str, Any], str, Path | None]:
    path: Path | None = None
    if raw_override is None:
        path = fixture_path(settings)
        raw_bytes = path.read_bytes()
    else:
        raw_bytes = json.dumps(
            raw_override,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    try:
        raw_value = (
            raw_override if raw_override is not None else json.loads(raw_bytes.decode("utf-8"))
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FixturePreparationError(
            "FIXTURE_INPUT_INVALID", "The Visual Design fixture is not valid UTF-8 JSON."
        ) from exc
    if not isinstance(raw_value, dict):
        raise FixturePreparationError(
            "FIXTURE_INPUT_INVALID", "The Visual Design fixture must contain a JSON object."
        )
    payload = dict(cast(dict[str, Any], raw_value))
    for key in _RUNTIME_FIELDS:
        payload.pop(key, None)
    try:
        visual = VisualDesignDirectorState.model_validate(payload)
    except Exception as exc:
        raise FixturePreparationError(
            "FIXTURE_SCHEMA_INVALID", "The Visual Design fixture does not match its state contract."
        ) from exc
    return visual, payload, hashlib.sha256(raw_bytes).hexdigest(), path


def _derived_profile(intake: dict[str, Any]) -> dict[str, Any]:
    manifest = intake.get("public_content_manifest")
    title = str(manifest.get("site_title", "") if isinstance(manifest, dict) else "")
    name = re.split(r"\s+[\u2014\u2013-]\s+", title, maxsplit=1)[0].strip()
    links = []
    if isinstance(manifest, dict):
        for href in manifest.get("external_links", []):
            if isinstance(href, str) and href.startswith(("http://", "https://", "mailto:")):
                links.append({"label": href.split("//", 1)[-1].split("/", 1)[0], "url": href})
    return {"name": name, "links": links} if name or links else {}


def build_fixture_content(visual: VisualDesignDirectorState) -> ContentArchitectState:
    """Create an explicitly unapproved content state from VDD's compact intake."""
    intake = visual.intake.model_dump(mode="json")
    return ContentArchitectState.model_validate(
        {
            "status": "content_review",
            "model_profile": "fixture",
            "site_story_strategy": intake.get("site_story_strategy", {}),
            "route_plan": intake.get("route_plan", []),
            "page_content_packs": intake.get("page_content_packs", []),
            "public_content_manifest": intake.get("public_content_manifest", {}),
            "claim_grounding": [],
            "privacy_and_confidentiality": intake.get("privacy_and_confidentiality", []),
            "media_status": intake.get("media_status", {}),
            "visual_director_handoff": intake.get("visual_director_handoff", {}),
            "intake": {"profile": _derived_profile(intake)},
            "warnings": [
                "Fixture content was derived from Visual Design intake; it is not an approved Content Architect snapshot."
            ],
        }
    )


def _fixture_source(
    visual: VisualDesignDirectorState,
    content: ContentArchitectState,
    raw_payload: dict[str, Any],
    fixture_hash: str,
) -> SourceRef:
    source_ref = visual.source_ref
    content_projection = projection_hash(content.model_dump(mode="json"))
    visual_projection = projection_hash(raw_payload)
    return SourceRef(
        content_hash=source_ref.content_architect_content_hash,
        visual_direction_hash="",
        route_publication_hash=source_ref.route_publication_hash,
        content_projection_hash=content_projection,
        visual_projection_hash=visual_projection,
        content_session_revision=source_ref.content_architect_session_revision,
        visual_session_revision=source_ref.content_architect_session_revision,
        # Keep fixture bundles reproducible across repeat runs. The VDD
        # snapshot timestamp is source provenance; using `now()` here would
        # make the ZIP bytes and object key change for identical input.
        captured_at=source_ref.snapshotted_at,
        discovery_brief_hash=f"fixture:{fixture_hash}",
    )


def _artifact_ref(settings: Settings, stored: StoredArtifact) -> ArtifactObjectRef:
    return ArtifactObjectRef(
        storage_profile=settings.artifact_storage.provider,
        bucket=settings.artifact_storage.bucket,
        object_key=stored.object_key,
        etag=stored.etag,
        sha256=stored.sha256,
        size_bytes=stored.size_bytes,
        content_type=stored.content_type,
        created_at=datetime.now(UTC).isoformat(),
        expires_at=stored.expires_at.isoformat(),
        last_verified_at=datetime.now(UTC).isoformat(),
    )


def _fixture_store(settings: Settings) -> tuple[ArtifactStore, str]:
    if not settings.build_preparation.fixture_upload:
        return (
            memory_artifact_store(),
            "fixture upload disabled; bundle kept in the development memory store",
        )
    try:
        return (
            build_r2_store(
                settings.artifact_storage,
                ttl_days=settings.build_preparation.bundle_ttl_days,
            ),
            "",
        )
    except ArtifactStoreError as exc:
        return memory_artifact_store(), f"R2 fixture upload unavailable; using memory store ({exc})"


async def run_fixture(
    settings: Settings,
    *,
    artifact_store: ArtifactStore | None = None,
    raw_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not settings.build_preparation.fixture_enabled:
        raise FixturePreparationError(
            "FIXTURE_DISABLED", "The temporary Build Preparation fixture is disabled."
        )
    visual, raw_payload, fixture_hash, path = load_fixture(settings, raw_override=raw_override)
    content = build_fixture_content(visual)
    target = load_target_contract()
    target_hash = target_contract_hash()
    source = _fixture_source(visual, content, raw_payload, fixture_hash)
    preparation_hash = projection_hash(
        {
            "fixture_hash": fixture_hash,
            "target_contract_hash": target_hash,
            "catalogue_hash": catalogue_hash(),
        }
    )
    blueprint, packets, compiler_warnings = compile_blueprint(
        content,
        visual,
        source=source,
        preparation_hash=preparation_hash,
        max_routes=settings.build_preparation.max_routes,
        target_contract_hash=target_hash,
        fixture_mode=True,
    )
    manifest: ResourceManifest = resolve_local_requirements(blueprint.resource_requirements)
    manifest.warnings = sorted(
        {*manifest.warnings, "fixture mode does not contact remote registries or Pexels"}
    )
    manifest.policy_hash = projection_hash(
        settings.build_preparation.model_dump(mode="json"),
        settings.resource_providers.model_dump(mode="json"),
    )
    manifest.manifest_hash = projection_hash(
        manifest.model_dump(mode="json", exclude={"manifest_hash"})
    )
    context = compile_context(
        blueprint,
        packets,
        manifest,
        target_contract=target,
    )

    storage_warning = ""
    bundle_ref: ArtifactObjectRef | None = None
    bundle_sha = ""
    bundle_size = 0
    workspace_root: Path | None = None
    try:
        candidate = _REPO_ROOT / "scratch"
        candidate.mkdir(parents=True, exist_ok=True)
        workspace_root = candidate
    except OSError:
        # Docker runs as a non-root user and the application image is
        # intentionally not writable. In that environment create_bundle's
        # own ephemeral /tmp directory is the correct workspace.
        workspace_root = None
    try:
        bundle, bundle_sha, bundle_size = create_bundle(
            blueprint,
            manifest,
            context,
            packets,
            target_contract=target,
            max_bundle_bytes=settings.build_preparation.max_bundle_bytes,
            workspace_dir=workspace_root,
        )
        store = artifact_store
        if store is None:
            store, storage_warning = _fixture_store(settings)
        if store is not None:
            expires_at = datetime.now(UTC) + timedelta(
                days=settings.build_preparation.bundle_ttl_days
            )
            object_key = (
                f"{settings.artifact_storage.prefix.rstrip('/')}/fixture/"
                f"{fixture_hash}/bundle-{bundle_sha}.zip"
            )
            stored = await store.head(object_key)
            if stored is None:
                stored = await store.put(
                    object_key,
                    bundle,
                    expires_at=expires_at,
                    metadata={
                        "fixture-hash": fixture_hash,
                        "schema-version": "1",
                        "publishable": "false",
                    },
                )
            bundle_ref = _artifact_ref(settings, stored)
    except ArtifactStoreError as exc:
        storage_warning = f"Temporary bundle storage failed; compilation still succeeded ({exc})"
    finally:
        # The fixture workspace is disposable and never used by the production
        # worker. Remove the generated bundle directory after upload.
        if "bundle" in locals():
            shutil.rmtree(bundle.parent, ignore_errors=True)

    warnings = sorted(
        set(compiler_warnings + manifest.warnings + ([storage_warning] if storage_warning else []))
    )
    return {
        "status": "succeeded",
        "fixture": True,
        "publishable": False,
        "input": {
            "path": str(path) if path is not None else "browser-provided JSON",
            "sha256": fixture_hash,
            "visual_status": visual.status.value,
            "visual_approval_present": visual.approved is not None,
            "route_count": len(visual.pages),
        },
        "blueprint": blueprint.model_dump(mode="json"),
        "manifest": manifest.model_dump(mode="json"),
        "context": context.model_dump(mode="json"),
        "page_packets": [packet.model_dump(mode="json") for packet in packets],
        "bundle": bundle_ref.model_dump(mode="json") if bundle_ref else None,
        "bundle_sha256": bundle_sha,
        "bundle_size": bundle_size,
        "warnings": warnings,
    }
