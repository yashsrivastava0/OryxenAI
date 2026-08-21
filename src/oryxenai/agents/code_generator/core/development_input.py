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

from oryxenai.agents.build_preparation.contracts import (
    DELEGATED_PACK_VERSION,
    DELEGATED_SCHEMA_VERSION,
    PACK_VERSION,
    PackContractError,
    canonical_json,
    validate_execution_contract_shape,
    validate_route_section_contract,
)
from oryxenai.agents.build_preparation.packager import (
    PackageError,
    restore_verified_bundle,
    verify_bundle_bytes,
)
from oryxenai.agents.code_generator.core.development_schemas import (
    AdmittedInputReference,
    InputReceipt,
)
from oryxenai.agents.code_generator.core.workspace import repository_root


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
        data = self.read(reference)
        receipt, projections, identity = self._validate_admitted_data(data)
        self._extract_verified(data, identity)
        return receipt, projections

    def _validate_admitted_data(self, data: bytes) -> tuple[InputReceipt, dict[str, Any], str]:
        """Validate a pack without writing an extracted copy to the workspace."""

        self._validate_zip(data)
        try:
            manifest = verify_bundle_bytes(data, max_bytes=int(self._config.max_uncompressed_bytes))
        except PackageError as exc:
            raise DevelopmentInputError(exc.code, exc.message) from exc
        accepted_versions = set(
            getattr(
                self._config,
                "accepted_pack_versions",
                [self._config.pack_version, DELEGATED_PACK_VERSION],
            )
        )
        if manifest.get("pack_version") not in accepted_versions:
            raise DevelopmentInputError(
                "PACK_VERSION_UNSUPPORTED", "Only Build Preparation pack v3 or v4 is admissible."
            )
        expires_at = manifest.get("expires_at")
        try:
            expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        except ValueError as exc:
            raise DevelopmentInputError(
                "PACK_EXPIRY_INVALID", "The pack has no valid expiry marker."
            ) from exc
        if expiry.tzinfo is None or expiry.astimezone(UTC) <= datetime.now(UTC):
            raise DevelopmentInputError(
                "PACK_EXPIRED", "The pack is stale and must be regenerated before planning."
            )
        required_paths = {
            "site/contract.json",
            "design/visual-direction.json",
            "provenance/approvals.json",
            "provenance/targets.json",
            "resources/projection.json",
            "resources/ledger.json",
            "resources/recipes/manifest.json",
            "execution/contract.json",
            "handoff-report.json",
        }
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
            missing = required_paths - names
            if missing:
                raise DevelopmentInputError(
                    "PACK_PROJECTION_MISSING", "The v3 pack is missing required projections."
                )
            projections = {path: _json_object(archive.read(path), path) for path in required_paths}
            route_resource_maps = {
                str(route.get("route_id", "")): _json_object(
                    archive.read(str((route.get("files") or {}).get("resources", ""))),
                    str((route.get("files") or {}).get("resources", "")),
                )
                for route in projections["site/contract.json"].get("routes", [])
                if isinstance(route, dict)
            }
        self._validate_projections(
            projections, package_paths=names, route_resource_maps=route_resource_maps
        )
        files = manifest.get("files")
        if not isinstance(files, list):
            raise DevelopmentInputError(
                "PACK_MANIFEST_INVALID", "The pack manifest file index is invalid."
            )
        projection_hashes = {
            path: _sha256(canonical_json(value)) for path, value in projections.items()
        }
        declared_hashes = projections["handoff-report.json"].get("projection_hashes")
        report_hashes = {
            "site": projection_hashes["site/contract.json"],
            "visual": projection_hashes["design/visual-direction.json"],
            "approvals": projection_hashes["provenance/approvals.json"],
            "targets": projection_hashes["provenance/targets.json"],
            "resources": projection_hashes["resources/projection.json"],
            "ledger": projection_hashes["resources/ledger.json"],
            "execution": projection_hashes["execution/contract.json"],
            "recipes": projection_hashes["resources/recipes/manifest.json"],
        }
        if declared_hashes != report_hashes:
            raise DevelopmentInputError(
                "PACK_PROJECTION_HASH_MISMATCH",
                "The handoff report does not match the admitted v3 projections.",
            )
        identity = _sha256(canonical_json({"manifest": files, "projections": projection_hashes}))
        site = projections["site/contract.json"]
        route_ids = [str(route["route_id"]) for route in site["routes"]]
        receipt = InputReceipt(
            receipt_id=f"input-{identity[:20]}",
            admitted_identity=identity,
            pack_sha256=_sha256(data),
            manifest_hash=_sha256(canonical_json(files)),
            projection_hashes=projection_hashes,
            route_ids=route_ids,
            target_id=str(projections["provenance/targets.json"]["target"].get("target_id", "")),
            pack_version=str(manifest["pack_version"]),
            schema_version=str(site.get("schema_version", "")),
        )
        return receipt, projections, identity

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

    def _validate_projections(
        self,
        projections: dict[str, dict[str, Any]],
        *,
        package_paths: set[str],
        route_resource_maps: dict[str, dict[str, Any]],
    ) -> None:
        site = projections["site/contract.json"]
        visual = projections["design/visual-direction.json"]
        approvals = projections["provenance/approvals.json"]
        targets = projections["provenance/targets.json"]
        handoff = projections["handoff-report.json"]
        execution = projections["execution/contract.json"]
        ledger = projections["resources/ledger.json"]
        recipe_manifest = projections["resources/recipes/manifest.json"]
        accepted_versions = set(
            getattr(
                self._config,
                "accepted_pack_versions",
                [self._config.pack_version, DELEGATED_PACK_VERSION],
            )
        )
        accepted_schema_versions = set(
            getattr(
                self._config,
                "accepted_schema_versions",
                [self._config.schema_version, DELEGATED_SCHEMA_VERSION],
            )
        )
        if site.get("schema_version") not in accepted_schema_versions:
            raise DevelopmentInputError(
                "PACK_SCHEMA_UNSUPPORTED", "The site contract schema is unsupported."
            )
        if any(
            projection.get("pack_version") not in accepted_versions
            for projection in (site, visual, execution, ledger, recipe_manifest)
        ):
            raise DevelopmentInputError(
                "PACK_VERSION_UNSUPPORTED",
                "The pack projections are not an accepted contract version.",
            )
        if (
            not approvals.get("approved")
            or not handoff.get("handoff_eligible")
            or approvals.get("stale") is True
            or handoff.get("stale") is True
        ):
            raise DevelopmentInputError(
                "PACK_APPROVALS_INVALID", "The pack has not passed approved handoff eligibility."
            )
        target = targets.get("target")
        if not isinstance(target, dict) or target.get("target_id") != self._config.target_contract:
            raise DevelopmentInputError(
                "PACK_TARGET_UNSUPPORTED", "The pack target contract is unsupported."
            )
        if targets.get("schema_version") not in accepted_schema_versions:
            raise DevelopmentInputError(
                "PACK_TARGET_SCHEMA_UNSUPPORTED", "The target projection schema is unsupported."
            )
        routes = site.get("routes")
        visual_routes = visual.get("routes")
        public_content = site.get("public_content")
        if (
            not isinstance(routes, list)
            or not isinstance(visual_routes, list)
            or not isinstance(public_content, list)
        ):
            raise DevelopmentInputError(
                "PACK_ROUTE_CONTRACT_INVALID", "The pack route projections are invalid."
            )
        route_ids = [str(item.get("route_id", "")) for item in routes if isinstance(item, dict)]
        visual_ids = [
            str(item.get("route_id", "")) for item in visual_routes if isinstance(item, dict)
        ]
        content_ids = [
            str(item.get("route_id", "")) for item in public_content if isinstance(item, dict)
        ]
        if not route_ids or len(route_ids) > int(self._config.max_routes):
            raise DevelopmentInputError(
                "PACK_ROUTE_CONTRACT_INVALID",
                "The pack route scope is invalid or exceeds its ceiling.",
            )
        if (
            len(set(route_ids)) != len(route_ids)
            or set(route_ids) != set(visual_ids)
            or set(route_ids) != set(content_ids)
        ):
            raise DevelopmentInputError(
                "PACK_ROUTE_CONTRACT_MISMATCH",
                "Route, content, and visual projections must match exactly.",
            )
        if len({route_id.casefold() for route_id in route_ids}) != len(route_ids):
            raise DevelopmentInputError(
                "PACK_ROUTE_CONTRACT_MISMATCH", "The pack contains case-colliding route IDs."
            )
        try:
            validate_route_section_contract(site)
        except PackContractError as exc:
            raise DevelopmentInputError(
                "PACK_CONTENT_INVALID",
                "The pack route/content contract is not executable.",
                details={
                    "contract_code": exc.code,
                    **{str(k): str(v) for k, v in exc.details.items()},
                },
            ) from exc
        route_paths: set[str] = set()
        content_by_route = {
            str(item.get("route_id", "")): item for item in public_content if isinstance(item, dict)
        }
        visual_by_route = {
            str(item.get("route_id", "")): item for item in visual_routes if isinstance(item, dict)
        }
        for route in routes:
            if not isinstance(route, dict):
                raise DevelopmentInputError(
                    "PACK_ROUTE_CONTRACT_INVALID", "A route contract entry is invalid."
                )
            route_id = str(route.get("route_id", ""))
            path = str(route.get("path", ""))
            if not _route_path(path) or path.casefold() in route_paths:
                raise DevelopmentInputError(
                    "PACK_ROUTE_CONTRACT_INVALID",
                    "The pack contains invalid or colliding route paths.",
                )
            route_paths.add(path.casefold())
            if str(visual_by_route[route_id].get("path", "")) != path:
                raise DevelopmentInputError(
                    "PACK_ROUTE_CONTRACT_MISMATCH",
                    "Visual route paths must match the site contract.",
                )
            file_references = route.get("files")
            if not isinstance(file_references, dict) or any(
                str(file_references.get(key, "")) not in package_paths
                for key in ("content", "resources", "brief")
            ):
                raise DevelopmentInputError(
                    "PACK_FILE_REFERENCE_INVALID",
                    "A route contract references an unavailable package file.",
                )
            route_sections = route.get("section_sequence")
            content_sections = content_by_route[route_id].get("sections")
            if not isinstance(route_sections, list) or not isinstance(content_sections, list):
                raise DevelopmentInputError(
                    "PACK_CONTENT_INVALID", "Route section references are invalid."
                )
            content_ids = [
                str(section.get("section_id", ""))
                for section in content_sections
                if isinstance(section, dict)
            ]
            if set(route_sections) != set(content_ids) or len(content_ids) != len(set(content_ids)):
                raise DevelopmentInputError(
                    "PACK_CONTENT_INVALID", "Route sections must cover the public content exactly."
                )
        fact_ids = {
            str(item.get("fact_id", ""))
            for item in site.get("facts", [])
            if isinstance(item, dict) and str(item.get("fact_id", ""))
        }
        criteria = site.get("criteria", [])
        if not isinstance(criteria, list) or any(
            not isinstance(item, dict) or str(item.get("route_id", "")) not in set(route_ids)
            for item in criteria
        ):
            raise DevelopmentInputError(
                "PACK_CRITERION_INVALID", "The pack contains an invalid route criterion."
            )
        for content_pack in content_by_route.values():
            for section in content_pack.get("sections", []):
                if not isinstance(section, dict) or not set(section.get("claim_ids", [])).issubset(
                    fact_ids
                ):
                    raise DevelopmentInputError(
                        "PACK_FACT_REFERENCE_INVALID",
                        "Public content references an unknown authoritative fact.",
                    )
        resources = projections["resources/projection.json"].get("resources", [])
        if not isinstance(resources, list) or any(
            not isinstance(resource, dict)
            or (resource.get("provider") and not str(resource.get("license", "")).strip())
            for resource in resources
        ):
            raise DevelopmentInputError(
                "PACK_LICENSE_INVALID", "A materialized resource has no usable license record."
            )
        if any(
            resource.get("kind") in {"photo", "component"}
            and (
                resource.get("provider") == "generated-local"
                or (resource.get("kind") == "photo" and resource.get("disposition") != "local_file")
                or (
                    resource.get("kind") == "component"
                    and resource.get("disposition") != "adaptable_source"
                )
            )
            for resource in resources
        ):
            raise DevelopmentInputError(
                "PACK_RESOURCE_NOT_REAL",
                "A visual resource is not a real locally materialized provider resource.",
            )
        self._validate_execution_contract(
            execution=execution,
            ledger=ledger,
            recipe_manifest=recipe_manifest,
            site=site,
            targets=targets,
            package_paths=package_paths,
            route_resource_maps=route_resource_maps,
        )

    def _validate_execution_contract(
        self,
        *,
        execution: dict[str, Any],
        ledger: dict[str, Any],
        recipe_manifest: dict[str, Any],
        site: dict[str, Any],
        targets: dict[str, Any],
        package_paths: set[str],
        route_resource_maps: dict[str, dict[str, Any]],
    ) -> None:
        accepted_schema_versions = set(
            getattr(
                self._config,
                "accepted_schema_versions",
                [self._config.schema_version, DELEGATED_SCHEMA_VERSION],
            )
        )
        try:
            validate_execution_contract_shape(
                execution=execution,
                ledger=ledger,
                recipe_manifest=recipe_manifest,
                site=site,
                package_paths=package_paths,
                allowed_dependencies=set(
                    (targets.get("target") or {}).get("allowed_dependencies", [])
                    if isinstance(targets.get("target"), dict)
                    else []
                ),
            )
        except PackContractError as exc:
            raise DevelopmentInputError(
                "PACK_EXECUTION_CONTRACT_INVALID",
                "The v3 execution contract is not admissible.",
                details={"contract_code": exc.code},
            ) from exc
        if execution.get("schema_version") not in accepted_schema_versions:
            raise DevelopmentInputError(
                "PACK_EXECUTION_SCHEMA_UNSUPPORTED", "The execution contract schema is unsupported."
            )
        slots = execution.get("slots")
        if not isinstance(slots, list) or not slots or execution.get("execution_gaps"):
            raise DevelopmentInputError(
                "PACK_EXECUTION_GAP", "The v3 pack has unresolved execution gaps."
            )
        slot_by_id = {
            str(slot.get("resource_slot_id", "")): slot
            for slot in slots
            if isinstance(slot, dict) and str(slot.get("resource_slot_id", ""))
        }
        if len(slot_by_id) != len(slots):
            raise DevelopmentInputError(
                "PACK_EXECUTION_SLOT_INVALID",
                "Execution slot identifiers must be unique and non-empty.",
            )
        recipes = recipe_manifest.get("recipes")
        recipe_ids = {
            str(recipe.get("recipe_id", ""))
            for recipe in recipes or []
            if isinstance(recipe, dict) and str(recipe.get("recipe_id", ""))
        }
        if not isinstance(recipes, list) or len(recipe_ids) != len(recipes):
            raise DevelopmentInputError(
                "PACK_RECIPE_INVALID", "The local recipe manifest is invalid."
            )
        target: dict[str, Any] = (
            targets["target"] if isinstance(targets.get("target"), dict) else {}
        )
        allowed_dependencies = set(target.get("allowed_dependencies", []) or [])
        route_ids = {
            str(route.get("route_id", ""))
            for route in site.get("routes", [])
            if isinstance(route, dict)
        }
        for slot_id, slot in slot_by_id.items():
            resolution = slot.get("resolution")
            if not isinstance(resolution, dict):
                raise DevelopmentInputError(
                    "PACK_EXECUTION_SLOT_INVALID", "An execution slot has no typed resolution."
                )
            resolution_type = str(resolution.get("resolution_type", ""))
            category = str(slot.get("category", "") or "").casefold()
            route_id = str(slot.get("route_id", "") or "")
            if route_id and route_id not in route_ids:
                raise DevelopmentInputError(
                    "PACK_EXECUTION_ROUTE_INVALID",
                    "An execution slot is outside the admitted route scope.",
                )
            if resolution_type == "local_materialized":
                paths = resolution.get("local_paths")
                if (
                    not isinstance(paths, list)
                    or not paths
                    or any(
                        not isinstance(path, str)
                        or not path
                        or not any(
                            name == path or name.startswith(path.rstrip("/") + "/")
                            for name in package_paths
                        )
                        for path in paths
                    )
                ):
                    raise DevelopmentInputError(
                        "PACK_EXECUTION_LOCAL_PATH_INVALID",
                        "A local execution binding is absent from the admitted archive.",
                    )
            elif resolution_type == "target_package_binding":
                if (
                    str(resolution.get("package_name", "")) not in allowed_dependencies
                    or not isinstance(resolution.get("expected_exports"), list)
                    or not resolution["expected_exports"]
                ):
                    raise DevelopmentInputError(
                        "PACK_EXECUTION_PACKAGE_INVALID",
                        "An execution package binding is not in the target dependency contract.",
                    )
            elif resolution_type == "local_recipe":
                if category in {
                    "image",
                    "photo",
                    "editorial_photo",
                    "portrait",
                    "component",
                    "visual_component",
                }:
                    raise DevelopmentInputError(
                        "PACK_VISUAL_RECIPE_FORBIDDEN",
                        "Image and component slots must use real local material, not recipes.",
                    )
                recipe_id = str(resolution.get("recipe_id", ""))
                recipe = next(
                    (
                        item
                        for item in recipes
                        if isinstance(item, dict) and str(item.get("recipe_id", "")) == recipe_id
                    ),
                    None,
                )
                if recipe is None or str(recipe.get("slot_id", "")) != slot_id:
                    raise DevelopmentInputError(
                        "PACK_RECIPE_DANGLING",
                        "An execution recipe does not bind its declared slot.",
                    )
                local_path = str(recipe.get("local_path", ""))
                if local_path not in package_paths:
                    raise DevelopmentInputError(
                        "PACK_RECIPE_PATH_INVALID", "A recipe file is missing from the archive."
                    )
            elif resolution_type == "delegated_acquisition":
                policy = resolution.get("delegation_policy")
                contract_policy = execution.get("policy", {}).get("delegated_acquisition", {})
                if (
                    execution.get("pack_version") != DELEGATED_PACK_VERSION
                    or not isinstance(policy, dict)
                    or not isinstance(contract_policy, dict)
                    or not contract_policy.get("enabled")
                    or policy.get("selection") != "closed_set_only"
                    or policy.get("llm_may_invent_candidates") is not False
                    or not policy.get("allowed_providers")
                    or int(policy.get("candidate_limit", 0)) <= 0
                ):
                    raise DevelopmentInputError(
                        "PACK_DELEGATION_POLICY_INVALID",
                        "A delegated slot must carry the explicit closed-set acquisition policy.",
                    )
            else:
                raise DevelopmentInputError(
                    "PACK_EXECUTION_SLOT_INVALID",
                    "A v3 execution slot has an unsupported resolution.",
                )
        decisions = ledger.get("resource_decisions")
        if not isinstance(decisions, list):
            raise DevelopmentInputError(
                "PACK_RESOURCE_LEDGER_INVALID", "The v3 resource ledger is invalid."
            )
        ledger_slots = {
            str(item.get("resource_slot_id", ""))
            for item in ledger.get("slots", [])
            if isinstance(item, dict) and str(item.get("resource_slot_id", ""))
        }
        if ledger_slots != set(slot_by_id):
            raise DevelopmentInputError(
                "PACK_RESOURCE_SLOT_MISMATCH",
                "The resource ledger must contain exactly one entry for every execution slot.",
            )
        known_sources = {
            str(decision.get("source_id", ""))
            for decision in decisions
            if isinstance(decision, dict) and str(decision.get("source_id", ""))
        }
        slot_sources = {
            source
            for slot in slots
            if isinstance(slot, dict)
            for source in slot.get("source_ids", [])
        }
        if not known_sources.issubset(slot_sources):
            raise DevelopmentInputError(
                "PACK_RESOURCE_LEDGER_DANGLING", "A known resource decision has no execution slot."
            )
        for route_id, route_resources in route_resource_maps.items():
            if route_id not in route_ids:
                raise DevelopmentInputError(
                    "PACK_ROUTE_RESOURCE_INVALID",
                    "A route resource map is outside the admitted scope.",
                )
            slot_ids = route_resources.get("slot_ids")
            if not isinstance(slot_ids, list) or any(
                str(slot_id) not in slot_by_id for slot_id in slot_ids
            ):
                raise DevelopmentInputError(
                    "PACK_ROUTE_RESOURCE_INVALID",
                    "Route resource maps must reference admitted execution slots.",
                )

    def _extract_verified(self, data: bytes, identity: str) -> None:
        root = (self._root / "admitted" / identity).resolve()
        if not root.is_relative_to(self._root):
            raise DevelopmentInputError(
                "INPUT_ROOT_UNSAFE", "The configured development input root is unsafe."
            )
        if root.exists():
            manifest = root / "manifest.json"
            if manifest.is_file():
                return
            raise DevelopmentInputError(
                "ADMITTED_COPY_INVALID", "The admitted input extraction is incomplete."
            )
        try:
            restore_verified_bundle(data, root, max_bytes=int(self._config.max_uncompressed_bytes))
        except PackageError as exc:
            raise DevelopmentInputError(exc.code, exc.message) from exc


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
