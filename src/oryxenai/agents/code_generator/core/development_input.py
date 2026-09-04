"""Safe fixture/upload admission for standalone Code Generator development."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.core.brief_ingestion import (
    BRIEF_CONTRACT_VERSION,
    BRIEF_ENVELOPE_VERSION,
    CONTENT_FILENAME,
    VISUAL_FILENAME,
    BriefContractError,
    compile_brief_envelope,
    make_brief_envelope,
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
    return path.resolve() if path.is_absolute() else (repository_root() / path).resolve()


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
    """Own configured brief fixtures and immutable two-brief envelopes."""

    def __init__(self, settings: Any) -> None:
        self._settings = settings
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
        try:
            data = self._read_brief_pair(fixture_root)
        except DevelopmentInputError as exc:
            if exc.code != "BRIEF_PAIR_INCOMPLETE":
                raise
            # Keep the checked-in privacy-safe development fixtures useful
            # while their source files are gradually migrated.  This adapter
            # conversion is deterministic and never used for production
            # Build Preparation state.
            data = self._legacy_fixture_briefs(fixture_root)
        return self._store_source(
            mode="fixture",
            source_id=fixture_id,
            filename=f"{fixture_id}-briefs.json",
            data=data,
        )

    def from_upload(self, *, filename: str, mime_type: str, data: bytes) -> AdmittedInputReference:
        normalized_mime = mime_type.split(";", 1)[0].strip().lower()
        if normalized_mime not in {"application/json", "text/json"}:
            raise DevelopmentInputError(
                "UPLOAD_MIME_INVALID",
                "Uploads must use application/json and contain the two Markdown briefs.",
            )
        if (
            not filename
            or Path(filename).name != filename
            or not filename.lower().endswith(".json")
        ):
            raise DevelopmentInputError(
                "UPLOAD_FILENAME_INVALID", "The upload filename must be a safe .json name."
            )
        if len(data) > int(self._config.max_upload_bytes):
            raise DevelopmentInputError(
                "UPLOAD_TOO_LARGE", "The uploaded brief envelope exceeds the configured size limit."
            )
        self._compile(data)
        return self._store_source(
            mode="upload", source_id=_sha256(data), filename=filename, data=data
        )

    def from_build_preparation_briefs(
        self, *, source_id: str, content_markdown: str, visual_markdown: str
    ) -> AdmittedInputReference:
        """Persist one session-owned immutable copy of the two brief strings."""

        try:
            data = make_brief_envelope(content_markdown, visual_markdown)
        except BriefContractError as exc:
            raise self._brief_error(exc) from exc
        if len(data) > int(self._config.max_uncompressed_bytes):
            raise DevelopmentInputError(
                "BRIEFS_TOO_LARGE", "The Build Preparation briefs exceed the configured limit."
            )
        return self._store_source(
            mode="build_preparation_briefs",
            source_id=source_id,
            filename=f"build-preparation-{_safe_filename_part(source_id)}-briefs.json",
            data=data,
        )

    def from_brief_uploads(
        self,
        *,
        content_filename: str,
        content_data: bytes,
        visual_filename: str,
        visual_data: bytes,
    ) -> AdmittedInputReference:
        """Admit two explicit Markdown uploads as one immutable source envelope."""

        if content_filename != CONTENT_FILENAME or visual_filename != VISUAL_FILENAME:
            raise DevelopmentInputError(
                "BRIEF_FILENAME_INVALID",
                f"Uploads must be named {CONTENT_FILENAME} and {VISUAL_FILENAME}.",
            )
        try:
            content = content_data.decode("utf-8-sig")
            visual = visual_data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DevelopmentInputError(
                "BRIEF_ENCODING_INVALID", "Markdown briefs must be UTF-8 encoded."
            ) from exc
        return self.from_build_preparation_briefs(
            source_id=_sha256(content_data + b"\0" + visual_data),
            content_markdown=content,
            visual_markdown=visual,
        )

    def list_build_preparation_packs(self) -> list[dict[str, Any]]:
        """Compatibility name: list local Build Preparation brief pairs newest first."""

        brief_sets: list[dict[str, Any]] = []
        for entry in self._mirror_entries():
            info = self._mirror_pack_info(entry)
            if info is not None:
                brief_sets.append(info)
        brief_sets.sort(key=lambda item: (item["modified_at"], item["brief_dir"]), reverse=True)
        return brief_sets

    def from_build_preparation_mirror(self, pack: str = "latest") -> AdmittedInputReference:
        """Store an immutable copy of a local Build Preparation brief pair."""

        entries = self._mirror_entries()
        if not entries:
            raise DevelopmentInputError(
                "BRIEF_MIRROR_UNAVAILABLE",
                "The Build Preparation mirror has no complete brief pairs.",
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
                    "BRIEF_MIRROR_NO_ELIGIBLE",
                    f"No eligible brief pair exists in the mirror (newest issue: {reason}).",
                )
        else:
            if Path(pack).name != pack:
                raise DevelopmentInputError(
                    "BRIEF_DIR_INVALID",
                    "The brief directory name is not a safe directory name.",
                )
            selected = next((entry for entry in entries if entry.name == pack), None)
            if selected is None:
                raise DevelopmentInputError(
                    "BRIEF_DIR_NOT_FOUND",
                    "The requested brief directory is not in the mirror.",
                )
        info = self._mirror_pack_info(selected)
        if not info["eligible"]:
            raise DevelopmentInputError(
                "BRIEFS_NOT_ADMISSIBLE",
                f"The selected briefs are not admissible ({info.get('issue', 'unknown')}).",
            )
        data = self._read_brief_pair(selected)
        if len(data) > int(self._config.max_uncompressed_bytes):
            raise DevelopmentInputError(
                "BRIEFS_TOO_LARGE", "The mirror brief pair exceeds the configured size limit."
            )
        return self._store_source(
            mode="build_preparation_mirror",
            source_id=selected.name,
            filename=f"{selected.name}-briefs.json",
            data=data,
        )

    def _mirror_entries(self) -> list[Path]:
        configured = _resolve_config_path(self._config.build_preparation_mirror_root)
        roots = [configured]
        # Build Preparation's own fixture/debug output is the canonical local
        # handoff when a deployment overlays the legacy development setting.
        prep_config = getattr(self._settings, "build_preparation", None)
        fixture_output = str(getattr(prep_config, "fixture_output_dir", "") or "").strip()
        if fixture_output:
            roots.append(_resolve_config_path(f"{fixture_output}/build-preparation"))
        entries: dict[str, Path] = {}
        for root in roots:
            if not root.is_dir():
                continue
            for entry in root.iterdir():
                if (
                    entry.is_dir()
                    and (entry / CONTENT_FILENAME).is_file()
                    and (entry / VISUAL_FILENAME).is_file()
                ):
                    entries.setdefault(entry.name, entry)
        return sorted(entries.values(), key=lambda entry: entry.name)

    def _mirror_pack_info(self, entry: Path) -> dict[str, Any]:
        """Return a non-secret validation summary for one mirrored brief pair."""

        content_path = entry / CONTENT_FILENAME
        visual_path = entry / VISUAL_FILENAME
        modified = max(content_path.stat().st_mtime, visual_path.stat().st_mtime)
        size_bytes = content_path.stat().st_size + visual_path.stat().st_size
        issue = ""
        summary: dict[str, Any] = {}
        try:
            _receipt, _projections, summary = self._compile(self._read_brief_pair(entry))
        except (DevelopmentInputError, OSError) as exc:
            issue = (
                f"{exc.code}: {exc.message}"
                if isinstance(exc, DevelopmentInputError)
                else f"unreadable briefs: {type(exc).__name__}"
            )
        info: dict[str, Any] = {
            "brief_dir": entry.name,
            # Keep this transitional display key so existing development UI
            # clients do not break while their labels migrate from pack to briefs.
            "pack_dir": entry.name,
            "size_bytes": size_bytes,
            "modified_at": datetime.fromtimestamp(modified, UTC).isoformat(),
            "source_version": BRIEF_CONTRACT_VERSION,
            "schema_version": BRIEF_ENVELOPE_VERSION,
            "run_id": summary.get("run_id", ""),
            "content_brief_sha256": summary.get("content_brief_sha256", ""),
            "visual_brief_sha256": summary.get("visual_brief_sha256", ""),
            "route_count": summary.get("route_count", 0),
            "section_count": summary.get("section_count", 0),
            "resource_coverage": summary.get("resource_count", 0),
            "component_coverage": summary.get("component_count", 0),
            "navigation_closed": bool(summary.get("navigation_closed", False)),
            "contract_hash": summary.get("contract_hash", ""),
            "eligible": not issue,
        }
        if issue:
            info["issue"] = issue
        info["selection_rank"] = self._pack_rank(info)
        return info

    @staticmethod
    def _pack_rank(info: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
        """Rank complete, richer brief pairs ahead of sparse fixtures."""

        return (
            int(bool(info.get("eligible"))),
            int(bool(info.get("navigation_closed"))),
            int(info.get("route_count", 0)),
            int(info.get("section_count", 0)),
            int(info.get("resource_coverage", 0)),
            int(info.get("component_coverage", 0)),
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
        receipt, projections, _summary = self._compile(self.read(reference))
        if receipt.source_sha256 != reference.source_sha256:
            raise DevelopmentInputError(
                "BRIEF_SOURCE_IDENTITY_MISMATCH",
                "The compiled brief receipt does not match the immutable source copy.",
            )
        return receipt, projections

    def _validate_admitted_data(self, data: bytes) -> tuple[InputReceipt, dict[str, Any], str]:
        receipt, projections, _summary = self._compile(data)
        return receipt, projections, receipt.contract_hash

    def _store_source(
        self, *, mode: str, source_id: str, filename: str, data: bytes
    ) -> AdmittedInputReference:
        receipt, _projections, _summary = self._compile(data)
        digest = _sha256(data)
        relative = Path("inputs") / digest[:2] / f"{digest}.json"
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

        # GenerationWorkspace intentionally consumes an identity-addressed,
        # immutable tree rather than the content-addressed upload path.  The
        # previous ZIP adapter populated ``admitted/<identity>`` by extracting
        # the verified archive; Markdown briefs have no archive to extract.
        # Keep that workspace boundary stable by publishing the exact envelope
        # under the compiled contract identity.  The envelope is only a
        # provenance anchor (resource bytes are acquired separately), but it
        # makes resumed and production generation runs use the same admission
        # contract as legacy fixtures.
        admitted_root = (self._root / "admitted" / receipt.admitted_identity).resolve()
        if not admitted_root.is_relative_to(self._root):
            raise DevelopmentInputError(
                "INPUT_ROOT_UNSAFE", "The configured development input root is unsafe."
            )
        admitted_root.mkdir(parents=True, exist_ok=True)
        admitted_copy = admitted_root / "brief-envelope.json"
        if admitted_copy.exists():
            if not admitted_copy.is_file() or admitted_copy.read_bytes() != data:
                raise DevelopmentInputError(
                    "ADMITTED_COPY_READBACK_FAILED",
                    "The identity-addressed brief copy could not be verified.",
                )
        else:
            partial = admitted_copy.with_suffix(".partial")
            partial.write_bytes(data)
            os.replace(partial, admitted_copy)
            if admitted_copy.read_bytes() != data:
                raise DevelopmentInputError(
                    "ADMITTED_COPY_READBACK_FAILED",
                    "The identity-addressed brief copy could not be verified.",
                )
        return AdmittedInputReference(
            mode=mode,  # type: ignore[arg-type]
            source_id=source_id,
            original_filename=filename,
            source_sha256=digest,
            stored_relative_path=relative.as_posix(),
            size_bytes=len(data),
        )

    def _read_brief_pair(self, root: Path) -> bytes:
        try:
            content = (root / CONTENT_FILENAME).read_text(encoding="utf-8-sig")
            visual = (root / VISUAL_FILENAME).read_text(encoding="utf-8-sig")
            return make_brief_envelope(content, visual)
        except FileNotFoundError as exc:
            raise DevelopmentInputError(
                "BRIEF_PAIR_INCOMPLETE",
                f"A brief source must contain {CONTENT_FILENAME} and {VISUAL_FILENAME}.",
            ) from exc
        except BriefContractError as exc:
            raise self._brief_error(exc) from exc

    def _legacy_fixture_briefs(self, root: Path) -> bytes:
        try:
            site = json.loads((root / "site" / "contract.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DevelopmentInputError(
                "BRIEF_PAIR_INCOMPLETE",
                f"A fixture must contain {CONTENT_FILENAME} and {VISUAL_FILENAME}.",
            ) from exc
        raw_routes = [item for item in site.get("routes", []) if isinstance(item, dict)]
        raw_content = [item for item in site.get("public_content", []) if isinstance(item, dict)]
        routes: list[dict[str, Any]] = []
        sections: list[tuple[str, str, dict[str, Any]]] = []
        for route in raw_routes:
            route_id = str(route.get("route_id", "home"))
            raw_sections: Any = next(
                (
                    item.get("sections", [])
                    for item in raw_content
                    if str(item.get("route_id", "")) == route_id
                ),
                [],
            )
            normalized_sections: list[str] = []
            for section in raw_sections if isinstance(raw_sections, list) else []:
                if not isinstance(section, dict):
                    continue
                section_id = f"{route_id}:{section.get('section_id', 'section')!s}"
                normalized_sections.append(section_id)
                sections.append(
                    (
                        section_id,
                        str(section.get("purpose", "")),
                        section.get("content", {})
                        if isinstance(section.get("content", {}), dict)
                        else {},
                    )
                )
            if normalized_sections:
                routes.append(
                    {
                        "route_id": route_id,
                        "path": str(route.get("path", "/")),
                        "title": str(route.get("title", route_id)),
                        "sections": normalized_sections,
                    }
                )
        if not routes:
            raise DevelopmentInputError("BRIEF_ROUTES_EMPTY", "The fixture has no route content.")
        run_id = f"fixture-{_safe_filename_part(root.name)}"
        content_index = {
            "kind": "content_index",
            "run_id": run_id,
            "content_architect_content_hash": "fixture-content-hash",
            "navigation_contract": {
                "closed": True,
                "allowed_destinations": [
                    *(str(route["route_id"]) for route in routes),
                    *(section_id for section_id, _purpose, _content in sections),
                ],
            },
            "routes": routes,
        }
        content_lines = ["# Fixture Content", "", "```json build-preparation-content-index"]
        content_lines.extend(json.dumps(content_index, indent=2, ensure_ascii=False).splitlines())
        content_lines.extend(["```", ""])
        for section_id, purpose, content in sections:
            content_lines.extend(
                [
                    f"### {section_id}",
                    f"*{purpose or 'Approved fixture section'}*",
                    "",
                    "```json section-content",
                    *json.dumps(content, indent=2, ensure_ascii=False).splitlines(),
                    "```",
                    "",
                ]
            )
        visual_index = {
            "kind": "visual_index",
            "run_id": run_id,
            "target_contract": "react-vite-v1",
            "visual_input_mode": "fixture",
            "routes": [str(route["route_id"]) for route in routes],
            "resources": [],
            "components": [],
            "recommended_dependencies": [],
        }
        visual_lines = [
            "# Fixture Visual & Build Brief",
            "",
            "```json build-preparation-visual-index",
        ]
        visual_lines.extend(json.dumps(visual_index, indent=2, ensure_ascii=False).splitlines())
        visual_lines.extend(
            ["```", "", "Use a restrained, accessible local composition with clear hierarchy."]
        )
        return make_brief_envelope("\n".join(content_lines), "\n".join(visual_lines))

    def _compile(
        self, data: bytes
    ) -> tuple[InputReceipt, dict[str, dict[str, Any]], dict[str, Any]]:
        try:
            receipt, projections, summary = compile_brief_envelope(data)
            return InputReceipt.model_validate(receipt), projections, summary
        except BriefContractError as exc:
            raise self._brief_error(exc) from exc

    @staticmethod
    def _brief_error(exc: BriefContractError) -> DevelopmentInputError:
        details = {
            str(key): value
            for key, value in exc.details.items()
            if isinstance(value, (str, int, float, bool))
        }
        return DevelopmentInputError(exc.code, exc.message, details=details)


def _safe_filename_part(value: str) -> str:
    normalized = "".join(char if char.isalnum() or char in "-_" else "-" for char in value)
    return normalized.strip("-")[:80] or hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
