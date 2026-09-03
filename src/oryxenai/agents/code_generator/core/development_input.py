"""Safe fixture/upload admission for standalone Code Generator development."""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from oryxenai.agents.code_generator.core.development_schemas import (
    AdmittedInputReference,
    InputReceipt,
)
from oryxenai.agents.code_generator.core.workspace import repository_root

# Build Preparation's Markdown-brief output (no more ZIP/JSON pack, no more
# execution/contract.json, resources/ledger.json, or the pack-v3/v4
# resolution-type taxonomy) still needs a real ingestion path here -- this is
# tracked as explicit follow-up work, not silently done. Until then, pack
# admission fails closed with one clear diagnostic rather than dereferencing
# a contract that no longer exists on the Build Preparation side.
PACK_VERSION = "build-preparation-pack-v3"


class DevelopmentInputError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_config_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (repository_root() / path).resolve()


def _safe_relative(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or bool(PureWindowsPath(value).drive)
        or ".." in path.parts
        or any(not part or any(ord(char) < 32 for char in part) for part in path.parts)
    ):
        raise DevelopmentInputError("ZIP_UNSAFE_PATH", "The ZIP contains an unsafe entry path.")
    reserved_names = {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
    if any(part.casefold().split(".", 1)[0] in reserved_names for part in path.parts):
        raise DevelopmentInputError(
            "ZIP_DEVICE_NAME", "The ZIP contains a reserved device-name path."
        )
    return str(path)


def _route_path(value: str) -> bool:
    return (
        bool(value)
        and value.startswith("/")
        and "\\" not in value
        and "//" not in value
        and ".." not in value.split("/")
        and not any(ord(char) < 32 for char in value)
    )


def _blocking_execution_gaps(execution: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only execution gaps that block Code Generator admission.

    Build Preparation keeps optional visual roles explicit as typed gaps so
    the generator can preserve the approved fallback without inventing a
    resource.  Required slots remain fail-closed; a gap with no matching slot
    is also treated as blocking because its provenance cannot be trusted.
    """

    slots = execution.get("slots")
    slot_by_id = (
        {
            str(slot.get("resource_slot_id", "")): slot
            for slot in slots
            if isinstance(slot, dict) and str(slot.get("resource_slot_id", ""))
        }
        if isinstance(slots, list)
        else {}
    )
    gaps = execution.get("execution_gaps", [])
    if not isinstance(gaps, list):
        return [{"slot_id": "", "reason": "malformed execution gaps"}]
    blocking: list[dict[str, Any]] = []
    for gap in gaps:
        if not isinstance(gap, dict):
            blocking.append({"slot_id": "", "reason": "malformed execution gap"})
            continue
        slot = slot_by_id.get(str(gap.get("slot_id", "")))
        if slot is None or bool(slot.get("required", True)):
            blocking.append(gap)
    return blocking


class DevelopmentInputAdapter:
    """Owns only configured fixture IDs and raw ZIP upload bytes."""

    def __init__(self, settings: Any) -> None:
        self._config = settings.code_generator_development
        self._root = _resolve_config_path(self._config.input_root)

    def fixtures(self) -> list[dict[str, str]]:
        return [
            {"fixture_id": fixture_id, "label": fixture_id}
            for fixture_id in sorted(self._config.fixture_map)
        ]

    def from_fixture(self, fixture_id: str) -> AdmittedInputReference:
        source = self._config.fixture_map.get(fixture_id)
        if not source:
            raise DevelopmentInputError(
                "FIXTURE_NOT_FOUND", "The requested development fixture is not configured."
            )
        fixture_root = _resolve_config_path(source)
        if not fixture_root.is_dir():
            raise DevelopmentInputError(
                "FIXTURE_UNAVAILABLE", "The configured development fixture is unavailable."
            )
        data = _zip_fixture_tree(fixture_root)
        return self._store_source(
            mode="fixture",
            source_id=fixture_id,
            filename=f"{fixture_id}.zip",
            data=data,
        )

    def from_upload(self, *, filename: str, mime_type: str, data: bytes) -> AdmittedInputReference:
        if mime_type.split(";", 1)[0].strip().lower() != "application/zip":
            raise DevelopmentInputError("UPLOAD_MIME_INVALID", "Uploads must use application/zip.")
        if not filename or Path(filename).name != filename or not filename.lower().endswith(".zip"):
            raise DevelopmentInputError(
                "UPLOAD_FILENAME_INVALID", "The upload filename must be a safe .zip name."
            )
        if len(data) > int(self._config.max_upload_bytes):
            raise DevelopmentInputError(
                "UPLOAD_TOO_LARGE", "The uploaded ZIP exceeds the configured size limit."
            )
        self._validate_zip(data)
        return self._store_source(
            mode="upload", source_id=_sha256(data), filename=filename, data=data
        )

    def from_build_preparation_artifact(
        self, *, source_id: str, filename: str, data: bytes
    ) -> AdmittedInputReference:
        """Store a verified object-store download in the common immutable input area."""

        if len(data) > int(self._config.max_uncompressed_bytes):
            raise DevelopmentInputError(
                "ARTIFACT_TOO_LARGE", "The Build Preparation artifact exceeds the configured limit."
            )
        return self._store_source(
            mode="build_preparation_artifact",
            source_id=source_id,
            filename=filename,
            data=data,
        )

    def list_build_preparation_packs(self) -> list[dict[str, Any]]:
        """Newest-first summary of local Build Preparation debug-mirror packs."""

        packs: list[dict[str, Any]] = []
        for entry in self._mirror_entries():
            info = self._mirror_pack_info(entry)
            if info is not None:
                packs.append(info)
        packs.sort(key=lambda item: (item["modified_at"], item["pack_dir"]), reverse=True)
        return packs

    def from_build_preparation_mirror(self, pack: str = "latest") -> AdmittedInputReference:
        """Store an immutable copy of a local Build Preparation mirror pack.

        Selection is advisory only (name, expiry, handoff flag read from the
        mirror's extracted manifest); full admission re-verifies every hash and
        projection when the planning job runs.
        """

        entries = self._mirror_entries()
        if not entries:
            raise DevelopmentInputError(
                "PACK_MIRROR_UNAVAILABLE",
                "The Build Preparation mirror has no packs. Run Build Preparation first.",
            )
        if pack in {"latest", "best"}:
            candidates = sorted(
                entries, key=lambda entry: (entry.stat().st_mtime_ns, entry.name), reverse=True
            )
            infos = [(entry, self._mirror_pack_info(entry)) for entry in candidates]
            if pack == "best":
                selected = max(
                    (entry for entry, info in infos if info["eligible"]),
                    key=lambda entry: self._pack_rank(
                        next(info for item, info in infos if item == entry)
                    ),
                    default=None,
                )
            else:
                selected = next((entry for entry, info in infos if info["eligible"]), None)
            if selected is None:
                reason = infos[0][1].get("issue", "unknown") if infos else "unknown"
                raise DevelopmentInputError(
                    "PACK_MIRROR_NO_ELIGIBLE",
                    f"No eligible pack in the mirror (newest issue: {reason}).",
                )
        else:
            if Path(pack).name != pack:
                raise DevelopmentInputError(
                    "PACK_DIR_INVALID", "The pack directory name is not a safe directory name."
                )
            selected = next((entry for entry in entries if entry.name == pack), None)
            if selected is None:
                raise DevelopmentInputError(
                    "PACK_DIR_NOT_FOUND", "The requested pack directory is not in the mirror."
                )
        info = self._mirror_pack_info(selected)
        if not info["eligible"]:
            raise DevelopmentInputError(
                "PACK_NOT_ADMISSIBLE",
                f"The selected pack is not admissible ({info.get('issue', 'unknown')}).",
            )
        data = (selected / "build-pack.zip").read_bytes()
        if len(data) > int(self._config.max_uncompressed_bytes):
            raise DevelopmentInputError(
                "UPLOAD_TOO_LARGE", "The mirror pack exceeds the configured size limit."
            )
        return self._store_source(
            mode="build_preparation_mirror",
            source_id=selected.name,
            filename=f"{selected.name}-build-pack.zip",
            data=data,
        )

    def _mirror_entries(self) -> list[Path]:
        root = _resolve_config_path(self._config.build_preparation_mirror_root)
        if not root.is_dir():
            return []
        return sorted(
            (
                entry
                for entry in root.iterdir()
                if entry.is_dir() and (entry / "build-pack.zip").is_file()
            ),
            key=lambda entry: entry.name,
        )

    def _mirror_pack_info(self, entry: Path) -> dict[str, Any]:
        """Eligibility summary for one mirror entry; ``eligible`` is False with
        an ``issue`` reason when the pack cannot be selected."""

        zip_path = entry / "build-pack.zip"
        stat = zip_path.stat()
        manifest: dict[str, Any] = {}
        handoff: dict[str, Any] = {}
        issue = ""
        execution_gaps = 1
        provenance_complete = 0
        resource_coverage = 0
        visual_readiness = 0
        context_dir = entry / "build-context"
        manifest_path = context_dir / "manifest.json"
        handoff_path = context_dir / "handoff-report.json"
        try:
            if manifest_path.is_file():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            else:
                with zipfile.ZipFile(zip_path) as archive:
                    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            if handoff_path.is_file():
                handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
            else:
                with zipfile.ZipFile(zip_path) as archive:
                    handoff = json.loads(archive.read("handoff-report.json").decode("utf-8"))
            with zipfile.ZipFile(zip_path) as archive:
                execution = json.loads(archive.read("execution/contract.json").decode("utf-8"))
                resources = json.loads(archive.read("resources/projection.json").decode("utf-8"))
                visual = json.loads(archive.read("design/visual-direction.json").decode("utf-8"))
                execution_gaps = (
                    len(execution.get("execution_gaps", [])) if isinstance(execution, dict) else 1
                )
                resource_coverage = (
                    len(resources.get("resources", [])) if isinstance(resources, dict) else 0
                )
                provenance_complete = int(
                    all(
                        path in archive.namelist()
                        for path in (
                            "provenance/approvals.json",
                            "provenance/licenses.json",
                            "provenance/targets.json",
                        )
                    )
                )
                visual_readiness = len(visual.get("routes", [])) if isinstance(visual, dict) else 0
        except (OSError, ValueError, UnicodeDecodeError, zipfile.BadZipFile, KeyError) as exc:
            manifest, handoff = {}, {}
            issue = f"unreadable pack: {type(exc).__name__}"
        pack_version = str(manifest.get("pack_version", ""))
        accepted_pack_versions = set(
            getattr(self._config, "accepted_pack_versions", [self._config.pack_version])
        )
        accepted_schema_versions = set(
            getattr(self._config, "accepted_schema_versions", [self._config.schema_version])
        )
        expires_at = str(manifest.get("expires_at", ""))
        expired = False
        if not issue:
            if pack_version not in accepted_pack_versions:
                issue = f"pack version {pack_version or 'unknown'} is not admissible"
            else:
                try:
                    expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    expired = expiry.tzinfo is None or expiry.astimezone(UTC) <= datetime.now(UTC)
                except ValueError:
                    expired, issue = True, "pack has no valid expiry marker"
                if expired and not issue:
                    issue = f"pack expired at {expires_at}"
                elif not issue and not bool(handoff.get("handoff_eligible", False)):
                    issue = "handoff report is not eligible"
                elif not issue:
                    manifest_schema = str(manifest.get("schema_version", ""))
                    if (
                        manifest_schema
                        and manifest_schema not in accepted_schema_versions
                        and not manifest_schema.startswith("build-preparation-handoff-")
                    ):
                        issue = "pack schema version is not admissible"
        if not issue:
            try:
                self._validate_admitted_data(zip_path.read_bytes())
            except (DevelopmentInputError, OSError) as exc:
                issue = (
                    f"{exc.code}: {exc.message}"
                    if isinstance(exc, DevelopmentInputError)
                    else f"unreadable pack: {type(exc).__name__}"
                )
        info: dict[str, Any] = {
            "pack_dir": entry.name,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
            "pack_version": pack_version,
            "schema_version": str(manifest.get("schema_version", "")),
            "expires_at": expires_at,
            "handoff_eligible": bool(handoff.get("handoff_eligible", False)),
            "execution_gaps": execution_gaps,
            "provenance_complete": provenance_complete,
            "resource_coverage": resource_coverage,
            "visual_readiness": visual_readiness,
            "expired": expired,
            "eligible": not issue,
        }
        if issue:
            info["issue"] = issue
        info["selection_rank"] = self._pack_rank(info)
        return info

    @staticmethod
    def _pack_rank(info: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
        """Lexicographic quality ranking; modified time is only the final tie-break."""

        return (
            int(bool(info.get("handoff_eligible"))),
            int(not bool(info.get("expired"))),
            int(info.get("execution_gaps", 1) == 0),
            int(info.get("provenance_complete", 0)),
            int(info.get("resource_coverage", 0)),
            int(info.get("visual_readiness", 0)),
        )

    def read(self, reference: AdmittedInputReference) -> bytes:
        candidate = (self._root / reference.stored_relative_path).resolve()
        if not candidate.is_relative_to(self._root) or not candidate.is_file():
            raise DevelopmentInputError(
                "INPUT_COPY_MISSING",
                "The immutable input copy is unavailable.",
                details={
                    "input_root": str(self._root),
                    "stored_relative_path": reference.stored_relative_path,
                    "resolved_candidate": str(candidate),
                },
            )
        data = candidate.read_bytes()
        if _sha256(data) != reference.source_sha256:
            raise DevelopmentInputError(
                "INPUT_COPY_HASH_MISMATCH",
                "The immutable input copy failed read-back verification.",
            )
        return data

    def admit(self, reference: AdmittedInputReference) -> tuple[InputReceipt, dict[str, Any]]:
        raise DevelopmentInputError(
            "PACK_INGESTION_NOT_MIGRATED",
            "Build Preparation now hands off two Markdown briefs instead of a "
            "versioned JSON/ZIP pack. Code Generator ingestion of that new "
            "contract is tracked as explicit follow-up work and is not yet "
            "implemented.",
        )

    def _validate_admitted_data(self, data: bytes) -> tuple[InputReceipt, dict[str, Any], str]:
        """Kept only as _mirror_pack_info's eligibility probe for legacy ZIP mirrors.

        Always fails closed: Build Preparation no longer produces this pack
        shape, so a legacy build-pack.zip in the local mirror is correctly
        reported as ineligible rather than admitted.
        """
        raise DevelopmentInputError(
            "PACK_INGESTION_NOT_MIGRATED",
            "Build Preparation now hands off two Markdown briefs instead of a "
            "versioned JSON/ZIP pack.",
        )

    def _store_source(
        self, *, mode: str, source_id: str, filename: str, data: bytes
    ) -> AdmittedInputReference:
        self._validate_zip(data)
        digest = _sha256(data)
        relative = Path("inputs") / digest[:2] / f"{digest}.zip"
        target = (self._root / relative).resolve()
        if not target.is_relative_to(self._root):
            raise DevelopmentInputError(
                "INPUT_ROOT_UNSAFE", "The configured development input root is unsafe."
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            temp = target.with_suffix(".partial")
            temp.write_bytes(data)
            os.replace(temp, target)
        copied = target.read_bytes()
        if copied != data:
            raise DevelopmentInputError(
                "INPUT_COPY_READBACK_FAILED", "The uploaded input copy could not be verified."
            )
        return AdmittedInputReference(
            mode=mode,  # type: ignore[arg-type]
            source_id=source_id,
            original_filename=filename,
            source_sha256=digest,
            stored_relative_path=relative.as_posix(),
            size_bytes=len(data),
        )

    def _validate_zip(self, data: bytes) -> None:
        if not data.startswith(b"PK"):
            raise DevelopmentInputError("ZIP_INVALID", "The input is not a ZIP archive.")
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = archive.infolist()
                if len(entries) > int(self._config.max_entries):
                    raise DevelopmentInputError("ZIP_ENTRY_LIMIT", "The ZIP has too many entries.")
                seen: set[str] = set()
                total = 0
                for entry in entries:
                    path = _safe_relative(entry.filename)
                    key = path.casefold()
                    if key in seen:
                        raise DevelopmentInputError(
                            "ZIP_CASE_COLLISION",
                            "The ZIP contains duplicate or case-colliding paths.",
                        )
                    seen.add(key)
                    if entry.is_dir():
                        continue
                    if stat.S_ISLNK(entry.external_attr >> 16):
                        raise DevelopmentInputError(
                            "ZIP_SYMLINK", "ZIP symbolic links are not allowed."
                        )
                    total += entry.file_size
                    if total > int(self._config.max_uncompressed_bytes):
                        raise DevelopmentInputError(
                            "ZIP_UNCOMPRESSED_LIMIT", "The ZIP expands beyond the configured limit."
                        )
                    if entry.compress_size and entry.file_size / entry.compress_size > float(
                        self._config.max_compression_ratio
                    ):
                        raise DevelopmentInputError(
                            "ZIP_COMPRESSION_RATIO",
                            "A ZIP entry exceeds the compression-ratio limit.",
                        )
                    if entry.file_size and not entry.compress_size:
                        raise DevelopmentInputError(
                            "ZIP_COMPRESSION_RATIO",
                            "A ZIP entry has an invalid compressed size.",
                        )
        except zipfile.BadZipFile as exc:
            raise DevelopmentInputError(
                "ZIP_INVALID", "The input is not a readable ZIP archive."
            ) from exc


def _json_object(data: bytes, path: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DevelopmentInputError(
            "PACK_PROJECTION_INVALID", "A required pack projection is invalid JSON."
        ) from exc
    if not isinstance(value, dict):
        raise DevelopmentInputError(
            "PACK_PROJECTION_INVALID", "A required pack projection is not a JSON object."
        )
    return value


def _zip_fixture_tree(root: Path) -> bytes:
    entries: list[tuple[str, bytes]] = []
    for path in sorted(root.rglob("*")):
        if (
            not path.is_file()
            or path.is_symlink()
            or path.relative_to(root).as_posix() == "manifest.json"
        ):
            continue
        entries.append((path.relative_to(root).as_posix(), path.read_bytes()))
    checksums = {path: _sha256(data) for path, data in entries}
    entries.append(
        (
            "provenance/checksums.json",
            json.dumps({"algorithm": "sha256", "files": checksums}, sort_keys=True).encode("utf-8"),
        )
    )
    manifest = {
        "pack_version": PACK_VERSION,
        "run_id": "privacy-safe-v2-fixture",
        "scope_hash": "fixture",
        "source_ref": {
            "content_architect_content_hash": "fixture-content-hash",
            "visual_design_director_direction_hash": "fixture-visual-hash",
            "input_projection_hash": "fixture-projection-hash",
        },
        "expires_at": "2099-01-01T00:00:00+00:00",
        "files": [
            {"path": path, "size_bytes": len(data), "sha256": _sha256(data)}
            for path, data in sorted(entries)
        ],
    }
    entries.append(("manifest.json", json.dumps(manifest, sort_keys=True).encode("utf-8")))
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output.getvalue()
