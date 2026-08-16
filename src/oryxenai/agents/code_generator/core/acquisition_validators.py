"""Deterministic policy and byte validation for Code Generator acquisition."""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from PIL import Image, UnidentifiedImageError

from oryxenai.agents.code_generator.core.development_schemas import (
    PlanDelta,
    ResourceCandidate,
    ResourceLedger,
    ResourceRequest,
    SitePlan,
)


class AcquisitionValidationError(ValueError):
    """A safe, stable policy or resource validation failure."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


_SAFE_VENDOR_PATH = re.compile(r"^src/components/vendor/[a-z0-9_-]+/.+$")
_PROVIDER_BY_CATEGORY = {
    "image": {"pexels", "unsplash", "fixture"},
    "texture": {"pexels", "unsplash", "fixture"},
    "illustration": {"pexels", "unsplash", "fixture"},
    "font": {"google_fonts", "fixture", "local"},
    "icon": {"lucide", "fixture", "local"},
    "component_source": {"shadcn", "magicui", "fixture"},
    "style_primitive": {"shadcn", "magicui", "fixture"},
}


def _setting(settings: Any, name: str, default: Any) -> Any:
    config = getattr(settings, "code_generator_acquisition", None)
    return getattr(config, name, default) if config is not None else default


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _plan_sections(plan: SitePlan, route_id: str) -> set[str]:
    for route in plan.routes:
        if route.route_id == route_id:
            return set(route.section_ids)
    return set()


def _plan_components(plan: SitePlan) -> set[str]:
    contracts = getattr(plan, "shared_component_contracts", [])
    return {str(item.component_id) for item in contracts if getattr(item, "component_id", "")}


def _fact_terms(projections: dict[str, dict[str, Any]] | None) -> set[str]:
    if not projections:
        return set()
    site = projections.get("site/contract.json", {})
    terms: set[str] = set()
    for fact in site.get("facts", []):
        if isinstance(fact, dict):
            terms.update(
                _tokens(" ".join(str(fact.get(key, "")) for key in ("fact_id", "text", "value")))
            )
    return terms


def validate_resource_request(
    value: ResourceRequest,
    *,
    plan: SitePlan,
    ledger_excluding: ResourceLedger | None = None,
    settings: Any = None,
    projections: dict[str, dict[str, Any]] | None = None,
    request_rounds: int = 0,
) -> ResourceRequest:
    """Validate a model/request proposal without performing any side effect."""

    route_ids = {route.route_id for route in plan.routes}
    if value.placement.route_id not in route_ids:
        raise AcquisitionValidationError(
            "REQ_PLACEMENT_UNKNOWN", "The resource request names an unknown route."
        )
    if value.placement.section_id and value.placement.section_id not in _plan_sections(
        plan, value.placement.route_id
    ):
        raise AcquisitionValidationError(
            "REQ_PLACEMENT_UNKNOWN", "The resource request names an unknown section."
        )
    if value.placement.component_id and value.placement.component_id not in _plan_components(plan):
        # Phase 1 plans do not carry component contracts yet. An explicitly named component is
        # still safe when it is a declared shared-system identifier.
        shared = {item for item in plan.shared_systems if item}
        if value.placement.component_id not in shared:
            raise AcquisitionValidationError(
                "REQ_PLACEMENT_UNKNOWN", "The resource request names an unknown component."
            )
    if not value.placement.purpose.strip() or not value.affected_work_unit_ids:
        raise AcquisitionValidationError(
            "REQ_NO_CONCRETE_USE", "Every resource request needs a placement and work unit."
        )
    policy = value.source_constraints.upstream_source_policy.casefold()
    if policy in {"approved_user_media", "user_media"}:
        raise AcquisitionValidationError(
            "REQ_STOCK_SUBSTITUTES_USER_MEDIA",
            "Approved user media cannot be replaced with acquired stock resources.",
        )
    fact_terms = _fact_terms(projections)
    query_terms = set().union(
        *(_tokens(term) for term in value.query.positive_terms + value.query.forbidden_subjects)
    )
    if fact_terms and query_terms.intersection(fact_terms):
        raise AcquisitionValidationError(
            "REQ_IMPLIES_FACT",
            "The resource query overlaps authoritative fact language and cannot create evidence.",
        )
    forbidden = {term.casefold() for term in _setting(settings, "forbidden_subject_terms", [])}
    requested_forbidden = {
        term.casefold() for term in value.query.forbidden_subjects + value.query.positive_terms
    }
    if forbidden.intersection(requested_forbidden):
        raise AcquisitionValidationError(
            "REQ_FORBIDDEN_SUBJECT", "The resource request contains a forbidden subject."
        )
    allowed = set(_PROVIDER_BY_CATEGORY.get(value.category, set()))
    allowed_config = _setting(settings, f"allowlist_{value.category}_providers", None)
    if value.category == "icon":
        allowed_config = [_setting(settings, "allowlist_icon_package", "lucide")]
    if value.category == "component_source":
        allowed_config = _setting(settings, "allowlist_component_registries", ["shadcn", "magicui"])
    if value.category == "style_primitive":
        allowed_config = _setting(
            settings, "allowlist_style_kinds", ["pattern", "token_preset", "helper"]
        )
    if allowed_config:
        allowed = {str(item) for item in allowed_config}
        # Offline fixtures are trusted test inputs, not production providers.
        allowed.add("fixture")
    source_kinds = set(value.source_constraints.allowed_source_kinds)
    if source_kinds and not source_kinds.intersection(allowed):
        raise AcquisitionValidationError(
            "REQ_CATEGORY_POLICY", "The requested category has no configured allowed source."
        )
    existing_hashes = {
        receipt.request_hash
        for receipt in (ledger_excluding.receipts if ledger_excluding is not None else [])
    }
    existing_hashes.update(
        request.request_hash
        for request in (ledger_excluding.requests if ledger_excluding is not None else [])
    )
    if value.request_hash in existing_hashes:
        raise AcquisitionValidationError(
            "REQ_ALREADY_LEDGERED", "The canonical resource request already has a receipt."
        )
    max_bytes = value.technical_constraints.max_bytes
    configured_max = _setting(settings, f"{value.category}_max_bytes", 0)
    if max_bytes < 0 or (configured_max and max_bytes and max_bytes > configured_max):
        raise AcquisitionValidationError(
            "REQ_TARGET_CAPABILITY", "The request exceeds the configured resource byte ceiling."
        )
    if request_rounds > int(_setting(settings, "max_request_rounds", 4)):
        raise AcquisitionValidationError(
            "REQ_ROUND_CEILING", "The acquisition request-round ceiling has been reached."
        )
    return value


def filter_candidates_by_policy(
    candidates: Iterable[ResourceCandidate], request: ResourceRequest
) -> list[ResourceCandidate]:
    """Remove candidates that trusted policy cannot vendor locally."""

    allowed_providers = set(request.source_constraints.allowed_source_kinds)
    result: list[ResourceCandidate] = []
    forbidden = {term.casefold() for term in request.query.forbidden_subjects}
    for candidate in candidates:
        if not candidate.licence.strip():
            continue
        if request.source_constraints.vendoring_required and not any(
            token in candidate.vendoring_policy.casefold()
            for token in ("vendor", "download", "local", "embed", "copy")
        ):
            continue
        if allowed_providers and candidate.provider_key not in allowed_providers:
            continue
        metadata_text = " ".join(
            [candidate.title, candidate.description, *candidate.tags]
        ).casefold()
        if any(term and term in metadata_text for term in forbidden):
            continue
        result.append(candidate)
    return result


def validate_plan_delta(value: PlanDelta, *, plan: SitePlan) -> PlanDelta:
    slot_ids = {slot.slot_id for slot in plan.resource_slots}
    for binding in value.binding_changes:
        binding_id = binding.request_id_or_pack_need_id
        if not binding_id or (
            binding_id not in slot_ids and not re.fullmatch(r"[0-9a-f]{64}", binding_id)
        ):
            raise AcquisitionValidationError(
                "PLAN_DELTA_BINDS_UNKNOWN_SLOT", "The PlanDelta binds an unknown resource slot."
            )
    if any(key not in slot_ids for key in value.placement_detail_changes):
        raise AcquisitionValidationError(
            "PLAN_DELTA_BINDS_UNKNOWN_SLOT", "PlanDelta placement details name an unknown slot."
        )
    if any(not _SAFE_VENDOR_PATH.fullmatch(path) for path in value.added_vendor_paths):
        raise AcquisitionValidationError(
            "PLAN_DELTA_VENDOR_PATH_INVALID",
            "PlanDelta vendor paths are outside the trusted vendor root.",
        )
    # The Phase 2 model contains no fields that can mutate authority. Reject a binding that
    # attempts to smuggle an authoritative change through a placement key.
    if any(
        key.casefold() in {"route_id", "section_id", "fact_id", "section_order", "owned_path"}
        for key in value.placement_detail_changes
    ):
        raise AcquisitionValidationError(
            "PLAN_DELTA_AUTHORITY_VIOLATION", "PlanDelta may change resource bindings only."
        )
    return value


def select_candidate(
    request: ResourceRequest,
    candidates: list[ResourceCandidate],
    *,
    prefer_model: bool = False,
    model_callable: Callable[[dict[str, Any]], dict[str, str]] | None = None,
) -> tuple[str, str]:
    """Select from already policy-filtered textual metadata."""

    if not candidates:
        raise AcquisitionValidationError(
            "NO_POLICY_CANDIDATES", "No candidate survived resource policy."
        )
    if prefer_model and model_callable is not None:
        result = model_callable(
            {
                "request_text": request.model_dump(mode="json"),
                "candidate_summaries": [
                    candidate.model_dump(mode="json") for candidate in candidates
                ],
            }
        )
        selected = str(result.get("selected_id", ""))
        if selected not in {candidate.candidate_id for candidate in candidates}:
            raise AcquisitionValidationError(
                "SCOUT_SELECTION_INVALID", "The resource scout selected an unknown candidate."
            )
        return selected, str(result.get("rationale", "model-selected candidate"))
    positive = set().union(*(_tokens(term) for term in request.query.positive_terms))
    negative = set().union(*(_tokens(term) for term in request.query.negative_terms))
    scored: list[tuple[int, str, ResourceCandidate]] = []
    for candidate in candidates:
        terms = _tokens(" ".join([candidate.title, candidate.description, *candidate.tags]))
        score = len(terms.intersection(positive)) - len(terms.intersection(negative))
        scored.append((score, candidate.candidate_id, candidate))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected_score, _, selected_candidate = scored[0]
    return selected_candidate.candidate_id, f"deterministic metadata overlap score={selected_score}"


def _raw_bytes(value: bytes | bytearray | Path | str) -> bytes:
    if isinstance(value, (str, Path)):
        return Path(value).read_bytes()
    return bytes(value)


def _reject(code: str, message: str) -> None:
    raise AcquisitionValidationError(code, message)


def _safe_archive(data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            total = 0
            seen: set[str] = set()
            for item in archive.infolist():
                name = item.filename.replace("\\", "/")
                if name.startswith("/") or ".." in Path(name).parts or "\x00" in name:
                    _reject("ARCHIVE_PATH_UNSAFE", "The resource archive contains an unsafe path.")
                folded = name.casefold()
                if folded in seen:
                    _reject(
                        "ARCHIVE_CASE_COLLISION", "The resource archive contains duplicate paths."
                    )
                seen.add(folded)
                total += item.file_size
                if total > 4 * 1024 * 1024:
                    _reject(
                        "DECOMP_BOMB", "The resource archive exceeds the decompression ceiling."
                    )
    except zipfile.BadZipFile:
        _reject("ARCHIVE_INVALID", "The resource archive is not a valid ZIP file.")


def inspect_bytes(
    path_or_bytes: bytes | bytearray | Path | str,
    *,
    category: str,
    max_bytes: int | None = None,
) -> dict[str, str | int | float | bool]:
    """Inspect bytes structurally; never inspect pixels or semantic appearance."""

    data = _raw_bytes(path_or_bytes)
    if max_bytes is not None and len(data) > max_bytes:
        _reject("EXCEEDS_MAX_BYTES", "The resource exceeds its configured byte ceiling.")
    digest = hashlib.sha256(data).hexdigest()
    lower = category.casefold()
    if lower in {"image", "texture", "illustration"}:
        if data.startswith(b"<svg") or b"<svg" in data[:512].lower():
            media_type = "image/svg+xml"
            _sanitize_svg(data)
            return {"media_type": media_type, "size": len(data), "sha256": digest, "svg": True}
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                width, height = image.size
                media_type = Image.MIME.get(image.format or "", "")
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as exc:
            code = (
                "DECOMP_BOMB" if isinstance(exc, Image.DecompressionBombError) else "DECODE_FAILED"
            )
            raise AcquisitionValidationError(
                code, "The image bytes could not be decoded within the safety limits."
            ) from exc
        if not media_type:
            _reject("BAD_MAGIC_BYTES", "The image has no recognized media type.")
        return {
            "media_type": media_type,
            "size": len(data),
            "sha256": digest,
            "width": width,
            "height": height,
        }
    if lower == "icon":
        _sanitize_svg(data)
        return {"media_type": "image/svg+xml", "size": len(data), "sha256": digest, "svg": True}
    if lower == "font":
        if not (data.startswith(b"wOFF") or data.startswith(b"wOF2")):
            _reject("BAD_MAGIC_BYTES", "The font is not a WOFF or WOFF2 file.")
        return {
            "media_type": "font/woff2" if data.startswith(b"wOF2") else "font/woff",
            "size": len(data),
            "sha256": digest,
        }
    if lower in {"component_source", "style_primitive"}:
        if data.startswith(b"PK"):
            _safe_archive(data)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AcquisitionValidationError(
                "SOURCE_NOT_UTF8", "The source resource is not UTF-8."
            ) from exc
        if re.search(r"(?:https?://|javascript:|eval\s*\()", text, re.IGNORECASE):
            _reject(
                "SOURCE_REMOTE_OR_DYNAMIC", "The source resource contains remote or dynamic code."
            )
        return {"media_type": "text/plain", "size": len(data), "sha256": digest}
    _reject("CATEGORY_UNSUPPORTED", f"No byte inspector exists for category {category!r}.")
    return {}  # pragma: no cover


def _sanitize_svg(data: bytes) -> None:
    try:
        root = ElementTree.fromstring(data)  # noqa: S314 - bounded SVG is checked before parsing
    except ElementTree.ParseError as exc:
        raise AcquisitionValidationError("SVG_INVALID", "The SVG is not well-formed XML.") from exc
    serialized = data.decode("utf-8", errors="ignore")
    if re.search(
        r"<script|javascript:|on[a-z]+\s*=|<foreignObject|href\s*=\s*['\"]https?", serialized, re.I
    ):
        _reject("SVG_UNSAFE_CONTENT", "The SVG contains scripts, handlers, or external references.")
    if any(element.tag.endswith("image") for element in root.iter()):
        _reject("SVG_EMBEDDED_RASTER", "The SVG contains an embedded raster image.")
